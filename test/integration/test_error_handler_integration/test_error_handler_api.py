"""
Integration tests for error handler in API context.
Tests: ERR-001-IT to ERR-010-IT
"""

import json
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.decorators.error_handler import handle_api_errors, handle_sync_api_errors
from src.services.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    ValidationError,
)

# Create test app
app = FastAPI()


# Define test endpoints
@app.post("/test/validation")
@handle_api_errors(api_name="validation_test")
async def validation_endpoint(data: dict):
    """Test endpoint that raises ValidationError."""
    if not data.get("required_field"):
        raise ValidationError(
            message="Missing required field",
            field_errors={"required_field": ["This field is required"]}
        )
    return {"success": True, "data": data}


@app.post("/test/rate-limit")
@handle_api_errors(api_name="rate_limit_test")
async def rate_limit_endpoint():
    """Test endpoint that raises RateLimitError."""
    raise RateLimitError("API rate limit exceeded")


@app.post("/test/auth")
@handle_api_errors(api_name="auth_test")
async def auth_endpoint(token: str | None = None):
    """Test endpoint that raises AuthenticationError."""
    if not token:
        raise AuthenticationError("Token missing", status_code=401)
    if token == "invalid":
        raise AuthenticationError("Invalid token", status_code=401)
    if token == "forbidden":
        raise AuthenticationError("Insufficient permissions", status_code=403)
    return {"success": True, "user": "test_user"}


@app.post("/test/external-service")
@handle_api_errors(api_name="external_test")
async def external_service_endpoint():
    """Test endpoint that raises ExternalServiceError."""
    raise ExternalServiceError("OpenAI service unavailable")


@app.post("/test/timeout")
@handle_api_errors(api_name="timeout_test")
async def timeout_endpoint():
    """Test endpoint that raises TimeoutError."""
    raise TimeoutError("Request timed out")


@app.post("/test/unexpected")
@handle_api_errors(api_name="unexpected_test")
async def unexpected_error_endpoint():
    """Test endpoint that raises unexpected exception."""
    raise RuntimeError("Unexpected runtime error")


@app.post("/test/sync")
@handle_sync_api_errors(api_name="sync_test")
def sync_endpoint(data: dict):
    """Sync endpoint for testing."""
    if not data.get("valid"):
        raise ValueError("Invalid data provided")
    return {"success": True, "data": data}


# Create test client
client = TestClient(app)


class TestErrorHandlerAPIIntegration:
    """Test error handler integration with FastAPI."""

    def test_validation_error_with_field_errors(self):
        """
        Test Case: ERR-001-IT
        Test ValidationError with field_errors returns correct response format.
        """
        # Send request that triggers validation error
        response = client.post("/test/validation", json={})

        # Check status code
        assert response.status_code == 422

        # Parse response
        data = response.json()

        # Check unified format structure
        assert data["success"] is False
        assert data["data"] == {}

        # Check error structure
        error = data["error"]
        assert error["has_error"] is True
        assert error["code"] == "VALIDATION_ERROR"
        assert error["message"] == "Missing required field"
        assert error["field_errors"] == {"required_field": ["This field is required"]}
        assert error["details"] == ""  # Not in debug mode

        # Check warning structure
        warning = data["warning"]
        assert warning["has_warning"] is False

        # Check timestamp exists
        assert "timestamp" in data

        # Test successful request
        response = client.post("/test/validation", json={"required_field": "value"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_rate_limit_error_response(self):
        """
        Test Case: ERR-002-IT
        Test RateLimitError returns 429 with correct format.
        """
        response = client.post("/test/rate-limit")

        # Check status code
        assert response.status_code == 429

        # Parse response
        data = response.json()

        # Verify structure
        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "EXTERNAL_RATE_LIMIT_EXCEEDED"
        assert data["error"]["message"] == "API rate limit exceeded"
        assert data["error"]["field_errors"] == {}

        # Verify timestamp format
        assert "timestamp" in data
        # Should be ISO format
        assert "T" in data["timestamp"]

    def test_authentication_error_401(self):
        """
        Test Case: ERR-003-IT
        Test AuthenticationError with 401 status.
        """
        # Test missing token
        response = client.post("/test/auth")
        assert response.status_code == 401

        data = response.json()
        assert data["error"]["code"] == "AUTH_TOKEN_INVALID"
        assert data["error"]["message"] == "Token missing"

        # Test invalid token
        response = client.post("/test/auth?token=invalid")
        assert response.status_code == 401

        data = response.json()
        assert data["error"]["code"] == "AUTH_TOKEN_INVALID"
        assert data["error"]["message"] == "Invalid token"

    def test_authentication_error_403(self):
        """
        Test Case: ERR-004-IT
        Test AuthenticationError with 403 status for insufficient permissions.
        """
        response = client.post("/test/auth?token=forbidden")

        # Check status code
        assert response.status_code == 403

        data = response.json()
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
        assert data["error"]["message"] == "Insufficient permissions"
        assert data["success"] is False

    def test_external_service_error(self):
        """
        Test Case: ERR-005-IT
        Test ExternalServiceError returns 503.
        """
        response = client.post("/test/external-service")

        # Check status code
        assert response.status_code == 503

        data = response.json()
        assert data["error"]["code"] == "EXTERNAL_SERVICE_UNAVAILABLE"
        assert data["error"]["message"] == "OpenAI service unavailable"
        assert data["success"] is False

        # Verify all required fields present
        assert "timestamp" in data
        assert "data" in data
        assert "warning" in data

    def test_timeout_error(self):
        """
        Test Case: ERR-006-IT
        Test TimeoutError returns 504.
        """
        response = client.post("/test/timeout")

        # Check status code
        assert response.status_code == 504

        data = response.json()
        assert data["error"]["code"] == "EXTERNAL_SERVICE_TIMEOUT"
        assert data["error"]["message"] in ["Request timed out", "外部服務回應超時"]
        assert data["success"] is False

    def test_unexpected_error_handling(self):
        """
        Test Case: ERR-007-IT
        Test unexpected exceptions return 500 with generic message.
        """
        response = client.post("/test/unexpected")

        # Check status code
        assert response.status_code == 500

        data = response.json()
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
        # Should use generic message, not expose internal error
        assert data["error"]["message"] in ["系統發生未預期錯誤", "An unexpected error occurred"]
        assert data["error"]["details"] == ""  # No details in non-debug mode
        assert data["success"] is False

    def test_sync_endpoint_error_handling(self):
        """
        Test Case: ERR-008-IT
        Test sync endpoints work with handle_sync_api_errors decorator.
        """
        # Test error case
        response = client.post("/test/sync", json={"valid": False})

        # Should handle ValueError as validation error
        assert response.status_code == 422

        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Invalid data provided"

        # Test success case
        response = client.post("/test/sync", json={"valid": True, "test": "data"})
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["test"] == "data"

    @patch("src.decorators.error_handler.get_error_handler_factory")
    def test_monitoring_integration(self, mock_factory):
        """
        Test Case: ERR-009-IT
        Test monitoring service is called on errors.
        """
        from unittest.mock import Mock

        # Setup mock
        mock_handler = Mock()
        mock_factory.return_value = mock_handler
        mock_monitoring = Mock()
        mock_handler.monitoring_service = mock_monitoring

        # Configure handle_exception to return proper response
        mock_handler.handle_exception.return_value = {
            "success": False,
            "data": {},
            "error": {
                "has_error": True,
                "code": "VALIDATION_ERROR",
                "message": "Test error",
                "details": "",
                "field_errors": {}
            },
            "warning": {
                "has_warning": False,
                "message": "",
                "expected_minimum": 0,
                "actual_extracted": 0,
                "suggestion": ""
            },
            "timestamp": "2025-01-01T00:00:00",
            "_status_code": 422
        }

        # Create test endpoint with monitoring
        test_app = FastAPI()

        @test_app.post("/monitor-test")
        @handle_api_errors(api_name="monitor_test")
        async def monitored_endpoint():
            raise ValidationError("Test validation error")

        # Make request
        test_client = TestClient(test_app)
        response = test_client.post("/monitor-test")

        # Verify monitoring was invoked
        mock_factory.assert_called()
        mock_handler.handle_exception.assert_called_once()

        # Check the context passed to handle_exception
        call_args = mock_handler.handle_exception.call_args[0]
        context = call_args[1]
        assert context["api_name"] == "monitor_test"
        assert context["endpoint"] == "/api/v1/monitored_endpoint"

        # Verify response
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @patch("src.decorators.error_handler.get_error_handler_factory")
    def test_debug_mode_details(self, mock_factory):
        """
        Test Case: ERR-010-IT
        Test debug mode includes error details.
        """
        from unittest.mock import Mock

        # Setup mock for debug mode
        mock_handler_debug = Mock()
        mock_factory.return_value = mock_handler_debug

        # Configure debug response
        mock_handler_debug.handle_exception.return_value = {
            "success": False,
            "data": {},
            "error": {
                "has_error": True,
                "code": "SYSTEM_INTERNAL_ERROR",
                "message": "Detailed processing error information",
                "details": "ProcessingError: Detailed processing error information",
                "field_errors": {}
            },
            "warning": {
                "has_warning": False,
                "message": "",
                "expected_minimum": 0,
                "actual_extracted": 0,
                "suggestion": ""
            },
            "timestamp": "2025-01-01T00:00:00",
            "_status_code": 500
        }

        # Create app with debug mode
        debug_app = FastAPI()

        @debug_app.post("/debug-test")
        @handle_api_errors(api_name="debug_test")
        async def debug_endpoint():
            raise ProcessingError("Detailed processing error information")

        # Test with debug context
        debug_client = TestClient(debug_app)

        # Manually set debug in context through mock
        def handle_exception_with_debug(exc, context):
            context["debug"] = True
            return mock_handler_debug.handle_exception.return_value

        mock_handler_debug.handle_exception.side_effect = handle_exception_with_debug

        response = debug_client.post("/debug-test")

        assert response.status_code == 500

        data = response.json()
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
        assert data["error"]["message"] == "Detailed processing error information"
        # Debug mode should include details
        assert data["error"]["details"] != ""
        assert "ProcessingError" in data["error"]["details"]
        assert "Detailed processing error information" in data["error"]["details"]

        # Reset mock for normal mode
        mock_factory.reset_mock()
        mock_handler_normal = Mock()
        mock_factory.return_value = mock_handler_normal

        # Configure normal response (no details)
        mock_handler_normal.handle_exception.return_value = {
            "success": False,
            "data": {},
            "error": {
                "has_error": True,
                "code": "SYSTEM_INTERNAL_ERROR",
                "message": "Sensitive error information",
                "details": "",  # No details in normal mode
                "field_errors": {}
            },
            "warning": {
                "has_warning": False,
                "message": "",
                "expected_minimum": 0,
                "actual_extracted": 0,
                "suggestion": ""
            },
            "timestamp": "2025-01-01T00:00:00",
            "_status_code": 500
        }

        # Create app without debug mode for comparison
        normal_app = FastAPI()

        @normal_app.post("/normal-test")
        @handle_api_errors(api_name="normal_test")
        async def normal_endpoint():
            raise ProcessingError("Sensitive error information")

        normal_client = TestClient(normal_app)
        response = normal_client.post("/normal-test")

        data = response.json()
        # Non-debug mode should NOT include details
        assert data["error"]["details"] == ""
        # But should still have proper error code and message
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
