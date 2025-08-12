"""
Unit tests for error codes module.
"""

import pytest

from src.constants.error_codes import (
    ERROR_CODE_MAPPING,
    ErrorCodes,
    get_error_message,
    get_status_code,
)


class TestErrorCodes:
    """Test error codes definitions and functions."""

    def test_error_codes_constants(self):
        """Test that error code constants are defined correctly."""
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCodes.AUTH_TOKEN_INVALID == "AUTH_TOKEN_INVALID"
        assert ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED == "EXTERNAL_RATE_LIMIT_EXCEEDED"
        assert ErrorCodes.SYSTEM_INTERNAL_ERROR == "SYSTEM_INTERNAL_ERROR"

    def test_error_code_mapping_structure(self):
        """Test that error code mapping has required fields."""
        for code, info in ERROR_CODE_MAPPING.items():
            assert "message" in info, f"Missing 'message' for {code}"
            assert "message_en" in info, f"Missing 'message_en' for {code}"
            assert "status_code" in info, f"Missing 'status_code' for {code}"
            assert isinstance(info["status_code"], int), f"status_code must be int for {code}"

    def test_get_error_message_chinese(self):
        """Test getting Chinese error messages."""
        message = get_error_message(ErrorCodes.VALIDATION_ERROR, "zh")
        assert message == "輸入資料驗證失敗"

        message = get_error_message(ErrorCodes.AUTH_TOKEN_INVALID, "zh")
        assert message == "無效的認證令牌"

    def test_get_error_message_english(self):
        """Test getting English error messages."""
        message = get_error_message(ErrorCodes.VALIDATION_ERROR, "en")
        assert message == "Input validation failed"

        message = get_error_message(ErrorCodes.AUTH_TOKEN_INVALID, "en")
        assert message == "Invalid authentication token"

    def test_get_error_message_unknown_code(self):
        """Test getting error message for unknown code."""
        message = get_error_message("UNKNOWN_CODE", "zh")
        assert message == "未知錯誤"

        message = get_error_message("UNKNOWN_CODE", "en")
        assert message == "Unknown error"

    def test_get_status_code(self):
        """Test getting HTTP status codes."""
        assert get_status_code(ErrorCodes.VALIDATION_ERROR) == 422
        assert get_status_code(ErrorCodes.AUTH_TOKEN_INVALID) == 401
        assert get_status_code(ErrorCodes.AUTH_INSUFFICIENT_PERMISSIONS) == 403
        assert get_status_code(ErrorCodes.RESOURCE_NOT_FOUND) == 404
        assert get_status_code(ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED) == 429
        assert get_status_code(ErrorCodes.SYSTEM_INTERNAL_ERROR) == 500
        assert get_status_code(ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE) == 503

    def test_get_status_code_unknown(self):
        """Test getting status code for unknown error code."""
        assert get_status_code("UNKNOWN_CODE") == 500
