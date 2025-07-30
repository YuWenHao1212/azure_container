"""
Utility functions for formatting errors with detailed types.
Supports validation errors, HTTP errors, and general exceptions.
"""
import traceback
from typing import Any

from pydantic import ValidationError

# Configuration for error context logging
ERROR_CONTEXT_CONFIG = {
    "enable_stack_trace": False,  # 初期先關閉，需要時開啟
    "enable_memory_stats": False,  # 需要時再開啟
    "enable_request_body": True,   # 422 錯誤需要
    "max_preview_length": 200,     # 預覽長度限制
    "max_stack_frames": 5,         # 堆疊追蹤的最大框架數
}


def format_validation_errors(exc: ValidationError) -> dict[str, Any]:
    """
    Format Pydantic ValidationError into a structured response with error types.
    
    Args:
        exc: Pydantic ValidationError exception
        
    Returns:
        Dictionary with formatted error details including types
    """
    errors = []
    error_summary = {
        "total_errors": len(exc.errors()),
        "error_types": set(),
        "affected_fields": set()
    }
    
    for error in exc.errors():
        # Format field path
        field_path = ".".join(str(loc) for loc in error['loc'])
        
        # Create formatted error
        formatted_error = {
            "field": field_path,
            "type": error['type'],
            "message": error['msg']
        }
        
        # Add context information if available
        if 'ctx' in error and error['ctx']:
            # Make sure context is JSON serializable
            ctx = {}
            for key, value in error['ctx'].items():
                if key != 'error':  # Skip error objects
                    try:
                        # Test if serializable
                        import json
                        json.dumps(value)
                        ctx[key] = value
                    except (TypeError, ValueError):
                        ctx[key] = str(value)
            if ctx:
                formatted_error['context'] = ctx
        
        # Add input value if available (be careful with sensitive data)
        if 'input' in error:
            input_value = str(error['input'])
            # Truncate long inputs
            if len(input_value) > 100:
                input_value = input_value[:100] + "..."
            formatted_error['input'] = input_value
        
        errors.append(formatted_error)
        
        # Update summary
        error_summary["error_types"].add(error['type'])
        error_summary["affected_fields"].add(field_path)
    
    # Convert sets to lists for JSON serialization
    error_summary["error_types"] = list(error_summary["error_types"])
    error_summary["affected_fields"] = list(error_summary["affected_fields"])
    
    return {
        "errors": errors,
        "summary": error_summary
    }


# User-friendly error type descriptions
ERROR_TYPE_DESCRIPTIONS = {
    # String validations
    "string_too_short": "The text is too short",
    "string_too_long": "The text is too long",
    "string_pattern_mismatch": "The format is invalid",
    "string_type": "Must be text",
    
    # Number validations
    "less_than_equal": "The number is too large",
    "greater_than_equal": "The number is too small",
    "int_type": "Must be a whole number",
    "float_type": "Must be a number",
    
    # Required fields
    "missing": "This field is required",
    "value_error": "The value is invalid",
    
    # Type errors
    "type_error": "Wrong data type",
    "json_invalid": "Invalid JSON format",
    
    # Custom validations
    "value_error.job_description.too_short": "Job description too short after trimming"
}


def get_error_type_description(error_type: str, default: str = None) -> str:
    """
    Get a user-friendly description for an error type.
    
    Args:
        error_type: The Pydantic error type
        default: Default description if type not found
        
    Returns:
        User-friendly error description
    """
    return ERROR_TYPE_DESCRIPTIONS.get(error_type, default or error_type)


def create_validation_error_response(exc: ValidationError, include_preview: bool = True) -> dict[str, Any]:
    """
    Create a complete validation error response with detailed error types.
    
    Args:
        exc: Pydantic ValidationError exception
        include_preview: Whether to include a preview of the invalid data
        
    Returns:
        Complete error response dictionary
    """
    formatted_errors = format_validation_errors(exc)
    
    # Get the most specific error for the main message
    first_error = formatted_errors["errors"][0] if formatted_errors["errors"] else None
    main_message = "Request validation failed"
    
    if first_error:
        if first_error["type"] == "missing":
            main_message = f"Missing required field: {first_error['field']}"
        elif first_error["type"] == "string_too_short":
            main_message = f"Field '{first_error['field']}' is too short"
        elif first_error["type"] == "value_error":
            main_message = first_error["message"]
    
    return {
        "code": "VALIDATION_ERROR",
        "message": main_message,
        "type": "validation_error",
        "details": formatted_errors
    }


def get_validation_error_metrics(exc: ValidationError) -> dict[str, Any]:
    """
    Extract metrics from validation errors for monitoring.
    
    Args:
        exc: Pydantic ValidationError exception
        
    Returns:
        Dictionary with error metrics for tracking
    """
    error_types = []
    error_fields = []
    
    for error in exc.errors():
        error_types.append(error['type'])
        error_fields.append(".".join(str(loc) for loc in error['loc']))
    
    # Find the primary error type (first or most common)
    primary_error_type = error_types[0] if error_types else "unknown"
    
    # Count occurrences of each error type
    error_type_counts = {}
    for error_type in error_types:
        error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
    
    return {
        "error_count": len(exc.errors()),
        "primary_error_type": primary_error_type,
        "all_error_types": ",".join(set(error_types)),
        "error_fields": ",".join(error_fields),
        "error_type_counts": error_type_counts
    }


def classify_exception(exc: Exception) -> dict[str, Any]:
    """
    Classify an exception and extract useful information for tracking.
    
    Args:
        exc: Any exception
        
    Returns:
        Dictionary with exception classification and details
    """
    exc_type = type(exc).__name__
    exc_module = type(exc).__module__
    
    # Common exception categories
    categories = {
        # Database errors
        "DatabaseError": ["IntegrityError", "DataError", "OperationalError", "ProgrammingError"],
        "ConnectionError": ["ConnectionError", "ConnectionRefusedError", "BrokenPipeError", "TimeoutError"],
        "AuthenticationError": ["AuthenticationError", "PermissionError", "Unauthorized"],
        "ValidationError": ["ValidationError", "ValueError", "TypeError", "JSONDecodeError"],
        "NotFoundError": ["FileNotFoundError", "KeyError", "AttributeError", "IndexError"],
        "ConfigurationError": ["ConfigurationError", "SettingsError", "EnvironmentError"],
        "ExternalServiceError": ["HTTPError", "RequestException", "APIError", "ServiceUnavailable"],
        "ResourceError": ["MemoryError", "ResourceWarning", "ResourceExhausted"],
    }
    
    # Determine category
    category = "UnknownError"
    for cat_name, exc_types in categories.items():
        if exc_type in exc_types:
            category = cat_name
            break
    
    # Extract useful details
    details = {
        "exception_type": exc_type,
        "exception_module": exc_module,
        "exception_category": category,
        "exception_message": str(exc),
        "is_retryable": category in ["ConnectionError", "ExternalServiceError", "ResourceError"],
        "is_client_error": category in ["ValidationError", "NotFoundError", "AuthenticationError"],
        "is_server_error": category in ["DatabaseError", "ConfigurationError", "UnknownError"],
    }
    
    # Add specific details for known exception types
    if hasattr(exc, 'status_code'):
        details["status_code"] = exc.status_code
    if hasattr(exc, 'error_code'):
        details["error_code"] = exc.error_code
    if hasattr(exc, 'detail'):
        details["detail"] = exc.detail
    
    return details


def create_error_response(
    error_code: str,
    message: str,
    exc: Exception = None,
    status_code: int = 500,
    include_details: bool = True
) -> dict[str, Any]:
    """
    Create a standardized error response with exception details.
    
    Args:
        error_code: Error code (e.g., "INTERNAL_SERVER_ERROR")
        message: User-friendly error message
        exc: Optional exception for additional details
        status_code: HTTP status code
        include_details: Whether to include exception details
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "code": error_code,
        "message": message,
        "type": "error"
    }
    
    if exc and include_details:
        exc_details = classify_exception(exc)
        response["details"] = {
            "error_type": exc_details["exception_type"],
            "error_category": exc_details["exception_category"],
            "is_retryable": exc_details["is_retryable"],
            "technical_details": {
                "module": exc_details["exception_module"],
                "message": exc_details["exception_message"]
            }
        }
        
        # Add HTTP status code mapping
        if status_code == 500:
            if exc_details["is_client_error"]:
                response["suggested_status"] = 400
            elif exc_details["exception_category"] == "AuthenticationError":
                response["suggested_status"] = 401
            elif exc_details["exception_category"] == "NotFoundError":
                response["suggested_status"] = 404
    
    return response


def get_safe_preview(data: Any, max_length: int = None) -> str:
    """
    Get a safe preview of data for logging.
    
    Args:
        data: Data to preview
        max_length: Maximum length of preview
        
    Returns:
        Safe string representation of data
    """
    if max_length is None:
        max_length = ERROR_CONTEXT_CONFIG.get("max_preview_length", 200)
    
    try:
        preview = str(data)
        if len(preview) > max_length:
            preview = preview[:max_length] + "..."
        return preview
    except Exception:
        return "[Unable to preview]"


def get_stack_trace_preview(exc: Exception, max_frames: int = None) -> list[str]:
    """
    Get a preview of the stack trace.
    
    Args:
        exc: Exception object
        max_frames: Maximum number of frames to include
        
    Returns:
        List of stack trace frames
    """
    if max_frames is None:
        max_frames = ERROR_CONTEXT_CONFIG.get("max_stack_frames", 5)
    
    try:
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        # Get the most relevant frames (skip the last few which are usually framework code)
        relevant_lines = []
        for line in tb_lines[-max_frames-1:-1]:  # Skip the last line (the exception itself)
            if line.strip():
                relevant_lines.append(line.strip())
        return relevant_lines
    except Exception:
        return ["[Unable to extract stack trace]"]


def extract_validation_errors(exc: ValidationError) -> list[dict[str, Any]]:
    """
    Extract validation errors in a structured format.
    
    Args:
        exc: Pydantic ValidationError
        
    Returns:
        List of validation error details
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error['loc']),
            "type": error['type'],
            "message": error['msg'][:100]  # Limit message length
        })
    return errors[:10]  # Limit to first 10 errors


def should_log_detail(error_code: int, detail_type: str) -> bool:
    """
    Determine if specific detail should be logged.
    
    Args:
        error_code: HTTP error code
        detail_type: Type of detail to log
        
    Returns:
        Whether to log the detail
    """
    # 422 errors always need request body for debugging
    if error_code == 422 and detail_type == "request_body":
        return ERROR_CONTEXT_CONFIG.get("enable_request_body", True)
    
    # 500 errors might need stack trace (disabled by default)
    if error_code == 500 and detail_type == "stack_trace":
        return ERROR_CONTEXT_CONFIG.get("enable_stack_trace", False)
    
    # 503 errors might need service health
    if error_code == 503 and detail_type == "service_health":
        return True
    
    # 429 errors need rate limit info
    return error_code == 429 and detail_type == "rate_limit"


def get_error_context(error_code: int, request: Any, exc: Exception = None) -> dict[str, Any]:
    """
    Get enriched error context based on error type.
    
    Args:
        error_code: HTTP error code
        request: Request object
        exc: Optional exception
        
    Returns:
        Dictionary with error context
    """
    # Base context for all errors
    context = {
        "endpoint": f"{request.method} {request.url.path}",
        "correlation_id": getattr(request.state, 'correlation_id', 'unknown'),
        "user_agent": request.headers.get("user-agent", "unknown")[:100],
        "content_type": request.headers.get("content-type", "unknown"),
        "query_params": str(dict(request.query_params))[:100] if request.query_params else None,
    }
    
    # Add specific context based on error code
    if error_code == 422 and should_log_detail(422, "request_body"):
        # For validation errors, include request preview
        request_body = getattr(request.state, 'request_body', None)
        if request_body:
            context["request_body_preview"] = get_safe_preview(request_body)
            context["request_body_size"] = len(str(request_body))
        
        if isinstance(exc, ValidationError):
            context["validation_errors"] = extract_validation_errors(exc)
            context["validation_error_count"] = len(exc.errors())
    
    elif error_code == 500:
        if exc:
            context["exception_class"] = type(exc).__name__
            context["exception_module"] = type(exc).__module__
            context["exception_message"] = str(exc)[:200]
            
            if should_log_detail(500, "stack_trace"):
                context["stack_trace_preview"] = get_stack_trace_preview(exc)
    
    elif error_code == 503:
        # Service unavailable - might want to add health checks
        context["error_reason"] = "service_unavailable"
        # Future: Add service health metrics
        
    elif error_code == 429:
        # Rate limit exceeded
        context["error_reason"] = "rate_limit_exceeded"
        # Future: Add rate limit details from headers
        if hasattr(request.state, 'rate_limit_key'):
            context["rate_limit_key"] = request.state.rate_limit_key
    
    elif error_code == 404:
        # Not found - log the attempted path
        context["attempted_path"] = request.url.path
        context["available_methods"] = getattr(request.state, 'available_methods', [])
    
    elif error_code == 405:
        # Method not allowed - log attempted method
        context["attempted_method"] = request.method
        context["allowed_methods"] = getattr(request.state, 'allowed_methods', [])
    
    return context