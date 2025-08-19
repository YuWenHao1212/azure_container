"""
Dynamic Course Cache Monitoring API endpoints.

Provides real-time cache statistics, health monitoring, and management tools
for the dynamic course availability cache system.
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.decorators.error_handler import handle_api_errors
from src.services.dynamic_course_cache import get_course_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v1/debug/course-cache/stats")
@handle_api_errors
async def get_cache_stats() -> dict[str, Any]:
    """
    Get comprehensive cache performance statistics.

    Returns:
        Cache statistics including hit rate, memory usage, and performance metrics
    """
    cache = get_course_cache()
    stats = await cache.get_stats()

    return {
        "success": True,
        "cache_stats": {
            "hit_rate": f"{stats.hit_rate:.1f}%",
            "total_requests": stats.total_requests,
            "cache_hits": stats.cache_hits,
            "cache_misses": stats.cache_misses,
            "active_items": stats.active_items,
            "memory_usage_mb": stats.memory_usage_mb,
            "avg_retrieval_time_ms": f"{stats.avg_retrieval_time_ms:.2f}",
            "expired_items_cleaned": stats.expired_items_cleaned
        },
        "performance": {
            "cache_efficiency": "high" if stats.hit_rate > 70 else "medium" if stats.hit_rate > 40 else "low",
            "memory_status": "normal" if stats.memory_usage_mb < 80 else "high",
            "avg_response_time": f"{stats.avg_retrieval_time_ms:.2f}ms"
        },
        "health": {
            "status": "healthy" if stats.memory_usage_mb < 100 and stats.hit_rate > 0 else "warning",
            "max_capacity": cache._max_size,
            "utilization": f"{(stats.active_items / cache._max_size) * 100:.1f}%",
            "ttl_minutes": cache._ttl.total_seconds() / 60
        }
    }


@router.get("/api/v1/debug/course-cache/top-items")
@handle_api_errors
async def get_top_cached_items(limit: int = 10) -> dict[str, Any]:
    """
    Get most frequently accessed cache items.

    Args:
        limit: Maximum number of items to return (default: 10, max: 50)

    Returns:
        List of top cache items with access statistics
    """
    if limit > 50:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 50")

    cache = get_course_cache()
    top_items = await cache.get_top_items(limit)

    return {
        "success": True,
        "top_cached_items": top_items,
        "total_items": len(top_items),
        "limit": limit,
        "metadata": {
            "sorted_by": "access_count",
            "order": "descending"
        }
    }


@router.post("/api/v1/debug/course-cache/clear")
@handle_api_errors
async def clear_cache() -> dict[str, Any]:
    """
    Clear all items from the dynamic cache.

    ⚠️ WARNING: This will remove all cached course availability data.
    Use with caution in production environments.

    Returns:
        Confirmation of cache clearing operation
    """
    cache = get_course_cache()

    # Get stats before clearing
    stats_before = await cache.get_stats()
    items_before = stats_before.active_items

    # Clear the cache
    await cache.clear()

    # Get stats after clearing
    stats_after = await cache.get_stats()

    logger.warning(f"[CacheAPI] Manual cache clear: removed {items_before} items")

    return {
        "success": True,
        "message": "Cache cleared successfully",
        "items_removed": items_before,
        "cache_stats": {
            "before": {
                "active_items": items_before,
                "memory_usage_mb": stats_before.memory_usage_mb
            },
            "after": {
                "active_items": stats_after.active_items,
                "memory_usage_mb": stats_after.memory_usage_mb
            }
        },
        "warning": "All cached course availability data has been removed"
    }


@router.post("/api/v1/debug/course-cache/cleanup")
@handle_api_errors
async def cleanup_expired() -> dict[str, Any]:
    """
    Manually trigger cleanup of expired cache items.

    This operation removes all items that have exceeded their TTL.
    It's normally done automatically by the background task.

    Returns:
        Number of expired items removed
    """
    cache = get_course_cache()

    # Get stats before cleanup
    stats_before = await cache.get_stats()

    # Run cleanup
    expired_count = await cache.cleanup_expired()

    # Get stats after cleanup
    stats_after = await cache.get_stats()

    logger.info(f"[CacheAPI] Manual cleanup: removed {expired_count} expired items")

    return {
        "success": True,
        "message": "Expired items cleanup completed",
        "expired_items_removed": expired_count,
        "cache_stats": {
            "before": {
                "active_items": stats_before.active_items,
                "memory_usage_mb": stats_before.memory_usage_mb
            },
            "after": {
                "active_items": stats_after.active_items,
                "memory_usage_mb": stats_after.memory_usage_mb
            }
        },
        "memory_freed_mb": round(stats_before.memory_usage_mb - stats_after.memory_usage_mb, 2)
    }


@router.get("/api/v1/debug/course-cache/health")
@handle_api_errors
async def get_cache_health() -> dict[str, Any]:
    """
    Get cache health status and recommendations.

    Returns:
        Health assessment with actionable recommendations
    """
    cache = get_course_cache()
    stats = await cache.get_stats()

    # Health assessment logic
    health_status = "healthy"
    issues = []
    recommendations = []

    # Check hit rate
    if stats.hit_rate < 20:
        health_status = "warning"
        issues.append("Low cache hit rate")
        recommendations.append("Monitor query patterns - cache may not be effective for current workload")
    elif stats.hit_rate < 50:
        issues.append("Moderate cache hit rate")
        recommendations.append("Consider extending TTL if data freshness allows")

    # Check memory usage
    if stats.memory_usage_mb > 80:
        health_status = "warning"
        issues.append("High memory usage")
        recommendations.append("Consider reducing cache size or running cleanup")

    # Check utilization
    utilization = (stats.active_items / cache._max_size) * 100
    if utilization > 90:
        health_status = "warning"
        issues.append("Cache near capacity")
        recommendations.append("Increase max_size or reduce TTL to prevent frequent evictions")

    # Check if any requests have been made
    if stats.total_requests == 0:
        health_status = "warning"
        issues.append("No cache activity")
        recommendations.append("Cache is initialized but not being used")

    return {
        "success": True,
        "health": {
            "status": health_status,
            "score": max(0, 100 - len(issues) * 20),  # Simple scoring
            "issues": issues,
            "recommendations": recommendations
        },
        "metrics": {
            "hit_rate": f"{stats.hit_rate:.1f}%",
            "memory_usage_mb": stats.memory_usage_mb,
            "utilization": f"{utilization:.1f}%",
            "avg_response_time_ms": f"{stats.avg_retrieval_time_ms:.2f}"
        },
        "thresholds": {
            "hit_rate_warning": "< 20%",
            "hit_rate_good": "> 50%",
            "memory_warning": "> 80MB",
            "utilization_warning": "> 90%"
        }
    }
