"""
Unified error handling factory module.

This module provides centralized error handling logic for all API endpoints,
similar to the successful pattern used in LLM Factory.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import status

from src.constants.error_codes import ERROR_CODE_MAPPING, ErrorCodes
from src.core.monitoring_logger import get_business_logger
from src.services.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    ServiceError,
    UnsupportedLanguageError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class ErrorHandlerFactory:
    """
    Unified error handling factory.

    Responsible for:
    1. Exception classification and mapping
    2. Error response generation
    3. Monitoring and logging
    4. Error context management
    """

    def __init__(self):
        """Initialize error handling factory."""
        self.business_logger = get_business_logger()
        self._init_error_mappings()

    def _init_error_mappings(self):
        """Initialize exception to error code mappings."""
        self.exception_mappings = {
            # Validation errors -> 422
            ValidationError: {
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_code": ErrorCodes.VALIDATION_ERROR,
            },
            ValueError: {
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_code": ErrorCodes.VALIDATION_ERROR,
            },

            # Unsupported language errors -> 422
            UnsupportedLanguageError: {
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_code": ErrorCodes.UNSUPPORTED_LANGUAGE,
            },

            # Authentication errors -> 401/403
            AuthenticationError: {
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "error_code": ErrorCodes.AUTH_TOKEN_INVALID,
            },

            # Rate limit errors -> 429
            RateLimitError: {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "error_code": ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED,
            },

            # External service errors -> 502/503
            ExternalServiceError: {
                "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                "error_code": ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE,
            },

            # Timeout errors -> 504
            TimeoutError: {
                "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
                "error_code": ErrorCodes.EXTERNAL_SERVICE_TIMEOUT,
            },

            # Processing errors -> 500
            ProcessingError: {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_code": ErrorCodes.SYSTEM_INTERNAL_ERROR,
            },

            # Default -> 500
            Exception: {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_code": ErrorCodes.SYSTEM_INTERNAL_ERROR,
            },
        }

    def handle_exception(
        self,
        exc: Exception,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle exception and return unified format error response.

        Args:
            exc: The caught exception
            context: Error context information

        Returns:
            Unified format error response dictionary
        """
        # 1. Classify exception
        error_info = self._classify_exception(exc)

        # 2. Get error message
        error_message = self._get_error_message(exc, error_info["error_code"])

        # 3. Log and monitor
        self._log_and_monitor(exc, error_info, context)

        # 4. Generate response
        return self._create_error_response(
            error_code=error_info["error_code"],
            message=error_message,
            details=self._get_error_details(exc, context),
            field_errors=self._extract_field_errors(exc),
            status_code=error_info["status_code"]
        )

    def _classify_exception(self, exc: Exception) -> dict[str, Any]:
        """Classify exception and return corresponding error info."""
        # Check if exception is a ServiceError with pre-set values
        if isinstance(exc, ServiceError) and exc.error_code and exc.status_code:
            return {
                "error_code": exc.error_code,
                "status_code": exc.status_code
            }

        # Check from most specific to most general
        for exc_type, error_info in self.exception_mappings.items():
            if isinstance(exc, exc_type):
                return error_info

        # Default error
        return self.exception_mappings[Exception]

    def _get_error_message(self, exc: Exception, error_code: str) -> str:
        """Get user-friendly error message."""
        # If exception has custom message, use it
        if hasattr(exc, 'message') and exc.message:
            return exc.message

        # Check for specific exception types with special handling
        if isinstance(exc, ValueError):
            return str(exc) if str(exc) else "Invalid input value"

        # Otherwise use error code corresponding standard message
        error_info = ERROR_CODE_MAPPING.get(error_code, {})
        return error_info.get("message", str(exc) if str(exc) else "Unknown error")

    def _get_error_details(
        self,
        exc: Exception,
        context: dict[str, Any]
    ) -> str:
        """Get error details (only in debug mode)."""
        if context.get('debug', False):
            return f"{type(exc).__name__}: {exc!s}"
        return ""

    def _extract_field_errors(self, exc: Exception) -> dict[str, list]:
        """Extract field-level errors."""
        if hasattr(exc, 'field_errors'):
            return exc.field_errors
        return {}

    def _log_and_monitor(
        self,
        exc: Exception,
        error_info: dict[str, Any],
        context: dict[str, Any]
    ):
        """Log error and send monitoring events."""
        # Log error
        logger.error(
            f"API Error: {error_info['error_code']} - {exc}",
            extra={
                "error_code": error_info["error_code"],
                "status_code": error_info["status_code"],
                "api_name": context.get("api_name"),
                "endpoint": context.get("endpoint"),
            },
            exc_info=True
        )

        # Send lightweight monitoring event
        try:
            self.business_logger.error(
                f"API Error: {error_info['error_code']} - {type(exc).__name__}: {exc}",
                extra={
                    "error_code": error_info["error_code"],
                    "status_code": error_info["status_code"],
                    "api_name": context.get("api_name"),
                    "endpoint": context.get("endpoint"),
                    "exception_type": type(exc).__name__,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log error in business logger: {e}")

    def _create_error_response(
        self,
        error_code: str,
        message: str,
        details: str = "",
        field_errors: dict[str, list] | None = None,
        status_code: int = 500
    ) -> dict[str, Any]:
        """Create unified format error response."""
        return {
            "success": False,
            "data": {},
            "error": {
                "has_error": True,
                "code": error_code,
                "message": message,
                "details": details,
                "field_errors": field_errors or {}
            },
            "warning": {
                "has_warning": False,
                "message": "",
                "expected_minimum": 0,
                "actual_extracted": 0,
                "suggestion": ""
            },
            "timestamp": datetime.utcnow().isoformat(),
            "_status_code": status_code  # Include status code for decorator use
        }


# Singleton instance
_error_handler_factory = None


def get_error_handler_factory() -> ErrorHandlerFactory:
    """Get error handler factory singleton."""
    global _error_handler_factory
    if _error_handler_factory is None:
        _error_handler_factory = ErrorHandlerFactory()
    return _error_handler_factory
