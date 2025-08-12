"""
Error handling decorator for API endpoints.

This decorator provides automatic error handling using the ErrorHandlerFactory,
simplifying error management across all API endpoints.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.services.error_handler_factory import get_error_handler_factory

logger = logging.getLogger(__name__)


def handle_api_errors(api_name: str | None = None):
    """
    Decorator to handle API errors automatically.

    Args:
        api_name: Name of the API for monitoring and logging

    Returns:
        Decorated function with automatic error handling

    Example:
        @handle_api_errors(api_name="keyword_extraction")
        async def extract_keywords(request: ExtractKeywordsRequest):
            # API implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get error handler factory singleton
            error_handler = get_error_handler_factory()

            # Extract endpoint name from function
            endpoint = func.__name__

            # Create error context
            context = {
                "api_name": api_name or endpoint,
                "endpoint": f"/api/v1/{endpoint}",
                "debug": False,  # Can be made configurable
            }

            try:
                # Execute the actual endpoint function
                result = await func(*args, **kwargs)
                return result

            except HTTPException:
                # Let FastAPI handle HTTP exceptions normally
                raise

            except Exception as e:
                # Handle all other exceptions with factory
                logger.error(
                    f"Error in {api_name or endpoint}: {e!s}",
                    exc_info=True
                )

                # Generate error response using factory
                error_response = error_handler.handle_exception(e, context)

                # Extract status code from response
                status_code = error_response.pop("_status_code", 500)

                # Return JSON response with appropriate status code
                return JSONResponse(
                    status_code=status_code,
                    content=error_response
                )

        return wrapper
    return decorator


def handle_sync_api_errors(api_name: str | None = None):
    """
    Decorator to handle synchronous API errors automatically.

    Similar to handle_api_errors but for synchronous endpoints.

    Args:
        api_name: Name of the API for monitoring and logging

    Returns:
        Decorated function with automatic error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get error handler factory singleton
            error_handler = get_error_handler_factory()

            # Extract endpoint name from function
            endpoint = func.__name__

            # Create error context
            context = {
                "api_name": api_name or endpoint,
                "endpoint": f"/api/v1/{endpoint}",
                "debug": False,  # Can be made configurable
            }

            try:
                # Execute the actual endpoint function
                result = func(*args, **kwargs)
                return result

            except HTTPException:
                # Let FastAPI handle HTTP exceptions normally
                raise

            except Exception as e:
                # Handle all other exceptions with factory
                logger.error(
                    f"Error in {api_name or endpoint}: {e!s}",
                    exc_info=True
                )

                # Generate error response using factory
                error_response = error_handler.handle_exception(e, context)

                # Extract status code from response
                status_code = error_response.pop("_status_code", 500)

                # Return JSON response with appropriate status code
                return JSONResponse(
                    status_code=status_code,
                    content=error_response
                )

        return wrapper
    return decorator
