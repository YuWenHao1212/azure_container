"""
Unit tests for error codes module.
Tests: ERR-001-UT to ERR-004-UT
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

    def test_error_codes_constants_completeness(self):
        """
        Test Case: ERR-001-UT
        Test that all necessary error code constants are defined.
        """
        # Verify essential error codes exist
        assert hasattr(ErrorCodes, "VALIDATION_ERROR")
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"

        assert hasattr(ErrorCodes, "AUTH_TOKEN_INVALID")
        assert ErrorCodes.AUTH_TOKEN_INVALID == "AUTH_TOKEN_INVALID"

        assert hasattr(ErrorCodes, "EXTERNAL_RATE_LIMIT_EXCEEDED")
        assert ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED == "EXTERNAL_RATE_LIMIT_EXCEEDED"

        assert hasattr(ErrorCodes, "SYSTEM_INTERNAL_ERROR")
        assert ErrorCodes.SYSTEM_INTERNAL_ERROR == "SYSTEM_INTERNAL_ERROR"

        # Additional important codes
        assert hasattr(ErrorCodes, "AUTH_INSUFFICIENT_PERMISSIONS")
        assert hasattr(ErrorCodes, "EXTERNAL_SERVICE_UNAVAILABLE")
        assert hasattr(ErrorCodes, "EXTERNAL_SERVICE_TIMEOUT")

    def test_error_code_mapping_structure(self):
        """
        Test Case: ERR-002-UT
        Test that ERROR_CODE_MAPPING has complete structure for each error code.
        """
        # Test essential error codes have complete mapping
        essential_codes = [
            ErrorCodes.VALIDATION_ERROR,
            ErrorCodes.AUTH_TOKEN_INVALID,
            ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED,
            ErrorCodes.SYSTEM_INTERNAL_ERROR,
        ]

        for code in essential_codes:
            assert code in ERROR_CODE_MAPPING, f"Missing mapping for {code}"

            mapping = ERROR_CODE_MAPPING[code]
            # Check required fields
            assert "message" in mapping, f"Missing 'message' for {code}"
            assert "message_en" in mapping, f"Missing 'message_en' for {code}"
            assert "status_code" in mapping, f"Missing 'status_code' for {code}"

            # Check field types
            assert isinstance(mapping["message"], str), f"message must be string for {code}"
            assert isinstance(mapping["message_en"], str), f"message_en must be string for {code}"
            assert isinstance(mapping["status_code"], int), f"status_code must be int for {code}"

            # Check status code range (4xx or 5xx)
            assert 400 <= mapping["status_code"] < 600, f"Invalid status code for {code}"

    def test_get_error_message_multilingual(self):
        """
        Test Case: ERR-003-UT
        Test get_error_message function for Chinese and English support.
        """
        # Test Chinese messages
        assert get_error_message(ErrorCodes.VALIDATION_ERROR, "zh") == "輸入資料驗證失敗"
        assert get_error_message(ErrorCodes.AUTH_TOKEN_INVALID, "zh") == "無效的認證令牌"
        assert get_error_message(ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED, "zh") == "超過 API 速率限制,請稍後再試"
        assert get_error_message(ErrorCodes.SYSTEM_INTERNAL_ERROR, "zh") == "系統發生未預期錯誤"

        # Test English messages
        assert get_error_message(ErrorCodes.VALIDATION_ERROR, "en") == "Input validation failed"
        assert get_error_message(ErrorCodes.AUTH_TOKEN_INVALID, "en") == "Invalid authentication token"
        assert get_error_message(ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED, "en") == "API rate limit exceeded, please try again later"
        assert get_error_message(ErrorCodes.SYSTEM_INTERNAL_ERROR, "en") == "An unexpected error occurred"

        # Test unknown error code
        assert get_error_message("UNKNOWN_CODE", "zh") == "未知錯誤"
        assert get_error_message("UNKNOWN_CODE", "en") == "Unknown error"

        # Test default language (zh)
        assert get_error_message(ErrorCodes.VALIDATION_ERROR) == "輸入資料驗證失敗"

    def test_get_status_code_mapping(self):
        """
        Test Case: ERR-004-UT
        Test get_status_code function returns correct HTTP status codes.
        """
        # Validation errors -> 422
        assert get_status_code(ErrorCodes.VALIDATION_ERROR) == 422
        assert get_status_code(ErrorCodes.VALIDATION_REQUIRED_FIELD) == 422
        assert get_status_code(ErrorCodes.VALIDATION_TOO_SHORT) == 422

        # Authentication errors -> 401/403
        assert get_status_code(ErrorCodes.AUTH_TOKEN_INVALID) == 401
        assert get_status_code(ErrorCodes.AUTH_TOKEN_MISSING) == 401
        assert get_status_code(ErrorCodes.AUTH_INSUFFICIENT_PERMISSIONS) == 403

        # Rate limit -> 429
        assert get_status_code(ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED) == 429

        # System errors -> 500
        assert get_status_code(ErrorCodes.SYSTEM_INTERNAL_ERROR) == 500
        assert get_status_code(ErrorCodes.SYSTEM_DATABASE_ERROR) == 500

        # External service errors -> 502/503/504
        assert get_status_code(ErrorCodes.EXTERNAL_SERVICE_ERROR) == 502
        assert get_status_code(ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE) == 503
        assert get_status_code(ErrorCodes.EXTERNAL_SERVICE_TIMEOUT) == 504

        # Unknown error code -> 500 (default)
        assert get_status_code("UNKNOWN_CODE") == 500
