"""
Unified response models for FHS architecture.
All API responses must use these models to ensure consistency.
Following Bubble.io compatibility requirements - no Optional types.
"""
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail model for API responses."""
    has_error: bool = Field(default=False, description="Whether error exists")
    code: str = Field(default="", description="Error code")
    message: str = Field(default="", description="Error message")
    details: str = Field(default="", description="Additional error details")


class WarningInfo(BaseModel):
    """Warning information for quality checks."""
    has_warning: bool = Field(default=False, description="Whether warning exists")
    message: str = Field(default="", description="Warning message")
    expected_minimum: int = Field(default=12, description="Expected minimum value")
    actual_extracted: int = Field(default=0, description="Actual extracted value")
    suggestion: str = Field(default="", description="Improvement suggestion")


class UnifiedResponse(BaseModel):
    """
    Unified response model for all API endpoints.
    Ensures consistent response structure across the application.
    """
    success: bool = Field(default=True, description="Request success status")
    data: dict[str, Any] = Field(default_factory=dict, description="Response data")
    error: ErrorDetail = Field(default_factory=ErrorDetail, description="Error information")
    warning: WarningInfo = Field(default_factory=WarningInfo, description="Warning information")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp in ISO format"
    )
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata including timing information")

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "success": True,
                "data": {
                    "message": "Operation completed successfully"
                },
                "error": {
                    "has_error": False,
                    "code": "",
                    "message": "",
                    "details": ""
                },
                "warning": {
                    "has_warning": False,
                    "message": "",
                    "expected_minimum": 12,
                    "actual_extracted": 0,
                    "suggestion": ""
                },
                "timestamp": "2025-06-30T08:15:33.569670"
            }
        }


class IntersectionStats(BaseModel):
    """Statistics for intersection-based extraction strategies."""
    intersection_count: int = Field(default=0, description="Number of intersecting items")
    round1_count: int = Field(default=0, description="Items from round 1")
    round2_count: int = Field(default=0, description="Items from round 2")
    total_available: int = Field(default=0, description="Total available items")
    final_count: int = Field(default=0, description="Final selected items")
    supplement_count: int = Field(default=0, description="Supplemented items")
    strategy_used: str = Field(default="", description="Strategy used for extraction")
    warning: bool = Field(default=False, description="Whether warning triggered")
    warning_message: str = Field(default="", description="Warning message if any")


class StandardizedTerm(BaseModel):
    """Standardized term mapping information."""
    original: str = Field(default="", description="Original term")
    standardized: str = Field(default="", description="Standardized term")
    method: str = Field(default="", description="Standardization method used")


def create_success_response(
    data: dict[str, Any],
    metadata: dict[str, Any] | None = None
) -> UnifiedResponse:
    """Create a successful response with given data and optional metadata."""
    response = UnifiedResponse(
        success=True,
        data=data,
        error=ErrorDetail(),
        warning=WarningInfo(),
        timestamp=datetime.utcnow().isoformat()
    )

    # Add metadata if provided
    if metadata:
        response.metadata = metadata

    return response


def create_error_response(
    code: str,
    message: str,
    details: str = "",
    data: dict[str, Any] | None = None
) -> UnifiedResponse:
    """Create an error response with given error information."""
    return UnifiedResponse(
        success=False,
        data=data or {},
        error=ErrorDetail(
            has_error=True,
            code=code,
            message=message,
            details=details
        ),
        warning=WarningInfo(),
        timestamp=datetime.utcnow().isoformat()
    )


class ErrorCodes:
    """Centralized error code definitions for API validation."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TEXT_TOO_SHORT = "TEXT_TOO_SHORT"
    INVALID_LANGUAGE = "INVALID_LANGUAGE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"


def create_validation_error_response(field: str, message: str) -> UnifiedResponse:
    """Create validation error response with appropriate error code."""
    error_code = (
        ErrorCodes.TEXT_TOO_SHORT if "200" in message or "length" in message.lower()
        else ErrorCodes.VALIDATION_ERROR
    )
    if "language" in message.lower():
        error_code = ErrorCodes.INVALID_LANGUAGE

    return UnifiedResponse(
        success=False,
        data={},
        error=ErrorDetail(
            has_error=True,
            code=error_code,
            message=f"Validation failed for field '{field}'",
            details=message
        ),
        warning=WarningInfo(),
        timestamp=datetime.utcnow().isoformat()
    )
