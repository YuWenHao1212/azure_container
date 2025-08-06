"""
Combined Analysis Service V2 for Azure Container API.

Unified service for index calculation and gap analysis with optimized performance.
Key component of the V2 refactoring with resource pooling and parallel processing.
"""
import asyncio
import logging
import os
import time
from typing import Any, Optional

from src.services.base import BaseService
from src.services.gap_analysis_v2 import GapAnalysisServiceV2
from src.services.index_calculation_v2 import IndexCalculationServiceV2
from src.services.resource_pool_manager import ResourcePoolManager
from src.utils.adaptive_retry import AdaptiveRetryStrategy
from src.utils.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class PartialFailureError(Exception):
    """Exception for partial failures with available data."""

    def __init__(self, message: str, partial_data: dict[str, Any], details: Optional[dict] = None):
        super().__init__(message)
        self.partial_data = partial_data
        self.details = details or {}


class CombinedAnalysisServiceV2(BaseService):
    """
    Unified analysis service V2 with performance optimizations.

    Key improvements:
    1. Resource pool management for connection reuse
    2. Intelligent parallel processing with shared embeddings
    3. Adaptive retry strategies
    4. Partial result support for improved reliability
    5. Context-aware gap analysis using index results

    Target Performance:
    - P50 response time: < 2 seconds (from 5-6 seconds)
    - P95 response time: < 4 seconds (from 10-12 seconds)
    - Resource efficiency: 90% reduction in initialization overhead
    """

    def __init__(
        self,
        index_service: Optional[IndexCalculationServiceV2] = None,
        gap_service: Optional[GapAnalysisServiceV2] = None,
        resource_pool: Optional[ResourcePoolManager] = None,
        enable_partial_results: Optional[bool] = None
    ):
        """
        Initialize V2 combined analysis service.

        Args:
            index_service: Index calculation service V2 instance
            gap_service: Gap analysis service V2 instance
            resource_pool: Resource pool manager instance
            enable_partial_results: Enable partial result support
        """
        super().__init__()

        # Service dependencies
        self.index_service = index_service or IndexCalculationServiceV2()
        self.gap_service = gap_service or GapAnalysisServiceV2()

        # Resource management
        pool_config = FeatureFlags.get_resource_pool_config()
        self.resource_pool = resource_pool or ResourcePoolManager(**pool_config)

        # Adaptive retry strategy
        self.retry_strategy = AdaptiveRetryStrategy() if FeatureFlags.ADAPTIVE_RETRY_ENABLED else None

        # Configuration
        self.enable_partial_results = (
            enable_partial_results if enable_partial_results is not None
            else FeatureFlags.ENABLE_PARTIAL_RESULTS
        )

        # Service statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "partial_successes": 0,
            "complete_failures": 0,
            "avg_response_time_ms": 0,
            "resource_pool_hits": 0,
            "parallel_efficiency": 0
        }

        # Performance tracking
        self._response_times = []
        self._max_history = 100  # Keep last 100 response times

    async def analyze(
        self,
        resume: str,
        job_description: str,
        keywords: list[str],
        language: str = "en",
        analysis_options: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Execute combined analysis with V2 optimizations.

        Args:
            resume: Resume content (HTML or plain text)
            job_description: Job description content
            keywords: List of keywords to analyze
            language: Output language (en or zh-TW)
            analysis_options: Additional analysis options

        Returns:
            Combined analysis results with index calculation and gap analysis

        Raises:
            PartialFailureError: When partial results are available
            Exception: When complete failure occurs
        """
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # Execute parallel analysis with resource pooling
            result = await self._execute_parallel_analysis(
                resume, job_description, keywords, language, analysis_options
            )

            # Success - update statistics
            self.stats["successful_requests"] += 1
            self._update_response_time_stats(time.time() - start_time)

            return result

        except Exception as e:
            if self.enable_partial_results:
                # Try to return partial results
                try:
                    partial_result = await self._handle_partial_failure(
                        e, resume, job_description, keywords, language
                    )
                    self.stats["partial_successes"] += 1
                    return partial_result
                except Exception as fallback_error:
                    # Complete failure
                    logger.warning(f"Partial result fallback also failed: {fallback_error}")

            self.stats["complete_failures"] += 1
            logger.error(f"Combined analysis failed completely: {e}")
            raise

    async def _execute_parallel_analysis(
        self,
        resume: str,
        job_description: str,
        keywords: list[str],
        language: str,
        analysis_options: Optional[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Execute analysis using three-phase parallel processing approach.

        Phase 1: Parallel embedding generation (shared)
        Phase 2: Index calculation with embeddings
        Phase 3: Context-aware gap analysis
        """
        phase_timings = {}

        # Phase 1: Generate embeddings using resource pool
        phase1_start = time.time()

        # Check if resource pool is enabled (for E2E tests)
        if os.getenv('RESOURCE_POOL_ENABLED', 'true').lower() == 'false':
            # Direct embedding generation without resource pool
            await self._generate_embeddings_parallel(
                None, resume, job_description
            )
        else:
            # Use resource pool for production
            async with self.resource_pool.get_client() as client:
                await self._generate_embeddings_parallel(
                    client, resume, job_description
                )
                self.stats["resource_pool_hits"] += 1

        phase_timings["embedding_generation"] = time.time() - phase1_start

        # Phase 2: Index calculation with pre-computed embeddings
        phase2_start = time.time()
        if self.retry_strategy:
            index_result = await self.retry_strategy.execute_with_retry(
                lambda: self.index_service.calculate_index(
                    resume=resume,
                    job_description=job_description,
                    keywords=keywords
                ),
                error_classifier=self._classify_index_error,
                get_retry_after=self._get_retry_after_from_error
            )
        else:
            # Direct call without retry
            index_result = await self.index_service.calculate_index(
                resume=resume,
                job_description=job_description,
                keywords=keywords
            )

        phase_timings["index_calculation"] = time.time() - phase2_start

        # Phase 3: Context-aware gap analysis
        phase3_start = time.time()
        if self.retry_strategy:
            gap_result = await self.retry_strategy.execute_with_retry(
                lambda: self.gap_service.analyze_with_context(
                    resume=resume,
                    job_description=job_description,
                    index_result=index_result,
                    language=language,
                    options=analysis_options
                ),
                error_classifier=self._classify_gap_error,
                get_retry_after=self._get_retry_after_from_error
            )
        else:
            gap_result = await self.gap_service.analyze_with_context(
                resume=resume,
                job_description=job_description,
                index_result=index_result,
                language=language,
                options=analysis_options
            )

        phase_timings["gap_analysis"] = time.time() - phase3_start

        # Calculate parallel processing efficiency
        total_sequential_time = sum(phase_timings.values())
        total_actual_time = time.time() - (
            phase3_start - phase_timings["embedding_generation"] - phase_timings["index_calculation"]
        )
        efficiency = 1 - (total_actual_time / total_sequential_time) if total_sequential_time > 0 else 0
        self.stats["parallel_efficiency"] = efficiency

        # Combine results
        return {
            "index_calculation": index_result,
            "gap_analysis": gap_result,
            "metadata": {
                "version": "2.0",
                "language_detected": language,
                "processing_approach": "parallel_optimized",
                "phase_timings_ms": {
                    phase: round(timing * 1000, 2)
                    for phase, timing in phase_timings.items()
                },
                "parallel_efficiency": round(efficiency * 100, 1),
                "resource_pool_used": True
            }
        }

    async def _generate_embeddings_parallel(
        self,
        client: Any,
        resume: str,
        job_description: str
    ) -> dict[str, list[float]]:
        """
        Generate embeddings in parallel using the provided client.

        Args:
            client: OpenAI client from resource pool
            resume: Resume text for embedding
            job_description: Job description text for embedding

        Returns:
            Dict with resume and job_description embeddings
        """
        # Clean texts for embedding (remove HTML, normalize)
        clean_resume = self._clean_text_for_embedding(resume)
        clean_job_desc = self._clean_text_for_embedding(job_description)

        # Generate embeddings in parallel
        async with asyncio.TaskGroup() as tg:
            resume_task = tg.create_task(
                self._create_embedding(client, clean_resume)
            )
            job_task = tg.create_task(
                self._create_embedding(client, clean_job_desc)
            )

        return {
            "resume": resume_task.result(),
            "job_description": job_task.result()
        }

    async def _create_embedding(self, client: Any, text: str) -> list[float]:
        """
        Create embedding using the provided text.

        Args:
            client: OpenAI client from resource pool (not used for embeddings)
            text: Text to embed

        Returns:
            Embedding vector
        """
        # For embeddings, we use the existing embedding service directly
        # since embeddings are handled by a specialized service, not LLM Factory
        from src.services.embedding_client import get_azure_embedding_client

        embedding_client = get_azure_embedding_client()
        async with embedding_client:
            embeddings = await embedding_client.create_embeddings([text])
            return embeddings[0]

    def _clean_text_for_embedding(self, text: str) -> str:
        """
        Clean text for embedding generation (remove HTML, normalize).

        Args:
            text: Raw text (may contain HTML)

        Returns:
            Cleaned text suitable for embedding
        """
        # Import here to avoid circular imports
        from src.services.text_processing import clean_html_text
        return clean_html_text(text)

    def _classify_index_error(self, error: Exception) -> str:
        """Classify index calculation errors for adaptive retry."""
        # Check error type first
        if isinstance(error, ValueError):
            return "validation"
        elif isinstance(error, asyncio.TimeoutError):
            return "timeout"

        error_msg = str(error).lower()

        if "embedding" in error_msg or "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"
        elif "rate" in error_msg and "limit" in error_msg:
            return "rate_limit"
        elif "empty" in error_msg or "invalid" in error_msg:
            return "empty_fields"
        else:
            return "general"

    def _classify_gap_error(self, error: Exception) -> str:
        """Classify gap analysis errors for adaptive retry."""
        # Check error type first
        if isinstance(error, ValueError):
            return "validation"
        elif isinstance(error, asyncio.TimeoutError):
            return "timeout"

        error_msg = str(error).lower()

        if "empty" in error_msg or "missing" in error_msg:
            return "empty_fields"
        elif "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"
        elif "rate" in error_msg and "limit" in error_msg:
            return "rate_limit"
        else:
            return "general"

    def _get_retry_after_from_error(self, error: Exception) -> Optional[int]:
        """
        Extract Retry-After value from error (Azure OpenAI rate limit errors).

        Args:
            error: Exception that may contain retry-after information

        Returns:
            Retry-after value in seconds, or None if not found
        """
        # Check if error has response attribute (from OpenAI SDK)
        if hasattr(error, 'response') and hasattr(error.response, 'headers'):
            retry_after = error.response.headers.get('Retry-After')
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    logger.warning(f"Invalid Retry-After header value: {retry_after}")

        # Check error message for retry-after information
        error_msg = str(error)
        import re
        match = re.search(r'retry[- ]after[:\s]+(\d+)', error_msg, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    async def _handle_partial_failure(
        self,
        error: Exception,
        resume: str,
        job_description: str,
        keywords: list[str],
        language: str
    ) -> dict[str, Any]:
        """
        Handle partial failure by attempting to return index results only.

        Args:
            error: Original error that caused failure
            resume: Resume content
            job_description: Job description content
            keywords: Keywords list
            language: Target language

        Returns:
            Partial results with index calculation only

        Raises:
            PartialFailureError: With partial data available
        """
        partial_result = {
            "index_calculation": None,
            "gap_analysis": None,
            "partial_failure": True,
            "error_details": {
                "message": str(error),
                "type": type(error).__name__,
                "fallback_attempted": True
            }
        }

        try:
            # Attempt index calculation only
            partial_result["index_calculation"] = await self.index_service.calculate_index(
                resume, job_description, keywords
            )

            logger.warning(f"Returning partial result - index only. Error: {error}")

            raise PartialFailureError(
                f"Gap analysis failed but index calculation succeeded: {error}",
                partial_result,
                {"attempted_fallback": True}
            )

        except Exception as index_error:
            logger.error(f"Index calculation also failed during partial recovery: {index_error}")
            # Complete failure - let original error bubble up
            raise error from None

    def _update_response_time_stats(self, response_time: float):
        """Update response time statistics."""
        # Add to history (keep last N)
        self._response_times.append(response_time)
        if len(self._response_times) > self._max_history:
            self._response_times.pop(0)

        # Update average
        self.stats["avg_response_time_ms"] = round(
            sum(self._response_times) / len(self._response_times) * 1000, 2
        )

    def get_service_stats(self) -> dict[str, Any]:
        """
        Get comprehensive service statistics for monitoring.

        Returns:
            Dict containing service statistics and performance metrics
        """
        # Get component stats
        resource_pool_stats = (
            self.resource_pool.get_stats()
            if os.getenv('RESOURCE_POOL_ENABLED', 'true').lower() != 'false'
            else {"pool_stats": {}, "efficiency": {}, "health": {}}
        )
        retry_stats = self.retry_strategy.get_stats() if self.retry_strategy else {}

        # Calculate success rates
        total_requests = max(self.stats["total_requests"], 1)
        success_rate = self.stats["successful_requests"] / total_requests
        partial_success_rate = self.stats["partial_successes"] / total_requests

        return {
            "service": "CombinedAnalysisServiceV2",
            "version": "2.0",
            "request_statistics": self.stats.copy(),
            "performance_metrics": {
                "success_rate": round(success_rate * 100, 2),
                "partial_success_rate": round(partial_success_rate * 100, 2),
                "avg_response_time_ms": self.stats["avg_response_time_ms"],
                "p95_response_time_ms": self._calculate_p95_response_time(),
                "parallel_efficiency_pct": round(self.stats["parallel_efficiency"] * 100, 1)
            },
            "resource_management": resource_pool_stats,
            "retry_strategy": retry_stats,
            "configuration": {
                "partial_results_enabled": self.enable_partial_results,
                "adaptive_retry_enabled": self.retry_strategy is not None,
                "resource_pool_config": FeatureFlags.get_resource_pool_config()
            }
        }

    def _calculate_p95_response_time(self) -> float:
        """Calculate P95 response time from recent history."""
        if not self._response_times:
            return 0.0

        sorted_times = sorted(self._response_times)
        p95_index = int(len(sorted_times) * 0.95)
        return round(sorted_times[p95_index] * 1000, 2) if p95_index < len(sorted_times) else 0.0

    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate input data for combined analysis.

        Args:
            data: Input data dictionary

        Returns:
            Validated data dictionary

        Raises:
            ValueError: If validation fails
        """
        required_fields = ['resume', 'job_description', 'keywords']

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

            if not data[field]:
                raise ValueError(f"Field '{field}' cannot be empty")

        # Validate text lengths
        if len(data['resume']) < 200:
            raise ValueError("Resume must be at least 200 characters")

        if len(data['job_description']) < 200:
            raise ValueError("Job description must be at least 200 characters")

        # Validate keywords
        if isinstance(data['keywords'], str):
            data['keywords'] = [k.strip() for k in data['keywords'].split(',') if k.strip()]

        if not isinstance(data['keywords'], list) or not data['keywords']:
            raise ValueError("Keywords must be a non-empty list or comma-separated string")

        # Validate language if provided
        if 'language' in data:
            if data['language'] not in ['en', 'zh-TW']:
                data['language'] = 'en'  # Default to English
        else:
            data['language'] = 'en'

        return data

    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Process the main business logic for combined analysis.

        Args:
            data: Validated input data

        Returns:
            Analysis results dictionary
        """
        return await self.analyze(
            resume=data['resume'],
            job_description=data['job_description'],
            keywords=data['keywords'],
            language=data.get('language', 'en'),
            analysis_options=data.get('analysis_options')
        )
