"""
Combined Index Calculation and Gap Analysis API Endpoint.
Handles both similarity calculation and gap analysis in a single request.
"""
import logging
import time
from typing import Any, ClassVar

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field, validator

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.decorators.error_handler import handle_api_errors
from src.models.response import (
    UnifiedResponse,
    create_success_response,
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
        default="",
        description="Category: SKILL (single course, 1-3 months) or FIELD (specialization/certification, 6+ months)"
    )
    description: str = Field(default="", description="Skill description")
    # Course Availability fields (added by CourseAvailabilityChecker)
    has_available_courses: bool | None = Field(
        default=None,
        description="Whether courses are available for this skill"
    )
    course_count: int | None = Field(
        default=None,
        description="Number of available courses for this skill"
    )
    available_course_ids: list[str] | None = Field(
        default=None,
        description="List of available course IDs for direct lookup (max 25)"
    )
    course_details: list[dict[str, Any]] | None = Field(
        default=None,
        description="Detailed course information including name, type, provider, and description"
    )


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
    """
    Response data for combined index calculation and gap analysis.

    Test ID: RS-002-IT - API response format validation
    """
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
    resume_structure: dict[str, Any] | None = Field(
        default=None,
        description="Resume structure analysis (V4 enhancement)"
    )
    resume_enhancement_project: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Recommended projects for resume enhancement (course_id as key)"
    )
    resume_enhancement_certification: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Recommended certifications for resume enhancement (course_id as key)"
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

        # Extract enhancement data from first skill query (if available)
        skill_queries = gap_result.get("SkillSearchQueries", [])
        resume_enhancement_project = {}
        resume_enhancement_certification = {}

        if skill_queries and len(skill_queries) > 0:
            first_skill = skill_queries[0]
            resume_enhancement_project = first_skill.get("resume_enhancement_project", {})
            resume_enhancement_certification = first_skill.get("resume_enhancement_certification", {})
            # Log extraction for debugging
            logger.info(
                f"[Enhancement] Extracted project count: {len(resume_enhancement_project)}, "
                f"certification count: {len(resume_enhancement_certification)}"
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
                    for skill in skill_queries
                ]
            ),
            # V4 Enhancement: Add resume structure if available
            resume_structure=result.get("resume_structure"),
            # V5 Enhancement: Add resume enhancement fields
            resume_enhancement_project=resume_enhancement_project,
            resume_enhancement_certification=resume_enhancement_certification
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

        return create_success_response(
            data=response_data.model_dump(),
            metadata=metadata  # Include timing metadata
        )

    except Exception as e:
        # Log the error with context for lightweight monitoring
        processing_time = time.time() - start_time
        logger.error(
            f"Index cal and gap analysis V2 error: {e}",
            extra={
                "processing_time_ms": round(processing_time * 1000, 2),
                "error_type": type(e).__name__,
                "language": request.language,
                "resume_length": len(request.resume),
                "jd_length": len(request.job_description)
            }
        )
        # Let unified error handler manage the response
        raise


@router.post(
    "/index-cal-and-gap-analysis",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Index and Perform Gap Analysis",
    description=(
        "Combined endpoint for calculating similarity index and performing gap analysis. "
        "Uses V2 implementation with parallel processing for optimal performance."
    ),
    responses={
        200: {
            "description": "Analysis completed successfully",
            "model": UnifiedResponse
        },
        400: {"description": "Invalid request data"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
        503: {"description": "External service unavailable"}
    },
    tags=["Index Calculation", "Gap Analysis"]
)
@handle_api_errors(api_name="index_cal_and_gap_analysis")
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
    start_time = time.time()

    # Log request start
    logger.info(f"Index cal and gap analysis request started for language: {request.language}")

    # Use keywords from request (already validated and processed)
    # The validator in IndexCalAndGapAnalysisRequest already handles:
    # - Converting string to list if needed
    # - Stripping whitespace
    # - Ensuring non-empty
    keywords_list = request.keywords  # Already guaranteed to be a list by validator

    # Use V2 implementation (optimized path)
    return await _execute_v2_analysis(request, keywords_list, start_time)
