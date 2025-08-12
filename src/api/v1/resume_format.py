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

from fastapi import APIRouter, Request

from src.core.monitoring_service import monitoring_service
from src.decorators.error_handler import handle_api_errors
from src.models.response import (
    UnifiedResponse,
    WarningInfo,
    create_success_response,
)
from src.models.resume_format import ResumeFormatRequest
from src.services.resume_format import ResumeFormatService

# Setup logging
logger = logging.getLogger(__name__)

# Create router for resume format endpoints
router = APIRouter()


@handle_api_errors(api_name="resume_format")
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
            "description": "Resume formatted successfully",
            "model": UnifiedResponse
        },
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"}
    }
)
async def format_resume(
    request: ResumeFormatRequest,
    raw_request: Request
) -> UnifiedResponse:
    """
    Format OCR text into structured HTML resume.

    Converts OCR-extracted text into a professionally formatted HTML resume with:
    - Section detection and organization
    - Contact information extraction and formatting
    - Experience formatting with structured lists
    - Education and skills organization
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

    # Initialize service using LLM Factory
    service = ResumeFormatService()  # Service will use LLM Factory internally

    # Format resume
    result = await service.format_resume(
        ocr_text=request.ocr_text,
        supplement_info=request.supplement_info
    )

    # Calculate processing time
    processing_time = time.time() - start_time

    # Build warnings if any
    warnings = []
    sections_dict = result.sections_detected.model_dump()
    missing_sections = [
        section for section, detected in sections_dict.items()
        if not detected and section in ["education", "skills", "experience"]
    ]

    if missing_sections:
        warnings.append(WarningInfo(
            has_warning=True,
            message=f"Missing sections: {', '.join(missing_sections)}",
            expected_minimum=3,
            actual_extracted=len(sections_dict) - len(missing_sections),
            suggestion="Review and add missing sections manually"
        ))

    # Track success metrics
    monitoring_service.track_event("ResumeFormatSuccess", {
        "request_id": request_id,
        "processing_time_ms": round(processing_time * 1000, 2),
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
