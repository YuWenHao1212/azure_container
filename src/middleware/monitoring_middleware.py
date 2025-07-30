"""
Monitoring middleware for request/response tracking.
Implements comprehensive monitoring for all API endpoints.
"""
import json
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.metrics.endpoint_metrics import endpoint_metrics
from src.core.monitoring.security_monitor import security_monitor
from src.core.monitoring_service import monitoring_service
from src.utils.response_validator import validate_bubble_compatibility
from src.utils.user_agent_parser import get_client_category, parse_user_agent


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring API requests and responses.
    
    Features:
    - Request/response time tracking
    - Error rate monitoring by endpoint
    - Correlation ID generation
    - Custom properties tracking
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with monitoring."""
        # Security check first
        security_result = await security_monitor.check_request_security(request)
        
        if security_result["is_blocked"]:
            # Return 403 for blocked requests
            monitoring_service.track_event(
                "request_blocked",
                {
                    "client_ip": security_result["client_ip"],
                    "threats": security_result["threats"]
                }
            )
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "data": {},
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Access denied",
                        "details": "Your request has been blocked for security reasons"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
        
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        request.state.security_result = security_result
        
        # Save request body for potential error tracking (especially for 422 errors)
        # This is needed because FastAPI's request body can only be read once
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"] and request.url.path.endswith("extract-jd-keywords"):
            try:
                body_bytes = await request.body()
                request_body = body_bytes.decode('utf-8')
                # Store in request state for later use
                request.state.request_body = request_body
                # Create a new receive function that returns the cached body
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception:
                pass
        
        # Extract request information
        endpoint = f"{request.method} {request.url.path}"
        start_time = time.time()
        
        # Parse User-Agent
        user_agent = request.headers.get("user-agent", "")
        client_info = parse_user_agent(user_agent)
        client_category = get_client_category(client_info["client_type"])
        
        # Track request start with enhanced client info
        monitoring_service.track_event(
            "RequestStarted",
            {
                "endpoint": endpoint,
                "method": request.method,
                "path": request.url.path,
                "correlation_id": correlation_id,
                "origin": request.headers.get("origin", "unknown"),
                "user_agent": user_agent,
                "client_type": client_info["client_type"],
                "client_details": client_info["client_details"],
                "client_category": client_category,
                "is_api_client": client_info["is_api_client"],
                "is_browser": client_info["is_browser"],
                "security_risk": security_result.get("risk_level", "low"),
                "is_suspicious": security_result.get("is_suspicious", False)
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Track endpoint metrics using EndpointMetrics
            endpoint_metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                custom_properties={
                    "correlation_id": correlation_id
                }
            )
            
            # Read response body for validation (only for keyword extraction 200 responses)
            validation_result = None
            response_body = None
            
            # Store original body_iterator
            if hasattr(response, "body_iterator"):
                # Collect the body
                body_parts = []
                async for chunk in response.body_iterator:
                    body_parts.append(chunk)
                
                # Reconstruct the body
                response_body = b"".join(body_parts)
                
                # Create new iterator for the response
                async def new_body_iterator():
                    yield response_body
                
                response.body_iterator = new_body_iterator()
            
            # Validate response for Bubble.io compatibility
            if request.url.path == "/api/v1/extract-jd-keywords" and response.status_code == 200 and response_body:
                try:
                    body_json = json.loads(response_body.decode('utf-8'))
                    validation_result = validate_bubble_compatibility(body_json)
                    
                    # Track validation result
                    if not validation_result.get("bubble_compatible", True):
                        monitoring_service.track_event(
                            "ResponseValidationFailed",
                            {
                                "endpoint": endpoint,
                                "correlation_id": correlation_id,
                                "validation_issues": validation_result.get("issues", []),
                                "client_type": client_info["client_type"]
                            }
                        )
                except Exception as e:
                    # If we can't validate, log the error
                    validation_result = {"error": f"Could not validate response: {str(e)}", "bubble_compatible": None}
            
            # Track successful request with enhanced properties
            monitoring_service.track_request(
                endpoint=endpoint,
                method=request.method,
                duration_ms=duration_ms,
                success=response.status_code < 400,
                status_code=response.status_code,
                custom_properties={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "query_params": str(request.url.query),
                    "response_headers": dict(response.headers),
                    "client_type": client_info["client_type"],
                    "client_category": client_category,
                    "bubble_compatible": validation_result.get("bubble_compatible") if validation_result else None,
                    "validation_issues": validation_result.get("issues") if validation_result and not validation_result.get("bubble_compatible") else None
                }
            )
            
            # Add monitoring headers to response
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
            
            # Track specific endpoint metrics
            if request.url.path.startswith("/api/v1/extract-jd-keywords"):
                monitoring_service.track_metric(
                    "keyword_extraction_request",
                    1,
                    {
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "endpoint": endpoint,
                        "client_type": client_info["client_type"]
                    }
                )
            
            # Track client type usage
            monitoring_service.track_event(
                "ClientTypeUsage",
                {
                    "client_type": client_info["client_type"],
                    "client_category": client_category,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "success": response.status_code < 400
                }
            )
            
            # Special tracking for Bubble.io requests
            if client_info["client_type"] == "bubble.io":
                monitoring_service.track_event(
                    "BubbleIORequest",
                    {
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                        "bubble_compatible": validation_result.get("bubble_compatible") if validation_result else None,
                        "has_validation_issues": len(validation_result.get("issues", [])) > 0 if validation_result else None
                    }
                )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract anonymized JD preview for keyword extraction errors
            jd_preview = ""
            error_type = type(e).__name__
            error_message = str(e)
            
            # For HTTPException, extract the actual error details
            if hasattr(e, 'status_code') and hasattr(e, 'detail'):
                status_code = e.status_code
                if isinstance(e.detail, dict) and 'error' in e.detail:
                    error_info = e.detail['error']
                    error_type = error_info.get('code', error_type)
                    error_message = error_info.get('message', error_message)
            else:
                status_code = 500
            
            if request.url.path.endswith("extract-jd-keywords"):
                try:
                    # Get request body
                    body = await request.body()
                    data = json.loads(body)
                    jd_text = data.get("job_description", "")
                    
                    # Simply truncate to 100 chars - no anonymization for job descriptions
                    if jd_text:
                        jd_preview = jd_text[:100] + ("..." if len(jd_text) > 100 else "")
                except Exception:
                    jd_preview = "[Failed to extract JD]"
            
            # Track endpoint metrics for errors using EndpointMetrics
            endpoint_metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                duration_ms=duration_ms,
                error_type=error_type,
                custom_properties={
                    "correlation_id": correlation_id,
                    "error_message": error_message
                }
            )
            
            # Prepare custom properties for error tracking
            error_properties = {
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
                "duration_ms": duration_ms,
                "client_type": client_info["client_type"],
                "client_category": client_category
            }
            
            # Add JD preview only for keyword extraction errors
            if jd_preview:
                error_properties["jd_preview"] = jd_preview
            
            # Track error
            monitoring_service.track_error(
                error_type=error_type,
                error_message=error_message,
                endpoint=endpoint,
                custom_properties=error_properties
            )
            
            # Re-raise the exception
            raise
    
    def get_endpoint_stats(self) -> dict:
        """Get current endpoint statistics."""
        return endpoint_metrics.get_endpoint_stats()