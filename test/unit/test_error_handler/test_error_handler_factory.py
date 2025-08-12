"""
Unit tests for error handler factory.
Tests: ERR-005-UT to ERR-011-UT, ERR-015-UT
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.constants.error_codes import ErrorCodes
from src.services.error_handler_factory import ErrorHandlerFactory, get_error_handler_factory
from src.services.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    ServiceError,
    ValidationError,
)


class TestErrorHandlerFactory:
    """Test error handler factory functionality."""

    def test_singleton_pattern(self):
        """
        Test Case: ERR-005-UT
        Test that ErrorHandlerFactory uses singleton pattern.
        """
        # Get factory instance multiple times
        factory1 = get_error_handler_factory()
        factory2 = get_error_handler_factory()
        factory3 = get_error_handler_factory()

        # Verify all instances are the same object
        assert factory1 is factory2
        assert factory2 is factory3
        assert id(factory1) == id(factory2) == id(factory3)

        # Verify it's an instance of ErrorHandlerFactory
        assert isinstance(factory1, ErrorHandlerFactory)

    @pytest.fixture
    def factory(self):
        """Create error handler factory instance with mocked monitoring."""
        with patch("src.services.error_handler_factory.get_business_logger"):
            return ErrorHandlerFactory()

    def test_exception_classification_logic(self, factory):
        """
        Test Case: ERR-006-UT
        Test _classify_exception method correctly classifies different exception types.
        """
        # Test ValidationError
        exc = ValidationError("Invalid input")
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.VALIDATION_ERROR
        assert result["status_code"] == 422

        # Test RateLimitError
        exc = RateLimitError("Rate limit exceeded")
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED
        assert result["status_code"] == 429

        # Test AuthenticationError with 401
        exc = AuthenticationError("Invalid token", status_code=401)
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.AUTH_TOKEN_INVALID
        assert result["status_code"] == 401

        # Test AuthenticationError with 403
        exc = AuthenticationError("Insufficient permissions", status_code=403)
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.AUTH_INSUFFICIENT_PERMISSIONS
        assert result["status_code"] == 403

        # Test ExternalServiceError
        exc = ExternalServiceError("Service unavailable")
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE
        assert result["status_code"] == 503

        # Test generic Exception
        exc = Exception("Unknown error")
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert result["status_code"] == 500

        # Test ProcessingError (inherits from ServiceError)
        exc = ProcessingError("Processing failed")
        result = factory._classify_exception(exc)
        assert result["error_code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert result["status_code"] == 500

    def test_service_error_enhanced_features(self):
        """
        Test Case: ERR-007-UT
        Test ServiceError.to_response() method and enhanced attributes.
        """
        # Test with error_code and status_code
        error = ValidationError(
            message="Validation failed",
            field_errors={"field1": ["error1"]}
        )

        # ValidationError should have these attributes set
        assert hasattr(error, "error_code")
        assert hasattr(error, "status_code")
        assert error.error_code == ErrorCodes.VALIDATION_ERROR
        assert error.status_code == 422

        # Test to_response method
        response = error.to_response()
        assert "error_code" in response
        assert "message" in response
        assert "status_code" in response
        assert response["error_code"] == ErrorCodes.VALIDATION_ERROR
        assert response["status_code"] == 422

        # Test ServiceError without pre-set values
        base_error = ServiceError("Test error")
        response = base_error.to_response()
        assert response["error_code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR  # Default
        assert response["status_code"] == 500  # Default

    def test_message_priority_logic(self, factory):
        """
        Test Case: ERR-008-UT
        Test _get_error_message method prioritizes custom messages.
        """
        # Test with custom message in exception
        exc = ServiceError("Custom error message")
        exc.message = "Custom error message"
        message = factory._get_error_message(exc, ErrorCodes.SYSTEM_INTERNAL_ERROR)
        assert message == "Custom error message"

        # Test ValueError special handling
        exc = ValueError("Invalid value provided")
        message = factory._get_error_message(exc, ErrorCodes.VALIDATION_ERROR)
        assert message == "Invalid value provided"

        # Test empty ValueError
        exc = ValueError("")
        message = factory._get_error_message(exc, ErrorCodes.VALIDATION_ERROR)
        assert message == "Invalid input value"

        # Test fallback to standard message
        exc = Exception("Some error")
        message = factory._get_error_message(exc, ErrorCodes.SYSTEM_INTERNAL_ERROR)
        assert message == "系統發生未預期錯誤"  # Default Chinese message

        # Test unknown error code
        exc = Exception("Some error")
        message = factory._get_error_message(exc, "UNKNOWN_CODE")
        assert message == "Some error"  # Falls back to str(exc)

    def test_field_errors_extraction(self, factory):
        """
        Test Case: ERR-009-UT
        Test _extract_field_errors method for ValidationError field_errors.
        """
        # Test with field_errors
        exc = ValidationError(
            message="Validation failed",
            field_errors={
                "resume": ["Too short", "Missing required sections"],
                "keywords": ["Required field"],
                "language": ["Invalid value"]
            }
        )

        field_errors = factory._extract_field_errors(exc)
        assert field_errors == {
            "resume": ["Too short", "Missing required sections"],
            "keywords": ["Required field"],
            "language": ["Invalid value"]
        }

        # Test without field_errors attribute
        exc = Exception("Regular exception")
        field_errors = factory._extract_field_errors(exc)
        assert field_errors == {}

        # Test with empty field_errors
        exc = ValidationError("Validation failed")
        exc.field_errors = {}
        field_errors = factory._extract_field_errors(exc)
        assert field_errors == {}

    def test_error_response_format(self, factory):
        """
        Test Case: ERR-010-UT
        Test _create_error_response generates correct unified format.
        """
        response = factory._create_error_response(
            error_code="TEST_ERROR",
            message="Test error message",
            details="Error details",
            field_errors={"field1": ["error1"]},
            status_code=400
        )

        # Check top-level structure
        assert response["success"] is False
        assert response["data"] == {}
        assert "error" in response
        assert "warning" in response
        assert "timestamp" in response
        assert "_status_code" in response

        # Check error structure
        error = response["error"]
        assert error["has_error"] is True
        assert error["code"] == "TEST_ERROR"
        assert error["message"] == "Test error message"
        assert error["details"] == "Error details"
        assert error["field_errors"] == {"field1": ["error1"]}

        # Check warning structure (default values)
        warning = response["warning"]
        assert warning["has_warning"] is False
        assert warning["message"] == ""
        assert warning["expected_minimum"] == 0
        assert warning["actual_extracted"] == 0
        assert warning["suggestion"] == ""

        # Check metadata
        assert response["_status_code"] == 400

        # Verify timestamp format (ISO 8601)
        timestamp = response["timestamp"]
        assert isinstance(timestamp, str)
        # Should parse without error
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_debug_mode_control(self, factory):
        """
        Test Case: ERR-011-UT
        Test _get_error_details shows details only in debug mode.
        """
        exc = ValueError("Sensitive error information")

        # Test with debug=True
        context = {"debug": True}
        details = factory._get_error_details(exc, context)
        assert details == "ValueError: Sensitive error information"

        # Test with debug=False
        context = {"debug": False}
        details = factory._get_error_details(exc, context)
        assert details == ""

        # Test without debug key (defaults to False)
        context = {}
        details = factory._get_error_details(exc, context)
        assert details == ""

        # Test with different exception types
        exc = RateLimitError("API rate limit")
        context = {"debug": True}
        details = factory._get_error_details(exc, context)
        assert "RateLimitError" in details
        assert "API rate limit" in details

    @patch("src.services.error_handler_factory.logger")
    def test_complete_exception_handling_flow(self, mock_logger, factory):
        """
        Test Case: ERR-015-UT
        Test handle_exception complete flow from exception to response.
        """
        # Create test exception
        exc = ValidationError(
            message="Resume too short",
            field_errors={"resume": ["Must be at least 200 characters"]}
        )

        # Create context
        context = {
            "api_name": "test_api",
            "endpoint": "/api/v1/test",
            "debug": False
        }

        # Execute handle_exception
        response = factory.handle_exception(exc, context)

        # Step 1: Verify exception was classified correctly
        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["_status_code"] == 422

        # Step 2: Verify message was retrieved correctly
        assert response["error"]["message"] == "Resume too short"

        # Step 3: Verify logging occurred
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args
        assert "VALIDATION_ERROR" in str(log_call)
        assert "test_api" in str(log_call[1]["extra"]["api_name"])

        # Step 4: Verify response structure (removed monitoring check)
        assert response["success"] is False
        assert response["error"]["has_error"] is True
        assert response["error"]["field_errors"] == {"resume": ["Must be at least 200 characters"]}
        assert response["error"]["details"] == ""  # Not in debug mode
        assert "timestamp" in response

        # Test with debug mode
        context["debug"] = True
        response = factory.handle_exception(exc, context)
        assert "ValidationError" in response["error"]["details"]
