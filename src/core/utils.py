"""
Core utility functions for the application.
"""
from decimal import ROUND_HALF_UP, Decimal


def stable_percentage_round(value: float) -> int:
    """
    Stable percentage rounding method to solve floating-point precision issues.
    
    Uses Decimal to ensure consistent rounding behavior, especially for x.5 values.
    This prevents inconsistent results like sometimes getting 78% and sometimes 79%
    for values near 78.5%.
    
    Args:
        value: Float value between 0 and 1 to be converted to percentage and rounded
        
    Returns:
        Integer percentage value (0-100)
        
    Examples:
        >>> stable_percentage_round(0.785)  # Always returns 79
        79
        >>> stable_percentage_round(0.784999)  # Always returns 78
        78
    """
    # Convert to Decimal using string to avoid floating-point precision issues
    decimal_percent = Decimal(str(value)) * Decimal('100')
    
    # Use ROUND_HALF_UP for consistent traditional rounding (0.5 always rounds up)
    rounded = decimal_percent.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    return int(rounded)