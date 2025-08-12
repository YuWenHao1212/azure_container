"""
Lightweight error dashboard endpoints for monitoring integration.
Provides error tracking statistics without heavy Application Insights dependency.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings
from src.middleware.lightweight_monitoring import response_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class ErrorSummary(BaseModel):
    """Error summary statistics"""
    error_code: str = Field(description="Error code")
    count: int = Field(description="Number of occurrences")
    last_seen: str | None = Field(description="Last occurrence timestamp")
    recent_examples: list[dict[str, Any]] = Field(description="Recent error examples")


class PerformanceStats(BaseModel):
    """Performance statistics for an endpoint"""
    endpoint: str = Field(description="Endpoint path")
    count: int = Field(description="Number of requests")
    avg_ms: float = Field(description="Average response time")
    min_ms: float = Field(description="Minimum response time")
    max_ms: float = Field(description="Maximum response time")
    p50_ms: float = Field(description="50th percentile response time")
    p95_ms: float = Field(description="95th percentile response time")
    p99_ms: float = Field(description="99th percentile response time")


class ErrorDashboardResponse(BaseModel):
    """Error dashboard response"""
    summary: dict[str, Any] = Field(description="Overall summary")
    top_errors: list[ErrorSummary] = Field(description="Top errors by frequency")
    slow_endpoints: list[PerformanceStats] = Field(description="Slowest endpoints")
    recent_errors: list[dict[str, Any]] = Field(description="Most recent errors")
    performance_by_endpoint: list[PerformanceStats] = Field(description="Performance stats by endpoint")


@router.get("/error-dashboard", response_model=ErrorDashboardResponse)
async def get_error_dashboard(
    settings: Settings = Depends(get_settings),
    limit: int = Query(default=10, description="Number of top items to return")
) -> ErrorDashboardResponse:
    """
    Get error dashboard with current statistics.

    Provides comprehensive error tracking and performance metrics
    from the lightweight monitoring system.
    """
    try:
        # Get current statistics from response tracker
        stats = response_tracker.get_stats()

        # Build top errors list
        top_errors = []
        if "errors" in stats:
            sorted_errors = sorted(
                stats["errors"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:limit]

            for error_code, error_data in sorted_errors:
                top_errors.append(ErrorSummary(
                    error_code=error_code,
                    count=error_data["count"],
                    last_seen=error_data.get("last_seen"),
                    recent_examples=error_data.get("recent_examples", [])
                ))

        # Build performance statistics
        performance_stats = []
        slow_endpoints = []

        if "endpoints" in stats:
            # Sort by response time for slow endpoints
            sorted_by_time = sorted(
                stats["endpoints"].items(),
                key=lambda x: x[1]["p95_ms"],
                reverse=True
            )[:limit]

            # Sort by request count for general performance
            sorted_by_count = sorted(
                stats["endpoints"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:limit]

            for endpoint, data in sorted_by_time:
                slow_endpoints.append(PerformanceStats(
                    endpoint=endpoint,
                    **data
                ))

            for endpoint, data in sorted_by_count:
                performance_stats.append(PerformanceStats(
                    endpoint=endpoint,
                    **data
                ))

        # Collect recent errors from all error types
        recent_errors = []
        if "errors" in stats:
            for error_code, error_data in stats["errors"].items():
                for example in error_data.get("recent_examples", []):
                    recent_errors.append({
                        "error_code": error_code,
                        "endpoint": example.get("endpoint"),
                        "timestamp": example.get("timestamp"),
                        "duration_ms": example.get("duration_ms")
                    })

        # Sort recent errors by timestamp (most recent first)
        recent_errors.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        recent_errors = recent_errors[:limit]

        # Build summary
        summary = {
            "total_endpoints_tracked": len(stats.get("endpoints", {})),
            "total_error_types": len(stats.get("errors", {})),
            "total_errors": stats.get("summary", {}).get("total_errors", 0),
            "monitoring_status": "active",
            "last_updated": "real-time"
        }

        return ErrorDashboardResponse(
            summary=summary,
            top_errors=top_errors,
            slow_endpoints=slow_endpoints,
            recent_errors=recent_errors,
            performance_by_endpoint=performance_stats
        )

    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error dashboard: {e!s}"
        ) from e


@router.get("/error-stats/{error_code}")
async def get_error_details(
    error_code: str,
    settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    """
    Get detailed information about a specific error code.
    """
    try:
        stats = response_tracker.get_stats()

        if "errors" not in stats or error_code not in stats["errors"]:
            raise HTTPException(
                status_code=404,
                detail=f"Error code '{error_code}' not found in current statistics"
            )

        error_data = stats["errors"][error_code]

        return {
            "error_code": error_code,
            "statistics": error_data,
            "analysis": {
                "frequency": "high" if error_data["count"] > 10 else "low",
                "last_occurrence": error_data.get("last_seen"),
                "affected_endpoints": list(set(
                    example.get("endpoint", "unknown")
                    for example in error_data.get("recent_examples", [])
                ))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving error details for {error_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve error details: {e!s}"
        ) from e


@router.get("/performance-summary")
async def get_performance_summary(
    settings: Settings = Depends(get_settings),
    threshold_ms: int = Query(default=1000, description="Slow request threshold in milliseconds")
) -> dict[str, Any]:
    """
    Get performance summary with configurable thresholds.
    """
    try:
        stats = response_tracker.get_stats()

        performance_summary = {
            "total_endpoints": len(stats.get("endpoints", {})),
            "slow_endpoints": [],
            "fast_endpoints": [],
            "performance_alerts": [],
            "threshold_ms": threshold_ms
        }

        if "endpoints" in stats:
            for endpoint, data in stats["endpoints"].items():
                endpoint_info = {
                    "endpoint": endpoint,
                    "avg_ms": data["avg_ms"],
                    "p95_ms": data["p95_ms"],
                    "count": data["count"]
                }

                # Categorize endpoints
                if data["p95_ms"] > threshold_ms:
                    performance_summary["slow_endpoints"].append(endpoint_info)

                    # Generate alert for very slow endpoints
                    if data["p95_ms"] > threshold_ms * 2:
                        performance_summary["performance_alerts"].append({
                            "type": "slow_endpoint",
                            "endpoint": endpoint,
                            "p95_ms": data["p95_ms"],
                            "severity": "high" if data["p95_ms"] > threshold_ms * 3 else "medium"
                        })
                else:
                    performance_summary["fast_endpoints"].append(endpoint_info)

        # Sort by performance
        performance_summary["slow_endpoints"].sort(
            key=lambda x: x["p95_ms"], reverse=True
        )
        performance_summary["fast_endpoints"].sort(
            key=lambda x: x["p95_ms"]
        )

        return performance_summary

    except Exception as e:
        logger.error(f"Error retrieving performance summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve performance summary: {e!s}"
        ) from e


@router.post("/reset-stats")
async def reset_monitoring_stats(
    settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    """
    Reset monitoring statistics (development/staging only).
    """
    # Only allow in non-production environments
    if settings.environment.lower() == "production":
        raise HTTPException(
            status_code=403,
            detail="Statistics reset not allowed in production environment"
        )

    try:
        # Reset the response tracker
        response_tracker.times.clear()
        response_tracker.error_counts.clear()
        response_tracker.last_errors.clear()

        logger.info("Monitoring statistics reset by admin request")

        return {
            "status": "success",
            "message": "Monitoring statistics have been reset"
        }

    except Exception as e:
        logger.error(f"Error resetting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset statistics: {e!s}"
        ) from e
