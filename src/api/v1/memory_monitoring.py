"""
Memory Monitoring API Endpoints for Azure Container Apps.
Provides memory usage statistics, leak detection, and resource management.
"""
import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.models.response import UnifiedResponse, create_error_response, create_success_response

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class MemoryStats(BaseModel):
    """Memory statistics model."""
    rss_mb: float = Field(description="Resident Set Size in MB")
    vms_mb: float = Field(description="Virtual Memory Size in MB")
    percent: float = Field(description="Memory percentage of system")
    available_mb: float = Field(description="Available system memory in MB")
    timestamp: str = Field(description="Timestamp of measurement")


class ResourceStats(BaseModel):
    """Resource usage statistics model."""
    active_connections: int = Field(description="Number of active connections")
    cached_objects: int = Field(description="Number of cached objects")
    active_tasks: int = Field(description="Number of active tasks")
    uptime_seconds: float = Field(description="Application uptime in seconds")
    memory_stats: MemoryStats = Field(description="Memory usage statistics")


class GarbageCollectionResult(BaseModel):
    """Garbage collection result model."""
    duration_ms: float = Field(description="GC duration in milliseconds")
    objects_collected: int = Field(description="Total objects collected")
    collections_by_generation: dict[str, int] = Field(description="Collections by GC generation")
    memory_before_mb: float = Field(description="Memory before GC (MB)")
    memory_after_mb: float = Field(description="Memory after GC (MB)")
    memory_freed_mb: float = Field(description="Memory freed by GC (MB)")


@router.get(
    "/memory/stats",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Memory Statistics",
    description="Get current memory usage and resource statistics"
)
async def get_memory_stats() -> UnifiedResponse:
    """
    Get current memory usage and resource statistics.

    Available in non-production environments only.
    """
    # Only allow in non-production environments
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code="FORBIDDEN",
                message="Memory monitoring not available in production",
                details="This endpoint is disabled in production for security"
            ).model_dump()
        ) from None

    try:
        # Try to get stats from resource manager
        from src.core.resource_manager import resource_manager

        stats = resource_manager.get_stats()

        # Convert to response model
        if stats.memory_metrics:
            memory_stats = MemoryStats(
                rss_mb=stats.memory_metrics.rss_mb,
                vms_mb=stats.memory_metrics.vms_mb,
                percent=stats.memory_metrics.percent,
                available_mb=stats.memory_metrics.available_mb,
                timestamp=datetime.fromtimestamp(stats.memory_metrics.timestamp, tz=UTC).isoformat()
            )
        else:
            # Fallback to basic memory stats
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()

            memory_stats = MemoryStats(
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=process.memory_percent(),
                available_mb=system_memory.available / 1024 / 1024,
                timestamp=datetime.now(UTC).isoformat()
            )

        resource_stats = ResourceStats(
            active_connections=stats.active_connections,
            cached_objects=stats.cached_objects,
            active_tasks=stats.active_tasks,
            uptime_seconds=stats.uptime_seconds,
            memory_stats=memory_stats
        )

        return create_success_response(data=resource_stats.model_dump())

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="SERVICE_UNAVAILABLE",
                message="Resource manager not available",
                details="Memory monitoring requires resource manager"
            ).model_dump()
        ) from e
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="Failed to get memory statistics",
                details=str(e)
            ).model_dump()
        ) from e


@router.post(
    "/memory/gc",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Force Garbage Collection",
    description="Force garbage collection and return statistics"
)
async def force_garbage_collection() -> UnifiedResponse:
    """
    Force garbage collection and return statistics.

    Available in non-production environments only.
    """
    # Only allow in non-production environments
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code="FORBIDDEN",
                message="Force GC not available in production",
                details="This endpoint is disabled in production for safety"
            ).model_dump()
        ) from None

    try:
        # Try to use resource manager for GC
        from src.core.resource_manager import resource_manager

        gc_result = await resource_manager.force_garbage_collection()

        # Convert to response model
        gc_response = GarbageCollectionResult(
            duration_ms=gc_result["duration_ms"],
            objects_collected=gc_result["objects_collected"],
            collections_by_generation=gc_result["collections_by_generation"],
            memory_before_mb=gc_result["memory_before_mb"],
            memory_after_mb=gc_result["memory_after_mb"],
            memory_freed_mb=gc_result["memory_freed_mb"]
        )

        logger.info(f"Forced GC completed: freed {gc_result['memory_freed_mb']:.1f}MB")

        return create_success_response(data=gc_response.model_dump())

    except ImportError:
        # Fallback to basic GC
        import gc
        import time

        import psutil

        process = psutil.Process()
        before_memory = process.memory_info().rss / 1024 / 1024

        start_time = time.time()
        collected = [gc.collect(i) for i in range(3)]
        duration = time.time() - start_time

        after_memory = process.memory_info().rss / 1024 / 1024

        gc_response = GarbageCollectionResult(
            duration_ms=duration * 1000,
            objects_collected=sum(collected),
            collections_by_generation={str(i): collected[i] for i in range(3)},
            memory_before_mb=before_memory,
            memory_after_mb=after_memory,
            memory_freed_mb=before_memory - after_memory
        )

        return create_success_response(data=gc_response.model_dump())

    except Exception as e:
        logger.error(f"Error during garbage collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="Failed to perform garbage collection",
                details=str(e)
            ).model_dump()
        ) from e


@router.post(
    "/memory/clear-cache",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear Application Cache",
    description="Clear all cached objects to free memory"
)
async def clear_cache() -> UnifiedResponse:
    """
    Clear all cached objects to free memory.

    Available in non-production environments only.
    """
    # Only allow in non-production environments
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code="FORBIDDEN",
                message="Cache clearing not available in production",
                details="This endpoint is disabled in production for safety"
            ).model_dump()
        ) from None

    try:
        from src.core.resource_manager import resource_manager

        # Get stats before clearing
        before_stats = resource_manager.get_stats()
        cached_before = before_stats.cached_objects

        # Clear cache
        resource_manager.clear_cache()

        # Get stats after clearing
        after_stats = resource_manager.get_stats()
        cached_after = after_stats.cached_objects

        result = {
            "cache_cleared": True,
            "objects_cleared": cached_before - cached_after,
            "objects_before": cached_before,
            "objects_after": cached_after
        }

        logger.info(f"Cache cleared: {result['objects_cleared']} objects removed")

        return create_success_response(data=result)

    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="SERVICE_UNAVAILABLE",
                message="Resource manager not available",
                details="Cache clearing requires resource manager"
            ).model_dump()
        ) from e
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="Failed to clear cache",
                details=str(e)
            ).model_dump()
        ) from e


@router.get(
    "/memory/health",
    response_model=UnifiedResponse,
    status_code=status.HTTP_200_OK,
    summary="Memory Health Check",
    description="Check if memory usage is within healthy limits"
)
async def memory_health_check() -> UnifiedResponse:
    """
    Check if memory usage is within healthy limits.

    This endpoint is available in all environments.
    """
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = process.memory_percent()

        # Define health thresholds
        container_limit_mb = float(os.getenv("CONTAINER_MEMORY_LIMIT_MB", "2048"))
        warning_threshold = float(os.getenv("MEMORY_WARNING_THRESHOLD", "1500"))
        critical_threshold = float(os.getenv("MEMORY_CRITICAL_THRESHOLD", "1800"))

        # Determine health status
        if memory_mb > critical_threshold:
            status_level = "critical"
            message = f"Memory usage {memory_mb:.1f}MB is critical"
        elif memory_mb > warning_threshold:
            status_level = "warning"
            message = f"Memory usage {memory_mb:.1f}MB is elevated"
        else:
            status_level = "healthy"
            message = f"Memory usage {memory_mb:.1f}MB is normal"

        health_data = {
            "status": status_level,
            "message": message,
            "memory_mb": round(memory_mb, 1),
            "memory_percent": round(memory_percent, 1),
            "container_limit_mb": container_limit_mb,
            "warning_threshold_mb": warning_threshold,
            "critical_threshold_mb": critical_threshold,
            "usage_percentage_of_limit": round((memory_mb / container_limit_mb) * 100, 1)
        }

        return create_success_response(data=health_data)

    except Exception as e:
        logger.error(f"Error in memory health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="INTERNAL_ERROR",
                message="Failed to check memory health",
                details=str(e)
            ).model_dump()
        ) from e
