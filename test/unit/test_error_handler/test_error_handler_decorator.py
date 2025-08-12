"""
Unit tests for error handler decorator.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.decorators.error_handler import handle_api_errors, handle_sync_api_errors
from src.services.exceptions import RateLimitError, ValidationError


class TestErrorHandlerDecorator:
    """Test error handler decorator functionality."""

    @pytest.mark.asyncio
    async def test_handle_api_errors_success(self):
        """Test decorator with successful execution."""
        @handle_api_errors(api_name="test_api")
        async def test_endpoint():
            return {"success": True, "data": "test"}

        result = await test_endpoint()
        assert result == {"success": True, "data": "test"}

    @pytest.mark.asyncio
    async def test_handle_api_errors_with_exception(self):
        """Test decorator handling exceptions."""
        @handle_api_errors(api_name="test_api")
        async def test_endpoint():
            raise ValidationError("Test validation error")

        with patch("src.decorators.error_handler.get_error_handler_factory") as mock_factory:
            mock_handler = Mock()
            mock_handler.handle_exception.return_value = {
                "success": False,
                "error": {
                    "has_error": True,
                    "code": "VALIDATION_ERROR",
                    "message": "Test validation error"
                },
                "_status_code": 422
            }
            mock_factory.return_value = mock_handler

            result = await test_endpoint()

            assert isinstance(result, JSONResponse)
            assert result.status_code == 422

            # Verify the factory was called
            mock_handler.handle_exception.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_api_errors_http_exception_passthrough(self):
        """Test that HTTP exceptions are passed through."""
        @handle_api_errors(api_name="test_api")
        async def test_endpoint():
            raise HTTPException(status_code=404, detail="Not found")

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    @pytest.mark.asyncio
    async def test_handle_api_errors_with_args_kwargs(self):
        """Test decorator with function arguments."""
        @handle_api_errors(api_name="test_api")
        async def test_endpoint(param1: str, param2: int = 10):
            return {"param1": param1, "param2": param2}

        result = await test_endpoint("test", param2=20)
        assert result == {"param1": "test", "param2": 20}

    def test_handle_sync_api_errors_success(self):
        """Test synchronous decorator with successful execution."""
        @handle_sync_api_errors(api_name="test_api")
        def test_endpoint():
            return {"success": True, "data": "test"}

        result = test_endpoint()
        assert result == {"success": True, "data": "test"}

    def test_handle_sync_api_errors_with_exception(self):
        """Test synchronous decorator handling exceptions."""
        @handle_sync_api_errors(api_name="test_api")
        def test_endpoint():
            raise RateLimitError("Rate limit exceeded")

        with patch("src.decorators.error_handler.get_error_handler_factory") as mock_factory:
            mock_handler = Mock()
            mock_handler.handle_exception.return_value = {
                "success": False,
                "error": {
                    "has_error": True,
                    "code": "EXTERNAL_RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded"
                },
                "_status_code": 429
            }
            mock_factory.return_value = mock_handler

            result = test_endpoint()

            assert isinstance(result, JSONResponse)
            assert result.status_code == 429

    def test_handle_sync_api_errors_http_exception_passthrough(self):
        """Test that HTTP exceptions are passed through in sync decorator."""
        @handle_sync_api_errors(api_name="test_api")
        def test_endpoint():
            raise HTTPException(status_code=403, detail="Forbidden")

        with pytest.raises(HTTPException) as exc_info:
            test_endpoint()

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Forbidden"

    @pytest.mark.asyncio
    async def test_decorator_without_api_name(self):
        """Test decorator without explicit api_name."""
        @handle_api_errors()
        async def test_endpoint():
            return {"success": True}

        result = await test_endpoint()
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @handle_api_errors(api_name="test_api")
        async def test_endpoint():
            """Test endpoint docstring."""
            return {"success": True}

        assert test_endpoint.__name__ == "test_endpoint"
        assert test_endpoint.__doc__ == "Test endpoint docstring."
