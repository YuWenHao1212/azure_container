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
from src.services.gap_analysis import GapAnalysisService
from src.services.index_calculation import IndexCalculationService


# Request/Response Models
class IndexCalAndGapAnalysisRequest(BaseModel):
    """Request model for combined index calculation and gap analysis."""
    resume: str = Field(..., description="Resume content (HTML or plain text)")
    job_description: str = Field(..., description="JD (HTML or plain text)")
    keywords: list[str] | str = Field(..., description="Keywords list or CSV string")
    language: str = Field(default="en", description="Output language (en or zh-TW)")


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

                # Implementation version
                "implementation_version": "v2"
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


async def _execute_v1_analysis(
    request: IndexCalAndGapAnalysisRequest,
    keywords_list: list[str],
    start_time: float
) -> UnifiedResponse:
    """
    Execute analysis using V1 implementation (existing logic).

    Args:
        request: API request data
        keywords_list: Processed keywords list
        start_time: Request start time for timing

    Returns:
        UnifiedResponse with V1 analysis results
    """
    # Step 1: Calculate index
    index_start_time = time.time()
    index_service = IndexCalculationService()
    index_result = await index_service.calculate_index(
        resume=request.resume,
        job_description=request.job_description,
        keywords=keywords_list
    )
    index_end_time = time.time()

    # Extract keyword coverage data
    keyword_coverage = index_result["keyword_coverage"]

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

    # Track V1 metrics
    processing_time = time.time() - start_time
    index_time = index_end_time - index_start_time
    gap_time = gap_end_time - index_end_time

    monitoring_service.track_event(
        "IndexCalAndGapAnalysisV1Completed",
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
            "missed_keywords_count": len(keyword_coverage["missed_keywords"]),

            # Implementation version
            "implementation_version": "v1"
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
                SkillQuery(**skill)
                for skill in gap_result.get("SkillSearchQueries", [])
            ]
        )
    )

    logger.info(
        f"V1 Index calculation and gap analysis completed: "
        f"similarity={index_result['similarity_percentage']}%, "
        f"coverage={keyword_coverage['coverage_percentage']}%, "
        f"skills={len(gap_result.get('SkillSearchQueries', []))}, "
        f"language={request.language}, "
        f"time={processing_time:.2f}s"
    )

    return create_success_response(data=response_data.model_dump())

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

        # Feature flag check for V2 implementation
        from src.utils.feature_flags import FeatureFlags

        # Extract user identifier from request headers (if available)
        user_id = req.headers.get('x-user-id', req.headers.get('x-api-key', ''))
        use_v2 = FeatureFlags.should_use_v2(user_id)

        if use_v2:
            # Use V2 implementation
            result = await _execute_v2_analysis(
                request, keywords_list, start_time
            )
        else:
            # Use V1 implementation (existing)
            result = await _execute_v1_analysis(
                request, keywords_list, start_time
            )

        # Add implementation version to response
        if isinstance(result.data, dict):
            result.data["implementation_version"] = "v2" if use_v2 else "v1"

        return result

    except Exception as e:
        # Enhanced error handling with implementation version info
        implementation_version = "unknown"
        try:
            from src.utils.feature_flags import FeatureFlags
            user_id = req.headers.get('x-user-id', req.headers.get('x-api-key', ''))
            implementation_version = "v2" if FeatureFlags.should_use_v2(user_id) else "v1"
        except Exception as ex:
            logger.warning(f"Failed to determine implementation version: {ex}")

        processing_time = time.time() - start_time

        # Log and track error with version info
        logger.error(f"Index cal and gap analysis error ({implementation_version}): {e}")
        monitoring_service.track_event(
            f"IndexCalAndGapAnalysis{implementation_version.upper()}Error",
            {
                "error_message": str(e),
                "error_type": type(e).__name__,
                "processing_time_ms": round(processing_time * 1000, 2),
                "implementation_version": implementation_version
            }
        )

        # Return appropriate HTTP error
        if isinstance(e, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_response(
                    code="VALIDATION_ERROR",
                    message="Invalid request data",
                    details=str(e)
                ).model_dump()
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    code="INTERNAL_ERROR",
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
                            "implementation_version": "v2"
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
