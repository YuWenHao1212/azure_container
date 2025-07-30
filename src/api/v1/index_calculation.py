"""
Index Calculation API Endpoints.
Handles resume similarity and keyword coverage analysis functionality.
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
from src.services.index_calculation import IndexCalculationService


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


@router.post(
    "/index-calculation",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Resume-Job Similarity Index",
    description="Calculate similarity percentage and keyword coverage between resume and job description"
)
async def calculate_index(
    request: IndexCalculationRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """
    Calculate similarity index between resume and job description.
    
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
        logger.info(
            f"Index calculation request: "
            f"resume_length={len(request.resume)}, "
            f"job_desc_length={len(request.job_description)}, "
            f"keywords_count={len(request.keywords) if isinstance(request.keywords, list) else len(request.keywords.split(','))}"
        )
        
        # Create service instance
        service = IndexCalculationService()
        
        # Calculate index
        result = await service.calculate_index(
            resume=request.resume,
            job_description=request.job_description,
            keywords=request.keywords
        )
        
        # Track metrics
        processing_time = time.time() - start_time
        monitoring_service.track_event(
            "IndexCalculationCompleted",
            {
                "raw_similarity": result["raw_similarity_percentage"],
                "transformed_similarity": result["similarity_percentage"],
                "keyword_coverage": result["keyword_coverage"]["coverage_percentage"],
                "processing_time_ms": round(processing_time * 1000, 2)
            }
        )
        
        # Create response data
        response_data = IndexCalculationData(
            raw_similarity_percentage=result["raw_similarity_percentage"],
            similarity_percentage=result["similarity_percentage"],
            keyword_coverage=KeywordCoverageData(**result["keyword_coverage"])
        )
        
        logger.info(
            f"Index calculation completed: "
            f"similarity={result['similarity_percentage']}%, "
            f"coverage={result['keyword_coverage']['coverage_percentage']}%, "
            f"time={processing_time:.2f}s"
        )
        
        return create_success_response(data=response_data.model_dump())
        
    except ServiceError as e:
        logger.error(f"Service error in index calculation: {e}")
        monitoring_service.track_event(
            "IndexCalculationServiceError",
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
        logger.error(f"Validation error in index calculation: {e}")
        monitoring_service.track_event(
            "IndexCalculationValidationError",
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
        logger.error(f"Unexpected error in index calculation: {e}", exc_info=True)
        monitoring_service.track_event(
            "IndexCalculationUnexpectedError",
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