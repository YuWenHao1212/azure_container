"""
Error capture middleware for debugging.
Captures request/response details for errors and stores them for analysis.
"""
import json
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.monitoring_config import StorageMode, monitoring_config

logger = logging.getLogger(__name__)


class ErrorStorage:
    """Manages error data storage with multiple backends"""

    def __init__(self):
        # Use smart configuration
        self.config = monitoring_config
        self.storage_mode = self.config.error_storage_mode
        self.max_memory_errors = self.config.max_memory_errors
        self.error_retention_hours = self.config.error_retention_hours

        # Memory storage
        self.memory_store = deque(maxlen=self.max_memory_errors)
        self.memory_lock = Lock()

        # Disk storage
        self.disk_path = Path(self.config.error_log_path)
        if self.storage_mode == StorageMode.DISK:
            self.disk_path.mkdir(parents=True, exist_ok=True)
            self._cleanup_old_files()

        # Log storage configuration
        storage_info = self.config.get_storage_info()
        logger.info(
            f"Error storage initialized: "
            f"Environment={storage_info['environment']}, "
            f"Mode={storage_info['storage_mode']}, "
            f"Location={storage_info['storage_location']}, "
            f"Auto-selected={storage_info['auto_selected']}"
        )

    async def store_error(self, error_data: dict[str, Any]):
        """Store error data based on configured mode"""
        # Always add to memory for quick access
        with self.memory_lock:
            self.memory_store.append(error_data)

        if self.storage_mode == StorageMode.DISK:
            await self._store_to_disk(error_data)
        elif self.storage_mode == StorageMode.BLOB:
            await self._store_to_blob(error_data)

    async def _store_to_disk(self, error_data: dict[str, Any]):
        """Store error to local disk"""
        try:
            # Create filename with timestamp and error code
            timestamp = error_data["timestamp"].replace(":", "-").replace(".", "-")
            error_code = error_data["error"]["code"]
            endpoint = error_data["request"]["endpoint"].replace("/", "_")

            filename = f"{timestamp}_{error_code}_{endpoint}.json"
            filepath = self.disk_path / filename

            # Write error data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(error_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Error saved to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save error to disk: {e}")

    async def _store_to_blob(self, error_data: dict[str, Any]):
        """Store error to Azure Blob Storage"""
        try:
            from azure.storage.blob.aio import BlobServiceClient

            # Use configuration
            connection_string = self.config.azure_storage_connection_string
            if not connection_string:
                # Try to build from account name and key
                if self.config.azure_storage_account_name and self.config.azure_storage_account_key:
                    connection_string = (
                        f"DefaultEndpointsProtocol=https;"
                        f"AccountName={self.config.azure_storage_account_name};"
                        f"AccountKey={self.config.azure_storage_account_key};"
                        f"EndpointSuffix=core.windows.net"
                    )
                else:
                    logger.warning("Blob storage configured but no connection string or account credentials")
                    return

            container_name = self.config.error_blob_container

            # Create blob name with date partitioning
            date_str = datetime.utcnow().strftime("%Y/%m/%d")
            timestamp = error_data["timestamp"]
            error_code = error_data["error"]["code"]

            blob_name = f"{date_str}/{timestamp}_{error_code}.json"

            # Upload to blob
            async with BlobServiceClient.from_connection_string(connection_string) as client:
                container_client = client.get_container_client(container_name)

                # Ensure container exists
                try:
                    await container_client.create_container()
                except Exception:
                    pass  # Container might already exist

                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(
                    json.dumps(error_data, indent=2, ensure_ascii=False),
                    overwrite=True
                )

            logger.info(f"Error saved to blob: {blob_name}")

        except Exception as e:
            logger.error(f"Failed to save error to blob: {e}")

    def get_recent_errors(self, count: int = 10) -> list:
        """Get recent errors from memory"""
        with self.memory_lock:
            return list(self.memory_store)[-count:]

    def _cleanup_old_files(self):
        """Clean up old error files from disk"""
        if self.storage_mode != StorageMode.DISK:
            return

        cutoff_time = datetime.utcnow() - timedelta(hours=self.error_retention_hours)

        for filepath in self.disk_path.glob("*.json"):
            try:
                # Parse timestamp from filename
                timestamp_str = filepath.stem.split("_")[0]
                file_time = datetime.fromisoformat(timestamp_str.replace("-", ":"))

                if file_time < cutoff_time:
                    filepath.unlink()
                    logger.info(f"Cleaned up old error file: {filepath}")
            except Exception:
                pass  # Skip files we can't parse


# Global error storage
error_storage = ErrorStorage()


class ErrorCaptureMiddleware(BaseHTTPMiddleware):
    """
    Captures full request/response details for errors to enable debugging.
    Works alongside LightweightMonitoringMiddleware for performance tracking.
    """

    def __init__(self, app):
        super().__init__(app)
        # Use smart configuration
        self.config = monitoring_config
        self.enabled = self.config.error_capture_enabled
        self.capture_success_samples = self.config.capture_success_samples
        self.max_body_size = self.config.max_capture_body_size

        # Sensitive data patterns to redact
        self.sensitive_patterns = [
            "password", "token", "key", "secret", "authorization", "api_key",
            "credit_card", "ssn", "email", "phone"
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Capture request/response for errors"""
        if not self.enabled or request.url.path == "/health":
            return await call_next(request)

        # Capture request data
        request_data = await self._capture_request(request)
        start_time = time.perf_counter()

        # Store body for reuse
        body_bytes = request_data.get("body_bytes")
        if body_bytes:
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Capture errors (4xx/5xx) or sample successes
            should_capture = (
                response.status_code >= 400 or
                (self.capture_success_samples and hash(request.url.path) % 100 == 0)
            )

            if should_capture:
                # Capture response data
                response_data = await self._capture_response(response)

                # Create error record
                error_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "duration_ms": duration_ms,
                    "request": request_data,
                    "response": response_data,
                    "error": self._extract_error_info(response_data)
                }

                # Store error
                await error_storage.store_error(error_record)

            return response

        except Exception as e:
            # Capture exception details
            duration_ms = (time.perf_counter() - start_time) * 1000

            error_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "correlation_id": getattr(request.state, "correlation_id", None),
                "duration_ms": duration_ms,
                "request": request_data,
                "response": {
                    "status_code": 500,
                    "headers": {},
                    "body": None
                },
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": str(e),
                    "type": type(e).__name__,
                    "traceback": self._get_safe_traceback()
                }
            }

            # Store error
            await error_storage.store_error(error_record)

            raise

    async def _capture_request(self, request: Request) -> dict[str, Any]:
        """Capture request details"""
        request_data = {
            "method": request.method,
            "endpoint": request.url.path,
            "query_params": dict(request.query_params),
            "headers": self._redact_headers(dict(request.headers)),
            "client_ip": request.client.host if request.client else None
        }

        # Capture body for POST/PUT/PATCH
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                request_data["body_bytes"] = body_bytes  # Store raw bytes

                if len(body_bytes) <= self.max_body_size:
                    # Try to parse as JSON
                    try:
                        body_json = json.loads(body_bytes)
                        request_data["body"] = self._redact_sensitive_data(body_json)
                    except Exception:
                        # Store as string if not JSON
                        request_data["body"] = body_bytes.decode('utf-8', errors='ignore')[:1000]
                else:
                    request_data["body"] = f"<Body too large: {len(body_bytes)} bytes>"
            except Exception as e:
                request_data["body"] = f"<Error reading body: {e!s}>"

        return request_data

    async def _capture_response(self, response: Response) -> dict[str, Any]:
        """Capture response details"""
        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }

        # Capture response body
        if hasattr(response, "body_iterator"):
            try:
                # Read response body
                body_parts = []
                async for chunk in response.body_iterator:
                    body_parts.append(chunk)

                body_bytes = b"".join(body_parts)

                # Recreate iterator
                async def new_iterator():
                    yield body_bytes
                response.body_iterator = new_iterator()

                # Parse body
                if len(body_bytes) <= self.max_body_size:
                    try:
                        body_json = json.loads(body_bytes)
                        response_data["body"] = self._redact_sensitive_data(body_json)
                    except Exception:
                        response_data["body"] = body_bytes.decode('utf-8', errors='ignore')[:1000]
                else:
                    response_data["body"] = f"<Body too large: {len(body_bytes)} bytes>"
            except Exception as e:
                response_data["body"] = f"<Error reading body: {e!s}>"

        return response_data

    def _extract_error_info(self, response_data: dict[str, Any]) -> dict[str, Any]:
        """Extract error information from response"""
        error_info = {
            "code": f"HTTP_{response_data['status_code']}",
            "message": "",
            "details": {}
        }

        # Try to extract from response body
        body = response_data.get("body")
        if isinstance(body, dict) and "error" in body:
            error = body["error"]
            if isinstance(error, dict):
                error_info.update({
                    "code": error.get("code", error_info["code"]),
                    "message": error.get("message", ""),
                    "details": error.get("details", {})
                })

        return error_info

    def _redact_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Redact sensitive headers"""
        redacted = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in self.sensitive_patterns):
                redacted[key] = "<REDACTED>"
            else:
                redacted[key] = value
        return redacted

    def _redact_sensitive_data(self, data: Any) -> Any:
        """Recursively redact sensitive data"""
        if isinstance(data, dict):
            redacted = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(pattern in key_lower for pattern in self.sensitive_patterns):
                    redacted[key] = "<REDACTED>"
                else:
                    redacted[key] = self._redact_sensitive_data(value)
            return redacted
        elif isinstance(data, list):
            return [self._redact_sensitive_data(item) for item in data]
        else:
            return data

    def _get_safe_traceback(self) -> str:
        """Get traceback without exposing sensitive info"""
        import traceback
        tb = traceback.format_exc()
        # Remove file paths that might expose system info
        lines = []
        for line in tb.split('\n'):
            if '/Users/' in line or '/home/' in line:
                line = line.split('/', 2)[-1]  # Keep only relative path
            lines.append(line)
        return '\n'.join(lines)


def get_error_debug_endpoint(app):
    """Add debug endpoint to retrieve captured errors"""

    @app.get("/api/v1/debug/errors")
    async def get_recent_errors(count: int = 10):
        """Get recent captured errors for debugging"""
        if not monitoring_config.error_capture_enabled:
            return {
                "success": False,
                "error": {
                    "code": "ERROR_CAPTURE_DISABLED",
                    "message": "Error capture is not enabled"
                }
            }

        errors = error_storage.get_recent_errors(count)
        storage_info = monitoring_config.get_storage_info()

        return {
            "success": True,
            "data": {
                "errors": errors,
                "count": len(errors),
                "storage_info": storage_info,
                "total_captured": len(error_storage.memory_store)
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.get("/api/v1/debug/storage-info")
    async def get_storage_info():
        """Get current error storage configuration"""
        storage_info = monitoring_config.get_storage_info()

        return {
            "success": True,
            "data": storage_info,
            "timestamp": datetime.utcnow().isoformat()
        }
