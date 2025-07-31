"""
Bilingual Keyword Extraction Service V2 with unified prompt management.
Uses UnifiedPromptService for YAML-based configuration management.
"""
import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, ClassVar

from src.core.metrics.cache_metrics import cache_metrics
from src.models.keyword_extraction import KeywordExtractionRequest, StandardizedTerm
from src.models.prompt_config import LLMConfig
from src.models.response import IntersectionStats, WarningInfo
from src.services.base import BaseService
from src.services.exceptions import (
    LanguageDetectionError,
    LowConfidenceDetectionError,
    UnsupportedLanguageError,
)
from src.services.keyword_standardizer import KeywordStandardizer
from src.services.language_detection import LanguageValidator
from src.services.language_detection.simple_language_detector import (
    SimplifiedLanguageDetector,
)
from src.services.openai_client import (
    AzureOpenAIClient,
    AzureOpenAIError,
)
from src.services.standardization import MultilingualStandardizer
from src.services.unified_prompt_service import get_unified_prompt_service


class KeywordExtractionServiceV2(BaseService):
    """
    Enhanced keyword extraction service with unified prompt management.

    Key improvements:
    - Uses UnifiedPromptService for YAML-based configuration
    - All LLM parameters come from prompt version files
    - No hardcoded parameters
    """

    SUPPORTED_LANGUAGES: ClassVar = ["en", "zh-TW"]

    def __init__(
        self,
        openai_client: AzureOpenAIClient | None = None,
        prompt_version: str = "latest",
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_parallel_processing: bool = True
    ):
        """Initialize the service with unified prompt management and flexible LLM
        selection."""
        super().__init__()

        # Core services - Use provided client or factory for flexible model selection
        if openai_client:
            self.openai_client = openai_client
            self.logger.info(
                f"Using provided LLM client: {type(openai_client).__name__}"
            )
        else:
            # Use the LLM Factory for dynamic model selection based on configuration
            from src.services.llm_factory import get_llm_client
            self.openai_client = get_llm_client(api_name="keywords")
            self.logger.info(
                f"Using factory-created LLM client: "
                f"{type(self.openai_client).__name__}"
            )

        # Unified prompt service - NEW!
        self.unified_prompt_service = get_unified_prompt_service()
        self.default_prompt_version = prompt_version

        # Language detection - Using simplified detector (only Trad Chinese + English)
        self.language_detector = SimplifiedLanguageDetector()
        self.language_validator = LanguageValidator(self.language_detector)

        # Standardization - Use preloaded instances when available
        try:
            from src.core.dependencies import (
                get_keyword_standardizer,
                get_multilingual_standardizer,
            )
            self.multilingual_standardizer = get_multilingual_standardizer()
            self.legacy_standardizer = get_keyword_standardizer()
            self.logger.info("Using preloaded standardizers from application startup")
        except (RuntimeError, ImportError):
            # Fallback for tests or when dependencies not initialized
            self.multilingual_standardizer = MultilingualStandardizer()
            self.legacy_standardizer = KeywordStandardizer()
            self.logger.info("Created new standardizer instances (fallback mode)")

        # 2-round strategy configuration
        self.keywords_per_round = 25
        self.min_intersection_threshold = 12
        self.supplement_target = 12
        self.max_return_keywords = 16

        # Performance optimization
        self.enable_cache = enable_cache
        self.cache_ttl_minutes = cache_ttl_minutes
        self.enable_parallel_processing = enable_parallel_processing

        # Cache storage
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0

        # Stats tracking
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
            f"Initialized KeywordExtractionServiceV2 with UnifiedPromptService - "
            f"Default version: {prompt_version}, "
            f"Languages: {self.SUPPORTED_LANGUAGES}"
        )

    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the extraction request."""
        request = KeywordExtractionRequest(**data)
        validated_data = request.dict()

        language = validated_data.get('language', 'auto')
        if language not in ["auto", *self.SUPPORTED_LANGUAGES]:
            raise ValueError(
                f"Language '{language}' not supported. "
                f"Supported: {['auto', *self.SUPPORTED_LANGUAGES]}"
            )

        return validated_data

    def _generate_cache_key(
        self, job_description: str, language: str, max_keywords: int,
        include_standardization: bool, prompt_version: str
    ) -> str:
        """Generate a unique cache key."""
        cache_input = (
            f"{job_description}|{language}|{max_keywords}|"
            f"{include_standardization}|{prompt_version}"
        )
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()

    def _get_cached_result(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached result if available."""
        if not self.enable_cache or cache_key not in self._cache:
            return None

        cached_entry = self._cache[cache_key]
        cached_time = cached_entry['timestamp']

        expiry_time = cached_time + timedelta(minutes=self.cache_ttl_minutes)
        if datetime.utcnow() > expiry_time:
            del self._cache[cache_key]
            return None

        return cached_entry['result']

    def _cache_result(self, cache_key: str, result: dict[str, Any]):
        """Cache the extraction result."""
        if not self.enable_cache:
            return

        self._cache[cache_key] = {
            'result': result.copy(),
            'timestamp': datetime.utcnow()
        }

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
        """Process keyword extraction with unified prompt management."""
        start_time = time.time()

        # Extract parameters
        job_description = data['job_description']
        max_keywords = data.get('max_keywords', self.max_return_keywords)
        include_standardization = data.get('include_standardization', True)
        language_param = data.get('language', 'auto')
        prompt_version = data.get('prompt_version', self.default_prompt_version)

        # Initialize language_detection_time to avoid UnboundLocalError
        language_detection_time = 0

        self.logger.info(
            f"Starting keyword extraction V2: "
            f"language={language_param}, version={prompt_version}, "
            f"max_keywords={max_keywords}"
        )

        try:
            # 1. Language detection
            detected_language, language_detection_time = await (
                self._detect_and_validate_language(
                    job_description, language_param
                )
            )

            # 2. Check cache
            cache_key = self._generate_cache_key(
                job_description, detected_language, max_keywords,
                include_standardization, prompt_version
            )

            cache_start = time.time()
            cached_result = self._get_cached_result(cache_key)
            cache_retrieval_time = (time.time() - cache_start) * 1000

            if cached_result is not None:
                processing_time = int((time.time() - start_time) * 1000)
                cached_result = cached_result.copy()
                cached_result['processing_time_ms'] = processing_time
                cached_result['cache_hit'] = True
                cached_result['language_detection_time_ms'] = language_detection_time

                self._cache_hits += 1
                self.extraction_stats["cache_hits"] += 1

                # Track cache hit metrics with token estimates
                cache_metrics.record_cache_access(
                    cache_hit=True,
                    cache_key=cache_key,
                    endpoint="/api/v1/extract-jd-keywords",
                    processing_time_ms=cache_retrieval_time,
                    model="gpt-4o-2",
                    actual_tokens={
                        "input": len(job_description) // 4,  # Rough estimate: 1 token
                        # per 4 chars
                        "output": len(str(cached_result.get('keywords', []))) // 4
                    }
                )

                self.logger.info("Cache hit for keyword extraction")
                return cached_result

            # Cache miss
            self._cache_misses += 1
            self.extraction_stats["cache_misses"] += 1

            # Track cache miss
            cache_metrics.record_cache_access(
                cache_hit=False,
                cache_key=cache_key,
                endpoint="/api/v1/extract-jd-keywords"
            )

            # 3. Execute extraction with YAML configuration
            extraction_result = await self._extract_keywords_with_config(
                job_description,
                detected_language,
                max_keywords,
                include_standardization,
                prompt_version
            )

            # 4. Build result
            processing_time = int((time.time() - start_time) * 1000)

            result = {
                **extraction_result,
                'processing_time_ms': processing_time,
                'detected_language': detected_language,
                'input_language': language_param,
                'language_detection_time_ms': language_detection_time,
                'cache_hit': False
            }

            # 5. Cache result
            self._cache_result(cache_key, result)

            # Track actual OpenAI API token usage for cache miss
            if 'llm_config_used' in extraction_result:
                # More accurate token estimation based on actual extraction
                cache_metrics.record_cache_access(
                    cache_hit=False,
                    cache_key=cache_key,
                    endpoint="/api/v1/extract-jd-keywords",
                    processing_time_ms=processing_time,
                    model="gpt-4o-2",
                    actual_tokens={
                        "input": len(job_description) // 4 + 200,  # JD + prompt
                        # template
                        "output": result.get('keyword_count', 0) * 10  # Estimate per
                        # keyword
                    }
                )

            # 6. Update stats
            self._update_extraction_stats(detected_language, extraction_result)

            self.logger.info(
                f"Extraction completed: keywords={result['keyword_count']}, "
                f"time={processing_time}ms"
            )

            return result

        except UnsupportedLanguageError as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.warning(
                f"Unsupported language detected: {e.detected_language}, "
                f"skipping LLM calls"
            )

            # Track unsupported language event with JD preview
            from src.core.monitoring_service import monitoring_service
            jd_preview = job_description[:100] + (
                "..." if len(job_description) > 100 else ""
            )
            monitoring_service.track_event(
                "UnsupportedLanguageSkipped",
                {
                    "detected_language": e.detected_language,
                    "jd_preview": jd_preview,
                    "jd_length": len(job_description),
                    "requested_language": language_param,
                    "processing_time_ms": processing_time
                }
            )

            # Re-raise the exception to be handled by API endpoint
            raise

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.error(f"Keyword extraction failed: {e!s}")
            raise

    async def _detect_and_validate_language(
        self, text: str, language_param: str
    ) -> tuple[str, int]:
        """Detect and validate language with unified event tracking."""
        start_time = time.time()

        # Initialize tracking variables
        detected_language = None
        language_composition = {}
        decision_reason = ""
        will_process = True
        jd_preview = None

        if language_param != 'auto':
            validation = await self.language_validator.validate_with_detection(
                text, language_param
            )
            if not validation.is_valid:
                self.logger.warning(
                    f"Language validation failed for {language_param}: "
                    f"{validation.errors}"
                )

        try:
            # Get detailed language analysis
            stats = self.language_detector.analyze_language_composition(text)

            # Calculate percentages for tracking
            if stats.total_chars > 0:
                language_composition = {
                    "en_percent": round(
                        (stats.english_chars / stats.total_chars) * 100, 1
                    ),
                    "zh_tw_percent": round(
                        (stats.traditional_chinese_chars / stats.total_chars) * 100, 1
                    ),
                    "zh_cn_percent": round(
                        (stats.simplified_chinese_chars / stats.total_chars) * 100, 1
                    ),
                    "ja_percent": round(
                        (stats.japanese_chars / stats.total_chars) * 100, 1
                    ),
                    "ko_percent": round(
                        (stats.korean_chars / stats.total_chars) * 100, 1
                    ),
                    "es_percent": round(
                        (stats.spanish_chars / stats.total_chars) * 100, 1
                    ),
                    "other_percent": round(
                        (stats.other_chars / stats.total_chars) * 100, 1
                    ),
                }

            detection_result = await self.language_detector.detect_language(text)
            detected_language = detection_result.language

            # Determine decision reason
            # Calculate total unsupported characters
            unsupported_chars = (
                stats.simplified_chinese_chars + stats.japanese_chars +
                stats.korean_chars + stats.spanish_chars + stats.other_chars
            )
            unsupported_ratio = (
                unsupported_chars / stats.total_chars if stats.total_chars > 0 else 0
            )

            if unsupported_ratio > 0.10:
                decision_reason = "unsupported_content"
            elif stats.traditional_chinese_chars > 0:
                # Calculate supported content (EN + zh-TW + numbers/symbols)
                # Note: numbers/symbols are not in total_chars, so
                # supported = total - unsupported
                supported_chars = stats.total_chars - unsupported_chars
                if supported_chars > 0:
                    zh_tw_ratio = stats.traditional_chinese_chars / supported_chars
                    if zh_tw_ratio >= 0.20:
                        decision_reason = "zh_tw_dominant"
                    else:
                        decision_reason = "english_default"
                else:
                    decision_reason = "english_default"
            else:
                decision_reason = "english_default"

            if language_param != 'auto' and language_param != detected_language:
                self.logger.warning(
                    f"Language mismatch: requested {language_param}, detected "
                    f"{detected_language}. Using requested language."
                )
                detected_language = language_param

        except UnsupportedLanguageError as e:
            self.logger.warning(f"Unsupported language detected: {e.detected_language}")
            detected_language = e.detected_language
            will_process = False
            decision_reason = "unsupported_content"
            jd_preview = text[:100] + ("..." if len(text) > 100 else "")

            # Track unified event for unsupported language
            from src.core.monitoring_service import monitoring_service
            monitoring_service.track_event(
                "LanguageDetected",
                {
                    "detected_language": "other",  # Group all unsupported as "other"
                    "language_composition": language_composition,
                    "decision_reason": decision_reason,
                    "will_process": will_process,
                    "requested_language": language_param,
                    "jd_length": len(text),
                    "jd_preview": jd_preview
                }
            )

            raise e

        except (LanguageDetectionError, LowConfidenceDetectionError) as e:
            self.logger.warning(f"Language detection issue: {e!s}")
            detected_language = language_param if language_param != 'auto' else 'en'
            decision_reason = "detection_error_fallback"

        except Exception as e:
            self.logger.error(f"Unexpected language detection error: {e!s}")
            detected_language = language_param if language_param != 'auto' else 'en'
            decision_reason = "detection_error_fallback"

        detection_time = int((time.time() - start_time) * 1000)

        # Track unified event for supported languages
        if detected_language in ["en", "zh-TW"]:
            from src.core.monitoring_service import monitoring_service
            monitoring_service.track_event(
                "LanguageDetected",
                {
                    "detected_language": detected_language,
                    "language_composition": language_composition,
                    "decision_reason": decision_reason,
                    "will_process": will_process,
                    "requested_language": language_param,
                    "jd_length": len(text),
                    "jd_preview": None  # No preview for supported languages
                }
            )

        self.logger.debug(
            f"Language detection: {detected_language} (time: {detection_time}ms)"
        )
        return detected_language, detection_time

    async def _extract_keywords_with_config(
        self,
        job_description: str,
        language: str,
        max_keywords: int,
        include_standardization: bool,
        prompt_version: str
    ) -> dict[str, Any]:
        """
        Execute keyword extraction using configuration from YAML.
        This is the key difference - all LLM parameters come from YAML!
        """
        # 1. Get prompt and LLM config from UnifiedPromptService
        try:
            formatted_prompt, llm_config = (
                self.unified_prompt_service.get_prompt_with_config(
                language=language,
                    version=prompt_version,
                    variables={"job_description": job_description}
                )
            )
        except Exception as e:
            self.logger.error(
                f"Failed to get prompt config for {language}/{prompt_version}: {e!s}"
            )
            raise ValueError(f"Prompt not available: {e!s}") from e

        # 2. Execute 2-round extraction with YAML-based config
        if self.enable_parallel_processing:
            round_start_time = time.time()
            round1_task = asyncio.create_task(
                self._extract_single_round(formatted_prompt, llm_config, round_num=1)
            )
            round2_task = asyncio.create_task(
                self._extract_single_round(formatted_prompt, llm_config, round_num=2)
            )

            round1_keywords, round2_keywords = await asyncio.gather(
                round1_task, round2_task
            )
            round_processing_time = int((time.time() - round_start_time) * 1000)

            self.logger.debug(
                f"Parallel extraction completed in {round_processing_time}ms"
            )
        else:
            round_start_time = time.time()
            round1_keywords = await self._extract_single_round(
                formatted_prompt, llm_config, round_num=1
            )
            round2_keywords = await self._extract_single_round(
                formatted_prompt, llm_config, round_num=2
            )
            round_processing_time = int((time.time() - round_start_time) * 1000)

            self.logger.debug(
                f"Sequential extraction completed in {round_processing_time}ms"
            )

        # 3. Calculate intersection and apply strategy
        intersection = set(round1_keywords) & set(round2_keywords)
        intersection_count = len(intersection)

        # 4. Determine strategy
        if intersection_count >= self.min_intersection_threshold:
            strategy_used = "pure_intersection"
            # Preserve order from round1
            candidate_keywords = [kw for kw in round1_keywords if kw in intersection]
            final_keywords = candidate_keywords[:max_keywords]
            has_warning = False
            warning_message = ""
        else:
            strategy_used = "supplement"
            # Preserve order: intersection first (from round1), then unique from round1,
            # then unique from round2
            ordered_keywords = [kw for kw in round1_keywords if kw in intersection]
            ordered_keywords.extend(
                [kw for kw in round1_keywords if kw not in intersection]
            )
            ordered_keywords.extend(
                [kw for kw in round2_keywords if kw not in round1_keywords]
            )
            all_unique = ordered_keywords

            if len(all_unique) >= self.supplement_target:
                final_keywords = all_unique[:self.supplement_target]
                has_warning = False
                warning_message = ""
            else:
                final_keywords = all_unique
                has_warning = True
                warning_message = (
                    f"僅能提取 {len(all_unique)} 個關鍵字,建議檢查職位描述品質"
                )

        # 5. Apply standardization
        standardized_terms = []
        if include_standardization:
            standardization_result = (
                self.multilingual_standardizer.standardize_keywords(
                    final_keywords, language
                )
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

        # 6. Build stats
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

        warning_info = WarningInfo(
            has_warning=has_warning,
            message=warning_message if has_warning else "",
            expected_minimum=self.supplement_target,
            actual_extracted=len(final_keywords),
            suggestion=(
                "請提供更詳細的技能要求、工作職責或必要條件" if has_warning else ""
            )
        ).dict()

        return {
            'keywords': final_keywords,
            'keyword_count': len(final_keywords),
            'standardized_terms': standardized_terms,
            'confidence_score': min(1.0, intersection_count / self.keywords_per_round),
            'extraction_method': strategy_used,
            'intersection_stats': intersection_stats,
            'warning': warning_info,
            'prompt_version': prompt_version,
            'llm_config_used': {
                'temperature': llm_config.temperature,
                'top_p': llm_config.top_p,
                'seed': llm_config.seed,
                'max_tokens': llm_config.max_tokens
            }
        }

    async def _extract_single_round(
        self, prompt: str, llm_config: LLMConfig, round_num: int
    ) -> list[str]:
        """
        Execute a single round using LLM config from YAML.
        This is the KEY CHANGE - no more hardcoded parameters!
        """
        try:
            # Use parameters from YAML configuration
            response = await self.openai_client.complete_text(
                prompt,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                top_p=llm_config.top_p,
                seed=llm_config.seed + (round_num - 1)  # Vary seed slightly for each
                # round
            )

            keywords = self._parse_keywords_from_response(response)

            self.logger.debug(
                f"Round {round_num}: extracted {len(keywords)} keywords "
                f"(temp={llm_config.temperature}, top_p={llm_config.top_p})"
            )
            return keywords[:self.keywords_per_round]

        except Exception as e:
            self.logger.error(f"Round {round_num} extraction failed: {e!s}")
            raise AzureOpenAIError(
                f"Keyword extraction round {round_num} failed: {e!s}"
            ) from e

    def _parse_keywords_from_response(self, response: str) -> list[str]:
        """Parse keywords from LLM response."""
        try:
            cleaned_response = response.strip()
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(lines[1:-1])

            if cleaned_response.strip().startswith('{'):
                data = json.loads(cleaned_response)
                if 'keywords' in data:
                    return data['keywords']
        except json.JSONDecodeError as e:
            self.logger.debug(
                f"JSON parsing failed: {e!s}, falling back to line parsing"
            )

        lines = response.strip().split('\n')
        keywords = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line in [
                '{', '}', '"keywords": [', ']', '```', '```json',
                '```javascript object notation'
            ]:
                continue

            line = line.lstrip('- •*1234567890.')
            line = line.strip()
            line = line.strip('"').strip("'").rstrip(',')

            if line and len(line) > 1 and not line.startswith('"keywords"'):
                keywords.append(line)

        return keywords

    def _update_extraction_stats(self, language: str, result: dict[str, Any]):
        """Update internal statistics."""
        self.extraction_stats["total_extractions"] += 1

        if language in self.extraction_stats["language_breakdown"]:
            self.extraction_stats["language_breakdown"][language] += 1

        strategy = result.get('extraction_method', 'unknown')
        if strategy in self.extraction_stats["strategy_breakdown"]:
            self.extraction_stats["strategy_breakdown"][strategy] += 1

        if result.get('warning', {}).get('has_warning', False):
            self.extraction_stats["warning_count"] += 1

    def get_service_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        cache_hit_rate = 0.0
        total_requests = self._cache_hits + self._cache_misses
        if total_requests > 0:
            cache_hit_rate = self._cache_hits / total_requests

        # Get available versions
        available_versions = {
            lang: self.unified_prompt_service.list_versions(lang)
            for lang in self.SUPPORTED_LANGUAGES
        }

        return {
            "service_name": "KeywordExtractionServiceV2",
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
            "prompt_management": {
                "default_version": self.default_prompt_version,
                "available_versions": available_versions,
                "uses_yaml_config": True
            }
        }

    def clear_cache(self):
        """Clear all cached results."""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Cleared cache of {cache_size} entries")

    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information."""
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
            "cache_hit_rate": round(
                self._cache_hits / max(1, self._cache_hits + self._cache_misses), 3
            ),
            "ttl_minutes": self.cache_ttl_minutes,
            "enabled": self.enable_cache
        }


# Global service instance cache
_keyword_extraction_service_v2 = None


def get_keyword_extraction_service_v2(
    llm_client: AzureOpenAIClient | None = None,
    prompt_version: str = "latest",
    enable_cache: bool = True,
    cache_ttl_minutes: int = 60,
    enable_parallel_processing: bool = True
) -> KeywordExtractionServiceV2:
    """
    Get singleton instance of KeywordExtractionServiceV2.

    This version uses UnifiedPromptService for YAML-based configuration.
    Supports dynamic LLM selection through the llm_client parameter.

    Args:
        llm_client: Optional LLM client. If not provided, uses factory default.
        prompt_version: Prompt version to use.
        enable_cache: Whether to enable caching.
        cache_ttl_minutes: Cache TTL in minutes.
        enable_parallel_processing: Whether to enable parallel processing.

    Returns:
        KeywordExtractionServiceV2 instance
    """
    global _keyword_extraction_service_v2

    # For simplicity, create new instance when different client is provided
    # In production, might want more sophisticated caching strategy
    if (_keyword_extraction_service_v2 is None or
        _keyword_extraction_service_v2.enable_cache != enable_cache or
        llm_client is not None):
        _keyword_extraction_service_v2 = KeywordExtractionServiceV2(
            openai_client=llm_client,
            prompt_version=prompt_version,
            enable_cache=enable_cache,
            cache_ttl_minutes=cache_ttl_minutes,
            enable_parallel_processing=enable_parallel_processing
        )

    return _keyword_extraction_service_v2
