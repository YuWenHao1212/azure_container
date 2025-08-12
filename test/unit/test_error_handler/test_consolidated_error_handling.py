"""
Consolidated error handling tests from various modules.
Tests: ERR-016-UT to ERR-020-UT

These tests consolidate common error handling patterns from multiple modules
to ensure unified error handling behavior across the system.
"""

from unittest.mock import Mock, patch

import pytest

from src.constants.error_codes import ErrorCodes
from src.services.error_handler_factory import ErrorHandlerFactory
from src.services.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    ProcessingError,
    RateLimitError,
    ServiceError,
    ValidationError,
)


class TestConsolidatedErrorHandling:
    """Consolidated error handling tests from multiple modules."""

    @pytest.fixture
    def factory(self):
        """Create error handler factory instance with mocked monitoring."""
        with patch("src.services.error_handler_factory.get_business_logger"):
            return ErrorHandlerFactory()

    def test_consolidated_validation_error_handling(self, factory):
        """
        Test Case: ERR-016-UT
        Consolidated validation error handling from INDEX_CALCULATION, HEALTH_KEYWORDS, RESUME_TAILORING.

        測試原因: 確保所有模組的驗證錯誤都有一致的處理方式
        合併來源:
        - INDEX_CALCULATION: 輸入長度驗證
        - HEALTH_KEYWORDS: 關鍵字最小數量驗證
        - RESUME_TAILORING: HTML格式驗證
        """
        # Test 1: Input too short (from INDEX_CALCULATION)
        exc = ValidationError(
            message="Input too short (minimum 200 characters)",
            field_errors={"resume": ["Must be at least 200 characters"]}
        )
        response = factory.handle_exception(exc, {"api_name": "validation_test"})

        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["_status_code"] == 422
        assert "too short" in response["error"]["message"].lower()
        assert "resume" in response["error"]["field_errors"]

        # Test 2: Insufficient keywords (from HEALTH_KEYWORDS)
        exc = ValidationError(
            message="Insufficient keywords extracted",
            field_errors={"keywords": ["Minimum 3 keywords required"]}
        )
        response = factory.handle_exception(exc, {"api_name": "keyword_test"})

        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["_status_code"] == 422
        assert "keywords" in response["error"]["field_errors"]

        # Test 3: Invalid HTML format (from RESUME_TAILORING)
        exc = ValidationError(
            message="Invalid HTML format",
            field_errors={"original_resume": ["Must be valid HTML"]}
        )
        response = factory.handle_exception(exc, {"api_name": "tailoring_test"})

        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["_status_code"] == 422
        assert "original_resume" in response["error"]["field_errors"]

    def test_consolidated_external_service_error_classification(self, factory):
        """
        Test Case: ERR-017-UT
        Consolidated external service error classification from INDEX_CALCULATION, RESUME_TAILORING.

        測試原因: 統一外部服務錯誤的分類和處理邏輯
        合併來源:
        - INDEX_CALCULATION: Azure OpenAI API 錯誤
        - RESUME_TAILORING: 第三方服務超時
        """
        # Test 1: Azure OpenAI rate limit (from INDEX_CALCULATION)
        exc = RateLimitError("Azure OpenAI rate limit exceeded")
        response = factory.handle_exception(exc, {"api_name": "index_calc"})

        assert response["error"]["code"] == ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED
        assert response["_status_code"] == 429
        assert "rate limit" in response["error"]["message"].lower()

        # Test 2: External service unavailable (from RESUME_TAILORING)
        exc = ExternalServiceError("External service unavailable")
        response = factory.handle_exception(exc, {"api_name": "tailoring"})

        assert response["error"]["code"] == ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE
        assert response["_status_code"] == 503

        # Test 3: Authentication failure
        exc = AuthenticationError("Invalid API key", status_code=401)
        response = factory.handle_exception(exc, {"api_name": "auth_test"})

        assert response["error"]["code"] == ErrorCodes.AUTH_TOKEN_INVALID
        assert response["_status_code"] == 401

    def test_consolidated_language_detection_error(self, factory):
        """
        Test Case: ERR-018-UT
        Consolidated language detection error handling from SERVICE_MODULES.

        測試原因: 確保語言檢測錯誤在所有服務中一致處理
        合併來源:
        - SERVICE_MODULES: 語言檢測服務的各種錯誤情況
        """
        # Test 1: Unsupported language
        exc = ValidationError(
            message="Unsupported language detected",
            field_errors={"language": ["Language 'ar' is not supported"]}
        )
        response = factory.handle_exception(exc, {"api_name": "language_service"})

        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert response["_status_code"] == 422
        assert "language" in response["error"]["field_errors"]

        # Test 2: Language detection failure (service error)
        exc = ProcessingError("Failed to detect language")
        response = factory.handle_exception(exc, {"api_name": "language_service"})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500

        # Test 3: Mixed language content warning (non-error case)
        # This would typically generate a warning, not an error
        # Warnings are handled differently, not through exception handler

    def test_consolidated_retry_mechanism_error_classification(self, factory):
        """
        Test Case: ERR-019-UT
        Consolidated retry mechanism error classification from GAP_ANALYSIS.

        測試原因: 確保重試機制的錯誤分類在所有模組中一致
        合併來源:
        - GAP_ANALYSIS: 自適應重試策略的錯誤分類
        """
        # Test 1: Retryable error (rate limit)
        exc = RateLimitError("Too many requests")
        result = factory._classify_exception(exc)

        assert result["error_code"] == ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED
        assert result["status_code"] == 429
        # Rate limit errors should be retryable

        # Test 2: Retryable error (temporary server error)
        exc = ExternalServiceError("Service temporarily unavailable")
        result = factory._classify_exception(exc)

        assert result["error_code"] == ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE
        assert result["status_code"] == 503
        # Service unavailable errors should be retryable

        # Test 3: Non-retryable error (validation)
        exc = ValidationError("Invalid input format")
        result = factory._classify_exception(exc)

        assert result["error_code"] == ErrorCodes.VALIDATION_ERROR
        assert result["status_code"] == 422
        # Validation errors should NOT be retryable

        # Test 4: Non-retryable error (authentication)
        exc = AuthenticationError("Invalid credentials", status_code=401)
        result = factory._classify_exception(exc)

        assert result["error_code"] == ErrorCodes.AUTH_TOKEN_INVALID
        assert result["status_code"] == 401
        # Authentication errors should NOT be retryable

    def test_consolidated_system_internal_error_handling(self, factory):
        """
        Test Case: ERR-020-UT
        Consolidated system internal error handling from RESUME_TAILORING, INDEX_CALCULATION.

        測試原因: 統一系統內部錯誤的處理和回應格式
        合併來源:
        - RESUME_TAILORING: LLM處理錯誤
        - INDEX_CALCULATION: 向量計算錯誤
        """
        # Test 1: Generic processing error (from RESUME_TAILORING)
        exc = ProcessingError("Failed to process resume")
        response = factory.handle_exception(exc, {"api_name": "tailoring"})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500
        assert response["success"] is False
        assert response["data"] == {}

        # Test 2: Calculation error (from INDEX_CALCULATION)
        exc = ServiceError("Vector calculation failed")
        response = factory.handle_exception(exc, {"api_name": "index_calc"})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500

        # Test 3: Unexpected exception
        exc = Exception("Unexpected error occurred")
        response = factory.handle_exception(exc, {"api_name": "unknown"})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500

        # Test 4: With debug mode enabled
        exc = ProcessingError("Detailed error information")
        response = factory.handle_exception(exc, {"api_name": "test", "debug": True})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500
        assert "ProcessingError" in response["error"]["details"]  # Debug info included

        # Test 5: Without debug mode (default)
        exc = ProcessingError("Sensitive error details")
        response = factory.handle_exception(exc, {"api_name": "test", "debug": False})

        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["_status_code"] == 500
        assert response["error"]["details"] == ""  # No debug info
