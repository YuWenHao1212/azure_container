"""
API Key authentication middleware for Container Apps.
Provides similar protection as Azure Function App host keys.
"""
import os

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API keys for all endpoints except health checks.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Get API key from environment variable
        self.api_key = os.getenv("CONTAINER_APP_API_KEY")
        self.bypass_paths = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate API key."""
        # Skip authentication for health checks and docs
        if request.url.path in self.bypass_paths:
            return await call_next(request)
        
        # Skip if API key is not configured (development mode)
        if not self.api_key:
            return await call_next(request)
        
        # Check for API key in query params (similar to Function Apps)
        code_param = request.query_params.get("code")
        
        # Also check for API key in headers (more secure)
        api_key_header = request.headers.get("X-API-Key")
        
        # Validate API key
        provided_key = code_param or api_key_header
        
        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "MISSING_API_KEY",
                        "message": "API key is required. Provide 'code' query parameter or 'X-API-Key' header.",
                        "type": "authentication_error"
                    }
                }
            )
        
        if provided_key != self.api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid API key",
                        "type": "authentication_error"
                    }
                }
            )
        
        # Valid API key, continue processing
        return await call_next(request)