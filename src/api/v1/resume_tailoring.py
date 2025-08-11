"""
Resume Tailoring API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ...core.config import Settings, get_settings
from ...models.api.resume_tailoring import (
    CoverageDetails,
    CoverageStats,
    ErrorInfo,
    KeywordTracking,
    SimilarityStats,
    TailoringResponse,
    TailoringResult,
    TailorResumeRequest,
    VisualMarkerStats,
    WarningInfo,
)
from ...services.exceptions import ServiceError
from ...services.resume_tailoring import ResumeTailoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tailor-resume")

# Initialize service
tailoring_service = ResumeTailoringService()


@router.post(
    "",
    response_model=TailoringResponse,
    summary="Tailor Resume",
    description="Optimize a resume based on job description and gap analysis results",
    responses={
        200: {
            "description": "Resume successfully tailored",
            "model": TailoringResponse
        },
        400: {
            "description": "Invalid request data",
            "model": TailoringResponse
        },
        500: {
            "description": "Internal server error",
            "model": TailoringResponse
        }
    }
)
async def tailor_resume(
    request: TailorResumeRequest,
    settings: Settings = Depends(get_settings)
) -> TailoringResponse:
    """
    Tailor a resume to better match a job description.

    This endpoint uses gap analysis results to:
    - Create or optimize Summary section
    - Convert experience bullets to STAR/PAR format
    - Integrate missing keywords naturally
    - Highlight core strengths
    - Add metric placeholders where needed

    The output includes visual markers (CSS classes) to show optimizations.
    """
    try:
        logger.info(
            f"Resume tailoring request for language: {request.options.language}"
        )

        # Extract keywords from gap analysis
        covered_keywords = request.gap_analysis.covered_keywords or []
        missing_keywords = request.gap_analysis.missing_keywords or []

        # Call service with keywords
        result = await tailoring_service.tailor_resume(
            job_description=request.job_description,
            original_resume=request.original_resume,
            gap_analysis=request.gap_analysis.model_dump(),
            covered_keywords=covered_keywords,
            missing_keywords=missing_keywords,
            output_language=request.options.language,
        )

        # Extract keyword tracking info
        keyword_tracking = result.get("keyword_tracking", {})
        removed_keywords = keyword_tracking.get("removed", [])

        # Create warning if keywords were removed
        warning = WarningInfo()
        if removed_keywords:
            warning = WarningInfo(
                has_warning=True,
                message=f"Optimization successful but {len(removed_keywords)} keywords removed",
                details=removed_keywords
            )
            logger.warning(f"Keywords removed during optimization: {removed_keywords}")

        # Build tailoring result
        # Check if service returned real metrics (using IndexCalculationServiceV2)
        similarity_metrics = result.get("similarity_metrics")
        coverage_metrics = result.get("coverage_metrics")

        # Use real metrics if available, otherwise use estimates
        if similarity_metrics:
            similarity = SimilarityStats(
                before=similarity_metrics["before"],
                after=similarity_metrics["after"],
                improvement=similarity_metrics["improvement"]
            )
        else:
            # Fallback to estimation
            similarity = SimilarityStats(
                before=request.gap_analysis.similarity_percentage,
                after=min(100, request.gap_analysis.similarity_percentage + 20),
                improvement=20
            )

        if coverage_metrics:
            coverage = CoverageStats(
                before=CoverageDetails(
                    percentage=coverage_metrics["before"]["percentage"],
                    covered=coverage_metrics["before"]["covered"],
                    missed=coverage_metrics["before"]["missed"]
                ),
                after=CoverageDetails(
                    percentage=coverage_metrics["after"]["percentage"],
                    covered=coverage_metrics["after"]["covered"],
                    missed=coverage_metrics["after"]["missed"]
                ),
                improvement=coverage_metrics["improvement"],
                newly_added=coverage_metrics["newly_added"],
                removed=coverage_metrics["removed"]
            )
        else:
            # Fallback to estimation
            coverage = CoverageStats(
                before=CoverageDetails(
                    percentage=request.gap_analysis.coverage_percentage,
                    covered=covered_keywords,
                    missed=missing_keywords
                ),
                after=CoverageDetails(
                    percentage=min(100, request.gap_analysis.coverage_percentage +
                                 len(keyword_tracking.get("newly_added", [])) * 5),
                    covered=keyword_tracking.get("still_covered", []) +
                           keyword_tracking.get("newly_added", []),
                    missed=keyword_tracking.get("still_missing", [])
                ),
                improvement=len(keyword_tracking.get("newly_added", [])) * 5,
                newly_added=keyword_tracking.get("newly_added", []),
                removed=keyword_tracking.get("removed", [])
            )

        tailoring_result = TailoringResult(
            resume=result.get("optimized_resume", ""),
            improvements=result.get("applied_improvements", ""),
            markers=VisualMarkerStats(
                keyword_new=len(keyword_tracking.get("newly_added", [])),
                keyword_existing=len(keyword_tracking.get("still_covered", [])),
                placeholder=0,  # TODO: count from HTML
                new_section=0,  # TODO: count from HTML
                modified=result.get("improvement_count", 0)
            ),
            similarity=similarity,
            coverage=coverage,
            keyword_tracking=KeywordTracking(
                still_covered=keyword_tracking.get("still_covered", []),
                removed=keyword_tracking.get("removed", []),
                newly_added=keyword_tracking.get("newly_added", []),
                still_missing=keyword_tracking.get("still_missing", []),
                warnings=keyword_tracking.get("warnings", [])
            )
        )

        logger.info(
            f"Resume tailoring completed: {len(keyword_tracking.get('newly_added', []))} keywords added, "
            f"{len(removed_keywords)} removed"
        )

        return TailoringResponse(
            success=True,
            data=tailoring_result,
            error=ErrorInfo(),
            warning=warning
        )

    except ValueError as e:
        error_msg = str(e).lower()

        # Determine error code based on error message
        if "too short" in error_msg:
            error_code = "VALIDATION_TOO_SHORT"
            field_errors = {
                "original_resume" if "resume" in error_msg else "job_description":
                ["Must be at least 200 characters"]
            }
        elif "required" in error_msg or "missing" in error_msg:
            error_code = "VALIDATION_REQUIRED_FIELD"
            field_errors = {"gap_analysis": ["Missing required field"]}
        else:
            error_code = "VALIDATION_INVALID_FORMAT"
            field_errors = {}

        logger.warning(f"Validation error: {e!s}")

        return TailoringResponse(
            success=False,
            data=None,
            error=ErrorInfo(
                has_error=True,
                code=error_code,
                message=str(e),
                details="Please check your input data",
                field_errors=field_errors
            ),
            warning=WarningInfo()
        )

    except HTTPException as e:
        # Handle HTTP exceptions from service layer
        if e.status_code == 429:
            error_code = "EXTERNAL_RATE_LIMIT_EXCEEDED"
            message = "AI service rate limit exceeded, please retry after 60 seconds"
        elif e.status_code == 502:
            error_code = "EXTERNAL_SERVICE_ERROR"
            message = "AI service error, please try again"
        elif e.status_code == 504:
            error_code = "EXTERNAL_SERVICE_TIMEOUT"
            message = "AI processing timeout, please retry"
        else:
            error_code = "SYSTEM_INTERNAL_ERROR"
            message = "Service temporarily unavailable"

        logger.error(f"HTTP exception in resume tailoring: {e.detail}")

        return TailoringResponse(
            success=False,
            data=None,
            error=ErrorInfo(
                has_error=True,
                code=error_code,
                message=message,
                details=e.detail if settings.debug else "",
                field_errors={}
            ),
            warning=WarningInfo()
        )

    except ServiceError as e:
        logger.error(f"Service error in resume tailoring: {e!s}")

        return TailoringResponse(
            success=False,
            data=None,
            error=ErrorInfo(
                has_error=True,
                code="SERVICE_CALCULATION_ERROR",
                message="Failed to calculate similarity metrics",
                details=str(e) if settings.debug else "Please try again later",
                field_errors={}
            ),
            warning=WarningInfo()
        )

    except Exception as e:
        logger.error(f"Resume tailoring failed: {e!s}", exc_info=True)

        return TailoringResponse(
            success=False,
            data=None,
            error=ErrorInfo(
                has_error=True,
                code="SYSTEM_INTERNAL_ERROR",
                message="An unexpected error occurred",
                details=str(e) if settings.debug else "Please try again later",
                field_errors={}
            ),
            warning=WarningInfo()
        )


# Health check endpoint removed - using unified /health endpoint in main.py
# Service-specific health info is available through the main health endpoint


@router.get(
    "/supported-languages",
    summary="Get Supported Languages",
    description="Get list of supported languages for resume tailoring"
)
async def get_supported_languages():
    """Get supported languages"""
    from ...core.language_handler import LanguageHandler

    return {
        "success": True,
        "data": {
            "languages": LanguageHandler.SUPPORTED_LANGUAGES,
            "default": LanguageHandler.DEFAULT_LANGUAGE
        }
    }
