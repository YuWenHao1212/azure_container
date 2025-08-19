"""
Dynamic Course Availability Cache System

A high-performance, memory-efficient caching system for course availability queries.
Uses LRU eviction with TTL expiration and thread-safe operations.

Features:
- Cache key based on full embedding text hash (not just skill_name)
- TTL-based expiration (30 minutes default)
- LRU eviction for memory management
- Thread-safe async operations
- Lightweight monitoring integration
"""
import asyncio
import contextlib
import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, ClassVar

from src.core.monitoring_service import monitoring_service

logger = logging.getLogger(__name__)


@dataclass
class CacheItem:
    """Cache item with metadata for LRU and TTL management"""
    data: dict[str, Any]
    timestamp: datetime
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    avg_retrieval_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    active_items: int = 0
    expired_items_cleaned: int = 0


class DynamicCourseCache:
    """
    Dynamic course availability cache with LRU + TTL management.

    Features:
    - Precise cache keys based on embedding text hash
    - Automatic TTL expiration (30 minutes default)
    - LRU eviction when capacity is reached
    - Thread-safe async operations
    - Monitoring integration for lightweight tracking
    """

    # Cache configuration
    DEFAULT_MAX_SIZE: ClassVar[int] = 1000
    DEFAULT_TTL_MINUTES: ClassVar[int] = 30
    CACHE_KEY_LENGTH: ClassVar[int] = 16  # MD5 hash truncated length

    def __init__(self, max_size: int | None = None, ttl_minutes: int | None = None):
        """
        Initialize dynamic cache.

        Args:
            max_size: Maximum number of cache items (default: 1000)
            ttl_minutes: Time-to-live in minutes (default: 30)
        """
        self._max_size = max_size or self.DEFAULT_MAX_SIZE
        self._ttl = timedelta(minutes=ttl_minutes or self.DEFAULT_TTL_MINUTES)

        # Cache storage and LRU tracking
        self._cache: dict[str, CacheItem] = {}
        self._access_order: deque[str] = deque()  # Most recent at right

        # Thread safety
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats = CacheStats()

        logger.info(
            f"[DynamicCourseCache] Initialized with max_size={self._max_size}, "
            f"ttl={self._ttl.total_seconds()/60:.1f}min"
        )

    def generate_cache_key(
        self,
        skill_query: dict[str, Any],
        skill_category: str,
        threshold: float,
        platform: str = "coursera"
    ) -> str:
        """
        Generate precise cache key based on embedding text and query parameters.

        Args:
            skill_query: Skill query with name, description, category
            skill_category: Skill category (SKILL, FIELD, DEFAULT)
            threshold: Similarity threshold
            platform: Course platform (default: coursera)

        Returns:
            16-character cache key (MD5 hash truncated)
        """
        # Generate embedding text using same logic as CourseAvailabilityChecker
        embedding_text = self._generate_embedding_text(skill_query, skill_category)

        # Combine all query parameters that affect results
        cache_components = [
            embedding_text,
            skill_category,
            f"{threshold:.2f}",  # Round to 2 decimal places
            platform
        ]

        # Generate MD5 hash and truncate
        cache_string = "|".join(cache_components)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()  # noqa: S324

        return cache_hash[:self.CACHE_KEY_LENGTH]

    def _generate_embedding_text(self, skill_query: dict[str, Any], skill_category: str) -> str:
        """
        Generate embedding text using same logic as CourseAvailabilityChecker.

        This ensures cache key consistency with actual query execution.
        """
        skill_name = skill_query.get('skill_name', '')
        description = skill_query.get('description', '')

        if skill_category == "SKILL":
            # For technical skills: emphasize course, project, certificate
            return f"{skill_name} course project certificate. {description}"
        elif skill_category == "FIELD":
            # For domain knowledge: emphasize specialization, degree
            return f"{skill_name} specialization degree. {description}"
        else:
            # Default: balanced approach
            return f"{skill_name} {description}"

    async def get(self, cache_key: str) -> dict[str, Any] | None:
        """
        Retrieve item from cache with LRU update.

        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cached data if found and not expired, None otherwise
        """
        start_time = datetime.now()

        async with self._lock:
            self._stats.total_requests += 1

            # Check if key exists
            if cache_key not in self._cache:
                self._stats.cache_misses += 1
                self._track_operation("cache_miss", start_time)
                return None

            item = self._cache[cache_key]

            # Check TTL expiration
            if self._is_expired(item):
                logger.debug(f"[DynamicCourseCache] Cache key expired: {cache_key}")
                self._remove_item(cache_key)
                self._stats.cache_misses += 1
                self._track_operation("cache_miss_expired", start_time)
                return None

            # Update LRU tracking
            self._update_access(cache_key, item)

            # Track cache hit
            self._stats.cache_hits += 1
            self._track_operation("cache_hit", start_time)

            logger.debug(f"[DynamicCourseCache] Cache hit: {cache_key}")
            return item.data.copy()  # Return copy to prevent modification

    async def set(self, cache_key: str, data: dict[str, Any]) -> None:
        """
        Store item in cache with capacity management.

        Args:
            cache_key: Cache key to store
            data: Data to cache
        """
        start_time = datetime.now()

        async with self._lock:
            # Create cache item
            item = CacheItem(
                data=data.copy(),  # Store copy to prevent external modification
                timestamp=datetime.now(),
                access_count=1,
                last_access=datetime.now()
            )

            # Check capacity and evict if necessary
            if cache_key not in self._cache and len(self._cache) >= self._max_size:
                self._evict_lru()

            # Store item
            self._cache[cache_key] = item
            self._access_order.append(cache_key)

            self._track_operation("cache_set", start_time)
            logger.debug(f"[DynamicCourseCache] Cache set: {cache_key}")

    async def clear(self) -> None:
        """Clear all cache items."""
        async with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            logger.info(f"[DynamicCourseCache] Cleared {cleared_count} items")

    async def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Returns:
            Number of items removed
        """
        async with self._lock:
            expired_keys = []

            for key, item in self._cache.items():
                if self._is_expired(item):
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_item(key)

            self._stats.expired_items_cleaned += len(expired_keys)

            if expired_keys:
                logger.info(f"[DynamicCourseCache] Cleaned {len(expired_keys)} expired items")

            return len(expired_keys)

    async def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        async with self._lock:
            # Update calculated fields
            if self._stats.total_requests > 0:
                self._stats.hit_rate = (self._stats.cache_hits / self._stats.total_requests) * 100

            self._stats.active_items = len(self._cache)
            self._stats.memory_usage_mb = self._estimate_memory_usage()

            return self._stats

    async def get_top_items(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get most frequently accessed cache items.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of top cache items with metadata
        """
        async with self._lock:
            # Sort by access count (descending)
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )[:limit]

            return [
                {
                    "cache_key": key,
                    "access_count": item.access_count,
                    "age_minutes": (datetime.now() - item.timestamp).total_seconds() / 60,
                    "last_access": item.last_access.isoformat(),
                    "data_size_bytes": len(str(item.data))
                }
                for key, item in sorted_items
            ]

    def _is_expired(self, item: CacheItem) -> bool:
        """Check if cache item has expired."""
        return datetime.now() - item.timestamp > self._ttl

    def _update_access(self, cache_key: str, item: CacheItem) -> None:
        """Update LRU tracking for accessed item."""
        # Update item metadata
        item.access_count += 1
        item.last_access = datetime.now()

        # Move to end of access order (most recent)
        with contextlib.suppress(ValueError):
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._access_order:
            return

        # Remove least recently used (leftmost)
        lru_key = self._access_order.popleft()
        if lru_key in self._cache:
            del self._cache[lru_key]
            logger.debug(f"[DynamicCourseCache] Evicted LRU item: {lru_key}")

    def _remove_item(self, cache_key: str) -> None:
        """Remove item from cache and access tracking."""
        if cache_key in self._cache:
            del self._cache[cache_key]

        with contextlib.suppress(ValueError):
            self._access_order.remove(cache_key)

    def _estimate_memory_usage(self) -> float:
        """Estimate cache memory usage in MB."""
        if not self._cache:
            return 0.0

        # Rough estimate: average item size * count
        sample_size = min(10, len(self._cache))
        total_size = 0

        for i, (key, item) in enumerate(self._cache.items()):
            if i >= sample_size:
                break
            # Estimate: key + data + metadata
            total_size += len(key) + len(str(item.data)) + 200  # 200 bytes for metadata

        avg_size = total_size / sample_size
        total_mb = (avg_size * len(self._cache)) / (1024 * 1024)

        return round(total_mb, 2)

    def _track_operation(self, operation: str, start_time: datetime) -> None:
        """Track cache operation for monitoring."""
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Update average retrieval time
        if operation in ["cache_hit", "cache_miss"]:
            current_avg = self._stats.avg_retrieval_time_ms
            total_ops = self._stats.cache_hits + self._stats.cache_misses

            if total_ops > 1:
                self._stats.avg_retrieval_time_ms = (
                    (current_avg * (total_ops - 1) + duration_ms) / total_ops
                )
            else:
                self._stats.avg_retrieval_time_ms = duration_ms

        # Send to monitoring service (lightweight mode)
        try:
            monitoring_service.track_event("DynamicCacheOperation", {
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "cache_size": len(self._cache),
                "hit_rate": self._stats.hit_rate
            })
        except Exception as e:
            # Don't let monitoring failures affect cache operations
            logger.warning(f"[DynamicCourseCache] Monitoring error: {e}")


# Global cache instance
_cache_instance: DynamicCourseCache | None = None


def get_course_cache() -> DynamicCourseCache:
    """
    Get global cache instance (singleton pattern).

    Returns:
        DynamicCourseCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = DynamicCourseCache()
        logger.info("[DynamicCourseCache] Created global cache instance")

    return _cache_instance


# Background cleanup task
async def start_background_cleanup():
    """Start background task for periodic cache cleanup."""
    cache = get_course_cache()

    while True:
        try:
            # Run cleanup every hour
            await asyncio.sleep(3600)
            await cache.cleanup_expired()
        except Exception as e:
            logger.error(f"[DynamicCourseCache] Background cleanup error: {e}")
            # Continue running despite errors
