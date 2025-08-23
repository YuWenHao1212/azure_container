"""
Resume Tailoring API endpoints.
"""

import logging
import time

from fastapi import APIRouter, Depends

from ...core.config import Settings, get_settings
from ...decorators.error_handler import handle_tailor_resume_errors
from ...models.api.resume_tailoring import (
    KeywordsMetrics,
    SimilarityMetrics,
    TailoringMetadata,
    TailoringResponse,
    TailoringResult,
    TailorResumeRequest,
    WarningInfo,
)
from ...services.resume_tailoring_v31 import ResumeTailoringServiceV31
from ...utils.bubble_compatibility import (
    BUBBLE_ARRAY_FIELDS,
    ensure_bubble_compatibility,
    validate_array_fields,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tailor-resume")

# Service will be initialized lazily
tailoring_service = None

def get_tailoring_service():
    """Get or create the tailoring service instance."""
    global tailoring_service
    if tailoring_service is None:
        tailoring_service = ResumeTailoringServiceV31()
    return tailoring_service


@router.post("")
@handle_tailor_resume_errors(api_name="tailor_resume")
async def tailor_resume(
    request: TailorResumeRequest,
    settings: Settings = Depends(get_settings)
) -> TailoringResponse:
    """
    Tailor a resume to better match a job description (v3.1.0).

    This endpoint uses gap analysis results to:
    - Create or optimize Summary section (LLM1)
    - Add missing Projects/Education sections (LLM2)
    - Integrate missing keywords naturally
    - Highlight core strengths
    - Add metric placeholders where needed

    The output includes visual markers (CSS classes) to show optimizations.
    """
    start_time = time.time()

    logger.info(
        f"Resume tailoring v3.1.0 request for language: {request.options.language}"
    )

    # Call the new v3.1.0 service
    service = get_tailoring_service()
    result = await service.tailor_resume(
        job_description=request.job_description,
        original_resume=request.original_resume,
        original_index=request.original_index,
        output_language=request.options.language
    )

    # Extract metrics from result
    keywords_metrics = result.get("Keywords", {})
    similarity_metrics = result.get("similarity", {})

    # Get warning info if keywords were removed
    removed_keywords = keywords_metrics.get("kw_removed", [])
    warning = WarningInfo()
    if removed_keywords:
        warning = WarningInfo(
            has_warning=True,
            message=f"Optimization successful but {len(removed_keywords)} keywords removed",
            details=removed_keywords
        )
        logger.warning(f"Keywords removed during optimization: {removed_keywords}")

    # Calculate total processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Extract timing information from result
    stage_timings = result.get("stage_timings", {})

    # Build the response in v3.1.0 format

    tailoring_result = TailoringResult(
        optimized_resume=result.get("optimized_resume", ""),
        applied_improvements=result.get("applied_improvements", []),
        total_processing_time_ms=result.get("total_processing_time_ms", processing_time_ms),
        pre_processing_ms=result.get("pre_processing_ms", 0),
        llm1_processing_time_ms=result.get("llm1_processing_time_ms", 0),
        llm2_processing_time_ms=result.get("llm2_processing_time_ms", 0),
        post_processing_ms=result.get("post_processing_ms", 0),
        stage_timings=stage_timings,
        Keywords=KeywordsMetrics(**keywords_metrics) if keywords_metrics else KeywordsMetrics(
            kcr_improvement=0,
            kcr_before=0,
            kcr_after=0,
            kw_before_covered=[],
            kw_before_missed=[],
            kw_after_covered=[],
            kw_after_missed=[],
            newly_added=[],
            kw_removed=[]
        ),
        similarity=SimilarityMetrics(**similarity_metrics) if similarity_metrics else SimilarityMetrics(
            SS_improvement=0,
            SS_before=0,
            SS_after=0
        ),
        metadata=result.get("metadata", TailoringMetadata())
    )

    logger.info(
        f"Resume tailoring v3.1.0 completed: {len(keywords_metrics.get('newly_added', []))} keywords added, "
        f"{len(removed_keywords)} removed"
    )

    response = TailoringResponse(
        success=True,
        data=tailoring_result,
        warning=warning
        # Note: error field is excluded when success=True (exclude_none=True in model)
    )

    # Ensure Bubble.io compatibility
    response_dict = response.model_dump(exclude_none=True)
    response_dict = ensure_bubble_compatibility(response_dict)
    response_dict = validate_array_fields(response_dict, BUBBLE_ARRAY_FIELDS)

    return response_dict


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
