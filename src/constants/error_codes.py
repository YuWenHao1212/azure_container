"""
Standard error codes definition for Azure Container API.

This module defines all standard error codes and their mappings to messages,
following the FastAPI error codes standard specification.
"""


class ErrorCodes:
    """Standard error code constants."""

    # Validation Errors (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VALIDATION_REQUIRED_FIELD = "VALIDATION_REQUIRED_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_TOO_SHORT = "VALIDATION_TOO_SHORT"
    VALIDATION_TOO_LONG = "VALIDATION_TOO_LONG"
    VALIDATION_OUT_OF_RANGE = "VALIDATION_OUT_OF_RANGE"

    # Authentication Errors (401/403)
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"  # noqa: S105
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # noqa: S105
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # noqa: S105
    AUTH_CREDENTIALS_INVALID = "AUTH_CREDENTIALS_INVALID"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"

    # Resource Errors (404/409)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"

    # Business Logic Errors (422)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    BUSINESS_INSUFFICIENT_BALANCE = "BUSINESS_INSUFFICIENT_BALANCE"
    BUSINESS_OPERATION_NOT_ALLOWED = "BUSINESS_OPERATION_NOT_ALLOWED"
    BUSINESS_QUOTA_EXCEEDED = "BUSINESS_QUOTA_EXCEEDED"

    # External Service Errors (502/503/504)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_RATE_LIMIT_EXCEEDED = "EXTERNAL_RATE_LIMIT_EXCEEDED"

    # System Errors (500)
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"
    SYSTEM_DATABASE_ERROR = "SYSTEM_DATABASE_ERROR"
    SYSTEM_CONFIGURATION_ERROR = "SYSTEM_CONFIGURATION_ERROR"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"

    # API Specific Errors
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    OPENAI_ERROR = "OPENAI_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


# Error code to message mapping
ERROR_CODE_MAPPING = {
    # Validation Errors
    ErrorCodes.VALIDATION_ERROR: {
        "message": "輸入資料驗證失敗",
        "message_en": "Input validation failed",
        "status_code": 422,
    },
    ErrorCodes.VALIDATION_REQUIRED_FIELD: {
        "message": "缺少必要欄位",
        "message_en": "Required field missing",
        "status_code": 422,
    },
    ErrorCodes.VALIDATION_INVALID_FORMAT: {
        "message": "資料格式不正確",
        "message_en": "Invalid data format",
        "status_code": 422,
    },
    ErrorCodes.VALIDATION_TOO_SHORT: {
        "message": "內容長度不足",
        "message_en": "Content too short",
        "status_code": 422,
    },
    ErrorCodes.VALIDATION_TOO_LONG: {
        "message": "內容超過長度限制",
        "message_en": "Content exceeds maximum length",
        "status_code": 422,
    },
    ErrorCodes.VALIDATION_OUT_OF_RANGE: {
        "message": "數值超出範圍",
        "message_en": "Value out of range",
        "status_code": 422,
    },
    # Authentication Errors
    ErrorCodes.AUTH_TOKEN_MISSING: {
        "message": "缺少認證令牌",
        "message_en": "Authentication token missing",
        "status_code": 401,
    },
    ErrorCodes.AUTH_TOKEN_INVALID: {
        "message": "無效的認證令牌",
        "message_en": "Invalid authentication token",
        "status_code": 401,
    },
    ErrorCodes.AUTH_TOKEN_EXPIRED: {
        "message": "認證令牌已過期",
        "message_en": "Authentication token expired",
        "status_code": 401,
    },
    ErrorCodes.AUTH_CREDENTIALS_INVALID: {
        "message": "認證憑證無效",
        "message_en": "Invalid credentials",
        "status_code": 401,
    },
    ErrorCodes.AUTH_ACCOUNT_DISABLED: {
        "message": "帳戶已停用",
        "message_en": "Account disabled",
        "status_code": 403,
    },
    ErrorCodes.AUTH_INSUFFICIENT_PERMISSIONS: {
        "message": "權限不足",
        "message_en": "Insufficient permissions",
        "status_code": 403,
    },
    # Resource Errors
    ErrorCodes.RESOURCE_NOT_FOUND: {
        "message": "資源不存在",
        "message_en": "Resource not found",
        "status_code": 404,
    },
    ErrorCodes.RESOURCE_ALREADY_EXISTS: {
        "message": "資源已存在",
        "message_en": "Resource already exists",
        "status_code": 409,
    },
    ErrorCodes.RESOURCE_CONFLICT: {
        "message": "資源衝突",
        "message_en": "Resource conflict",
        "status_code": 409,
    },
    ErrorCodes.RESOURCE_LOCKED: {
        "message": "資源被鎖定",
        "message_en": "Resource locked",
        "status_code": 423,
    },
    # Business Logic Errors
    ErrorCodes.BUSINESS_RULE_VIOLATION: {
        "message": "違反業務規則",
        "message_en": "Business rule violation",
        "status_code": 422,
    },
    ErrorCodes.BUSINESS_INSUFFICIENT_BALANCE: {
        "message": "餘額不足",
        "message_en": "Insufficient balance",
        "status_code": 422,
    },
    ErrorCodes.BUSINESS_OPERATION_NOT_ALLOWED: {
        "message": "操作不被允許",
        "message_en": "Operation not allowed",
        "status_code": 403,
    },
    ErrorCodes.BUSINESS_QUOTA_EXCEEDED: {
        "message": "超出配額限制",
        "message_en": "Quota exceeded",
        "status_code": 429,
    },
    # External Service Errors
    ErrorCodes.EXTERNAL_SERVICE_ERROR: {
        "message": "外部服務錯誤",
        "message_en": "External service error",
        "status_code": 502,
    },
    ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE: {
        "message": "外部服務暫時無法使用",
        "message_en": "External service temporarily unavailable",
        "status_code": 503,
    },
    ErrorCodes.EXTERNAL_SERVICE_TIMEOUT: {
        "message": "外部服務回應超時",
        "message_en": "External service timeout",
        "status_code": 504,
    },
    ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED: {
        "message": "超過 API 速率限制,請稍後再試",
        "message_en": "API rate limit exceeded, please try again later",
        "status_code": 429,
    },
    # System Errors
    ErrorCodes.SYSTEM_INTERNAL_ERROR: {
        "message": "系統發生未預期錯誤",
        "message_en": "An unexpected error occurred",
        "status_code": 500,
    },
    ErrorCodes.SYSTEM_DATABASE_ERROR: {
        "message": "資料庫錯誤",
        "message_en": "Database error",
        "status_code": 500,
    },
    ErrorCodes.SYSTEM_CONFIGURATION_ERROR: {
        "message": "系統配置錯誤",
        "message_en": "System configuration error",
        "status_code": 500,
    },
    ErrorCodes.SYSTEM_MAINTENANCE: {
        "message": "系統維護中",
        "message_en": "System under maintenance",
        "status_code": 503,
    },
    # API Specific Errors
    ErrorCodes.UNSUPPORTED_LANGUAGE: {
        "message": "不支援的語言",
        "message_en": "Unsupported language",
        "status_code": 422,
    },
    ErrorCodes.OPENAI_ERROR: {
        "message": "AI 服務處理失敗",
        "message_en": "AI service processing failed",
        "status_code": 500,
    },
    ErrorCodes.SERVICE_UNAVAILABLE: {
        "message": "服務暫時無法使用",
        "message_en": "Service temporarily unavailable",
        "status_code": 503,
    },
    ErrorCodes.TIMEOUT_ERROR: {
        "message": "請求處理超時",
        "message_en": "Request processing timeout",
        "status_code": 408,
    },
}


def get_error_message(error_code: str, language: str = "zh") -> str:
    """
    Get error message by error code and language.

    Args:
        error_code: The error code constant
        language: Language code ('zh' for Chinese, 'en' for English)

    Returns:
        The error message in specified language
    """
    error_info = ERROR_CODE_MAPPING.get(error_code, {})
    if language == "en":
        return error_info.get("message_en", "Unknown error")
    return error_info.get("message", "未知錯誤")


def get_status_code(error_code: str) -> int:
    """
    Get HTTP status code by error code.

    Args:
        error_code: The error code constant

    Returns:
        The corresponding HTTP status code
    """
    return ERROR_CODE_MAPPING.get(error_code, {}).get("status_code", 500)
