"""
Resource Manager for managing memory, connections, and preventing memory leaks.
Designed for Azure Container Apps production environment.
"""
import asyncio
import contextlib
import gc
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Optional
from weakref import WeakSet

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    """Memory usage metrics snapshot."""
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage of system
    available_mb: float  # Available system memory in MB
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResourceStats:
    """Resource usage statistics."""
    active_connections: int = 0
    cached_objects: int = 0
    active_tasks: int = 0
    memory_metrics: Optional[MemoryMetrics] = None
    uptime_seconds: float = 0
    last_gc_time: float = 0
    gc_collections: Dict[int, int] = field(default_factory=dict)


class ResourceManager:
    """
    Centralized resource manager for preventing memory leaks.

    Features:
    - HTTP connection lifecycle management
    - Task tracking and cleanup
    - Memory monitoring and garbage collection
    - Cache size limits
    - Resource leak detection
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_cache_size: int = 1000,
        memory_check_interval: int = 300,  # 5 minutes
        enable_monitoring: bool = True
    ):
        self.max_connections = max_connections
        self.max_cache_size = max_cache_size
        self.memory_check_interval = memory_check_interval
        self.enable_monitoring = enable_monitoring

        # Resource tracking
        self._active_connections: WeakSet = WeakSet()
        self._active_tasks: WeakSet = WeakSet()
        self._cached_objects: Dict[str, Any] = {}
        self._startup_time = time.time()

        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_event = asyncio.Event()

        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None

        # Memory thresholds (MB)
        self.memory_warning_threshold = int(os.getenv("MEMORY_WARNING_THRESHOLD", "1500"))  # 1.5GB
        self.memory_critical_threshold = int(os.getenv("MEMORY_CRITICAL_THRESHOLD", "1800"))  # 1.8GB

        logger.info(f"ResourceManager initialized: max_connections={max_connections}, "
                   f"max_cache_size={max_cache_size}, monitoring_enabled={enable_monitoring}")

    async def start(self):
        """Start the resource manager and monitoring."""
        if self.enable_monitoring:
            self._monitor_task = asyncio.create_task(self._memory_monitor_loop())
            logger.info("Resource monitoring started")

    async def shutdown(self):
        """Shutdown the resource manager and cleanup all resources."""
        logger.info("Starting resource manager shutdown")

        # Signal shutdown
        self._shutdown_event.set()

        # Stop monitoring
        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

        # Cleanup resources
        await self._cleanup_all_resources()

        logger.info("Resource manager shutdown completed")

    def register_connection(self, connection: Any) -> None:
        """Register an active connection for tracking."""
        with self._lock:
            if len(self._active_connections) >= self.max_connections:
                logger.warning(f"Connection limit reached: {self.max_connections}")
            self._active_connections.add(connection)

    def register_task(self, task: Any) -> None:
        """Register an active task for tracking."""
        with self._lock:
            self._active_tasks.add(task)

    def set_cache_object(self, key: str, value: Any) -> None:
        """Set cache object with size limit."""
        with self._lock:
            if len(self._cached_objects) >= self.max_cache_size:
                # Remove oldest entries (simple FIFO)
                oldest_keys = list(self._cached_objects.keys())[:10]
                for old_key in oldest_keys:
                    del self._cached_objects[old_key]
                logger.debug(f"Cache size limit reached, removed {len(oldest_keys)} entries")

            self._cached_objects[key] = value

    def get_cache_object(self, key: str) -> Optional[Any]:
        """Get cache object."""
        with self._lock:
            return self._cached_objects.get(key)

    def clear_cache(self) -> None:
        """Clear all cached objects."""
        with self._lock:
            cache_size = len(self._cached_objects)
            self._cached_objects.clear()
            logger.info(f"Cleared {cache_size} cached objects")

    def get_stats(self) -> ResourceStats:
        """Get current resource usage statistics."""
        with self._lock:
            # Get memory metrics
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_percent = process.memory_percent()
                system_memory = psutil.virtual_memory()

                memory_metrics = MemoryMetrics(
                    rss_mb=memory_info.rss / 1024 / 1024,
                    vms_mb=memory_info.vms / 1024 / 1024,
                    percent=memory_percent,
                    available_mb=system_memory.available / 1024 / 1024
                )
            except Exception as e:
                logger.warning(f"Failed to get memory metrics: {e}")
                memory_metrics = None

            # Get GC stats
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]

            return ResourceStats(
                active_connections=len(self._active_connections),
                cached_objects=len(self._cached_objects),
                active_tasks=len(self._active_tasks),
                memory_metrics=memory_metrics,
                uptime_seconds=time.time() - self._startup_time,
                last_gc_time=getattr(self, '_last_gc_time', 0),
                gc_collections=gc_stats
            )

    async def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return results."""
        start_time = time.time()

        # Get before stats
        before_stats = self.get_stats()

        # Force GC for all generations
        collected = [gc.collect(i) for i in range(3)]

        # Update last GC time
        self._last_gc_time = time.time()

        # Get after stats
        after_stats = self.get_stats()

        gc_duration = time.time() - start_time

        result = {
            "duration_ms": round(gc_duration * 1000, 2),
            "objects_collected": sum(collected),
            "collections_by_generation": {str(i): collected[i] for i in range(3)},
            "memory_before_mb": before_stats.memory_metrics.rss_mb if before_stats.memory_metrics else 0,
            "memory_after_mb": after_stats.memory_metrics.rss_mb if after_stats.memory_metrics else 0,
            "memory_freed_mb": (
                (before_stats.memory_metrics.rss_mb - after_stats.memory_metrics.rss_mb)
                if before_stats.memory_metrics and after_stats.memory_metrics else 0
            )
        }

        logger.info(f"Forced garbage collection: {result}")
        return result

    async def _memory_monitor_loop(self):
        """Background memory monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self._check_memory_usage()
                await asyncio.sleep(self.memory_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitor loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _check_memory_usage(self):
        """Check memory usage and take action if needed."""
        stats = self.get_stats()
        if not stats.memory_metrics:
            return

        memory_mb = stats.memory_metrics.rss_mb

        # Import monitoring service here to avoid circular imports
        try:
            from src.core.monitoring_service import monitoring_service
            monitoring_service.track_event("MemoryUsageCheck", {
                "memory_mb": memory_mb,
                "memory_percent": stats.memory_metrics.percent,
                "active_connections": stats.active_connections,
                "cached_objects": stats.cached_objects,
                "active_tasks": stats.active_tasks
            })
        except ImportError:
            pass

        # Check thresholds
        if memory_mb > self.memory_critical_threshold:
            logger.error(
                f"CRITICAL: Memory usage {memory_mb:.1f}MB exceeds threshold "
                f"{self.memory_critical_threshold}MB"
            )
            await self._handle_critical_memory()
        elif memory_mb > self.memory_warning_threshold:
            logger.warning(
                f"WARNING: Memory usage {memory_mb:.1f}MB exceeds threshold "
                f"{self.memory_warning_threshold}MB"
            )
            await self._handle_warning_memory()

    async def _handle_warning_memory(self):
        """Handle warning-level memory usage."""
        # Clear half of cache
        with self._lock:
            cache_size = len(self._cached_objects)
            if cache_size > 100:
                keys_to_remove = list(self._cached_objects.keys())[:cache_size // 2]
                for key in keys_to_remove:
                    del self._cached_objects[key]
                logger.info(f"Cleared {len(keys_to_remove)} cache entries due to memory warning")

        # Force GC
        await self.force_garbage_collection()

    async def _handle_critical_memory(self):
        """Handle critical-level memory usage."""
        logger.error("Handling critical memory situation")

        # Clear all cache
        self.clear_cache()

        # Force aggressive GC
        await self.force_garbage_collection()

        # Wait and check again
        await asyncio.sleep(5)
        stats = self.get_stats()
        if stats.memory_metrics and stats.memory_metrics.rss_mb > self.memory_critical_threshold:
            logger.critical(f"Memory still critical after cleanup: {stats.memory_metrics.rss_mb:.1f}MB")

    async def _cleanup_all_resources(self):
        """Cleanup all tracked resources."""
        # Clear cache
        self.clear_cache()

        # Force GC
        await self.force_garbage_collection()

        # Log final stats
        final_stats = self.get_stats()
        logger.info(f"Final resource stats: connections={final_stats.active_connections}, "
                   f"tasks={final_stats.active_tasks}, "
                   f"memory={final_stats.memory_metrics.rss_mb:.1f}MB"
                   if final_stats.memory_metrics else "memory=unknown")

    @asynccontextmanager
    async def managed_connection(self, connection_factory):
        """Context manager for connection lifecycle management."""
        connection = None
        try:
            connection = await connection_factory()
            self.register_connection(connection)
            yield connection
        finally:
            if connection and hasattr(connection, 'aclose'):
                try:
                    await connection.aclose()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")

    @asynccontextmanager
    async def managed_task(self, task_coro) -> AsyncGenerator[asyncio.Task, None]:
        """Context manager for task lifecycle management."""
        task = None
        try:
            task = asyncio.create_task(task_coro)
            self.register_task(task)
            yield task
            await task
        except asyncio.CancelledError:
            if task:
                task.cancel()
            raise
        except Exception:
            if task:
                task.cancel()
            raise


# Global resource manager instance
resource_manager = ResourceManager()


# Convenience functions
async def start_resource_manager():
    """Start the global resource manager."""
    await resource_manager.start()


async def shutdown_resource_manager():
    """Shutdown the global resource manager."""
    await resource_manager.shutdown()


def get_resource_stats() -> ResourceStats:
    """Get current resource statistics."""
    return resource_manager.get_stats()


async def force_gc() -> Dict[str, Any]:
    """Force garbage collection."""
    return await resource_manager.force_garbage_collection()
