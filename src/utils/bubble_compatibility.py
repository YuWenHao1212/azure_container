"""
Utility functions to ensure Bubble.io compatibility.
"""

from typing import Any


def ensure_bubble_compatibility(data: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure response format is compatible with Bubble.io requirements.

    Key behaviors:
    - Converts empty arrays to [""] for Bubble.io schema consistency
    - Ensures consistent field structure
    - Maintains type consistency for schema inference

    Args:
        data: Response dictionary to process

    Returns:
        Processed dictionary with guaranteed compatibility
    """

    def process_value(value: Any) -> Any:
        """Recursively process values to ensure compatibility."""
        if isinstance(value, list):
            # Convert empty arrays to [""] for Bubble.io compatibility
            # Bubble.io has issues with empty arrays in schema inference
            if len(value) == 0:
                return [""]
            # Process list items recursively
            return [process_value(item) for item in value]
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            return {k: process_value(v) for k, v in value.items()}
        elif value is None:
            # Handle None values based on context
            # For strings, return empty string
            # For numbers, return 0
            # This is context-dependent and might need adjustment
            return value
        return value

    return process_value(data)


def validate_array_fields(response: dict[str, Any], array_fields: list[str]) -> dict[str, Any]:
    """
    Validate that specified fields are always arrays.

    Args:
        response: Response dictionary
        array_fields: List of field paths that must be arrays

    Returns:
        Response with validated array fields
    """
    for field_path in array_fields:
        parts = field_path.split('.')
        current = response

        # Navigate to parent of target field
        for part in parts[:-1]:
            if part in current and isinstance(current[part], dict):
                current = current[part]
            else:
                break

        # Ensure final field is an array
        field_name = parts[-1]
        if field_name in current:
            if current[field_name] is None:
                current[field_name] = []
            elif not isinstance(current[field_name], list):
                current[field_name] = [current[field_name]]

    return response


# List of field paths that must always be arrays for Bubble.io
BUBBLE_ARRAY_FIELDS = [
    "data.keyword_tracking.still_covered",
    "data.keyword_tracking.removed",
    "data.keyword_tracking.newly_added",
    "data.keyword_tracking.still_missing",
    "data.keyword_tracking.warnings",
    "data.coverage.before.covered",
    "data.coverage.before.missed",
    "data.coverage.after.covered",
    "data.coverage.after.missed",
    "data.coverage.newly_added",
    "data.coverage.removed",
    "warning.details",
]
