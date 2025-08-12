"""
Unit tests for error handler factory.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.constants.error_codes import ErrorCodes
from src.services.error_handler_factory import ErrorHandlerFactory, get_error_handler_factory
from src.services.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    ValidationError,
)


class TestErrorHandlerFactory:
    """Test error handler factory functionality."""

    @pytest.fixture
    def factory(self):
        """Create error handler factory instance."""
        with patch("src.services.error_handler_factory.monitoring_service"):
            return ErrorHandlerFactory()

    def test_singleton_instance(self):
        """Test that factory uses singleton pattern."""
        factory1 = get_error_handler_factory()
        factory2 = get_error_handler_factory()
        assert factory1 is factory2

    def test_classify_validation_error(self, factory):
        """Test classification of validation errors."""
        exc = ValidationError("Invalid input")
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.VALIDATION_ERROR
        assert error_info["status_code"] == 422

    def test_classify_rate_limit_error(self, factory):
        """Test classification of rate limit errors."""
        exc = RateLimitError("Rate limit exceeded")
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED
        assert error_info["status_code"] == 429

    def test_classify_authentication_error_401(self, factory):
        """Test classification of 401 authentication errors."""
        exc = AuthenticationError("Invalid token", status_code=401)
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.AUTH_TOKEN_INVALID
        assert error_info["status_code"] == 401

    def test_classify_authentication_error_403(self, factory):
        """Test classification of 403 authentication errors."""
        exc = AuthenticationError("Insufficient permissions", status_code=403)
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.AUTH_INSUFFICIENT_PERMISSIONS
        assert error_info["status_code"] == 403

    def test_classify_external_service_error(self, factory):
        """Test classification of external service errors."""
        exc = ExternalServiceError("Service unavailable")
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE
        assert error_info["status_code"] == 503

    def test_classify_generic_exception(self, factory):
        """Test classification of generic exceptions."""
        exc = Exception("Unknown error")
        error_info = factory._classify_exception(exc)
        assert error_info["error_code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert error_info["status_code"] == 500

    def test_handle_exception_with_validation_error(self, factory):
        """Test handling validation error."""
        exc = ValidationError("Invalid input", field_errors={"field1": ["error1"]})
        context = {"api_name": "test_api", "endpoint": "/test"}

        response = factory.handle_exception(exc, context)

        assert response["success"] is False
        assert response["error"]["has_error"] is True
        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["error"]["field_errors"] == {"field1": ["error1"]}
        assert response["_status_code"] == 422

    def test_handle_exception_with_custom_message(self, factory):
        """Test handling exception with custom message."""
        exc = ProcessingError("Custom error message")
        context = {"api_name": "test_api", "endpoint": "/test"}

        response = factory.handle_exception(exc, context)

        assert response["error"]["message"] == "Custom error message"

    def test_handle_exception_with_debug_mode(self, factory):
        """Test handling exception in debug mode."""
        exc = ValueError("Test error")
        context = {"api_name": "test_api", "endpoint": "/test", "debug": True}

        response = factory.handle_exception(exc, context)

        assert "ValueError: Test error" in response["error"]["details"]

    def test_handle_exception_without_debug_mode(self, factory):
        """Test handling exception without debug mode."""
        exc = ValueError("Test error")
        context = {"api_name": "test_api", "endpoint": "/test", "debug": False}

        response = factory.handle_exception(exc, context)

        assert response["error"]["details"] == ""

    @patch("src.services.error_handler_factory.logger")
    def test_logging_on_exception(self, mock_logger, factory):
        """Test that exceptions are logged."""
        exc = Exception("Test error")
        context = {"api_name": "test_api", "endpoint": "/test"}

        factory.handle_exception(exc, context)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "SYSTEM_INTERNAL_ERROR" in str(call_args)

    def test_error_response_structure(self, factory):
        """Test that error response has correct structure."""
        exc = ValidationError("Test error")
        context = {"api_name": "test_api", "endpoint": "/test"}

        response = factory.handle_exception(exc, context)

        # Check required fields
        assert "success" in response
        assert "data" in response
        assert "error" in response
        assert "warning" in response
        assert "timestamp" in response
        assert "_status_code" in response

        # Check error structure
        assert "has_error" in response["error"]
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert "details" in response["error"]
        assert "field_errors" in response["error"]

        # Check warning structure
        assert "has_warning" in response["warning"]
        assert "message" in response["warning"]
