"""
Index Calculation API Endpoints.
Handles resume similarity and keyword coverage analysis functionality.
"""
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.models.response import (
    UnifiedResponse,
    create_error_response,
    create_success_response,
)


# Request/Response Models
class IndexCalculationRequest(BaseModel):
    """Request model for index calculation."""
    resume: str = Field(..., description="Resume content (HTML or plain text)")
    job_description: str = Field(..., description="Job description (HTML or plain text)")
    keywords: list[str] | str = Field(..., description="Keywords list or comma-separated string")


class KeywordCoverageData(BaseModel):
    """Keyword coverage analysis data."""
    total_keywords: int = Field(default=0, description="Total number of keywords")
    covered_count: int = Field(default=0, description="Number of keywords found")
    coverage_percentage: int = Field(default=0, description="Coverage percentage")
    covered_keywords: list[str] = Field(default_factory=list, description="Found keywords")
    missed_keywords: list[str] = Field(default_factory=list, description="Missing keywords")


class IndexCalculationData(BaseModel):
    """Response data for index calculation."""
    raw_similarity_percentage: int = Field(default=0, description="Raw cosine similarity percentage")
    similarity_percentage: int = Field(default=0, description="Transformed similarity percentage")
    keyword_coverage: KeywordCoverageData = Field(
        default_factory=KeywordCoverageData,
        description="Keyword coverage analysis"
    )


# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


async def calculate_index(
    request: IndexCalculationRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """
    Calculate similarity index between resume and job description using V2 service.

    Args:
        request: Index calculation request data
        req: FastAPI request object
        settings: Application settings

    Returns:
        UnifiedResponse with calculation results
    """
    start_time = time.time()

    try:
        # Log request
        keywords_count = (
            len(request.keywords) if isinstance(request.keywords, list)
            else len(request.keywords.split(','))
        )
        logger.info(
            f"Index calculation V2 request: "
            f"resume_length={len(request.resume)}, "
            f"job_desc_length={len(request.job_description)}, "
            f"keywords_count={keywords_count}"
        )

        # Create V2 service instance with optimized settings
        from src.services.index_calculation_v2 import get_index_calculation_service_v2
        service = get_index_calculation_service_v2()

        # Determine if we should include timing breakdown (development mode only)
        include_timing = os.getenv("ENVIRONMENT", "production") == "development"

        # Calculate index using V2 service
        result = await service.calculate_index(
            resume=request.resume,
            job_description=request.job_description,
            keywords=request.keywords,
            include_timing=include_timing
        )

        # Track metrics
        processing_time = time.time() - start_time
        monitoring_service.track_event(
            "IndexCalculationV2Completed",
            {
                "raw_similarity": result["raw_similarity_percentage"],
                "transformed_similarity": result["similarity_percentage"],
                "keyword_coverage": result["keyword_coverage"]["coverage_percentage"],
                "processing_time_ms": round(processing_time * 1000, 2),
                "cache_hit": result["cache_hit"],
                "service_version": "v2"
            }
        )

        # Create response data with guaranteed schema for Bubble.io compatibility
        response_data = IndexCalculationData(
            raw_similarity_percentage=result["raw_similarity_percentage"],
            similarity_percentage=result["similarity_percentage"],
            keyword_coverage=KeywordCoverageData(**result["keyword_coverage"])
        )

        # Build final response with required fields
        final_result = response_data.model_dump()

        # Add V2-specific fields
        final_result["processing_time_ms"] = result["processing_time_ms"]
        final_result["cache_hit"] = result["cache_hit"]

        # Always include timing_breakdown (empty in production, populated in development)
        final_result["timing_breakdown"] = result.get("timing_breakdown", {})

        logger.info(
            f"Index calculation V2 completed: "
            f"similarity={result['similarity_percentage']}%, "
            f"coverage={result['keyword_coverage']['coverage_percentage']}%, "
            f"cache_hit={result['cache_hit']}, "
            f"time={processing_time:.2f}s"
        )

        return create_success_response(data=final_result)

    except TimeoutError as e:
        # Timeout errors (408 Request Timeout)
        logger.error(f"Timeout error in index calculation V2: {e}")
        monitoring_service.track_event(
            "IndexCalculationV2TimeoutError",
            {
                "error_message": str(e),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                "service_version": "v2"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=create_error_response(
                code="TIMEOUT_ERROR",
                message="Request processing timeout",
                details="The request took too long to process"
            ).model_dump()
        ) from e

    except ValueError as e:
        logger.error(f"Validation error in index calculation V2: {e}")
        monitoring_service.track_event(
            "IndexCalculationV2ValidationError",
            {
                "error_message": str(e),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                "service_version": "v2"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=create_error_response(
                code="VALIDATION_ERROR",
                message="Invalid request data",
                details=str(e)
            ).model_dump()
        ) from e

    except Exception as e:
        # Import specific exception types
        from src.services.exceptions import AuthenticationError, ExternalServiceError, RateLimitError, ServiceError

        # Check for specific error types
        if isinstance(e, RateLimitError) or "rate limit" in str(e).lower():
            # Rate limit errors (429 Too Many Requests)
            logger.error(f"Rate limit error in index calculation V2: {e}")
            monitoring_service.track_event(
                "IndexCalculationV2RateLimitError",
                {
                    "error_message": str(e),
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "service_version": "v2"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=create_error_response(
                    code="RATE_LIMIT_ERROR",
                    message="Rate limit exceeded",
                    details="Please try again later"
                ).model_dump()
            ) from e

        elif isinstance(e, AuthenticationError):
            # Authentication errors (401/403)
            logger.error(f"Authentication error in index calculation V2: {e}")
            monitoring_service.track_event(
                "IndexCalculationV2AuthenticationError",
                {
                    "error_message": str(e),
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "service_version": "v2"
                }
            )
            # Use the status code from the AuthenticationError
            auth_status_code = getattr(e, 'status_code', 401)
            raise HTTPException(
                status_code=auth_status_code,
                detail=create_error_response(
                    code="AUTHENTICATION_ERROR" if auth_status_code == 401 else "FORBIDDEN",
                    message=str(e),
                    details="Authentication failed"
                ).model_dump()
            ) from e

        elif isinstance(e, ExternalServiceError):
            # External service errors (502 Bad Gateway)
            logger.error(f"External service error in index calculation V2: {e}")
            monitoring_service.track_event(
                "IndexCalculationV2ExternalServiceError",
                {
                    "error_message": str(e),
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "service_version": "v2"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=create_error_response(
                    code="EXTERNAL_SERVICE_ERROR",
                    message="External service error",
                    details=str(e)
                ).model_dump()
            ) from e

        elif isinstance(e, ServiceError):
            # General service errors (503 Service Unavailable)
            logger.error(f"Service error in index calculation V2: {e}")
            monitoring_service.track_event(
                "IndexCalculationV2ServiceError",
                {
                    "error_message": str(e),
                    "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    "service_version": "v2"
                }
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=create_error_response(
                    code="SERVICE_ERROR",
                    message="Service temporarily unavailable",
                    details=str(e)
                ).model_dump()
            ) from e
        logger.error(f"Unexpected error in index calculation V2: {e}", exc_info=True)
        monitoring_service.track_event(
            "IndexCalculationV2UnexpectedError",
            {
                "error_message": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                "service_version": "v2"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details="Please try again later"
            ).model_dump()
        ) from e

@router.post(
    "/index-calculation",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Resume-Job Similarity Index",
    description="Calculate similarity percentage and keyword coverage between resume and job description"
)
async def index_calculation_endpoint(
    request: IndexCalculationRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """Wrapper endpoint for calculate_index function."""
    return await calculate_index(request, req, settings)


@router.get(
    "/index-calculation/stats",
    summary="Get Index Calculation Service Statistics",
    description="Retrieve service statistics including cache performance and calculation metrics"
)
async def get_index_calculation_stats() -> dict[str, Any]:
    """
    Get comprehensive Index Calculation V2 service statistics.

    Returns:
        Dictionary containing service performance and cache statistics
    """
    try:
        from src.services.index_calculation_v2 import get_index_calculation_service_v2
        service = get_index_calculation_service_v2()

        stats = service.get_service_stats()

        # Track stats access
        monitoring_service.track_event(
            "IndexCalculationV2StatsAccessed",
            {
                "total_calculations": stats["calculation_stats"]["total_calculations"],
                "cache_hit_rate": stats["cache_performance"]["hit_rate"],
                "service_version": "v2"
            }
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get index calculation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to retrieve statistics: {e!s}"}
        ) from e


@router.get(
    "/index-calculation/cache-info",
    summary="Get Cache Information",
    description="Retrieve detailed cache information and performance metrics"
)
async def get_cache_info() -> dict[str, Any]:
    """
    Get detailed cache information for Index Calculation V2 service.

    Returns:
        Dictionary containing cache details and performance metrics
    """
    try:
        from src.services.index_calculation_v2 import get_index_calculation_service_v2
        service = get_index_calculation_service_v2()

        cache_info = service.get_cache_info()

        # Track cache info access
        monitoring_service.track_event(
            "IndexCalculationV2CacheInfoAccessed",
            {
                "cache_size": cache_info["total_entries"],
                "cache_hit_rate": cache_info["cache_hit_rate"],
                "service_version": "v2"
            }
        )

        return cache_info

    except Exception as e:
        logger.error(f"Failed to get cache info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to retrieve cache information: {e!s}"}
        ) from e


@router.post(
    "/index-calculation/clear-cache",
    summary="Clear Service Cache",
    description="Clear all cached embeddings and similarity calculations"
)
async def clear_cache() -> dict[str, str]:
    """
    Clear all cached data in Index Calculation V2 service.

    Returns:
        Status message confirming cache clearance
    """
    try:
        from src.services.index_calculation_v2 import get_index_calculation_service_v2
        service = get_index_calculation_service_v2()

        # Get cache size before clearing
        cache_info = service.get_cache_info()
        cache_size = cache_info["total_entries"]

        # Clear cache
        service.clear_cache()

        # Track cache clear event
        monitoring_service.track_event(
            "IndexCalculationV2CacheCleared",
            {
                "entries_cleared": cache_size,
                "service_version": "v2"
            }
        )

        logger.info(f"Index calculation V2 cache cleared: {cache_size} entries removed")

        return {
            "status": "success",
            "message": f"Cache cleared successfully. {cache_size} entries removed.",
            "service_version": "v2"
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to clear cache: {e!s}"}
        ) from e
