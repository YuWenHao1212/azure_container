"""
API Response validator for Bubble.io compatibility.
Ensures all responses follow the UnifiedResponse structure.
"""
import json
from typing import Any


def validate_bubble_compatibility(response_body: Any) -> dict[str, Any]:
    """
    Validate that response follows Bubble.io compatibility rules.

    Rules:
    1. All fields must always exist (no Optional fields)
    2. Failed responses must use empty values, not null
    3. Must follow UnifiedResponse structure
    4. HTTP 200 must use same JSON structure

    Args:
        response_body: Response body to validate

    Returns:
        Dictionary with validation results and issues
    """
    issues = []
    is_valid = True

    # Check if it's a dict
    if not isinstance(response_body, dict):
        return {
            "is_valid": False,
            "issues": ["Response is not a JSON object"],
            "bubble_compatible": False
        }

    # Required top-level fields
    required_fields = ["success", "data", "error", "timestamp"]
    missing_fields = []

    for field in required_fields:
        if field not in response_body:
            missing_fields.append(field)
            is_valid = False

    if missing_fields:
        issues.append(f"Missing required fields: {', '.join(missing_fields)}")

    # Check for null values (Bubble.io doesn't handle them well)
    null_fields = check_for_nulls(response_body)
    if null_fields:
        issues.append(f"Found null values in fields: {', '.join(null_fields)}")
        is_valid = False

    # Validate success field
    if "success" in response_body and not isinstance(response_body["success"], bool):
        issues.append("'success' field must be boolean")
        is_valid = False

    # Validate data field
    if "data" in response_body:
        if not isinstance(response_body["data"], dict):
            issues.append("'data' field must be an object/dict")
            is_valid = False
        elif response_body.get("success") is False:
            # For failed responses, data should be empty dict
            if response_body["data"] != {}:
                issues.append("Failed responses should have empty data: {}")
                is_valid = False

    # Validate error field
    if "error" in response_body:
        if not isinstance(response_body["error"], dict):
            issues.append("'error' field must be an object/dict")
            is_valid = False
        else:
            # Error structure validation
            error_obj = response_body["error"]
            error_required = ["code", "message", "details"]
            for field in error_required:
                if field not in error_obj:
                    issues.append(f"'error' object missing required field: {field}")
                    is_valid = False
                elif error_obj[field] is None:
                    issues.append(f"'error.{field}' should not be null")
                    is_valid = False

            # For successful responses, error fields should be empty strings
            if response_body.get("success") is True:
                if error_obj.get("code") != "":
                    issues.append("Successful responses should have empty error code")
                    is_valid = False
                if error_obj.get("message") != "":
                    issues.append("Successful responses should have empty error message")
                    is_valid = False

    # Check specific endpoint data structures
    if "data" in response_body and isinstance(response_body["data"], dict):
        data = response_body["data"]

        # For keyword extraction endpoint - check if it has expected structure
        if any(key in data for key in ["keywords", "keyword_count", "confidence_score", "extraction_method"]):
            validate_keyword_extraction_response(data, issues)

    return {
        "is_valid": is_valid,
        "issues": issues,
        "bubble_compatible": is_valid and len(issues) == 0,
        "field_count": count_fields(response_body),
        "has_nulls": len(null_fields) > 0
    }


def check_for_nulls(obj: Any, path: str = "") -> list[str]:
    """
    Recursively check for null values in response.

    Args:
        obj: Object to check
        path: Current path in object

    Returns:
        List of paths containing null values
    """
    null_paths = []

    if obj is None:
        return [path or "root"]

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            null_paths.extend(check_for_nulls(value, current_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]"
            null_paths.extend(check_for_nulls(item, current_path))

    return null_paths


def validate_keyword_extraction_response(data: dict[str, Any], issues: list[str]) -> None:
    """
    Validate keyword extraction endpoint response structure.
    Ensures consistent format for 200 responses.

    Args:
        data: Data portion of response
        issues: List to append issues to
    """
    # Required fields for keyword extraction success response
    required_fields = [
        "keywords",
        "keyword_count",
        "confidence_score",
        "extraction_method",
        "intersection_stats",
        "warning",
        "prompt_version",
        "llm_config_used",
        "processing_time_ms",
        "detected_language",
        "input_language",
        "cache_hit",
        "total_processing_time_ms",
        "timing_breakdown"
    ]

    # Check all required fields exist
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing required field in keyword extraction response: '{field}'")

    # Check keywords structure
    if "keywords" in data:
        if data["keywords"] is None:
            issues.append("'keywords' should be empty list, not null")
        elif not isinstance(data["keywords"], list):
            issues.append("'keywords' must be a list")
        elif len(data["keywords"]) > 0:
            # Check keyword structure
            for i, keyword in enumerate(data["keywords"]):
                if not isinstance(keyword, str):
                    issues.append(f"'keywords[{i}]' must be a string")

    # Check keyword_count
    if "keyword_count" in data:
        if not isinstance(data["keyword_count"], int):
            issues.append("'keyword_count' must be an integer")
        elif data["keyword_count"] < 0:
            issues.append("'keyword_count' cannot be negative")

    # Check numeric fields
    numeric_fields = {
        "confidence_score": (0.0, 1.0),
        "processing_time_ms": (0.0, float('inf')),
        "total_processing_time_ms": (0.0, float('inf')),
        "language_detection_time_ms": (0.0, float('inf'))
    }

    for field, (min_val, max_val) in numeric_fields.items():
        if field in data:
            if data[field] is None:
                issues.append(f"'{field}' should be a number, not null")
            elif not isinstance(data[field], int | float):
                issues.append(f"'{field}' must be a number")
            elif not (min_val <= data[field] <= max_val):
                issues.append(f"'{field}' value {data[field]} out of range [{min_val}, {max_val}]")

    # Check boolean fields
    if "cache_hit" in data and not isinstance(data["cache_hit"], bool):
        issues.append("'cache_hit' must be a boolean")

    # Check string fields
    string_fields = ["extraction_method", "prompt_version", "detected_language", "input_language"]
    for field in string_fields:
        if field in data:
            if data[field] is None:
                issues.append(f"'{field}' should be a string, not null")
            elif not isinstance(data[field], str):
                issues.append(f"'{field}' must be a string")
            elif field != "input_language" and data[field] == "":  # input_language can be empty
                issues.append(f"'{field}' should not be empty")

    # Check complex objects
    if "intersection_stats" in data and not isinstance(data["intersection_stats"], dict):
        issues.append("'intersection_stats' must be an object")

    if "warning" in data:
        if not isinstance(data["warning"], dict):
            issues.append("'warning' must be an object")
        else:
            # Check warning structure
            warning_required = ["has_warning", "message", "expected_minimum", "actual_extracted", "suggestion"]
            for field in warning_required:
                if field not in data["warning"]:
                    issues.append(f"'warning' object missing required field: {field}")

    if "llm_config_used" in data and not isinstance(data["llm_config_used"], dict):
        issues.append("'llm_config_used' must be an object")

    if "timing_breakdown" in data and not isinstance(data["timing_breakdown"], dict):
        issues.append("'timing_breakdown' must be an object")


def count_fields(obj: Any) -> int:
    """
    Count total number of fields in response.

    Args:
        obj: Object to count fields in

    Returns:
        Total field count
    """
    if isinstance(obj, dict):
        count = len(obj)
        for value in obj.values():
            count += count_fields(value)
        return count
    elif isinstance(obj, list):
        count = 0
        for item in obj:
            count += count_fields(item)
        return count
    else:
        return 0


def generate_validation_report(response_body: Any) -> str:
    """
    Generate a human-readable validation report.

    Args:
        response_body: Response to validate

    Returns:
        Formatted validation report
    """
    result = validate_bubble_compatibility(response_body)

    report = []
    report.append("=== Bubble.io Compatibility Report ===")
    report.append(f"Status: {'✓ COMPATIBLE' if result['bubble_compatible'] else '✗ INCOMPATIBLE'}")
    report.append(f"Total Fields: {result['field_count']}")
    report.append(f"Has Null Values: {'Yes' if result['has_nulls'] else 'No'}")

    if result['issues']:
        report.append("\nIssues Found:")
        for i, issue in enumerate(result['issues'], 1):
            report.append(f"  {i}. {issue}")
    else:
        report.append("\nNo issues found.")

    report.append("\nResponse Structure:")
    json_str = json.dumps(response_body, indent=2)
    report.append(json_str[:500] + "..." if len(json_str) > 500 else json_str)

    return "\n".join(report)
