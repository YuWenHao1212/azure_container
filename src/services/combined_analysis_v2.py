"""
Combined Analysis Service V2 for Azure Container API.

Unified service for index calculation and gap analysis with optimized performance.
Key component of the V2 refactoring with resource pooling and parallel processing.
"""
import asyncio
import logging
import os
import time
from typing import Any

from src.services.base import BaseService
from src.services.gap_analysis_v2 import GapAnalysisServiceV2
from src.services.index_calculation_v2 import IndexCalculationServiceV2
from src.services.resource_pool_manager import ResourcePoolManager
from src.utils.adaptive_retry import AdaptiveRetryStrategy
from src.utils.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


class PartialFailureError(Exception):
    """Exception for partial failures with available data."""

    def __init__(self, message: str, partial_data: dict[str, Any], details: dict | None = None):
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
        index_service: IndexCalculationServiceV2 | None = None,
        gap_service: GapAnalysisServiceV2 | None = None,
        resource_pool: ResourcePoolManager | None = None,
        enable_partial_results: bool | None = None
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
        analysis_options: dict[str, Any] | None = None
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
        analysis_options: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Execute analysis using V3 true parallel processing approach.

        V3 Optimization (Plan B):
        - Keywords and Embeddings start simultaneously at T=0
        - Gap Analysis starts immediately after Keywords (50ms)
        - Index calculation runs in background
        """
        import asyncio

        # Detailed timing tracking for V3 optimization
        detailed_timings = {
            "start": time.time(),
            "embedding_start": None,
            "resume_embedding_start": None,
            "resume_embedding_end": None,
            "jd_embedding_start": None,
            "jd_embedding_end": None,
            "embedding_end": None,
            "keyword_match_start": None,
            "keyword_match_end": None,
            "index_llm_start": None,
            "index_llm_end": None,
            "gap_context_start": None,
            "gap_context_end": None,
            "gap_llm_start": None,
            "gap_llm_end": None,
            "end": None
        }

        phase_timings = {}

        # V3 TRUE PARALLEL: Start Keywords and Embeddings simultaneously at T=0
        phase1_start = time.time()
        detailed_timings["embedding_start"] = phase1_start
        detailed_timings["keyword_match_start"] = phase1_start

        # Create async tasks for parallel execution
        keyword_task = asyncio.create_task(
            asyncio.to_thread(self._quick_keyword_match, resume, keywords)
        )

        # Start embeddings generation in parallel
        embedding_task = None
        if os.getenv('RESOURCE_POOL_ENABLED', 'true').lower() == 'false':
            # Direct embedding generation without resource pool
            embedding_task = asyncio.create_task(
                self._generate_embeddings_parallel(None, resume, job_description)
            )
        else:
            # Use resource pool for production
            async def _generate_with_pool():
                async with self.resource_pool.get_client() as client:
                    result = await self._generate_embeddings_parallel(
                        client, resume, job_description
                    )
                    self.stats["resource_pool_hits"] += 1
                    return result

            embedding_task = asyncio.create_task(_generate_with_pool())

        # Wait for keywords to complete (should be ~50ms)
        keyword_coverage = await keyword_task
        detailed_timings["keyword_match_end"] = time.time()

        # V3 KEY OPTIMIZATION: Start Gap Analysis immediately with just keywords
        gap_start = time.time()
        detailed_timings["gap_context_start"] = gap_start
        detailed_timings["gap_llm_start"] = gap_start

        # Build minimal index_result with just keywords (no similarity_score needed)
        minimal_index_result = {
            "keyword_coverage": keyword_coverage,
            "similarity_percentage": 0,  # Default value to avoid errors
            "raw_similarity_percentage": 0,
            "processing_time_ms": 0
        }

        # Start Gap Analysis immediately (not waiting for embeddings or full index)
        if self.retry_strategy:
            gap_task = asyncio.create_task(
                self.retry_strategy.execute_with_retry(
                    lambda: self.gap_service.analyze_with_context(
                        resume=resume,
                        job_description=job_description,
                        index_result=minimal_index_result,
                        language=language,
                        options=analysis_options
                    ),
                    error_classifier=self._classify_gap_error,
                    get_retry_after=self._get_retry_after_from_error
                )
            )
        else:
            gap_task = asyncio.create_task(
                self.gap_service.analyze_with_context(
                    resume=resume,
                    job_description=job_description,
                    index_result=minimal_index_result,
                    language=language,
                    options=analysis_options
                )
            )

        # Wait for embeddings to complete (background task)
        await embedding_task
        detailed_timings["embedding_end"] = time.time()
        phase_timings["embedding_generation"] = detailed_timings["embedding_end"] - phase1_start

        # Calculate full Index in background (not blocking Gap Analysis)
        index_start = time.time()
        detailed_timings["index_llm_start"] = index_start

        if self.retry_strategy:
            index_task = asyncio.create_task(
                self.retry_strategy.execute_with_retry(
                    lambda: self.index_service.calculate_index(
                        resume=resume,
                        job_description=job_description,
                        keywords=keywords
                    ),
                    error_classifier=self._classify_index_error,
                    get_retry_after=self._get_retry_after_from_error
                )
            )
        else:
            index_task = asyncio.create_task(
                self.index_service.calculate_index(
                    resume=resume,
                    job_description=job_description,
                    keywords=keywords
                )
            )

        # Wait for Gap Analysis to complete (critical path)
        gap_result = await gap_task
        detailed_timings["gap_llm_end"] = time.time()
        phase_timings["gap_analysis"] = detailed_timings["gap_llm_end"] - gap_start

        # Wait for Index to complete (background)
        index_result = await index_task
        detailed_timings["index_llm_end"] = time.time()
        phase_timings["index_calculation"] = detailed_timings["index_llm_end"] - index_start

        detailed_timings["end"] = time.time()

        # Calculate parallel processing efficiency
        total_sequential_time = sum(phase_timings.values())
        total_actual_time = detailed_timings["end"] - detailed_timings["start"]
        efficiency = 1 - (total_actual_time / total_sequential_time) if total_sequential_time > 0 else 0
        self.stats["parallel_efficiency"] = efficiency

        # Calculate detailed timing breakdown
        timing_breakdown = {
            "total_time": round((detailed_timings["end"] - detailed_timings["start"]) * 1000, 2),
            "keyword_matching_time": (
                round((detailed_timings["keyword_match_end"] - detailed_timings["keyword_match_start"]) * 1000, 2)
                if detailed_timings["keyword_match_end"] and detailed_timings["keyword_match_start"]
                else None
            ),
            "embedding_time": (
                round((detailed_timings["embedding_end"] - detailed_timings["embedding_start"]) * 1000, 2)
                if detailed_timings["embedding_end"] and detailed_timings["embedding_start"]
                else None
            ),
            "index_calculation_time": (
                round((detailed_timings["index_llm_end"] - detailed_timings["index_llm_start"]) * 1000, 2)
                if detailed_timings["index_llm_end"] and detailed_timings["index_llm_start"]
                else None
            ),
            "gap_analysis_time": (
                round((detailed_timings["gap_llm_end"] - detailed_timings["gap_llm_start"]) * 1000, 2)
                if detailed_timings["gap_llm_end"] and detailed_timings["gap_llm_start"]
                else None
            ),
        }

        # Log V3 optimization performance
        logger.info(
            "V3 Optimization - True parallel execution",
            extra={
                "timing_breakdown_ms": timing_breakdown,
                "optimization": "Plan B",
                "keyword_to_gap_latency_ms": timing_breakdown.get("keyword_matching_time", 0),
                "phase_percentages": {
                    "keywords": (
                        round(
                            (timing_breakdown.get("keyword_matching_time", 0) / timing_breakdown["total_time"] * 100), 1
                        )
                        if timing_breakdown.get("keyword_matching_time")
                        else None
                    ),
                    "embedding": (
                        round((timing_breakdown.get("embedding_time", 0) / timing_breakdown["total_time"] * 100), 1)
                        if timing_breakdown.get("embedding_time")
                        else None
                    ),
                    "index": (
                        round(
                            timing_breakdown.get("index_calculation_time", 0) / timing_breakdown["total_time"] * 100,
                            1
                        )
                        if timing_breakdown.get("index_calculation_time")
                        else None
                    ),
                    "gap": (
                        round((timing_breakdown.get("gap_analysis_time", 0) / timing_breakdown["total_time"] * 100), 1)
                        if timing_breakdown.get("gap_analysis_time")
                        else None
                    ),
                }
            }
        )

        # Combine results (maintain API compatibility)
        return {
            "index_calculation": index_result,
            "gap_analysis": gap_result,
            "metadata": {
                "version": "3.0",
                "language_detected": language,
                "processing_approach": "v3_true_parallel",
                "optimization": "Plan B - Gap starts after keywords only",
                "phase_timings_ms": {
                    phase: round(timing * 1000, 2)
                    for phase, timing in phase_timings.items()
                },
                "detailed_timings_ms": timing_breakdown,
                "parallel_efficiency": round(efficiency * 100, 1),
                "resource_pool_used": os.getenv('RESOURCE_POOL_ENABLED', 'true').lower() != 'false'
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

    def _quick_keyword_match(self, resume: str, keywords: list[str]) -> dict[str, Any]:
        """
        Quickly match keywords without LLM calls.
        Extracted from IndexCalculationServiceV2 for fast execution (~50ms).

        Args:
            resume: Resume text
            keywords: List of keywords to match

        Returns:
            Keyword coverage dictionary
        """
        from src.services.text_processing import clean_html_text

        # Clean HTML if present
        resume_text = clean_html_text(resume)

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

        # Prepare resume text for matching (case insensitive)
        resume_search_text = resume_text.lower()

        covered = []
        missed = []

        for keyword in keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            # Case insensitive search
            search_keyword = keyword.lower()

            # Try exact word boundary match
            import re
            found = bool(re.search(rf'\b{re.escape(search_keyword)}\b', resume_search_text))

            # Try plural matching if not found
            if not found:
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
        percentage = round(covered_count / total * 100) if total else 0

        return {
            "total_keywords": total,
            "covered_count": covered_count,
            "coverage_percentage": percentage,
            "covered_keywords": covered,
            "missed_keywords": missed
        }

    async def _generate_embeddings_parallel_with_timing(
        self,
        client: Any,
        resume: str,
        job_description: str
    ) -> tuple[dict[str, list[float]], dict[str, float]]:
        """
        Generate embeddings in parallel with detailed timing tracking.

        Args:
            client: OpenAI client from resource pool
            resume: Resume text for embedding
            job_description: Job description text for embedding

        Returns:
            Tuple of (embeddings dict, timings dict)
        """
        timings = {}

        # Clean texts for embedding (remove HTML, normalize)
        clean_start = time.time()
        clean_resume = self._clean_text_for_embedding(resume)
        clean_job_desc = self._clean_text_for_embedding(job_description)
        timings["text_cleaning"] = time.time() - clean_start

        # Track individual embedding times
        resume_start = time.time()
        jd_start = None

        # Generate embeddings in parallel
        async def timed_resume_embedding():
            result = await self._create_embedding(client, clean_resume)
            timings["resume_embedding"] = time.time() - resume_start
            return result

        async def timed_jd_embedding():
            nonlocal jd_start
            jd_start = time.time()
            result = await self._create_embedding(client, clean_job_desc)
            timings["jd_embedding"] = time.time() - jd_start
            return result

        async with asyncio.TaskGroup() as tg:
            resume_task = tg.create_task(timed_resume_embedding())
            job_task = tg.create_task(timed_jd_embedding())

        embeddings = {
            "resume": resume_task.result(),
            "job_description": job_task.result()
        }

        # Log embedding timings
        logger.debug(
            "Embedding generation timings",
            extra={
                "text_cleaning_ms": round(timings["text_cleaning"] * 1000, 2),
                "resume_embedding_ms": round(timings["resume_embedding"] * 1000, 2),
                "jd_embedding_ms": round(timings["jd_embedding"] * 1000, 2),
                "parallel": True
            }
        )

        return embeddings, timings

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

    def _get_retry_after_from_error(self, error: Exception) -> int | None:
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
