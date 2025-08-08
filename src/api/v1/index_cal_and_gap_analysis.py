"""
Combined Index Calculation and Gap Analysis API Endpoint.
Handles both similarity calculation and gap analysis in a single request.
"""
import logging
import time
from typing import Any, ClassVar

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError, validator

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.models.response import (
    ErrorCodes,
    UnifiedResponse,
    create_error_response,
    create_success_response,
    create_validation_error_response,
)


# Request/Response Models
class IndexCalAndGapAnalysisRequest(BaseModel):
    """Request model for combined index calculation and gap analysis with comprehensive validation."""
    resume: str = Field(
        ...,
        min_length=200,
        description="Resume content (HTML or plain text), minimum 200 characters"
    )
    job_description: str = Field(
        ...,
        min_length=200,
        description="Job description (HTML or plain text), minimum 200 characters"
    )
    keywords: list[str] | str = Field(
        ...,
        description="Keywords list or CSV string"
    )
    language: str = Field(
        default="en",
        description="Output language (en or zh-TW)"
    )

    @validator('language')
    def validate_language(cls, v):
        """Validate language parameter against whitelist."""
        valid_languages = {'en', 'zh-tw', 'zh-TW'}
        if v.lower() not in {lang.lower() for lang in valid_languages}:
            raise ValueError(f"Unsupported language: {v}. Supported: en, zh-TW")
        # Normalize case
        return 'zh-TW' if v.lower() == 'zh-tw' else v

    @validator('resume')
    def validate_resume_content(cls, v):
        """Additional resume content validation."""
        if not v.strip():
            raise ValueError("Resume content cannot be empty")
        return v.strip()

    @validator('job_description')
    def validate_jd_content(cls, v):
        """Additional job description content validation."""
        if not v.strip():
            raise ValueError("Job description content cannot be empty")
        return v.strip()

    @validator('keywords')
    def validate_keywords(cls, v):
        """Ensure keywords are not empty."""
        if isinstance(v, str):
            keywords_list = [k.strip() for k in v.split(",") if k.strip()]
        else:
            keywords_list = [k.strip() for k in v if k.strip()]

        if not keywords_list:
            raise ValueError("Keywords cannot be empty")
        return keywords_list

    class Config:
        # Custom error messages for validation
        schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "resume": (
                    "Senior Software Engineer with 8+ years experience in Python, FastAPI, React, "
                    "and cloud technologies. Proven track record in building scalable web applications "
                    "and leading development teams. Expert in microservices architecture, Docker, "
                    "Kubernetes, and CI/CD pipelines."
                ),
                "job_description": (
                    "Looking for Senior Full Stack Developer with 5+ years experience. "
                    "Must have expertise in Python, FastAPI, React, Docker, Kubernetes, AWS. "
                    "Experience with microservices architecture and database design required. "
                    "Strong problem-solving and team collaboration skills essential."
                ),
                "keywords": ["Python", "FastAPI", "React", "Docker", "Kubernetes", "AWS"],
                "language": "en"
            }
        }


class SkillQuery(BaseModel):
    """Skill development query model."""
    skill_name: str = Field(default="", description="Skill name")
    skill_category: str = Field(
        default="", description="Category: TECHNICAL or NON_TECHNICAL"
    )
    description: str = Field(default="", description="Skill description")


class GapAnalysisData(BaseModel):
    """Gap analysis response data."""
    CoreStrengths: str = Field(default="", description="Core strengths HTML")
    KeyGaps: str = Field(default="", description="Key gaps HTML")
    QuickImprovements: str = Field(default="", description="Quick improvements HTML")
    OverallAssessment: str = Field(default="", description="Overall assessment HTML")
    SkillSearchQueries: list[SkillQuery] = Field(
        default_factory=list, description="Skill development priorities"
    )


class KeywordCoverageData(BaseModel):
    """Keyword coverage analysis data."""
    total_keywords: int = Field(default=0, description="Total number of keywords")
    covered_count: int = Field(default=0, description="Number of keywords found")
    coverage_percentage: int = Field(default=0, description="Coverage percentage")
    covered_keywords: list[str] = Field(
        default_factory=list, description="Found keywords"
    )
    missed_keywords: list[str] = Field(
        default_factory=list, description="Missing keywords"
    )


class IndexCalAndGapAnalysisData(BaseModel):
    """Response data for combined index calculation and gap analysis."""
    raw_similarity_percentage: int = Field(
        default=0, description="Raw cosine similarity percentage"
    )
    similarity_percentage: int = Field(
        default=0, description="Transformed similarity percentage"
    )
    keyword_coverage: KeywordCoverageData = Field(
        default_factory=KeywordCoverageData,
        description="Keyword coverage analysis"
    )
    gap_analysis: GapAnalysisData = Field(
        default_factory=GapAnalysisData,
        description="Gap analysis results"
    )


# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


async def _execute_v2_analysis(
    request: IndexCalAndGapAnalysisRequest,
    keywords_list: list[str],
    start_time: float
) -> UnifiedResponse:
    """
    Execute analysis using V2 implementation with optimizations.

    Args:
        request: API request data
        keywords_list: Processed keywords list
        start_time: Request start time for timing

    Returns:
        UnifiedResponse with V2 analysis results
    """
    from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2

    try:
        # Initialize V2 service
        v2_service = CombinedAnalysisServiceV2()

        # Execute combined analysis
        result = await v2_service.analyze(
            resume=request.resume,
            job_description=request.job_description,
            keywords=keywords_list,
            language=request.language
        )

        # Extract data for response formatting
        index_result = result["index_calculation"]
        gap_result = result["gap_analysis"]
        metadata = result.get("metadata", {})

        # Track V2 metrics
        processing_time = time.time() - start_time
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisV2Completed",
            {
                # Core metrics
                "raw_similarity": index_result["raw_similarity_percentage"],
                "transformed_similarity": index_result["similarity_percentage"],
                "keyword_coverage": index_result["keyword_coverage"]["coverage_percentage"],
                "language": request.language,
                "skills_identified": len(gap_result.get("SkillSearchQueries", [])),

                # V2 specific metrics
                "total_time_ms": round(processing_time * 1000, 2),
                "phase_timings": metadata.get("phase_timings_ms", {}),
                "parallel_efficiency": metadata.get("parallel_efficiency", 0),
                "resource_pool_used": metadata.get("resource_pool_used", False),

                # Data size metrics
                "resume_length": len(request.resume),
                "jd_length": len(request.job_description),
                "keywords_count": len(keywords_list),

                # Result metrics
                "matched_keywords_count": len(index_result["keyword_coverage"]["covered_keywords"]),
                "missed_keywords_count": len(index_result["keyword_coverage"]["missed_keywords"]),


            }
        )

        # Create response data
        response_data = IndexCalAndGapAnalysisData(
            raw_similarity_percentage=index_result["raw_similarity_percentage"],
            similarity_percentage=index_result["similarity_percentage"],
            keyword_coverage=KeywordCoverageData(**index_result["keyword_coverage"]),
            gap_analysis=GapAnalysisData(
                CoreStrengths=gap_result.get("CoreStrengths", ""),
                KeyGaps=gap_result.get("KeyGaps", ""),
                QuickImprovements=gap_result.get("QuickImprovements", ""),
                OverallAssessment=gap_result.get("OverallAssessment", ""),
                SkillSearchQueries=[
                    SkillQuery(**skill)
                    for skill in gap_result.get("SkillSearchQueries", [])
                ]
            )
        )

        logger.info(
            f"V2 Index calculation and gap analysis completed: "
            f"similarity={index_result['similarity_percentage']}%, "
            f"coverage={index_result['keyword_coverage']['coverage_percentage']}%, "
            f"skills={len(gap_result.get('SkillSearchQueries', []))}, "
            f"language={request.language}, "
            f"time={processing_time:.2f}s, "
            f"efficiency={metadata.get('parallel_efficiency', 0):.1f}%"
        )

        return create_success_response(data=response_data.model_dump())

    except Exception as e:
        # Handle V2 specific errors, potentially with partial results
        if hasattr(e, 'partial_data') and e.partial_data:
            # Partial failure with some results
            logger.warning(f"V2 analysis returned partial results: {e}")

            partial_data = e.partial_data
            if partial_data.get('index_calculation'):
                # Create response with partial data
                response_data = IndexCalAndGapAnalysisData(
                    raw_similarity_percentage=partial_data['index_calculation']['raw_similarity_percentage'],
                    similarity_percentage=partial_data['index_calculation']['similarity_percentage'],
                    keyword_coverage=KeywordCoverageData(**partial_data['index_calculation']['keyword_coverage']),
                    gap_analysis=GapAnalysisData()  # Empty gap analysis
                )

                response = create_success_response(data=response_data.model_dump())
                response.data["partial_failure"] = True
                response.data["error_details"] = partial_data.get("error_details", {})
                return response

        # Complete failure - re-raise for main error handler
        raise




async def calculate_index_and_analyze_gap(
    request: IndexCalAndGapAnalysisRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """
    Calculate similarity index and perform gap analysis with enhanced error handling.

    Uses V2 implementation (V1 has been removed for code simplification).

    Args:
        request: Combined calculation and analysis request data
        req: FastAPI request object
        settings: Application settings

    Returns:
        UnifiedResponse with calculation and analysis results
    """
    start_time = time.time()

    try:
        # Validate and normalize language (case-insensitive)
        if request.language.lower() == "zh-tw":
            request.language = "zh-TW"
        elif request.language.lower() != "en":
            request.language = "en"

        # Convert keywords to list if string
        keywords_list = (
            request.keywords if isinstance(request.keywords, list)
            else [k.strip() for k in request.keywords.split(",") if k.strip()]
        )

        # Log request
        logger.info(
            f"Index calculation and gap analysis request: "
            f"resume_length={len(request.resume)}, "
            f"job_desc_length={len(request.job_description)}, "
            f"keywords_count={len(keywords_list)}, "
            f"language={request.language}"
        )

        # Execute V2 analysis (V1 has been removed)
        result = await _execute_v2_analysis(
            request, keywords_list, start_time
        )

        return result

    except ValidationError as e:
        # Handle Pydantic validation errors
        error_details = []
        for error in e.errors():
            field = error['loc'][-1] if error['loc'] else 'unknown'
            message = error['msg']
            error_details.append(f"{field}: {message}")

        processing_time = time.time() - start_time
        logger.warning(f"Validation error after {processing_time:.2f}s: {'; '.join(error_details)}")

        monitoring_service.track_event("APIValidationError", {
            "error_fields": [error['loc'][-1] if error['loc'] else 'unknown' for error in e.errors()],
            "processing_time_ms": round(processing_time * 1000, 2),
            "error_count": len(e.errors())
        })

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_validation_error_response(
                field="request",
                message="; ".join(error_details)
            ).model_dump()
        ) from e

    except TimeoutError as e:
        # Handle both TimeoutError and asyncio.TimeoutError
        processing_time = time.time() - start_time
        logger.error(f"Request timeout after {processing_time:.2f}s: {e}")

        monitoring_service.track_event("APITimeoutError", {
            "processing_time_ms": round(processing_time * 1000, 2),
            "error_type": "timeout"
        })

        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=create_error_response(
                code=ErrorCodes.TIMEOUT_ERROR,
                message="Request timed out",
                details="The request took too long to process. Please try again."
            ).model_dump()
        ) from e

    except Exception as e:
        # Check for timeout errors in error message (when asyncio.TimeoutError is wrapped)
        error_message = str(e).lower()
        if "timeout" in error_message or "timed out" in error_message:
            processing_time = time.time() - start_time
            logger.error(f"Request timeout after {processing_time:.2f}s: {e}")

            monitoring_service.track_event("APITimeoutError", {
                "processing_time_ms": round(processing_time * 1000, 2),
                "error_type": "timeout"
            })

            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=create_error_response(
                    code=ErrorCodes.TIMEOUT_ERROR,
                    message="Request timed out",
                    details="The request took too long to process. Please try again."
                ).model_dump()
            ) from e

        # Handle rate limit errors specifically
        if hasattr(e, 'status_code') and e.status_code == 429:
            processing_time = time.time() - start_time
            logger.warning(f"Rate limit exceeded after {processing_time:.2f}s: {e}")

            monitoring_service.track_event("APIRateLimitError", {
                "processing_time_ms": round(processing_time * 1000, 2),
                "error_type": "rate_limit"
            })

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=create_error_response(
                    code=ErrorCodes.RATE_LIMIT_ERROR,
                    message="Rate limit exceeded",
                    details="Too many requests. Please wait and try again."
                ).model_dump()
            ) from e

        # General error handling (simplified without version checking)
        processing_time = time.time() - start_time

        # Log and track error
        logger.error(f"Index cal and gap analysis error: {e}")
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisV2Error",
            {
                "error_message": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round(processing_time * 1000, 2)
            }
        )

        # Return appropriate HTTP error
        if isinstance(e, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_response(
                    code=ErrorCodes.VALIDATION_ERROR,
                    message="Invalid request data",
                    details=str(e)
                ).model_dump()
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    code=ErrorCodes.INTERNAL_ERROR,
                    message="An unexpected error occurred",
                    details="Please try again later"
                ).model_dump()
            ) from e


# Add the actual route endpoint
@router.post(
    "/index-cal-and-gap-analysis",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate similarity index and perform gap analysis",
    description=(
        "Calculate similarity index between resume and job description, "
        "then perform comprehensive gap analysis with improvement recommendations. "
        "Supports both V1 and V2 implementations with feature flags."
    ),
    responses={
        200: {
            "description": "Analysis completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "raw_similarity_percentage": 68,
                            "similarity_percentage": 78,
                            "keyword_coverage": {
                                "total_keywords": 8,
                                "covered_count": 3,
                                "coverage_percentage": 38,
                                "covered_keywords": ["Python", "FastAPI", "Docker"],
                                "missed_keywords": ["React", "Kubernetes", "AWS"]
                            },
                            "gap_analysis": {
                                "CoreStrengths": "<ol><li>Strong Python expertise</li></ol>",
                                "KeyGaps": "<ol><li>Missing React experience</li></ol>",
                                "QuickImprovements": "<ol><li>Add React projects</li></ol>",
                                "OverallAssessment": "<p>Strong backend developer</p>",
                                "SkillSearchQueries": []
                            },

                        },
                        "error": {"code": "", "message": "", "details": ""},
                        "timestamp": "2025-08-03T10:30:00.000Z"
                    }
                }
            }
        },
        400: {"description": "Invalid request data"},
        500: {"description": "Internal server error"}
    }
)
async def index_cal_and_gap_analysis_endpoint(
    request: IndexCalAndGapAnalysisRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """
    Calculate similarity index and perform gap analysis.

    This endpoint combines index calculation and gap analysis into a single request,
    supporting both V1 (sequential) and V2 (parallel) implementations based on
    feature flags.

    Args:
        request: Combined calculation and analysis request data
        req: FastAPI request object
        settings: Application settings

    Returns:
        UnifiedResponse with calculation and analysis results
    """
    return await calculate_index_and_analyze_gap(request, req, settings)
