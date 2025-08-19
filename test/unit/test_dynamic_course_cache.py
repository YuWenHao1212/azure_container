"""
Unit tests for DynamicCourseCache system.

Tests cache functionality including:
- Cache key generation
- TTL expiration
- LRU eviction
- Thread safety
- Statistics tracking
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.dynamic_course_cache import CacheItem, CacheStats, DynamicCourseCache


class TestDynamicCourseCache:
    """Unit tests for DynamicCourseCache"""

    @pytest.fixture
    def cache(self):
        """Create cache instance for testing"""
        return DynamicCourseCache(max_size=5, ttl_minutes=1)  # Small size and TTL for testing

    @pytest.fixture
    def sample_skill_query(self):
        """Sample skill query for testing"""
        return {
            "skill_name": "Python",
            "description": "Programming language for web development",
            "skill_category": "SKILL"
        }

    @pytest.fixture
    def sample_cache_data(self):
        """Sample cache data"""
        return {
            "has_available_courses": True,
            "course_count": 5,
            "available_course_ids": ["coursera_crse:v1-123", "coursera_crse:v1-456"],
            "preferred_courses": 3,
            "other_courses": 2
        }

    def test_cache_key_generation(self, cache, sample_skill_query):
        """Test cache key generation with different parameters"""
        # Test basic key generation
        key1 = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)
        assert len(key1) == 16  # MD5 hash truncated to 16 chars

        # Test key consistency
        key2 = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)
        assert key1 == key2

        # Test different parameters produce different keys
        key3 = cache.generate_cache_key(sample_skill_query, "FIELD", 0.30)
        assert key1 != key3

        key4 = cache.generate_cache_key(sample_skill_query, "SKILL", 0.25)
        assert key1 != key4

    def test_embedding_text_generation(self, cache):
        """Test embedding text generation for different skill categories"""
        skill_query = {
            "skill_name": "Python",
            "description": "Programming language"
        }

        # Test SKILL category
        text_skill = cache._generate_embedding_text(skill_query, "SKILL")
        assert "course project certificate" in text_skill
        assert "Python" in text_skill
        assert "Programming language" in text_skill

        # Test FIELD category
        text_field = cache._generate_embedding_text(skill_query, "FIELD")
        assert "specialization degree" in text_field
        assert "Python" in text_field

        # Test DEFAULT category
        text_default = cache._generate_embedding_text(skill_query, "DEFAULT")
        assert text_default == "Python Programming language"

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache, sample_skill_query, sample_cache_data):
        """Test basic get/set operations"""
        cache_key = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)

        # Test cache miss
        result = await cache.get(cache_key)
        assert result is None

        # Test cache set
        await cache.set(cache_key, sample_cache_data)

        # Test cache hit
        result = await cache.get(cache_key)
        assert result is not None
        assert result["has_available_courses"] is True
        assert result["course_count"] == 5
        assert len(result["available_course_ids"]) == 2

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, sample_skill_query, sample_cache_data):
        """Test TTL expiration functionality"""
        # Create cache with very short TTL
        cache = DynamicCourseCache(max_size=10, ttl_minutes=0.01)  # 0.6 seconds
        cache_key = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)

        # Set cache item
        await cache.set(cache_key, sample_cache_data)

        # Should be available immediately
        result = await cache.get(cache_key)
        assert result is not None

        # Wait for expiration
        await asyncio.sleep(1)

        # Should be expired now
        result = await cache.get(cache_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, sample_cache_data):
        """Test LRU eviction when cache reaches capacity"""
        cache = DynamicCourseCache(max_size=3, ttl_minutes=60)  # Small cache for testing

        # Fill cache to capacity
        keys = []
        for i in range(3):
            skill_query = {"skill_name": f"Skill{i}", "description": "test", "skill_category": "SKILL"}
            key = cache.generate_cache_key(skill_query, "SKILL", 0.30)
            keys.append(key)
            await cache.set(key, {**sample_cache_data, "course_count": i})

        # Access first key to make it most recent
        await cache.get(keys[0])

        # Add new item - should evict keys[1] (least recently used)
        new_skill = {"skill_name": "NewSkill", "description": "test", "skill_category": "SKILL"}
        new_key = cache.generate_cache_key(new_skill, "SKILL", 0.30)
        await cache.set(new_key, sample_cache_data)

        # Check which items remain
        assert await cache.get(keys[0]) is not None  # Most recent, should remain
        assert await cache.get(keys[1]) is None      # Should be evicted
        assert await cache.get(keys[2]) is not None  # Second most recent, should remain
        assert await cache.get(new_key) is not None  # New item, should remain

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, cache, sample_skill_query, sample_cache_data):
        """Test cache statistics tracking"""
        cache_key = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)

        # Initial stats
        stats = await cache.get_stats()
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0

        # Cache miss
        await cache.get(cache_key)
        stats = await cache.get_stats()
        assert stats.total_requests == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 0.0

        # Cache set and hit
        await cache.set(cache_key, sample_cache_data)
        await cache.get(cache_key)
        stats = await cache.get_stats()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 50.0

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, sample_cache_data):
        """Test manual cleanup of expired items"""
        cache = DynamicCourseCache(max_size=10, ttl_minutes=0.01)  # Very short TTL

        # Add multiple items
        keys = []
        for i in range(3):
            skill_query = {"skill_name": f"Skill{i}", "description": "test", "skill_category": "SKILL"}
            key = cache.generate_cache_key(skill_query, "SKILL", 0.30)
            keys.append(key)
            await cache.set(key, sample_cache_data)

        # Wait for expiration
        await asyncio.sleep(1)

        # Run cleanup
        expired_count = await cache.cleanup_expired()
        assert expired_count == 3

        # Check that items are gone
        for key in keys:
            assert await cache.get(key) is None

    @pytest.mark.asyncio
    async def test_clear_cache(self, cache, sample_skill_query, sample_cache_data):
        """Test cache clearing functionality"""
        cache_key = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)

        # Add item
        await cache.set(cache_key, sample_cache_data)
        assert await cache.get(cache_key) is not None

        # Clear cache
        await cache.clear()

        # Check that item is gone
        assert await cache.get(cache_key) is None

        # Check stats reflect empty cache
        stats = await cache.get_stats()
        assert stats.active_items == 0

    @pytest.mark.asyncio
    async def test_top_items(self, cache, sample_cache_data):
        """Test top items functionality"""
        # Add items with different access patterns
        keys = []
        for i in range(3):
            skill_query = {"skill_name": f"Skill{i}", "description": "test", "skill_category": "SKILL"}
            key = cache.generate_cache_key(skill_query, "SKILL", 0.30)
            keys.append(key)
            await cache.set(key, sample_cache_data)

        # Access keys different numbers of times
        await cache.get(keys[0])  # 1 access
        await cache.get(keys[1])  # 1 access
        await cache.get(keys[1])  # 2 accesses total
        await cache.get(keys[2])  # 1 access
        await cache.get(keys[2])  # 2 accesses
        await cache.get(keys[2])  # 3 accesses total

        # Get top items
        top_items = await cache.get_top_items(3)
        assert len(top_items) == 3
        assert top_items[0]["access_count"] == 3  # keys[2]
        assert top_items[1]["access_count"] == 2  # keys[1]
        assert top_items[2]["access_count"] == 1  # keys[0]

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache, sample_cache_data):
        """Test thread safety with concurrent access"""
        cache_key = "test_key"

        async def set_and_get():
            await cache.set(cache_key, sample_cache_data)
            return await cache.get(cache_key)

        # Run multiple concurrent operations
        tasks = [set_and_get() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_memory_estimation(self, cache, sample_cache_data):
        """Test memory usage estimation"""
        # Initial memory should be minimal
        stats = await cache.get_stats()
        initial_memory = stats.memory_usage_mb
        assert initial_memory == 0.0

        # Add items and check memory increases
        for i in range(5):
            skill_query = {"skill_name": f"Skill{i}", "description": "test" * 100, "skill_category": "SKILL"}
            key = cache.generate_cache_key(skill_query, "SKILL", 0.30)
            await cache.set(key, {**sample_cache_data, "extra_data": "x" * 1000})

        stats = await cache.get_stats()
        assert stats.memory_usage_mb > initial_memory

    @pytest.mark.asyncio
    @patch('src.services.dynamic_course_cache.monitoring_service')
    async def test_monitoring_integration(self, mock_monitoring, cache, sample_skill_query, sample_cache_data):
        """Test monitoring service integration"""
        cache_key = cache.generate_cache_key(sample_skill_query, "SKILL", 0.30)

        # Perform cache operations
        await cache.get(cache_key)  # Miss
        await cache.set(cache_key, sample_cache_data)
        await cache.get(cache_key)  # Hit

        # Check that monitoring events were sent
        assert mock_monitoring.track_event.call_count >= 2

        # Check event types
        call_args_list = mock_monitoring.track_event.call_args_list
        event_types = [call[0][0] for call in call_args_list]
        assert "DynamicCacheOperation" in event_types

    def test_cache_item_dataclass(self):
        """Test CacheItem dataclass functionality"""
        data = {"test": "value"}
        item = CacheItem(data=data, timestamp=datetime.now())

        assert item.data == data
        assert isinstance(item.timestamp, datetime)
        assert item.access_count == 0
        assert isinstance(item.last_access, datetime)

    def test_cache_stats_dataclass(self):
        """Test CacheStats dataclass functionality"""
        stats = CacheStats()

        # Check default values
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.hit_rate == 0.0
        assert stats.avg_retrieval_time_ms == 0.0
        assert stats.memory_usage_mb == 0.0
        assert stats.active_items == 0
        assert stats.expired_items_cleaned == 0

    @pytest.mark.asyncio
    async def test_edge_cases(self, cache):
        """Test edge cases and error conditions"""
        # Test empty skill query
        empty_query = {"skill_name": "", "description": "", "skill_category": "SKILL"}
        key = cache.generate_cache_key(empty_query, "SKILL", 0.30)
        assert len(key) == 16

        # Test get with non-existent key
        result = await cache.get("non_existent_key")
        assert result is None

        # Test set with empty data
        await cache.set("empty_key", {})
        result = await cache.get("empty_key")
        assert result == {}

        # Test top items with empty cache
        top_items = await cache.get_top_items(10)
        assert top_items == []

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test global cache instance singleton pattern"""
        from src.services.dynamic_course_cache import get_course_cache

        cache1 = get_course_cache()
        cache2 = get_course_cache()

        # Should be the same instance
        assert cache1 is cache2
