"""
Resume Format API Endpoints.
Handles resume formatting functionality.

Features:
- POST /api/v1/format-resume endpoint
- OCR text to structured HTML conversion
- Bubble.io compatible responses
- Comprehensive error handling (400, 500, 503)
"""
import logging
import time

from fastapi import APIRouter, HTTPException, Request, status

from src.core.monitoring_service import monitoring_service
from src.models.response import (
    UnifiedResponse,
    WarningInfo,
    create_error_response,
    create_success_response,
)
from src.models.resume_format import ResumeFormatRequest
from src.services.exceptions import ValidationError
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
    get_azure_openai_client,
)
from src.services.resume_format import ResumeFormatService

# Setup logging
logger = logging.getLogger(__name__)

# Create router for resume format endpoints
router = APIRouter()


@router.post(
    "/format-resume",
    response_model=UnifiedResponse,
    summary="Format OCR text into structured HTML resume",
    description=(
        "Converts OCR-extracted text into a professionally formatted HTML resume. "
        "OCR format: 【Type】:Content on each line (e.g., 【Title】:John Smith). "
        "Common types: Title, NarrativeText, ListItem, UncategorizedText. "
        "Returns HTML compatible with TinyMCE editor."
    ),
    responses={
        200: {
            "description": "Successfully formatted resume",
            "model": UnifiedResponse,
        },
        400: {"description": "Invalid request (e.g., OCR text too short)"},
        500: {"description": "Internal server error"},
        503: {"description": "Service temporarily unavailable"},
    },
)
async def format_resume(
    request: ResumeFormatRequest,
    raw_request: Request,
) -> UnifiedResponse:
    """
    Format OCR text into structured HTML resume.

    This endpoint takes OCR-extracted text and converts it into a properly
    formatted HTML resume. It handles:
    - OCR error correction
    - Structure reconstruction
    - Date standardization
    - Section detection
    - Language preservation

    Args:
        request: Resume format request containing OCR text and optional supplement info
        raw_request: Raw FastAPI request object

    Returns:
        UnifiedResponse containing formatted HTML resume

    Raises:
        HTTPException: For various error conditions (400, 500, 503)
    """
    start_time = time.time()
    request_id = getattr(raw_request.state, "request_id", "unknown")

    try:
        logger.info(
            f"[{request_id}] Resume format request received, "
            f"OCR text length: {len(request.ocr_text)}"
        )

        # Track request
        monitoring_service.track_event("ResumeFormatRequest", {
            "request_id": request_id,
            "ocr_text_length": len(request.ocr_text),
            "has_supplement_info": bool(request.supplement_info),
            "supplement_fields": (
                list(request.supplement_info.model_dump(exclude_none=True).keys())
                if request.supplement_info else []
            )
        })

        # Initialize service
        openai_client = get_azure_openai_client()
        service = ResumeFormatService(openai_client=openai_client)

        # Format resume
        result = await service.format_resume(
            ocr_text=request.ocr_text,
            supplement_info=request.supplement_info
        )

        # Calculate processing time
        processing_time = time.time() - start_time

        # Build warnings if any sections are missing
        warnings = []
        sections_dict = result.sections_detected.model_dump()
        missing_sections = [
            section for section, detected in sections_dict.items()
            if not detected
        ]

        if missing_sections:
            warnings.append(
                WarningInfo(
                    code="MISSING_SECTIONS",
                    message=f"Some resume sections could not be detected: {', '.join(missing_sections)}",
                    details={"missing_sections": missing_sections}
                )
            )

        # Track success
        monitoring_service.track_event("ResumeFormatSuccess", {
            "request_id": request_id,
            "processing_time_ms": processing_time * 1000,
            "html_length": len(result.formatted_resume),
            "sections_detected_count": sum(1 for v in sections_dict.values() if v),
            "total_corrections": sum(result.corrections_made.model_dump().values()),
            "supplement_fields_used": result.supplement_info_used
        })

        # Create success response
        response = create_success_response(result.model_dump())

        # Add warnings if any
        if warnings:
            response.warning = WarningInfo(
                has_warning=True,
                message=warnings[0].message,
                expected_minimum=0,
                actual_extracted=0,
                suggestion="Review and add missing sections manually"
            )

        return response

    except ValidationError as e:
        # Handle validation errors (400)
        logger.warning(f"[{request_id}] Validation error: {e!s}")

        monitoring_service.track_event("ResumeFormatValidationError", {
            "request_id": request_id,
            "error": str(e),
            "ocr_text_length": len(request.ocr_text)
        })

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code="VALIDATION_ERROR",
                message=str(e),
                details="Input validation failed"
            ).model_dump()
        ) from e

    except AzureOpenAIRateLimitError as e:
        # Handle rate limit errors (503)
        logger.error(f"[{request_id}] OpenAI rate limit error: {e!s}")

        monitoring_service.track_event("ResumeFormatRateLimit", {
            "request_id": request_id,
            "error": str(e)
        })

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="RATE_LIMIT_ERROR",
                message="Service is temporarily unavailable due to high demand. Please try again later.",
                details="Rate limit exceeded"
            ).model_dump()
        ) from e

    except (AzureOpenAIAuthError, AzureOpenAIServerError) as e:
        # Handle OpenAI service errors (503)
        logger.error(f"[{request_id}] OpenAI service error: {e!s}")

        monitoring_service.track_event("ResumeFormatServiceError", {
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="OPENAI_SERVICE_ERROR",
                message="OpenAI service is currently unavailable. Please try again later.",
                details=str(e)
            ).model_dump()
        ) from e

    except Exception as e:
        # Handle unexpected errors (500)
        logger.error(
            f"[{request_id}] Unexpected error in resume format: {e!s}",
            exc_info=True
        )

        monitoring_service.track_event("ResumeFormatUnexpectedError", {
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred while formatting the resume.",
                details=str(e)
            ).model_dump()
        ) from e
