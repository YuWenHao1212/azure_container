"""
Bilingual Keyword Extraction Service with 2-round intersection strategy.
Supports English and Traditional Chinese with language consistency.
Implements Work Item #343 and bilingual requirements.

Performance Optimizations:
- Parallel processing for Round 1 and Round 2 execution (~50% speed improvement)
- Caching mechanism for identical text results (100x speed improvement for repeated requests)
"""
import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any

from src.models.keyword_extraction import KeywordExtractionRequest, StandardizedTerm
from src.models.response import IntersectionStats, WarningInfo
from src.services.base import BaseService
from src.services.exceptions import (
    LanguageDetectionError,
    LowConfidenceDetectionError,
    UnsupportedLanguageError,
    create_unsupported_language_response,
)
from src.services.keyword_standardizer import KeywordStandardizer
from src.services.language_detection import (
    BilingualPromptManager,
    LanguageDetectionService,
    LanguageValidator,
)
from src.services.openai_client import (
    AzureOpenAIClient,
    AzureOpenAIError,
    get_azure_openai_client,
)
from src.services.openai_client_gpt41 import (
    AzureOpenAIGPT41Client,
    get_gpt41_mini_client,
)
from src.services.standardization import MultilingualStandardizer


class KeywordExtractionService(BaseService):
    """
    Bilingual keyword extraction service using 2-round intersection strategy.
    
    Features:
    - Language detection (en/zh-TW only)
    - Language-specific prompt management
    - Multilingual keyword standardization
    - 2-round intersection strategy for consistency
    - Warning system for low-quality extractions
    - Parallel processing for Round 1 and Round 2 (~50% speed improvement)
    - Caching mechanism for identical text results (100x speed improvement)
    """
    
    SUPPORTED_LANGUAGES = ["en", "zh-TW"]
    
    def __init__(
        self,
        openai_client: AzureOpenAIClient | AzureOpenAIGPT41Client | None = None,
        prompt_version: str = "latest",
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_parallel_processing: bool = True,
        use_gpt41_mini: bool = True
    ):
        """Initialize the bilingual service with all dependencies."""
        super().__init__()
        
        # Core services - use GPT-4.1 mini if enabled and no client provided
        if openai_client is None:
            if use_gpt41_mini:
                try:
                    self.openai_client = get_gpt41_mini_client()
                    self.logger.info("Using GPT-4.1 mini Japan East for keyword extraction")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize GPT-4.1 mini client: {e}. Falling back to GPT-4o-2")
                    self.openai_client = get_azure_openai_client()
            else:
                self.openai_client = get_azure_openai_client()
        else:
            self.openai_client = openai_client
        
        # Bilingual components
        self.language_detector = LanguageDetectionService()
        self.language_validator = LanguageValidator(self.language_detector)
        self.prompt_manager = BilingualPromptManager()
        self.multilingual_standardizer = MultilingualStandardizer()
        
        # Legacy standardizer for backward compatibility
        self.legacy_standardizer = KeywordStandardizer()
        
        # 2-round strategy configuration
        self.keywords_per_round = 25  # LLM extracts 25 keywords per round
        self.min_intersection_threshold = 12  # Minimum intersection for pure strategy
        self.supplement_target = 12  # Target keywords for supplement strategy  
        self.max_return_keywords = 16  # Maximum API response keywords
        
        # Performance optimization configuration
        self.enable_cache = enable_cache
        self.cache_ttl_minutes = cache_ttl_minutes
        self.enable_parallel_processing = enable_parallel_processing
        
        # Cache storage for identical text results
        self._cache = {}  # {cache_key: {result, timestamp}}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Performance tracking
        self.extraction_stats = {
            "total_extractions": 0,
            "language_breakdown": {"en": 0, "zh-TW": 0},
            "strategy_breakdown": {"pure_intersection": 0, "supplement": 0},
            "warning_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "parallel_processing_enabled": enable_parallel_processing,
            "cache_enabled": enable_cache
        }
        
        self.logger.info(
            f"Initialized Bilingual KeywordExtractionService - "
            f"Languages: {self.SUPPORTED_LANGUAGES}, "
            f"Keywords per round: {self.keywords_per_round}, "
            f"Cache enabled: {enable_cache}, "
            f"Parallel processing: {enable_parallel_processing}"
        )
    
    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the bilingual extraction request."""
        # Validate using Pydantic model with language parameter
        request = KeywordExtractionRequest(**data)
        validated_data = request.dict()
        
        # Additional language validation
        language = validated_data.get('language', 'auto')
        if language not in ['auto'] + self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{language}' not supported. Supported: {['auto'] + self.SUPPORTED_LANGUAGES}")
        
        return validated_data
    
    def _generate_cache_key(self, job_description: str, language: str, max_keywords: int, 
                           include_standardization: bool, prompt_version: str) -> str:
        """
        Generate a unique cache key for the given parameters.
        
        Args:
            job_description: Job description text
            language: Detected/specified language
            max_keywords: Maximum keywords to return
            include_standardization: Whether to apply standardization
            prompt_version: Prompt version to use
            
        Returns:
            Cache key string
        """
        # Create a string representation of all parameters that affect the result
        cache_input = f"{job_description}|{language}|{max_keywords}|{include_standardization}|{prompt_version}"
        
        # Generate SHA256 hash for consistent, compact key
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> dict[str, Any] | None:
        """
        Get cached result if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached result or None if not available/expired
        """
        if not self.enable_cache or cache_key not in self._cache:
            return None
        
        cached_entry = self._cache[cache_key]
        cached_time = cached_entry['timestamp']
        
        # Check if cache entry is still valid
        expiry_time = cached_time + timedelta(minutes=self.cache_ttl_minutes)
        if datetime.utcnow() > expiry_time:
            # Cache expired, remove it
            del self._cache[cache_key]
            return None
        
        return cached_entry['result']
    
    def _cache_result(self, cache_key: str, result: dict[str, Any]):
        """
        Cache the extraction result.
        
        Args:
            cache_key: Cache key to store under
            result: Extraction result to cache
        """
        if not self.enable_cache:
            return
        
        # Store result with timestamp
        self._cache[cache_key] = {
            'result': result.copy(),
            'timestamp': datetime.utcnow()
        }
        
        # Clean expired entries periodically (every 100 requests)
        if len(self._cache) % 100 == 0:
            self._cleanup_expired_cache()
    
    def _cleanup_expired_cache(self):
        """Remove expired cache entries."""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, entry in self._cache.items():
            expiry_time = entry['timestamp'] + timedelta(minutes=self.cache_ttl_minutes)
            if current_time > expiry_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Process bilingual keyword extraction using 2-round intersection strategy.
        Supports language detection, language-specific processing, caching, and parallel processing.
        """
        start_time = time.time()
        
        # Extract parameters
        job_description = data['job_description']
        max_keywords = data.get('max_keywords', self.max_return_keywords)
        include_standardization = data.get('include_standardization', True)
        language_param = data.get('language', 'auto')
        prompt_version = data.get('prompt_version', 'latest')
        
        self.logger.info(
            f"Starting bilingual keyword extraction: "
            f"language={language_param}, max_keywords={max_keywords}, "
            f"job_description_length={len(job_description)}"
        )
        
        try:
            # 1. Language detection and validation
            detected_language, language_detection_time = await self._detect_and_validate_language(
                job_description, language_param
            )
            
            # 2. Check cache first (after language detection for accurate cache key)
            cache_key = self._generate_cache_key(
                job_description, detected_language, max_keywords, 
                include_standardization, prompt_version
            )
            
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                # Cache hit - return cached result with updated timing
                processing_time = int((time.time() - start_time) * 1000)
                cached_result = cached_result.copy()  # Don't modify original cached data
                cached_result['processing_time_ms'] = processing_time
                cached_result['cache_hit'] = True
                cached_result['language_detection_time_ms'] = language_detection_time
                
                # Update cache statistics
                self._cache_hits += 1
                self.extraction_stats["cache_hits"] += 1
                
                self.logger.info(
                    f"Cache hit for keyword extraction: "
                    f"language={detected_language}, processing_time={processing_time}ms (cached), "
                    f"cache_key={cache_key[:16]}..."
                )
                
                return cached_result
            
            # Cache miss - proceed with full extraction
            self._cache_misses += 1
            self.extraction_stats["cache_misses"] += 1
            
            # 3. Execute language-aware 2-round extraction
            extraction_result = await self._extract_keywords_bilingual(
                job_description, 
                detected_language,
                max_keywords, 
                include_standardization,
                prompt_version
            )
            
            # 4. Calculate total processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            # 5. Build final result
            result = {
                **extraction_result,
                'processing_time_ms': processing_time,
                'detected_language': detected_language,
                'input_language': language_param,
                'language_detection_time_ms': language_detection_time,
                'cache_hit': False
            }
            
            # 6. Cache the result for future requests
            self._cache_result(cache_key, result)
            
            # 7. Update statistics
            self._update_extraction_stats(detected_language, extraction_result)
            
            self.logger.info(
                f"Bilingual extraction completed: "
                f"language={detected_language}, processing_time={processing_time}ms, "
                f"final_keywords={result['keyword_count']}, "
                f"intersection_size={result['intersection_stats']['intersection_count']}, "
                f"standardized_terms={len(result.get('standardized_terms', []))}, "
                f"cache_key={cache_key[:16]}..."
            )
            
            return result
        
        except UnsupportedLanguageError as e:
            # Return structured error response for unsupported languages
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.warning(f"Unsupported language request: {e.detected_language}")
            
            # Create error response but don't raise exception
            error_response = create_unsupported_language_response(e)
            error_response['data']['processing_time_ms'] = processing_time
            return error_response['data']  # Return data part for consistency
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Bilingual keyword extraction failed: {str(e)}")
            raise
    
    async def _detect_and_validate_language(self, text: str, language_param: str) -> tuple[str, int]:
        """
        Detect and validate language for the input text.
        
        Args:
            text: Input text for language detection
            language_param: Language parameter from request
            
        Returns:
            Tuple of (detected_language, detection_time_ms)
        """
        start_time = time.time()
        
        if language_param != 'auto':
            # Language explicitly specified
            # Still validate the text is compatible
            validation = await self.language_validator.validate_with_detection(text, language_param)
            if not validation.is_valid:
                # If validation fails, use detection anyway
                self.logger.warning(f"Language validation failed for {language_param}: {validation.errors}")
        
        # Perform language detection
        try:
            detection_result = await self.language_detector.detect_language(text)
            detected_language = detection_result.language
            
            # If explicit language specified, use it (with warning if mismatch)
            if language_param != 'auto' and language_param != detected_language:
                self.logger.warning(
                    f"Language mismatch: requested {language_param}, detected {detected_language}. "
                    f"Using requested language."
                )
                detected_language = language_param
        
        except UnsupportedLanguageError as e:
            # Language detected but not supported - this should be an error response
            self.logger.warning(f"Unsupported language detected: {e.detected_language}")
            raise e
                
        except (LanguageDetectionError, LowConfidenceDetectionError) as e:
            # Detection failed or low confidence - use fallback
            self.logger.warning(f"Language detection issue: {str(e)}")
            detected_language = language_param if language_param != 'auto' else 'en'
            
        except Exception as e:
            self.logger.error(f"Unexpected language detection error: {str(e)}")
            # Fallback to explicit language or default to English
            detected_language = language_param if language_param != 'auto' else 'en'
        
        detection_time = int((time.time() - start_time) * 1000)
        
        self.logger.debug(f"Language detection: {detected_language} (time: {detection_time}ms)")
        return detected_language, detection_time
    
    async def _extract_keywords_bilingual(
        self, 
        job_description: str, 
        language: str,
        max_keywords: int, 
        include_standardization: bool,
        prompt_version: str
    ) -> dict[str, Any]:
        """
        Execute bilingual keyword extraction using 2-round intersection strategy.
        
        Args:
            job_description: Job description text
            language: Detected/specified language
            max_keywords: Maximum keywords to return
            include_standardization: Whether to apply standardization
            prompt_version: Prompt version to use
            
        Returns:
            Dictionary with extraction results
        """
        # 1. Get language-specific prompt
        try:
            formatted_prompt = self.prompt_manager.format_prompt(
                language, prompt_version, job_description
            )
        except Exception as e:
            self.logger.error(f"Failed to get prompt for {language}: {str(e)}")
            raise ValueError(f"Prompt not available for language: {language}")
        
        # 2. Execute 2-round extraction (parallel or sequential)
        if self.enable_parallel_processing:
            # Parallel execution for ~50% speed improvement
            round_start_time = time.time()
            round1_task = asyncio.create_task(self._extract_single_round(formatted_prompt, round_num=1))
            round2_task = asyncio.create_task(self._extract_single_round(formatted_prompt, round_num=2))
            
            # Wait for both rounds to complete
            round1_keywords, round2_keywords = await asyncio.gather(round1_task, round2_task)
            round_processing_time = int((time.time() - round_start_time) * 1000)
            
            self.logger.debug(f"Parallel round extraction completed in {round_processing_time}ms")
        else:
            # Sequential execution (original behavior)
            round_start_time = time.time()
            round1_keywords = await self._extract_single_round(formatted_prompt, round_num=1)
            round2_keywords = await self._extract_single_round(formatted_prompt, round_num=2)
            round_processing_time = int((time.time() - round_start_time) * 1000)
            
            self.logger.debug(f"Sequential round extraction completed in {round_processing_time}ms")
        
        # 3. Calculate intersection and apply strategy
        intersection = set(round1_keywords) & set(round2_keywords)
        intersection_count = len(intersection)
        
        # 4. Determine strategy and select keywords
        if intersection_count >= self.min_intersection_threshold:
            # Pure intersection strategy
            strategy_used = "pure_intersection"
            candidate_keywords = list(intersection)
            final_keywords = candidate_keywords[:max_keywords]
            has_warning = False
            warning_message = ""
            
        else:
            # Supplement strategy
            strategy_used = "supplement"
            all_unique = list(set(round1_keywords) | set(round2_keywords))
            
            if len(all_unique) >= self.supplement_target:
                final_keywords = all_unique[:self.supplement_target]
                has_warning = False
                warning_message = ""
            else:
                # Insufficient keywords - warning case
                final_keywords = all_unique
                has_warning = True
                warning_message = f"僅能提取 {len(all_unique)} 個關鍵字，建議檢查職位描述品質"
        
        # 5. Apply standardization if requested
        standardized_terms = []
        if include_standardization:
            standardization_result = self.multilingual_standardizer.standardize_keywords(
                final_keywords, language
            )
            final_keywords = standardization_result.standardized_keywords
            standardized_terms = [
                StandardizedTerm(
                    original=mapping['original'],
                    standardized=mapping['standardized'], 
                    method=mapping['method']
                ).dict()
                for mapping in standardization_result.mappings
            ]
        
        # 6. Build intersection statistics
        intersection_stats = IntersectionStats(
            intersection_count=intersection_count,
            round1_count=len(round1_keywords),
            round2_count=len(round2_keywords),
            total_available=len(set(round1_keywords) | set(round2_keywords)),
            final_count=len(final_keywords),
            supplement_count=max(0, len(final_keywords) - intersection_count),
            strategy_used=strategy_used,
            warning=has_warning,
            warning_message=warning_message
        ).dict()
        
        # 7. Build warning info
        warning_info = WarningInfo(
            has_warning=has_warning,
            message=warning_message if has_warning else "",
            expected_minimum=self.supplement_target,
            actual_extracted=len(final_keywords),
            suggestion="請提供更詳細的技能要求、工作職責或必要條件" if has_warning else ""
        ).dict()
        
        return {
            'keywords': final_keywords,
            'keyword_count': len(final_keywords),
            'standardized_terms': standardized_terms,
            'confidence_score': min(1.0, intersection_count / self.keywords_per_round),
            'extraction_method': strategy_used,
            'intersection_stats': intersection_stats,
            'warning': warning_info,
            'prompt_version': prompt_version
        }
    
    async def _extract_single_round(self, prompt: str, round_num: int) -> list[str]:
        """
        Execute a single round of keyword extraction.
        
        Args:
            prompt: Formatted prompt for LLM
            round_num: Round number for logging
            
        Returns:
            List of extracted keywords
        """
        try:
            # Time the LLM call
            llm_start = time.time()
            
            # Use complete_text for simple extraction with optimal parameters
            response = await self.openai_client.complete_text(
                prompt,
                temperature=0.0,  # Zero temperature for maximum consistency
                max_tokens=1000,
                top_p=0.1,  # Low top_p for focused output (0.1 showed best results)
                seed=42  # Fixed seed for deterministic output
            )
            
            llm_time = (time.time() - llm_start) * 1000
            
            # Parse keywords from response
            keywords = self._parse_keywords_from_response(response)
            
            self.logger.debug(f"Round {round_num}: LLM call took {llm_time:.2f}ms, extracted {len(keywords)} keywords")
            return keywords[:self.keywords_per_round]  # Ensure exactly 25 keywords
            
        except Exception as e:
            self.logger.error(f"Round {round_num} extraction failed: {str(e)}")
            raise AzureOpenAIError(f"Keyword extraction round {round_num} failed: {str(e)}")
    
    def _parse_keywords_from_response(self, response: str) -> list[str]:
        """
        Parse keywords from LLM response.
        
        Args:
            response: Raw LLM response
            
        Returns:
            List of parsed keywords
        """
        # Try JSON format first
        try:
            # Clean response first - remove any markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith('```'):
                # Remove markdown code block markers
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(lines[1:-1])
            
            if cleaned_response.strip().startswith('{'):
                data = json.loads(cleaned_response)
                if 'keywords' in data:
                    return data['keywords']
        except json.JSONDecodeError as e:
            self.logger.debug(f"JSON parsing failed: {str(e)}, falling back to line parsing")
        
        # Fall back to line-by-line parsing
        lines = response.strip().split('\n')
        keywords = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip JSON markers
            if line in ['{', '}', '"keywords": [', ']', '```', '```json', '```javascript object notation']:
                continue
                
            # Remove common prefixes and formatting
            line = line.lstrip('- •*1234567890.')
            line = line.strip()
            
            # Remove quotes and trailing commas
            line = line.strip('"').strip("'").rstrip(',')
            
            # Skip if line is too short or looks like a JSON artifact
            if line and len(line) > 1 and not line.startswith('"keywords"'):
                keywords.append(line)
        
        return keywords
    
    def _update_extraction_stats(self, language: str, result: dict[str, Any]):
        """Update internal statistics tracking."""
        self.extraction_stats["total_extractions"] += 1
        
        if language in self.extraction_stats["language_breakdown"]:
            self.extraction_stats["language_breakdown"][language] += 1
        
        strategy = result.get('extraction_method', 'unknown')
        if strategy in self.extraction_stats["strategy_breakdown"]:
            self.extraction_stats["strategy_breakdown"][strategy] += 1
        
        if result.get('warning', {}).get('has_warning', False):
            self.extraction_stats["warning_count"] += 1
    
    def get_service_stats(self) -> dict[str, Any]:
        """Get service statistics for monitoring."""
        cache_hit_rate = 0.0
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            cache_hit_rate = self._cache_hits / total_requests
        
        return {
            "service_name": "BilingualKeywordExtractionService",
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "extraction_stats": self.extraction_stats.copy(),
            "performance_optimizations": {
                "parallel_processing_enabled": self.enable_parallel_processing,
                "cache_enabled": self.enable_cache,
                "cache_ttl_minutes": self.cache_ttl_minutes,
                "cache_size": len(self._cache),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": round(cache_hit_rate, 3)
            },
            "multilingual_standardizer_stats": self.multilingual_standardizer.get_all_standardization_stats(),
            "language_detector_ready": self.language_detector is not None,
            "prompt_manager_ready": self.prompt_manager is not None
        }
    
    def clear_cache(self):
        """Clear all cached results. Useful for testing or memory management."""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Cleared cache of {cache_size} entries")
    
    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information for debugging."""
        current_time = datetime.utcnow()
        active_entries = 0
        expired_entries = 0
        
        for entry in self._cache.values():
            expiry_time = entry['timestamp'] + timedelta(minutes=self.cache_ttl_minutes)
            if current_time <= expiry_time:
                active_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "cache_hit_rate": round(self._cache_hits / max(1, self._cache_hits + self._cache_misses), 3),
            "ttl_minutes": self.cache_ttl_minutes,
            "enabled": self.enable_cache
        }


# Global service instance cache
_keyword_extraction_service = None


def get_keyword_extraction_service(
    prompt_version: str = "latest",
    enable_cache: bool = True,
    cache_ttl_minutes: int = 60,
    enable_parallel_processing: bool = True,
    use_gpt41_mini: bool = True
) -> KeywordExtractionService:
    """
    Get a singleton instance of KeywordExtractionService with performance optimizations.
    
    Args:
        prompt_version: Prompt version to use
        enable_cache: Enable caching for identical text (default: True)
        cache_ttl_minutes: Cache time-to-live in minutes (default: 60)
        enable_parallel_processing: Enable parallel Round 1/2 processing (default: True)
        use_gpt41_mini: Use GPT-4.1 mini Japan East for better performance (default: True)
    
    Returns:
        KeywordExtractionService: Configured service instance with optimizations
    """
    global _keyword_extraction_service
    
    # For testing: always create new instance if cache setting changed
    if (_keyword_extraction_service is None or 
        _keyword_extraction_service.enable_cache != enable_cache):
        _keyword_extraction_service = KeywordExtractionService(
            prompt_version=prompt_version,
            enable_cache=enable_cache,
            cache_ttl_minutes=cache_ttl_minutes,
            enable_parallel_processing=enable_parallel_processing,
            use_gpt41_mini=use_gpt41_mini
        )
    
    return _keyword_extraction_service


async def get_keyword_extraction_service_async(
    prompt_version: str = "latest",
    enable_cache: bool = True,
    cache_ttl_minutes: int = 60,
    enable_parallel_processing: bool = True,
    use_gpt41_mini: bool = True
) -> KeywordExtractionService:
    """
    Async version of get_keyword_extraction_service for API endpoints.
    
    Args:
        prompt_version: Prompt version to use
        enable_cache: Enable caching for identical text (default: True)
        cache_ttl_minutes: Cache time-to-live in minutes (default: 60)
        enable_parallel_processing: Enable parallel Round 1/2 processing (default: True)
        use_gpt41_mini: Use GPT-4.1 mini Japan East for better performance (default: True)
    
    Returns:
        KeywordExtractionService: Configured service instance with optimizations
    """
    return get_keyword_extraction_service(
        prompt_version=prompt_version,
        enable_cache=enable_cache,
        cache_ttl_minutes=cache_ttl_minutes,
        enable_parallel_processing=enable_parallel_processing,
        use_gpt41_mini=use_gpt41_mini
    )


# Create default service instance
keyword_service = get_keyword_extraction_service()