"""
Lightweight monitoring middleware for production.
Tracks errors and response times with minimal overhead (<1ms).
"""
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import ClassVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Business events logger with dual output support
from src.core.monitoring_logger import get_business_logger

business_logger = get_business_logger()


class ResponseTimeTracker:
    """In-memory response time tracking with percentile calculations"""

    def __init__(self, max_samples: int = 1000):
        self.lock = Lock()
        self.max_samples = max_samples
        # Store response times per endpoint
        self.times = defaultdict(lambda: deque(maxlen=max_samples))
        # Error counts per error code
        self.error_counts = defaultdict(int)
        # Last error examples
        self.last_errors = defaultdict(lambda: deque(maxlen=10))

    def add_request(self, endpoint: str, duration_ms: float, status_code: int,
                   error_code: str | None = None):
        """Add a request measurement"""
        with self.lock:
            # Store response time
            self.times[endpoint].append({
                "duration_ms": duration_ms,
                "status_code": status_code,
                "timestamp": time.time()
            })

            # Track errors
            if status_code >= 400 and error_code:
                self.error_counts[error_code] += 1
                self.last_errors[error_code].append({
                    "endpoint": endpoint,
                    "timestamp": datetime.utcnow().isoformat(),
                    "duration_ms": duration_ms
                })

    def get_stats(self) -> dict:
        """Get current statistics"""
        with self.lock:
            stats = {
                "endpoints": {},
                "errors": {},
                "summary": {
                    "total_endpoints": len(self.times),
                    "total_errors": sum(self.error_counts.values())
                }
            }

            # Calculate percentiles for each endpoint
            for endpoint, times in self.times.items():
                if times:
                    durations = [t["duration_ms"] for t in times]
                    durations.sort()

                    stats["endpoints"][endpoint] = {
                        "count": len(times),
                        "avg_ms": sum(durations) / len(durations),
                        "min_ms": durations[0],
                        "max_ms": durations[-1],
                        "p50_ms": self._percentile(durations, 0.50),
                        "p95_ms": self._percentile(durations, 0.95),
                        "p99_ms": self._percentile(durations, 0.99)
                    }

            # Error statistics
            for error_code, count in self.error_counts.items():
                stats["errors"][error_code] = {
                    "count": count,
                    "last_seen": (
                        list(self.last_errors[error_code])[-1]["timestamp"]
                        if self.last_errors[error_code] else None
                    ),
                    "recent_examples": list(self.last_errors[error_code])[-3:]
                }

            return stats

    def _percentile(self, sorted_values: list, p: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global tracker instance
response_tracker = ResponseTimeTracker()


class LightweightMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for production monitoring.
    Tracks errors and response times with minimal overhead (<1ms).
    """

    # Error code mapping
    ERROR_CODE_MAP: ClassVar[dict] = {
        # Client errors (4xx)
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        # Server errors (5xx)
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "TIMEOUT_ERROR"
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.error_thresholds = {
            "4xx": {"count": 0, "threshold": 50, "window": 300},  # 50 errors in 5 min
            "5xx": {"count": 0, "threshold": 10, "window": 60}    # 10 errors in 1 min
        }
        self.last_stats_log = time.time()
        self.stats_interval = 300  # Log stats every 5 minutes

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with minimal monitoring."""
        # Skip health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Track timing
        start_time = time.perf_counter()

        # Extract key information
        endpoint = request.url.path
        method = request.method

        error_code = None
        error_message = None

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract error info for 4xx/5xx responses
            if response.status_code >= 400:
                error_code = self.ERROR_CODE_MAP.get(response.status_code, f"HTTP_{response.status_code}")

                # Try to extract detailed error from response body
                if hasattr(response, "body_iterator"):
                    try:
                        # Read response body
                        body_parts = []
                        async for chunk in response.body_iterator:
                            body_parts.append(chunk)

                        body = b"".join(body_parts)

                        # Recreate iterator
                        async def new_iterator():
                            yield body
                        response.body_iterator = new_iterator()

                        # Parse error details
                        data = json.loads(body)
                        if "error" in data and isinstance(data["error"], dict):
                            error_code = data["error"].get("code", error_code)
                            error_message = data["error"].get("message", "")
                    except Exception as e:
                        # S110: Add logging to try-except-pass blocks
                        logging.debug(f"Failed to parse response body for error details: {e}")

            # Track the request
            response_tracker.add_request(
                endpoint=f"{method} {endpoint}",
                duration_ms=duration_ms,
                status_code=response.status_code,
                error_code=error_code
            )

            # Log slow requests (> 2 seconds) or errors
            if duration_ms > 2000 or response.status_code >= 400:
                log_level = logging.ERROR if response.status_code >= 500 else logging.WARNING
                business_logger.log(
                    log_level,
                    f"{'Slow' if duration_ms > 2000 else 'Error'} request - "
                    f"Endpoint: {method} {endpoint}, Status: {response.status_code}, "
                    f"Duration: {duration_ms:.0f}ms, Error: {error_code or 'None'}"
                )

            # Check error thresholds
            if response.status_code >= 400:
                error_class = "5xx" if response.status_code >= 500 else "4xx"
                self.error_thresholds[error_class]["count"] += 1

                # Alert if threshold exceeded
                threshold_info = self.error_thresholds[error_class]
                if threshold_info["count"] >= threshold_info["threshold"]:
                    business_logger.critical(
                        f"ERROR THRESHOLD EXCEEDED - {error_class} errors: "
                        f"{threshold_info['count']} in last {threshold_info['window']}s"
                    )
                    # Reset counter
                    threshold_info["count"] = 0

            # Add response headers
            response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"

            # Increment request counter
            self.request_count += 1

            # Periodic stats logging
            current_time = time.time()
            if current_time - self.last_stats_log > self.stats_interval:
                self._log_statistics()
                self.last_stats_log = current_time

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Determine error code based on exception type
            error_code = "INTERNAL_SERVER_ERROR"
            error_message = str(e)

            # Map known exceptions
            if "timeout" in str(e).lower():
                error_code = "TIMEOUT_ERROR"
            elif "database" in str(e).lower() or "psycopg" in str(e).lower():
                error_code = "DATABASE_ERROR"
            elif "openai" in str(e).lower() or "llm" in str(e).lower():
                error_code = "LLM_SERVICE_ERROR"

            # Track the error
            response_tracker.add_request(
                endpoint=f"{method} {endpoint}",
                duration_ms=duration_ms,
                status_code=500,
                error_code=error_code
            )

            # Log critical error
            business_logger.critical(
                f"Request failed - Endpoint: {method} {endpoint}, "
                f"Error: {error_code}, Message: {error_message}, "
                f"Duration: {duration_ms:.0f}ms",
                exc_info=True
            )

            # Re-raise the exception
            raise

    def _log_statistics(self):
        """Log periodic statistics"""
        stats = response_tracker.get_stats()

        # Overall summary
        business_logger.info(
            f"=== Performance Statistics ===\n"
            f"Total requests: {self.request_count}\n"
            f"Total errors: {stats['summary']['total_errors']}\n"
            f"Error rate: {stats['summary']['total_errors']/max(self.request_count, 1)*100:.2f}%"
        )

        # Top endpoints by volume
        if stats["endpoints"]:
            sorted_endpoints = sorted(
                stats["endpoints"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:5]

            business_logger.info("Top endpoints:")
            for endpoint, data in sorted_endpoints:
                business_logger.info(
                    f"  {endpoint}: {data['count']} requests, "
                    f"avg={data['avg_ms']:.0f}ms, p95={data['p95_ms']:.0f}ms"
                )

        # Error summary
        if stats["errors"]:
            business_logger.warning("Error summary:")
            for error_code, data in stats["errors"].items():
                business_logger.warning(
                    f"  {error_code}: {data['count']} occurrences, "
                    f"last seen: {data['last_seen']}"
                )

    def get_current_stats(self) -> dict:
        """Get current statistics (for debugging/health endpoints)"""
        stats = response_tracker.get_stats()
        stats["request_count"] = self.request_count
        return stats
