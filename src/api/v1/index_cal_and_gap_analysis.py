"""
Combined Index Calculation and Gap Analysis API Endpoint.
Handles both similarity calculation and gap analysis in a single request.
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.models.response import (
    UnifiedResponse,
    create_error_response,
    create_success_response,
)
from src.services.exceptions import ServiceError
from src.services.gap_analysis import GapAnalysisService
from src.services.index_calculation import IndexCalculationService


# Request/Response Models
class IndexCalAndGapAnalysisRequest(BaseModel):
    """Request model for combined index calculation and gap analysis."""
    resume: str = Field(..., description="Resume content (HTML or plain text)")
    job_description: str = Field(..., description="Job description (HTML or plain text)")
    keywords: list[str] | str = Field(..., description="Keywords list or comma-separated string")
    language: str = Field(default="en", description="Output language (en or zh-TW)")


class SkillQuery(BaseModel):
    """Skill development query model."""
    skill_name: str = Field(default="", description="Skill name")
    skill_category: str = Field(default="", description="Skill category (TECHNICAL or NON_TECHNICAL)")
    description: str = Field(default="", description="Skill description")


class GapAnalysisData(BaseModel):
    """Gap analysis response data."""
    CoreStrengths: str = Field(default="", description="Core strengths HTML")
    KeyGaps: str = Field(default="", description="Key gaps HTML")
    QuickImprovements: str = Field(default="", description="Quick improvements HTML")
    OverallAssessment: str = Field(default="", description="Overall assessment HTML")
    SkillSearchQueries: list[SkillQuery] = Field(default_factory=list, description="Skill development priorities")


class KeywordCoverageData(BaseModel):
    """Keyword coverage analysis data."""
    total_keywords: int = Field(default=0, description="Total number of keywords")
    covered_count: int = Field(default=0, description="Number of keywords found")
    coverage_percentage: int = Field(default=0, description="Coverage percentage")
    covered_keywords: list[str] = Field(default_factory=list, description="Found keywords")
    missed_keywords: list[str] = Field(default_factory=list, description="Missing keywords")


class IndexCalAndGapAnalysisData(BaseModel):
    """Response data for combined index calculation and gap analysis."""
    raw_similarity_percentage: int = Field(default=0, description="Raw cosine similarity percentage")
    similarity_percentage: int = Field(default=0, description="Transformed similarity percentage")
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


@router.post(
    "/index-cal-and-gap-analysis",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Index and Perform Gap Analysis",
    description="Calculate similarity index and perform comprehensive gap analysis between resume and job description"
)
async def calculate_index_and_analyze_gap(
    request: IndexCalAndGapAnalysisRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """
    Calculate similarity index and perform gap analysis.
    
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
        
        # Log request
        logger.info(
            f"Index calculation and gap analysis request: "
            f"resume_length={len(request.resume)}, "
            f"job_desc_length={len(request.job_description)}, "
            f"keywords_count={len(request.keywords) if isinstance(request.keywords, list) else len(request.keywords.split(','))}, "
            f"language={request.language}"
        )
        
        # Step 1: Calculate index
        index_start_time = time.time()
        index_service = IndexCalculationService()
        index_result = await index_service.calculate_index(
            resume=request.resume,
            job_description=request.job_description,
            keywords=request.keywords
        )
        index_end_time = time.time()
        
        # Extract keyword coverage data
        keyword_coverage = index_result["keyword_coverage"]
        
        # Convert keywords to list if string
        keywords_list = (
            request.keywords if isinstance(request.keywords, list)
            else [k.strip() for k in request.keywords.split(",") if k.strip()]
        )
        
        # Step 2: Perform gap analysis
        gap_service = GapAnalysisService()
        gap_result = await gap_service.analyze_gap(
            job_description=request.job_description,
            resume=request.resume,
            job_keywords=keywords_list,
            matched_keywords=keyword_coverage["covered_keywords"],
            missing_keywords=keyword_coverage["missed_keywords"],
            language=request.language
        )
        gap_end_time = time.time()
        
        # Track metrics
        processing_time = time.time() - start_time
        index_time = index_end_time - index_start_time
        gap_time = gap_end_time - index_end_time
        
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisCompleted",
            {
                # Existing metrics
                "raw_similarity": index_result["raw_similarity_percentage"],
                "transformed_similarity": index_result["similarity_percentage"],
                "keyword_coverage": keyword_coverage["coverage_percentage"],
                "language": request.language,
                "skills_identified": len(gap_result.get("SkillSearchQueries", [])),
                
                # Time metrics
                "total_time_ms": round(processing_time * 1000, 2),
                "index_calc_time_ms": round(index_time * 1000, 2),
                "gap_analysis_time_ms": round(gap_time * 1000, 2),
                
                # Data size metrics
                "resume_length": len(request.resume),
                "jd_length": len(request.job_description),
                "keywords_count": len(keywords_list),
                
                # Result metrics
                "matched_keywords_count": len(keyword_coverage["covered_keywords"]),
                "missed_keywords_count": len(keyword_coverage["missed_keywords"])
            }
        )
        
        # Create response data
        response_data = IndexCalAndGapAnalysisData(
            raw_similarity_percentage=index_result["raw_similarity_percentage"],
            similarity_percentage=index_result["similarity_percentage"],
            keyword_coverage=KeywordCoverageData(**keyword_coverage),
            gap_analysis=GapAnalysisData(
                CoreStrengths=gap_result.get("CoreStrengths", ""),
                KeyGaps=gap_result.get("KeyGaps", ""),
                QuickImprovements=gap_result.get("QuickImprovements", ""),
                OverallAssessment=gap_result.get("OverallAssessment", ""),
                SkillSearchQueries=[
                    SkillQuery(**skill) for skill in gap_result.get("SkillSearchQueries", [])
                ]
            )
        )
        
        logger.info(
            f"Index calculation and gap analysis completed: "
            f"similarity={index_result['similarity_percentage']}%, "
            f"coverage={keyword_coverage['coverage_percentage']}%, "
            f"skills={len(gap_result.get('SkillSearchQueries', []))}, "
            f"language={request.language}, "
            f"time={processing_time:.2f}s"
        )
        
        return create_success_response(data=response_data.model_dump())
        
    except ServiceError as e:
        logger.error(f"Service error in index cal and gap analysis: {e}")
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisServiceError",
            {
                "error_message": str(e),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="SERVICE_ERROR",
                message="Service temporarily unavailable",
                details=str(e)
            ).model_dump()
        )
        
    except ValueError as e:
        logger.error(f"Validation error in index cal and gap analysis: {e}")
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisValidationError",
            {
                "error_message": str(e),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code="VALIDATION_ERROR",
                message="Invalid request data",
                details=str(e)
            ).model_dump()
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in index cal and gap analysis: {e}", exc_info=True)
        monitoring_service.track_event(
            "IndexCalAndGapAnalysisUnexpectedError",
            {
                "error_message": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details="Please try again later"
            ).model_dump()
        )