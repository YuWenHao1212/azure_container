"""
Main FastAPI application entry point.
Following FHS architecture principles.
"""
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.v1 import router as v1_router
from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.middleware.error_capture_middleware import ErrorCaptureMiddleware
from src.middleware.lightweight_monitoring import (
    LightweightMonitoringMiddleware,
)
from src.middleware.monitoring_middleware import MonitoringMiddleware

# Load environment variables from .env file
load_dotenv()

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application with lifecycle management."""

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="""
        Azure FastAPI Resume API - FHS Architecture

        **v2.0 主要更新**:
        - 🎯 最多返回 16 個關鍵字(提升一致性)
        - 📊 一致性大幅提升: 短文本 78%、長文本 60%
        - 🔧 支援 Prompt 版本控制(v1.0.0, v1.2.0, latest)
        - ⚡ 並行處理優化, 效能提升 50%

        **核心功能**:
        - 2 輪交集策略確保結果一致性
        - 智能關鍵字標準化
        - Bubble.io 相容的固定 Schema
        - 完整的錯誤處理和品質警告
        """,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods_list,
        allow_headers=settings.cors_allow_headers_list,
    )

    # Add API Key authentication middleware for Container Apps
    import os
    if os.getenv("CONTAINER_APP_API_KEY"):
        from src.middleware.api_key_middleware import APIKeyMiddleware
        app.add_middleware(APIKeyMiddleware)
        logger.info("API Key authentication enabled")

    # Add monitoring middleware based on environment
    # Use lightweight monitoring by default, old monitoring only if explicitly enabled
    if os.getenv('MONITORING_ENABLED', 'false').lower() == 'true':
        # Heavy monitoring (Application Insights) - only if explicitly enabled
        app.add_middleware(MonitoringMiddleware)
        logger.info("Heavy monitoring (Application Insights) enabled")
    elif os.getenv('LIGHTWEIGHT_MONITORING', 'true').lower() == 'true':
        # Lightweight monitoring - enabled by default
        # Add error capture first (processes errors before monitoring)
        if os.getenv('ERROR_CAPTURE_ENABLED', 'true').lower() == 'true':
            app.add_middleware(ErrorCaptureMiddleware)
            logger.info("Error capture middleware enabled")
        app.add_middleware(LightweightMonitoringMiddleware)
        logger.info("Lightweight monitoring enabled")
    else:
        logger.info("All monitoring disabled")

    # Include API routers
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "success": True,
            "data": {
                "name": settings.app_name,
                "version": settings.app_version,
                "api_v1": f"{settings.api_v1_prefix}/",
                "docs": "/docs",
                "status": "healthy"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # Monitoring stats endpoint (dev/staging only)
    @app.get("/api/v1/monitoring/stats")
    async def get_monitoring_stats():
        """Get current monitoring statistics (non-production only)."""
        if os.getenv("ENVIRONMENT", "local") == "production":
            raise HTTPException(403, "Not available in production")

        # Check if lightweight monitoring is enabled
        if os.getenv('LIGHTWEIGHT_MONITORING', 'true').lower() == 'true':
            # Try to get stats from the global response_tracker
            try:
                from src.middleware.lightweight_monitoring import response_tracker
                stats = response_tracker.get_stats()
                return {
                    "success": True,
                    "data": stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "success": True,
                    "data": {"message": f"Error getting stats: {e!s}"},
                    "timestamp": datetime.utcnow().isoformat()
                }

        return {
            "success": True,
            "data": {"message": "Lightweight monitoring is disabled"},
            "timestamp": datetime.utcnow().isoformat()
        }

    # Error storage info endpoint (dev/staging only)
    @app.get("/api/v1/debug/storage-info")
    async def get_storage_info():
        """Get error storage configuration (non-production only)."""
        if os.getenv("ENVIRONMENT", "local") == "production":
            raise HTTPException(403, "Not available in production")

        # Check if error capture is enabled
        if os.getenv('ERROR_CAPTURE_ENABLED', 'true').lower() == 'true':
            try:
                from src.core.monitoring_config import monitoring_config
                return {
                    "success": True,
                    "data": monitoring_config.get_storage_info(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "success": True,
                    "data": {"message": f"Error getting storage info: {e!s}"},
                    "timestamp": datetime.utcnow().isoformat()
                }

        return {
            "success": True,
            "data": {"message": "Error capture middleware not enabled"},
            "timestamp": datetime.utcnow().isoformat()
        }

    # Recent errors endpoint (dev/staging only)
    @app.get("/api/v1/debug/errors")
    async def get_recent_errors(count: int = 10):
        """Get recent captured errors (non-production only)."""
        if os.getenv("ENVIRONMENT", "local") == "production":
            raise HTTPException(403, "Not available in production")

        # Check if error capture is enabled
        if os.getenv('ERROR_CAPTURE_ENABLED', 'true').lower() == 'true':
            try:
                from src.middleware.error_capture_middleware import error_storage
                errors = error_storage.get_recent_errors(count)
                return {
                    "success": True,
                    "data": {
                        "errors": errors,
                        "count": len(errors)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                return {
                    "success": True,
                    "data": {"message": f"Error getting recent errors: {e!s}"},
                    "timestamp": datetime.utcnow().isoformat()
                }

        return {
            "success": True,
            "data": {"message": "Error capture middleware not enabled"},
            "timestamp": datetime.utcnow().isoformat()
        }

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "success": True,
            "data": {
                "status": "healthy",
                "version": settings.app_version,
                "timestamp": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # Debug endpoint for monitoring
    @app.get("/debug/monitoring")
    async def debug_monitoring():
        """Debug endpoint to check monitoring status."""
        import contextlib
        import io

        from src.debug_monitoring import debug_monitoring as debug_func

        # Capture output
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            debug_func()
        output = f.getvalue()

        return {
            "success": True,
            "data": {
                "debug_output": output.split('\n')
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # Starlette HTTP Exception handler (for method not allowed, etc.)
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request, exc):
        """Handle Starlette HTTP exceptions with unified response format."""
        from src.utils.error_formatting import get_error_context

        logger.warning(f"Starlette HTTP exception: {exc.status_code} - {exc.detail}")

        # Track HTTP errors with context
        if monitoring_service:
            error_category = (
                "ClientError" if 400 <= exc.status_code < 500 else "ServerError"
            )
            error_type = {
                400: "BadRequest",
                401: "Unauthorized",
                403: "Forbidden",
                404: "NotFound",
                405: "MethodNotAllowed",
                408: "RequestTimeout",
                409: "Conflict",
                429: "TooManyRequests",
                500: "InternalServerError",
                502: "BadGateway",
                503: "ServiceUnavailable",
                504: "GatewayTimeout"
            }.get(exc.status_code, f"HTTP_{exc.status_code}")

            # Get enriched error context
            error_context = get_error_context(exc.status_code, request, exc)

            monitoring_service.track_event(
                "HTTPErrorTracked",
                {
                    "status_code": exc.status_code,
                    "error_type": error_type,
                    "error_category": error_category,
                    "error_message": str(exc.detail),
                    **error_context  # Include all context fields
                }
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": {},
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "type": "http_error",
                    "details": {
                        "status_code": exc.status_code,
                        "error_category": (
                            "client_error" if 400 <= exc.status_code < 500
                            else "server_error"
                        )
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    # HTTP Exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions with unified response format."""
        from src.utils.error_formatting import get_error_context

        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

        # Track HTTP errors with categorization and context
        if monitoring_service:
            error_category = (
                "ClientError" if 400 <= exc.status_code < 500 else "ServerError"
            )
            error_type = {
                400: "BadRequest",
                401: "Unauthorized",
                403: "Forbidden",
                404: "NotFound",
                405: "MethodNotAllowed",
                408: "RequestTimeout",
                409: "Conflict",
                429: "TooManyRequests",
                500: "InternalServerError",
                502: "BadGateway",
                503: "ServiceUnavailable",
                504: "GatewayTimeout"
            }.get(exc.status_code, f"HTTP_{exc.status_code}")

            # Get enriched error context
            error_context = get_error_context(exc.status_code, request, exc)

            monitoring_service.track_event(
                "HTTPErrorTracked",
                {
                    "status_code": exc.status_code,
                    "error_type": error_type,
                    "error_category": error_category,
                    "error_message": str(exc.detail),
                    **error_context  # Include all context fields
                }
            )

        # If detail is already a dict (from our custom error responses), use it
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail
            )

        # Otherwise, create unified response format
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": {},
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "type": "http_error",
                    "details": {
                        "status_code": exc.status_code,
                        "error_category": (
                            "client_error" if 400 <= exc.status_code < 500
                            else "server_error"
                        )
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    # Request validation error handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        """Handle request validation errors with unified response format."""

        from src.utils.error_formatting import (
            create_validation_error_response,
            get_error_context,
            get_validation_error_metrics,
        )

        logger.warning(f"Validation error: {exc.errors()}")

        # Check if this is a JSON parsing error
        for error in exc.errors():
            if error.get('type') == 'json_invalid':
                # Return 400 for JSON parsing errors
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "data": {},
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Invalid JSON format",
                            "type": "bad_request",
                            "details": "The request body contains invalid JSON"
                        },
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                )

        # Extract validation error metrics
        error_metrics = get_validation_error_metrics(exc)

        # Get enriched error context
        error_context = get_error_context(422, request, exc)

        # Track error with enhanced context
        if monitoring_service:
            monitoring_service.track_error(
                error_type="VALIDATION_ERROR",
                error_message=(
                    f"Validation failed: {error_metrics['primary_error_type']}"
                ),
                endpoint=f"{request.method} {request.url.path}",
                custom_properties={
                    **error_metrics,  # Include all error metrics
                    **error_context   # Include enhanced context
                }
            )

            # Track detailed validation error event
            monitoring_service.track_event(
                "ValidationErrorDetails",
                {
                    "primary_error_type": error_metrics['primary_error_type'],
                    "all_error_types": error_metrics['all_error_types'],
                    "error_count": error_metrics['error_count'],
                    "affected_fields": error_metrics['error_fields'],
                    **error_context  # Include context here too
                }
            )

        # Create detailed error response
        error_response = create_validation_error_response(exc)

        return JSONResponse(
            status_code=422,  # Use 422 for validation errors (Unprocessable Entity)
            content={
                "success": False,
                "data": {},
                "error": error_response,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Handle all unhandled exceptions."""
        from src.utils.error_formatting import (
            classify_exception,
            create_error_response,
            get_error_context,
        )

        logger.error(f"Unhandled exception: {exc!s}", exc_info=True)

        # Classify the exception
        exc_details = classify_exception(exc)

        # Get enriched error context
        error_context = get_error_context(500, request, exc)

        # Track error with detailed type information and context
        if monitoring_service:
            monitoring_service.track_error(
                error_type=exc_details["exception_type"],
                error_message=str(exc),
                endpoint=f"{request.method} {request.url.path}",
                custom_properties={
                    "exception_category": exc_details["exception_category"],
                    "exception_module": exc_details["exception_module"],
                    "is_retryable": exc_details["is_retryable"],
                    "is_client_error": exc_details["is_client_error"],
                    "is_server_error": exc_details["is_server_error"],
                    **error_context  # Include enhanced context
                }
            )

            # Track a specific event for exception categorization
            monitoring_service.track_event(
                "ExceptionCategorized",
                {
                    "exception_type": exc_details["exception_type"],
                    "exception_category": exc_details["exception_category"],
                    "endpoint": f"{request.method} {request.url.path}",
                    "is_retryable": exc_details["is_retryable"],
                    **error_context  # Include context here too
                }
            )

        # Create error response with details
        error_response = create_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            exc=exc,
            status_code=500,
            include_details=settings.debug
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": {},
                "error": error_response,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    logger.info(f"{settings.app_name} initialized successfully")
    # Add lifecycle event handlers
    @app.on_event("startup")
    async def startup_event():
        """Application startup event handler."""
        logger.info("Starting Azure Container API application")

        # Initialize resource manager
        try:
            from src.core.resource_manager import start_resource_manager
            await start_resource_manager()
            logger.info("Resource manager started successfully")
        except ImportError:
            logger.warning("Resource manager not available")
        except Exception as e:
            logger.error(f"Failed to start resource manager: {e}")

        # Log startup information
        import psutil
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            startup_memory = memory_info.rss / 1024 / 1024
            logger.info(f"Application started with {startup_memory:.1f}MB memory footprint")
        except Exception as e:
            logger.warning(f"Could not get startup memory info: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event handler."""
        logger.info("Shutting down Azure Container API application")

        # Cleanup resource manager
        try:
            from src.core.resource_manager import shutdown_resource_manager
            await shutdown_resource_manager()
            logger.info("Resource manager shutdown completed")
        except ImportError:
            logger.warning("Resource manager not available for shutdown")
        except Exception as e:
            logger.error(f"Error during resource manager shutdown: {e}")

        # Final memory report
        import psutil
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            final_memory = memory_info.rss / 1024 / 1024
            logger.info(f"Application shutdown with {final_memory:.1f}MB final memory usage")
        except Exception as e:
            logger.warning(f"Could not get final memory info: {e}")

    return app


# Create app instance
app = create_app()


# Startup event to preload heavy resources
@app.on_event("startup")
async def startup_event():
    """
    Initialize heavy resources at application startup.
    This ensures all standardization dictionaries are loaded once and reused.
    """
    from src.core.dependencies import initialize_dependencies

    logger.info("🚀 Starting application initialization...")
    start_time = datetime.utcnow()

    try:
        # Initialize all dependencies (standardizers, prompt service, etc.)
        initialize_dependencies()

        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Application startup completed in {elapsed_time:.2f} seconds")

        # Track startup success
        if monitoring_service.is_enabled:
            monitoring_service.track_event(
                "ApplicationStartup",
                {
                    "startup_time_seconds": elapsed_time,
                    "environment": os.getenv("ENVIRONMENT", "unknown"),
                    "version": settings.app_version
                }
            )
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}", exc_info=True)
        # Don't prevent startup, but log the error
        if monitoring_service.is_enabled:
            monitoring_service.track_error(
                error_type="STARTUP_ERROR",
                error_message=str(e),
                endpoint="startup"
            )
