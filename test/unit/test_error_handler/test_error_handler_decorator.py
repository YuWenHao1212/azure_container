"""
Unit tests for error handler decorator.
Tests: ERR-012-UT to ERR-014-UT
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.decorators.error_handler import handle_api_errors, handle_sync_api_errors
from src.services.exceptions import RateLimitError, ValidationError


class TestErrorHandlerDecorator:
    """Test error handler decorator functionality."""

    def test_decorator_preserves_function_metadata(self):
        """
        Test Case: ERR-012-UT
        Test that @functools.wraps correctly preserves function metadata.
        """
        # Test async decorator
        @handle_api_errors(api_name="test_api")
        async def async_test_function():
            """This is async test function docstring."""
            return {"result": "success"}

        # Check metadata preserved
        assert async_test_function.__name__ == "async_test_function"
        assert async_test_function.__doc__ == "This is async test function docstring."

        # Test sync decorator
        @handle_sync_api_errors(api_name="test_api")
        def sync_test_function():
            """This is sync test function docstring."""
            return {"result": "success"}

        # Check metadata preserved
        assert sync_test_function.__name__ == "sync_test_function"
        assert sync_test_function.__doc__ == "This is sync test function docstring."

        # Test with parameters
        @handle_api_errors(api_name="param_test")
        async def function_with_params(param1: str, param2: int = 10):
            """Function with parameters."""
            return {"param1": param1, "param2": param2}

        assert function_with_params.__name__ == "function_with_params"
        # Verify function signature is preserved (can be called with params)
        result = asyncio.run(function_with_params("test", param2=20))
        assert result == {"param1": "test", "param2": 20}

    @pytest.mark.asyncio
    async def test_http_exception_passthrough(self):
        """
        Test Case: ERR-013-UT
        Test that HTTPException is not intercepted by decorator.
        """
        # Test async decorator
        @handle_api_errors(api_name="http_test")
        async def async_raises_http_exception():
            raise HTTPException(status_code=404, detail="Not found")

        # HTTPException should be raised directly
        with pytest.raises(HTTPException) as exc_info:
            await async_raises_http_exception()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

        # Test with different status codes
        @handle_api_errors()
        async def raises_403():
            raise HTTPException(status_code=403, detail="Forbidden")

        with pytest.raises(HTTPException) as exc_info:
            await raises_403()

        assert exc_info.value.status_code == 403

        # Test sync decorator
        @handle_sync_api_errors(api_name="sync_http_test")
        def sync_raises_http_exception():
            raise HTTPException(status_code=401, detail="Unauthorized")

        with pytest.raises(HTTPException) as exc_info:
            sync_raises_http_exception()

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    @pytest.mark.asyncio
    async def test_monitoring_service_invocation(self):
        """
        Test Case: ERR-014-UT
        Test that errors are sent to monitoring system and failures don't affect main flow.
        """
        with patch("src.decorators.error_handler.get_error_handler_factory") as mock_factory:
            # Setup mock factory
            mock_handler = Mock()
            mock_factory.return_value = mock_handler

            # Setup monitoring service mock
            mock_monitoring = Mock()
            mock_handler.monitoring_service = mock_monitoring

            # Setup handle_exception to return error response
            mock_handler.handle_exception.return_value = {
                "success": False,
                "error": {
                    "has_error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "Test error"
                },
                "_status_code": 422
            }

            # Test async decorator
            @handle_api_errors(api_name="monitoring_test")
            async def async_function_with_error():
                raise ValidationError("Test validation error")

            # Execute function
            result = await async_function_with_error()

            # Verify factory was called
            mock_factory.assert_called_once()

            # Verify handle_exception was called with correct params
            mock_handler.handle_exception.assert_called_once()
            call_args = mock_handler.handle_exception.call_args

            # Check exception type
            assert isinstance(call_args[0][0], ValidationError)

            # Check context
            context = call_args[0][1]
            assert context["api_name"] == "monitoring_test"
            assert context["endpoint"] == "/api/v1/async_function_with_error"
            assert context["debug"] is False

            # Check response
            assert isinstance(result, JSONResponse)
            assert result.status_code == 422

            # Test monitoring failure doesn't break main flow
            mock_handler.handle_exception.side_effect = [
                {
                    "success": False,
                    "error": {"has_error": True, "code": "TEST", "message": "Test"},
                    "_status_code": 500
                }
            ]
            mock_monitoring.track_error.side_effect = Exception("Monitoring failed")

            # Function should still return response even if monitoring fails
            @handle_api_errors()
            async def function_with_monitoring_failure():
                raise Exception("Test error")

            result = await function_with_monitoring_failure()
            assert isinstance(result, JSONResponse)
            assert result.status_code == 500

        # Test sync decorator monitoring
        with patch("src.decorators.error_handler.get_error_handler_factory") as mock_factory:
            mock_handler = Mock()
            mock_factory.return_value = mock_handler
            mock_handler.handle_exception.return_value = {
                "success": False,
                "error": {"has_error": True, "code": "RATE_LIMIT", "message": "Rate limited"},
                "_status_code": 429
            }

            @handle_sync_api_errors(api_name="sync_monitoring")
            def sync_function_with_error():
                raise RateLimitError("Rate limit exceeded")

            result = sync_function_with_error()

            # Verify handle_exception was called
            mock_handler.handle_exception.assert_called_once()

            # Check response
            assert isinstance(result, JSONResponse)
            assert result.status_code == 429
