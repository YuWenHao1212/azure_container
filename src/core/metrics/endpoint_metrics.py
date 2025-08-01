"""
Endpoint-level metrics collection and monitoring.
Tracks error rates, performance, and usage patterns per endpoint.
"""
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from src.core.monitoring_service import monitoring_service


class EndpointMetrics:
    """
    Endpoint-level metrics tracking.

    Features:
    - Per-endpoint error rate calculation
    - Response time tracking
    - Status code distribution
    - Real-time metrics updates
    """

    def __init__(self):
        """Initialize endpoint metrics tracking."""
        self.metrics = defaultdict(lambda: {
            "total_requests": 0,
            "failed_requests": 0,
            "total_duration_ms": 0,
            "min_duration_ms": float('inf'),
            "max_duration_ms": 0,
            "status_codes": defaultdict(int),
            "errors_by_type": defaultdict(int),
            "last_updated": None,
            "hourly_stats": defaultdict(lambda: {
                "requests": 0,
                "failures": 0,
                "total_duration": 0
            })
        })

        # Separate tracking for methods
        self.method_metrics = defaultdict(lambda: defaultdict(int))

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        error_type: str | None = None,
        custom_properties: dict[str, Any] | None = None
    ):
        """
        Record a request for an endpoint.

        Args:
            endpoint: The API endpoint path
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            error_type: Type of error if failed
            custom_properties: Additional properties to track
        """
        # Update endpoint metrics
        metrics = self.metrics[endpoint]
        metrics["total_requests"] += 1
        metrics["total_duration_ms"] += duration_ms
        metrics["min_duration_ms"] = min(metrics["min_duration_ms"], duration_ms)
        metrics["max_duration_ms"] = max(metrics["max_duration_ms"], duration_ms)
        metrics["status_codes"][status_code] += 1
        metrics["last_updated"] = datetime.now(UTC)

        # Track failures
        if status_code >= 400:
            metrics["failed_requests"] += 1
            if error_type:
                metrics["errors_by_type"][error_type] += 1

        # Update hourly stats
        current_hour = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        hourly = metrics["hourly_stats"][current_hour]
        hourly["requests"] += 1
        hourly["total_duration"] += duration_ms
        if status_code >= 400:
            hourly["failures"] += 1

        # Track method distribution
        self.method_metrics[endpoint][method] += 1

        # Calculate and send metrics
        self._calculate_and_send_metrics(endpoint, method, status_code, duration_ms)

    def _calculate_and_send_metrics(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ):
        """Calculate derived metrics and send to monitoring service."""
        metrics = self.metrics[endpoint]

        # Calculate error rate
        error_rate = 0.0
        if metrics["total_requests"] > 0:
            error_rate = (metrics["failed_requests"] / metrics["total_requests"]) * 100

        # Calculate average duration
        avg_duration = 0.0
        if metrics["total_requests"] > 0:
            avg_duration = metrics["total_duration_ms"] / metrics["total_requests"]

        # Send endpoint error rate metric
        monitoring_service.track_metric(
            "endpoint_error_rate",
            error_rate,
            {
                "endpoint": endpoint,
                "method": method,
                "total_requests": metrics["total_requests"],
                "failed_requests": metrics["failed_requests"]
            }
        )

        # Send endpoint performance metrics
        monitoring_service.track_metric(
            "endpoint_duration_ms",
            duration_ms,
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "avg_duration": avg_duration,
                "min_duration": metrics["min_duration_ms"],
                "max_duration": metrics["max_duration_ms"]
            }
        )

        # Send specific metrics for critical endpoints
        if endpoint == "/api/v1/extract-jd-keywords":
            monitoring_service.track_metric(
                "keyword_extraction_error_rate",
                error_rate,
                {
                    "total_requests": metrics["total_requests"],
                    "failed_requests": metrics["failed_requests"],
                    "avg_duration_ms": avg_duration
                }
            )

    def get_endpoint_stats(self, endpoint: str | None = None, include_summary: bool = True) -> dict[str, Any]:
        """
        Get statistics for endpoints.

        Args:
            endpoint: Specific endpoint to get stats for (None for all)
            include_summary: Include summary stats (for integration tests)

        Returns:
            Dictionary containing endpoint statistics
        """
        if endpoint:
            if endpoint not in self.metrics:
                return {"error": f"No data for endpoint: {endpoint}"}

            metrics = self.metrics[endpoint]
            return self._format_endpoint_stats(endpoint, metrics)

        # For unit tests - return simple endpoint dict
        if not include_summary:
            stats = {}
            for ep, metrics in self.metrics.items():
                stats[ep] = self._format_endpoint_stats(ep, metrics)
            return stats

        # For integration tests - return with summary
        total_requests = 0
        success_requests = 0
        error_requests = 0
        endpoints_by_path = {}

        # Collect stats per endpoint
        for ep, metrics in self.metrics.items():
            total_requests += metrics["total_requests"]
            failed = metrics["failed_requests"]
            success_requests += (metrics["total_requests"] - failed)
            error_requests += failed

            # Group by path and method
            if ep not in endpoints_by_path:
                endpoints_by_path[ep] = {}

            # Get method from method_metrics
            for method in self.method_metrics[ep]:
                endpoints_by_path[ep][method] = self._format_endpoint_stats(ep, metrics)

        return {
            "total_requests": total_requests,
            "success_requests": success_requests,
            "error_requests": error_requests,
            "endpoints": endpoints_by_path
        }

    def _format_endpoint_stats(self, endpoint: str, metrics: dict[str, Any]) -> dict[str, Any]:
        """Format endpoint statistics for display."""
        total_requests = metrics["total_requests"]

        if total_requests == 0:
            return {
                "endpoint": endpoint,
                "total_requests": 0,
                "error_rate": "0.00%",
                "avg_duration_ms": "0.00"
            }

        error_rate = (metrics["failed_requests"] / total_requests) * 100
        avg_duration = metrics["total_duration_ms"] / total_requests

        return {
            "endpoint": endpoint,
            "total_requests": total_requests,
            "failed_requests": metrics["failed_requests"],
            "error_rate": error_rate,  # Return as float for integration tests
            "error_rate_str": f"{error_rate:.2f}%",  # String format for display
            "error_types": dict(metrics["errors_by_type"]),  # For integration test compatibility
            "avg_duration_ms": f"{avg_duration:.2f}",
            "min_duration_ms": f"{metrics['min_duration_ms']:.2f}",
            "max_duration_ms": f"{metrics['max_duration_ms']:.2f}",
            "status_code_distribution": dict(metrics["status_codes"]),
            "errors_by_type": dict(metrics["errors_by_type"]),
            "method_distribution": dict(self.method_metrics.get(endpoint, {})),
            "last_updated": metrics["last_updated"].isoformat() if metrics["last_updated"] else None
        }

    def get_error_rate_summary(self) -> dict[str, Any]:
        """Get error rate summary for all endpoints."""
        summary = {
            "total_endpoints": len(self.metrics),
            "endpoints_with_errors": 0,
            "overall_error_rate": 0.0,
            "endpoints": []
        }

        total_requests = 0
        total_failures = 0

        for endpoint, metrics in self.metrics.items():
            requests = metrics["total_requests"]
            failures = metrics["failed_requests"]

            total_requests += requests
            total_failures += failures

            if failures > 0:
                summary["endpoints_with_errors"] += 1

            error_rate = (failures / requests * 100) if requests > 0 else 0

            summary["endpoints"].append({
                "endpoint": endpoint,
                "error_rate": f"{error_rate:.2f}%",
                "total_requests": requests,
                "failed_requests": failures
            })

        # Calculate overall error rate
        if total_requests > 0:
            summary["overall_error_rate"] = f"{(total_failures / total_requests * 100):.2f}%"

        # Sort by error rate
        summary["endpoints"].sort(
            key=lambda x: float(x["error_rate"].rstrip('%')),
            reverse=True
        )

        return summary

    def reset_metrics(self, endpoint: str | None = None):
        """
        Reset metrics for an endpoint or all endpoints.

        Args:
            endpoint: Specific endpoint to reset (None for all)
        """
        if endpoint:
            if endpoint in self.metrics:
                del self.metrics[endpoint]
                if endpoint in self.method_metrics:
                    del self.method_metrics[endpoint]
        else:
            self.metrics.clear()
            self.method_metrics.clear()


# Global endpoint metrics instance
endpoint_metrics = EndpointMetrics()
