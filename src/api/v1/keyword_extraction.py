"""
Keyword Extraction API Endpoints.
Implements Work Item #347: 建立 API 端點

Handles job description keyword extraction functionality with:
- POST /api/v1/extract-jd-keywords endpoint
- Integration with KeywordExtractionService (Work Item #343)
- Bubble.io compatible responses
- Comprehensive error handling (400, 500, 503)
"""
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.core.config import get_settings
from src.core.monitoring.storage.failure_storage import failure_storage
from src.core.monitoring_service import monitoring_service
from src.decorators.error_handler import handle_api_errors
from src.models.keyword_extraction import (
    KeywordExtractionRequest,
)
from src.models.response import (
    ErrorDetail,
    UnifiedResponse,
    WarningInfo,
    create_error_response,
    create_success_response,
)
from src.services.exceptions import (
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    UnsupportedLanguageError,
    ValidationError,
)
from src.services.keyword_extraction_v2 import (
    get_keyword_extraction_service_v2,
)
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
)

# Setup logging
logger = logging.getLogger(__name__)

# Create router for keyword extraction endpoints
router = APIRouter()


@router.post(
    "/extract-jd-keywords",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract keywords from job description",
    description=(
        "Extract and analyze keywords from job descriptions using "
        "2-round intersection strategy with Azure OpenAI GPT-4o-2"
    ),
    responses={
        200: {
            "description": "Keywords extracted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "keywords": ["Python", "FastAPI", "Machine Learning"],
                            "keyword_count": 3,
                            "confidence_score": 0.85,
                            "extraction_method": "2_round_intersection",
                            "processing_time_ms": 2500
                        },
                        "error": {"code": "", "message": "", "details": ""},
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Job description too short",
                            "details": "Job description must be at least 50 characters"
                        },
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        },
        408: {
            "description": "Request timeout",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "TIMEOUT_ERROR",
                            "message": "Request processing timeout",
                            "details": "The request took too long to process"
                        },
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        },
        429: {
            "description": "Too many requests",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "RATE_LIMIT_ERROR",
                            "message": "Rate limit exceeded",
                            "details": "Please try again later"
                        },
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "INTERNAL_SERVER_ERROR",
                            "message": "Processing failed due to internal error",
                            "details": ""
                        },
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        },
        503: {
            "description": "Azure OpenAI service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "SERVICE_UNAVAILABLE",
                            "message": (
                                "Azure OpenAI service is temporarily "
                                "unavailable"
                            ),
                            "details": "Please try again later"
                        },
                        "timestamp": "2025-07-01T13:09:40.123Z"
                    }
                }
            }
        }
    },
    tags=["Keyword Extraction"]
)
@handle_api_errors(api_name="keyword_extraction")
async def extract_jd_keywords(
    request: KeywordExtractionRequest,
    settings = Depends(get_settings),
    http_request: Request = None
) -> UnifiedResponse:
    """
    Extract keywords from job description using 2-round intersection strategy.

    **Work Item**: #347 (建立 API 端點)
    **Parent**: User Story #338 (建構 API 端點)
    **Dependencies**:
    - Work Item #343: 實作關鍵字提取核心邏輯 ✅
    - Work Item #346: 建立請求/回應模型 ✅
    - Work Item #340: 實作 OpenAI 客戶端 ✅

    **Technical Features**:
    - 2-round intersection strategy for consistent results
    - Parallel processing for ~50% performance improvement
    - Azure OpenAI GPT-4o-2 integration
    - Intelligent supplementation when intersection < 12 keywords
    - Comprehensive error handling and logging
    - Bubble.io compatible response format

    **Parameters**:
    - **job_description**: Job description text (minimum 50 characters)
    - **max_keywords**: Maximum keywords to extract (5-30, default: 15)
    - **prompt_version**: Prompt version to use (default: "latest")

    **Response**:
    Returns UnifiedResponse with KeywordExtractionData containing:
    - keywords: List of extracted keywords
    - keyword_count: Number of keywords extracted
    - confidence_score: Extraction confidence (0.6-0.95)
    - extraction_method: "2_round_intersection"
    - intersection_stats: Detailed extraction statistics
    - warning: Quality warnings if any
    - processing_time_ms: Total processing time

    **Error Codes**:
    - 400: VALIDATION_ERROR - Invalid input parameters
    - 408: TIMEOUT_ERROR - Request processing timeout
    - 429: RATE_LIMIT_ERROR - Rate limit exceeded
    - 500: INTERNAL_SERVER_ERROR - Unexpected processing error
    - 503: SERVICE_UNAVAILABLE - Azure OpenAI service issues
    """
    request_start = time.time()
    timing_breakdown = {
        "validation_ms": 0,
        "language_detection_ms": 0,
        "keyword_extraction_ms": 0,
        "total_ms": 0
    }

    logger.info(
        f"Keyword extraction request received: "
        f"job_description_length={len(request.job_description)}, "
        f"max_keywords={request.max_keywords}, "
        f"prompt_version={request.prompt_version}"
    )

    # Get HTTP headers for model selection (if enabled)
    headers = {}
    if http_request:
        headers = dict(http_request.headers)

    # Use smart LLM client selection (hybrid approach)
    from src.services.llm_factory import get_llm_client_smart, get_llm_info

    llm_client = get_llm_client_smart(
        api_name="keywords",
        request_model=getattr(request, 'llm_model', None),  # Future: add to request
        # model
        headers=headers
    )

    # Log which model is being used
    llm_info = get_llm_info(llm_client)
    logger.info(f"Using LLM model: {llm_info['model']} from {llm_info['region']}")

    # Create V2 service with dynamic LLM client
    service = get_keyword_extraction_service_v2(
        llm_client=llm_client,  # Pass the dynamically selected client
        prompt_version=request.prompt_version,
        enable_cache=True,  # ✅ Cache enabled for production performance
        cache_ttl_minutes=60,  # Cache for 1 hour
        enable_parallel_processing=True  # ✅ Keep parallel processing for speed
    )

    try:
        # Validate request using Work Item #346 validator
        validation_start = time.time()
        validated_data = await service.validate_input(request.dict())
        timing_breakdown["validation_ms"] = (time.time() - validation_start) * 1000

        logger.info(
            f"Request validation passed in "
            f"{timing_breakdown['validation_ms']:.2f}ms"
        )

        # Process keyword extraction using Work Item #343 core logic
        extraction_start = time.time()
        result = await service.process(validated_data)
        timing_breakdown["keyword_extraction_ms"] = (
            (time.time() - extraction_start) * 1000
        )

        # Calculate total processing time
        timing_breakdown["total_ms"] = (time.time() - request_start) * 1000
        result['total_processing_time_ms'] = round(timing_breakdown["total_ms"], 2)
        result['timing_breakdown'] = timing_breakdown

        # Track detailed processing time metrics
        monitoring_service.track_metric(
            "keyword_extraction_processing_time",
            timing_breakdown["total_ms"],
            {
                "language": result.get('detected_language', 'unknown'),
                "prompt_version": result.get(
                    'prompt_version_used', request.prompt_version
                ),
                "jd_length": len(request.job_description),
                "keyword_count": result.get('keyword_count', 0),
                "validation_ms": timing_breakdown["validation_ms"],
                "extraction_ms": timing_breakdown["keyword_extraction_ms"]
            }
        )

        logger.info(
            f"Keyword extraction completed successfully: "
            f"keywords={result['keyword_count']}, "
            f"method={result['extraction_method']}, "
            f"time={timing_breakdown['total_ms']:.2f}ms, "
            f"confidence={result['confidence_score']}"
        )

        # Log detailed timing breakdown for performance analysis
        logger.debug(
            f"Timing breakdown - "
            f"validation: {timing_breakdown['validation_ms']:.2f}ms, "
            f"extraction: {timing_breakdown['keyword_extraction_ms']:.2f}ms, "
            f"total: {timing_breakdown['total_ms']:.2f}ms"
        )

        # Check for warnings in intersection stats and create appropriate response
        warning_info = WarningInfo()
        intersection_stats = result.get('intersection_stats', {})

        if intersection_stats.get('warning', False):
            warning_info = WarningInfo(
                has_warning=True,
                message=intersection_stats.get(
                    'warning_message', 'Quality warning detected'
                ),
                expected_minimum=12,
                actual_extracted=result.get('keyword_count', 0),
                suggestion=(
                    "Consider providing a more detailed job description with "
                    "specific requirements and technologies"
                )
            )

        # Track extracted keywords for analysis (rolling window of last 100)
        if result.get('keywords'):
            monitoring_service.track_event(
                "KeywordsExtracted",
                {
                    "keywords": result['keywords'],
                    "keyword_count": len(result['keywords']),
                    "language": result.get('detected_language', 'unknown'),
                    "extraction_method": result.get('extraction_method', 'unknown'),
                    "client_type": (
                        getattr(request.state, 'client_type', 'unknown')
                        if hasattr(request, 'state') else 'unknown'
                    ),
                    "correlation_id": (
                        getattr(request.state, 'correlation_id', '')
                        if hasattr(request, 'state') else ''
                    )
                }
            )

        # Create response with warning information
        return UnifiedResponse(
            success=True,
            data=result,
            error=ErrorDetail(),
            warning=warning_info,
            timestamp=datetime.utcnow().isoformat()
        )

    except UnsupportedLanguageError as e:
        # Store failure for analysis
        await failure_storage.store_failure(
            category="unsupported_language",
            job_description=request.job_description,
            failure_reason=str(e),
            additional_info={
                "detected_language": e.detected_language,
                "supported_languages": e.supported_languages,
                "confidence": getattr(e, 'confidence', None)
            }
        )
        # Re-raise for decorator to handle
        raise

    except ValueError as e:
        # Store failure for analysis
        await failure_storage.store_failure(
            category="validation_error",
            job_description=request.job_description,
            failure_reason=str(e),
            additional_info={
                "max_keywords": request.max_keywords,
                "prompt_version": request.prompt_version
            }
        )
        # Convert to ValidationError for consistent handling
        raise ValidationError(str(e)) from e

    except AzureOpenAIRateLimitError as e:
        # Store API failure
        await failure_storage.store_failure(
            category="rate_limit_error",
            job_description=request.job_description,
            failure_reason=str(e),
            additional_info={
                "error_type": type(e).__name__
            }
        )
        # Convert to RateLimitError for decorator to handle
        raise RateLimitError(str(e)) from e

    except (AzureOpenAIAuthError, AzureOpenAIServerError) as e:
        # Store API failure
        await failure_storage.store_failure(
            category="api_error",
            job_description=request.job_description,
            failure_reason=str(e),
            additional_info={
                "error_type": type(e).__name__
            }
        )
        # Convert to ExternalServiceError for decorator to handle
        raise ExternalServiceError(f"Azure OpenAI service error: {e}") from e

    except AzureOpenAIError as e:
        # Store failure and re-raise as ProcessingError
        await failure_storage.store_failure(
            category="openai_error",
            job_description=request.job_description,
            failure_reason=str(e),
            additional_info={"error_type": type(e).__name__}
        )
        raise ProcessingError(f"OpenAI processing error: {e}") from e

    except TimeoutError:
        # Re-raise TimeoutError for decorator to handle (504)
        raise

    except Exception as e:
        # Log unexpected errors but let decorator handle response
        logger.error(f"Unexpected error during keyword extraction: {e}", exc_info=True)
        raise

    finally:
        # Cleanup - close service if needed
        if hasattr(service, 'close'):
            try:
                await service.close()
            except Exception as e:
                logger.warning(f"Error closing service: {e}")


# Health check endpoint removed - using unified /health endpoint in main.py
# This function is no longer needed as we have a single health check endpoint


@router.get(
    "/version",
    response_model=UnifiedResponse,
    summary="Get keyword extraction service version",
    description="Get detailed version and capability information",
    tags=["Service Info"]
)
async def keyword_extraction_version() -> UnifiedResponse:
    """
    Get version and capability information for keyword extraction service.

    Returns detailed information about:
    - Service version and build info
    - Implemented Work Items
    - Available features and capabilities
    - Performance characteristics
    """
    version_data = {
        "service": "keyword_extraction",
        "version": "2.0.0",
        "build_date": "2025-07-03",
        "work_items_implemented": [
            {
                "id": "#340",
                "title": "實作 OpenAI 客戶端",
                "status": "completed"
            },
            {
                "id": "#343",
                "title": "實作關鍵字提取核心邏輯",
                "status": "completed"
            },
            {
                "id": "#346",
                "title": "建立請求/回應模型",
                "status": "completed"
            },
            {
                "id": "#347",
                "title": "建立 API 端點",
                "status": "completed"
            }
        ],
        "capabilities": {
            "extraction_method": "2_round_intersection",
            "parallel_processing": True,
            "caching_mechanism": True,
            "max_keywords_per_round": 25,
            "min_intersection_size": 12,
            "confidence_score_range": "0.6-0.95",
            "azure_openai_model": "gpt-4o-2",
            "bubble_io_compatible": True,
            "bilingual_support": ["en", "zh-TW"],
            "performance_improvements": {
                "parallel_processing_speedup": "~50%",
                "cache_speedup": "~100x for repeated requests",
                "cache_ttl_minutes": 60
            },
            "performance_target": "<4s processing time with optimizations",
            "yaml_based_configuration": True,
            "prompt_version_support": True,
            "available_prompt_versions": ["1.0.0", "1.2.0", "1.3.0", "latest"]
        },
        "api_endpoints": {
            "extract_keywords": "POST /api/v1/extract-jd-keywords",
            "health_check": "GET /health",
            "version_info": "GET /api/v1/version",
            "prompt_version": "GET /api/v1/prompt-version"
        }
    }

    return create_success_response(version_data)


@router.get(
    "/prompt-version",
    response_model=UnifiedResponse,
    summary="Get active prompt version for keyword extraction",
    description=(
        "Get the currently active prompt version and configuration details "
        "for keyword extraction task"
    ),
    tags=["Service Info"]
)
async def get_keyword_extraction_prompt_version(
    language: str = "en",
    settings = Depends(get_settings)
) -> UnifiedResponse:
    """
    Get active prompt version information for keyword extraction task.

    Parameters:
    - language: Language code ("en" or "zh-TW")

    Returns:
    - Task name (keyword_extraction)
    - Active prompt version details
    - LLM configuration
    - Available versions
    """
    try:
        from src.services.unified_prompt_service import get_unified_prompt_service

        # Get the prompt service
        prompt_service = get_unified_prompt_service()

        # Task is hardcoded to keyword_extraction for this endpoint
        task = "keyword_extraction"

        # Get active version
        active_version = prompt_service.get_active_version(language)

        # Get available versions
        available_versions = prompt_service.list_versions(language)

        # Get prompt config for active version if exists
        prompt_info = {}
        if active_version:
            try:
                config = prompt_service.get_prompt_config(language, active_version)
                prompt_info = {
                    "version": config.version,
                    "status": config.metadata.status,
                    "author": config.metadata.author,
                    "description": config.metadata.description,
                    "created_at": config.metadata.created_at,
                    "llm_config": {
                        "temperature": config.llm_config.temperature,
                        "max_tokens": config.llm_config.max_tokens,
                        "seed": config.llm_config.seed,
                        "top_p": config.llm_config.top_p
                    },
                    "multi_round_enabled": config.multi_round_config.get(
                        "enabled", False
                    )
                }
            except Exception as e:
                logger.warning(f"Failed to load prompt config: {e}")

        response_data = {
            "task": task,
            "language": language,
            "active_version": active_version,
            "available_versions": available_versions,
            "prompt_info": prompt_info,
            "default_request_version": "1.4.0",  # From KeywordExtractionRequest default
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(
            f"Retrieved prompt version info for task={task}, language={language}"
        )
        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Failed to get prompt version: {e!s}")

        error_response = create_error_response(
            code="PROMPT_VERSION_ERROR",
            message="無法取得提示版本資訊",
            details=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.dict()
        ) from None


# Health check endpoint removed - using unified /health endpoint in main.py
# This duplicate function has been removed to avoid conflicts
