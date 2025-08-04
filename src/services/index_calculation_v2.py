"""
Index Calculation Service V2 with enhanced performance and caching.

Key improvements over V1:
- In-memory LRU caching with TTL
- Parallel processing using Python 3.11 TaskGroup
- Comprehensive service statistics
- Enhanced monitoring and error handling
- Backward-compatible API interface
"""
import asyncio
import hashlib
import logging
import math
import re
import time
from datetime import datetime, timedelta
from typing import Any, Union

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.core.utils import stable_percentage_round
from src.services.base import BaseService
from src.services.embedding_client import get_azure_embedding_client
from src.services.exceptions import ServiceError
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
)
from src.services.text_processing import clean_html_text

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: Any, ttl_minutes: int = 60):
        self.value = value
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class IndexCalculationServiceV2(BaseService):
    """
    Enhanced index calculation service with caching and parallel processing.

    Features:
    - In-memory LRU caching with configurable TTL
    - Parallel processing for embeddings and keyword analysis
    - Comprehensive performance metrics and statistics
    - Python 3.11 TaskGroup for improved error handling
    - Backward-compatible API interface
    """

    def __init__(
        self,
        embedding_client=None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        cache_max_size: int = 1000,
        enable_parallel_processing: bool = True
    ):
        """Initialize the V2 service with enhanced features."""
        super().__init__()

        # Dependencies
        self.embedding_client = embedding_client or get_azure_embedding_client()

        # Configuration
        self.enable_cache = enable_cache
        self.cache_ttl_minutes = cache_ttl_minutes
        self.cache_max_size = cache_max_size
        self.enable_parallel_processing = enable_parallel_processing

        # Cache storage with LRU eviction
        self._cache: dict[str, CacheEntry] = {}
        self._cache_access_order: list[str] = []  # For LRU tracking

        # Service statistics
        self.calculation_stats = {
            "total_calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_processing_time_ms": 0.0,
            "total_processing_time_ms": 0.0,
            "error_count": 0,
            "average_similarity_score": 0.0,
            "total_similarity_score": 0.0,
            "average_keyword_coverage": 0.0,
            "total_keyword_coverage": 0.0
        }

        # Cache performance metrics
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }

        self.logger.info(
            f"Initialized IndexCalculationServiceV2 - "
            f"cache_enabled={enable_cache}, "
            f"parallel_processing={enable_parallel_processing}, "
            f"cache_ttl={cache_ttl_minutes}m"
        )

    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate input data for index calculation.

        Args:
            data: Input data dictionary

        Returns:
            Validated data dictionary

        Raises:
            ValueError: If validation fails
        """
        # Extract required fields
        resume = data.get("resume", "")
        job_description = data.get("job_description", "")
        keywords = data.get("keywords", [])

        # Validate required fields
        if not resume or not isinstance(resume, str):
            raise ValueError("Resume must be a non-empty string")

        if not job_description or not isinstance(job_description, str):
            raise ValueError("Job description must be a non-empty string")

        if not keywords:
            raise ValueError("Keywords must be provided")

        # Validate text lengths
        resume_length = len(resume)
        jd_length = len(job_description)
        total_length = resume_length + jd_length

        # Check minimum length
        if total_length < 100:
            raise ValueError("Combined resume and job description text is too short (minimum 100 characters)")

        # Check individual minimum lengths
        if resume_length < 10:
            raise ValueError("Resume is too short (minimum 10 characters)")

        if jd_length < 10:
            raise ValueError("Job description is too short (minimum 10 characters)")

        # Check maximum lengths (500KB limit)
        max_length = 500 * 1024  # 500KB
        if resume_length > max_length:
            raise ValueError(f"Resume is too long (maximum {max_length} characters)")

        if jd_length > max_length:
            raise ValueError(f"Job description is too long (maximum {max_length} characters)")

        # Validate keywords format
        if isinstance(keywords, str):
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
            if not keyword_list:
                raise ValueError("No valid keywords found in string")
            data["keywords"] = keyword_list
        elif isinstance(keywords, list):
            if not all(isinstance(k, str) and k.strip() for k in keywords):
                raise ValueError("All keywords must be non-empty strings")
        else:
            raise ValueError("Keywords must be a list of strings or comma-separated string")

        return data

    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Process index calculation with validated data.

        Args:
            data: Validated input data

        Returns:
            Calculation results
        """
        resume = data["resume"]
        job_description = data["job_description"]
        keywords = data["keywords"]
        include_timing = data.get("include_timing", False)

        return await self.calculate_index(
            resume=resume,
            job_description=job_description,
            keywords=keywords,
            include_timing=include_timing
        )

    def _generate_cache_key(
        self,
        text: str,
        cache_type: str = "embedding"
    ) -> str:
        """
        Generate cache key using SHA256 hash.

        Args:
            text: Input text for caching
            cache_type: Type of cache (embedding, similarity, coverage)

        Returns:
            SHA256 hash as cache key
        """
        # Normalize text for consistent caching
        normalized_text = self._normalize_text(text)
        cache_input = f"{cache_type}:{normalized_text}"
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()

    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent cache keys."""
        # Clean HTML and normalize whitespace
        cleaned = clean_html_text(text)
        normalized = re.sub(r'\s+', ' ', cleaned.strip().lower())
        return normalized

    def _get_cached_result(self, cache_key: str) -> Any | None:
        """
        Get cached result if available and not expired.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached result or None if not found/expired
        """
        if not self.enable_cache or cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]

        # Check expiration
        if entry.is_expired():
            self._remove_from_cache(cache_key)
            self._cache_stats["evictions"] += 1
            return None

        # Update LRU order
        self._update_cache_access(cache_key)
        self._cache_stats["hits"] += 1
        self.calculation_stats["cache_hits"] += 1

        return entry.value

    def _cache_result(self, cache_key: str, result: Any):
        """
        Cache result with LRU eviction policy.

        Args:
            cache_key: Key to store result under
            result: Result to cache
        """
        if not self.enable_cache:
            return

        # Check cache size and evict if necessary
        if len(self._cache) >= self.cache_max_size:
            self._evict_lru()

        # Store new entry
        self._cache[cache_key] = CacheEntry(result, self.cache_ttl_minutes)
        self._cache_access_order.append(cache_key)
        self._cache_stats["size"] = len(self._cache)

        # Periodic cleanup
        if len(self._cache) % 100 == 0:
            self._cleanup_expired_entries()

    def _update_cache_access(self, cache_key: str):
        """Update LRU access order for cache key."""
        if cache_key in self._cache_access_order:
            self._cache_access_order.remove(cache_key)
        self._cache_access_order.append(cache_key)

    def _remove_from_cache(self, cache_key: str):
        """Remove key from cache and access order."""
        if cache_key in self._cache:
            del self._cache[cache_key]
        if cache_key in self._cache_access_order:
            self._cache_access_order.remove(cache_key)
        self._cache_stats["size"] = len(self._cache)

    def _evict_lru(self):
        """Evict least recently used cache entry."""
        if self._cache_access_order:
            lru_key = self._cache_access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                self._cache_stats["evictions"] += 1
                self._cache_stats["size"] = len(self._cache)

    def _cleanup_expired_entries(self):
        """Remove expired cache entries."""
        current_time = datetime.utcnow()
        expired_keys = []

        for key, entry in self._cache.items():
            if current_time > entry.expires_at:
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_from_cache(key)
            self._cache_stats["evictions"] += 1

        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def _get_or_compute_embedding(self, text: str) -> list[float]:
        """
        Get embedding from cache or compute if not cached.

        Args:
            text: Text to get embedding for

        Returns:
            Embedding vector
        """
        cache_key = self._generate_cache_key(text, "embedding")

        # Try cache first
        cached_embedding = self._get_cached_result(cache_key)
        if cached_embedding is not None:
            return cached_embedding

        # Cache miss - compute embedding
        self._cache_stats["misses"] += 1
        self.calculation_stats["cache_misses"] += 1

        # Create embedding
        try:
            embeddings = await self.embedding_client.create_embeddings([text])
            embedding = embeddings[0]
        except AzureOpenAIRateLimitError as e:
            # Handle rate limit errors
            raise ServiceError("Azure OpenAI rate limit exceeded") from e
        except AzureOpenAIAuthError as e:
            # Handle authentication errors
            raise ServiceError("Azure OpenAI authentication failed") from e
        except AzureOpenAIServerError as e:
            # Handle server errors
            raise ServiceError("Azure OpenAI server error") from e
        except AzureOpenAIError as e:
            # Handle other Azure OpenAI errors
            raise ServiceError(f"Azure OpenAI service error: {e}") from e
        except Exception as e:
            # Handle unexpected errors
            raise ServiceError(f"Failed to create embeddings: {e}") from e

        # Cache the result
        self._cache_result(cache_key, embedding)

        return embedding

    async def _compute_embeddings_parallel(
        self,
        resume: str,
        job_description: str
    ) -> tuple[list[float], list[float]]:
        """
        Compute embeddings for resume and job description in parallel.

        Args:
            resume: Resume text
            job_description: Job description text

        Returns:
            Tuple of (resume_embedding, job_embedding)
        """
        if self.enable_parallel_processing:
            # Use asyncio.gather instead of TaskGroup for simpler error handling
            try:
                resume_embedding, job_embedding = await asyncio.gather(
                    self._get_or_compute_embedding(resume),
                    self._get_or_compute_embedding(job_description),
                    return_exceptions=False
                )
                return resume_embedding, job_embedding
            except Exception as e:
                # If parallel processing fails, log and fall back to sequential
                self.logger.warning(f"Parallel embedding computation failed: {e}, falling back to sequential")
                resume_embedding = await self._get_or_compute_embedding(resume)
                job_embedding = await self._get_or_compute_embedding(job_description)
                return resume_embedding, job_embedding
        else:
            # Sequential execution
            resume_embedding = await self._get_or_compute_embedding(resume)
            job_embedding = await self._get_or_compute_embedding(job_description)
            return resume_embedding, job_embedding

    def _calculate_similarity(
        self,
        resume_embedding: list[float],
        job_embedding: list[float]
    ) -> tuple[int, int]:
        """
        Calculate cosine similarity and apply sigmoid transformation.

        Args:
            resume_embedding: Resume embedding vector
            job_embedding: Job description embedding vector

        Returns:
            Tuple of (raw_similarity_percentage, transformed_similarity_percentage)
        """
        # Calculate cosine similarity
        resume_vec = np.array(resume_embedding).reshape(1, -1)
        job_vec = np.array(job_embedding).reshape(1, -1)

        raw_similarity = float(cosine_similarity(resume_vec, job_vec)[0][0])

        # Apply sigmoid transformation
        settings = get_settings()
        transformed_similarity = self._sigmoid_transform(
            raw_similarity,
            settings.sigmoid_x0,
            settings.sigmoid_k
        )

        # Convert to percentages
        raw_percentage = stable_percentage_round(raw_similarity)
        transformed_percentage = stable_percentage_round(transformed_similarity)

        return raw_percentage, transformed_percentage

    def _sigmoid_transform(
        self,
        x: float,
        x0: float = 0.373,
        k: float = 15.0
    ) -> float:
        """
        Apply sigmoid transformation to similarity score.

        Args:
            x: Raw similarity score (0-1)
            x0: Sigmoid center point
            k: Sigmoid steepness

        Returns:
            Transformed score (0-1)
        """
        try:
            return 1 / (1 + math.exp(-k * (x - x0)))
        except OverflowError:
            return 1.0 if x > x0 else 0.0

    def _analyze_keyword_coverage(
        self,
        resume_text: str,
        keywords: Union[list[str], str]
    ) -> dict[str, Any]:
        """
        Analyze keyword coverage in resume text.

        Args:
            resume_text: Resume text (plain text or HTML)
            keywords: List of keywords or comma-separated string

        Returns:
            Dictionary containing coverage analysis
        """
        # Clean HTML if present
        resume_text = clean_html_text(resume_text)

        # Handle empty inputs
        if not keywords or not resume_text:
            return {
                "total_keywords": 0,
                "covered_count": 0,
                "coverage_percentage": 0,
                "covered_keywords": [],
                "missed_keywords": []
            }

        # Convert keywords to list if string
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        settings = get_settings()

        # Prepare resume text for matching
        resume_search_text = (
            resume_text.lower()
            if not settings.keyword_match_case_sensitive
            else resume_text
        )

        covered = []
        missed = []

        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            # Prepare keyword for matching
            search_keyword = (
                keyword.lower()
                if not settings.keyword_match_case_sensitive
                else keyword
            )

            # Try exact word boundary match
            found = bool(re.search(rf'\b{re.escape(search_keyword)}\b', resume_search_text))

            # Try plural matching if enabled and not found
            if not found and settings.enable_plural_matching:
                # Check if keyword ends with 's' and try without it
                if search_keyword.endswith('s') and len(search_keyword) > 1:
                    singular = search_keyword[:-1]
                    found = bool(re.search(rf'\b{re.escape(singular)}\b', resume_search_text))
                # Or check if we can add 's' to match plural
                elif not search_keyword.endswith('s'):
                    plural = search_keyword + 's'
                    found = bool(re.search(rf'\b{re.escape(plural)}\b', resume_search_text))

            if found:
                covered.append(keyword)
            else:
                missed.append(keyword)

        # Calculate statistics
        total = len([k for k in keywords if k.strip()])
        covered_count = len(covered)
        # Use stable rounding for percentage calculation
        percentage = stable_percentage_round(covered_count / total) if total else 0

        return {
            "total_keywords": total,
            "covered_count": covered_count,
            "coverage_percentage": percentage,
            "covered_keywords": covered,
            "missed_keywords": missed
        }

    async def calculate_index(
        self,
        resume: str,
        job_description: str,
        keywords: Union[list[str], str],
        include_timing: bool = False
    ) -> dict[str, Any]:
        """
        Calculate complete index including similarity and keyword coverage.

        Args:
            resume: Resume content (HTML or plain text)
            job_description: Job description (HTML or plain text)
            keywords: Keywords list or comma-separated string
            include_timing: Whether to include timing breakdown

        Returns:
            Dictionary containing calculation results
        """
        start_time = time.time()
        timing_breakdown = {}

        try:
            # Track timing for validation
            validation_start = time.time()

            # Validate inputs first
            # Check for empty inputs
            if not resume or not isinstance(resume, str):
                raise ValueError("Resume must be a non-empty string")

            if not job_description or not isinstance(job_description, str):
                raise ValueError("Job description must be a non-empty string")

            if not keywords:
                raise ValueError("Keywords must be provided")

            # Validate text lengths
            resume_length = len(resume)
            jd_length = len(job_description)
            total_length = resume_length + jd_length

            # Check minimum length
            if total_length < 100:
                raise ValueError("Combined resume and job description text is too short (minimum 100 characters)")

            # Check individual minimum lengths
            if resume_length < 10:
                raise ValueError("Resume is too short (minimum 10 characters)")

            if jd_length < 10:
                raise ValueError("Job description is too short (minimum 10 characters)")

            # Check maximum lengths (500KB limit)
            max_length = 500 * 1024  # 500KB
            if resume_length > max_length:
                raise ValueError(f"Resume is too long (maximum {max_length} characters)")

            if jd_length > max_length:
                raise ValueError(f"Job description is too long (maximum {max_length} characters)")

            if include_timing:
                timing_breakdown["validation_ms"] = round(
                    (time.time() - validation_start) * 1000, 2
                )

            # Parallel processing phase
            parallel_start = time.time()

            # Compute embeddings (method handles parallel vs sequential internally)
            resume_embedding, job_embedding = await self._compute_embeddings_parallel(
                resume, job_description
            )
            
            # Analyze keyword coverage synchronously (it's fast)
            keyword_coverage = self._analyze_keyword_coverage(resume, keywords)

            if include_timing:
                timing_breakdown["embedding_generation_ms"] = round(
                    (time.time() - parallel_start) * 1000, 2
                )

            # Calculate similarity (depends on embeddings)
            similarity_start = time.time()
            raw_similarity, transformed_similarity = self._calculate_similarity(
                resume_embedding, job_embedding
            )

            if include_timing:
                timing_breakdown["similarity_calculation_ms"] = round(
                    (time.time() - similarity_start) * 1000, 2
                )
                timing_breakdown["keyword_analysis_ms"] = 0  # Included in parallel phase

            # Calculate total processing time
            total_time = time.time() - start_time
            processing_time_ms = round(total_time * 1000, 2)

            if include_timing:
                timing_breakdown["total_ms"] = processing_time_ms

            # Update statistics
            self._update_calculation_stats(
                processing_time_ms,
                transformed_similarity,
                keyword_coverage["coverage_percentage"]
            )

            # Check if this was a cache hit (at least one embedding was cached)
            cache_hit = self._cache_stats["hits"] > 0

            # Track metrics
            monitoring_service.track_event(
                "IndexCalculationV2Completed",
                {
                    "raw_similarity": raw_similarity,
                    "transformed_similarity": transformed_similarity,
                    "keyword_coverage": keyword_coverage["coverage_percentage"],
                    "processing_time_ms": processing_time_ms,
                    "cache_hit": cache_hit,
                    "parallel_processing": self.enable_parallel_processing
                }
            )

            result = {
                "raw_similarity_percentage": raw_similarity,
                "similarity_percentage": transformed_similarity,
                "keyword_coverage": keyword_coverage,
                "processing_time_ms": processing_time_ms,
                "cache_hit": cache_hit
            }

            # Add timing breakdown only in development or if requested
            if include_timing:
                result["timing_breakdown"] = timing_breakdown
            else:
                result["timing_breakdown"] = {}  # Always include for Bubble.io compatibility

            return result

        except ValueError as e:
            # Re-raise ValueError directly for input validation errors
            self.calculation_stats["error_count"] += 1
            self.logger.error(f"Validation error in index calculation: {e}")
            raise
        except Exception as e:
            self.calculation_stats["error_count"] += 1
            self.logger.error(f"Index calculation failed: {e}")
            raise ServiceError(f"Index calculation failed: {e}") from e

    def _update_calculation_stats(
        self,
        processing_time_ms: float,
        similarity_score: int,
        coverage_percentage: int
    ):
        """Update internal calculation statistics."""
        self.calculation_stats["total_calculations"] += 1
        self.calculation_stats["total_processing_time_ms"] += processing_time_ms
        self.calculation_stats["total_similarity_score"] += similarity_score
        self.calculation_stats["total_keyword_coverage"] += coverage_percentage

        # Calculate averages
        total_calcs = self.calculation_stats["total_calculations"]
        self.calculation_stats["average_processing_time_ms"] = round(
            self.calculation_stats["total_processing_time_ms"] / total_calcs, 2
        )
        self.calculation_stats["average_similarity_score"] = round(
            self.calculation_stats["total_similarity_score"] / total_calcs, 1
        )
        self.calculation_stats["average_keyword_coverage"] = round(
            self.calculation_stats["total_keyword_coverage"] / total_calcs, 1
        )

    def get_service_stats(self) -> dict[str, Any]:
        """
        Get comprehensive service statistics.

        Returns:
            Dictionary containing service statistics
        """
        # Calculate cache hit rate
        cache_hit_rate = 0.0
        if self.calculation_stats["total_calculations"] > 0:
            cache_hit_rate = (
                self.calculation_stats["cache_hits"] /
                self.calculation_stats["total_calculations"]
            )

        return {
            "service_name": "IndexCalculationServiceV2",
            "calculation_stats": {
                "total_calculations": self.calculation_stats["total_calculations"],
                "average_processing_time_ms": self.calculation_stats["average_processing_time_ms"],
                "cache_hit_rate": round(cache_hit_rate, 3),
                "error_count": self.calculation_stats["error_count"],
                "average_similarity_score": self.calculation_stats["average_similarity_score"],
                "average_keyword_coverage": self.calculation_stats["average_keyword_coverage"]
            },
            "cache_performance": {
                "enabled": self.enable_cache,
                "hit_rate": round(cache_hit_rate, 3),
                "total_hits": self._cache_stats["hits"],
                "total_misses": self._cache_stats["misses"],
                "cache_size": self._cache_stats["size"],
                "max_size": self.cache_max_size,
                "ttl_minutes": self.cache_ttl_minutes,
                "evictions": self._cache_stats["evictions"]
            },
            "performance_optimizations": {
                "parallel_processing_enabled": self.enable_parallel_processing,
                "cache_enabled": self.enable_cache,
                "cache_ttl_minutes": self.cache_ttl_minutes,
                "cache_size": self._cache_stats["size"]
            }
        }

    def clear_cache(self):
        """Clear all cached results."""
        cache_size = len(self._cache)
        self._cache.clear()
        self._cache_access_order.clear()
        self._cache_stats["size"] = 0
        self.logger.info(f"Cleared cache of {cache_size} entries")

    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information."""
        current_time = datetime.utcnow()
        active_entries = 0
        expired_entries = 0

        for entry in self._cache.values():
            if current_time <= entry.expires_at:
                active_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "cache_hit_rate": round(
                self._cache_stats["hits"] / max(1, self._cache_stats["hits"] + self._cache_stats["misses"]), 3
            ),
            "ttl_minutes": self.cache_ttl_minutes,
            "enabled": self.enable_cache,
            "max_size": self.cache_max_size,
            "evictions": self._cache_stats["evictions"]
        }


# Global service instance (following the pattern used in other services)
_index_calculation_service_v2: IndexCalculationServiceV2 | None = None


def get_index_calculation_service_v2() -> IndexCalculationServiceV2:
    """
    Get or create the global IndexCalculationServiceV2 instance.

    Returns:
        IndexCalculationServiceV2 instance
    """
    global _index_calculation_service_v2
    if _index_calculation_service_v2 is None:
        _index_calculation_service_v2 = IndexCalculationServiceV2()
    return _index_calculation_service_v2
