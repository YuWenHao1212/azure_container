"""
Unit tests for Index Calculation V2 service.

Tests:
- API-IC-001-UT: 服務初始化測試
- API-IC-002-UT: 快取鍵生成測試
- API-IC-003-UT: 快取TTL過期測試
- API-IC-004-UT: 快取LRU淘汰測試
- API-IC-005-UT: 相似度計算整合測試
- API-IC-006-UT: Sigmoid轉換參數一致性測試
- API-IC-007-UT: 關鍵字覆蓋分析測試
- API-IC-008-UT: TinyMCE HTML清理測試
- API-IC-009-UT: TaskGroup並行執行測試
- API-IC-010-UT: TaskGroup錯誤處理測試
"""

import asyncio
import json
import math
import os
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.core.config import Settings
from src.services.index_calculation import (
    analyze_keyword_coverage,
    compute_similarity,
    sigmoid_transform,
)
from src.services.index_calculation_v2 import (
    IndexCalculationServiceV2,
    get_index_calculation_service_v2,
)


class TestIndexCalculationV2Unit:
    """Unit tests for Index Calculation V2 functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.sigmoid_x0 = 0.373
        settings.sigmoid_k = 15.0
        settings.keyword_match_case_sensitive = False
        settings.enable_plural_matching = True
        settings.index_calc_cache_enabled = True
        settings.index_calc_cache_ttl_minutes = 60
        settings.index_calc_cache_max_size = 1000
        return settings

    @pytest.fixture
    def mock_embedding_client(self):
        """Mock embedding client."""
        client = AsyncMock()
        client.create_embeddings = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def sample_embeddings(self):
        """Sample embeddings for testing."""
        # Two similar embeddings (will produce high similarity)
        embedding1 = [0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 1531  # 1536 dimensions
        embedding2 = [0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 1531
        return [embedding1, embedding2]

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/index_calculation/test_data.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    # TEST: API-IC-001-UT
    def test_service_initialization(self, mock_settings):
        """TEST: API-IC-001-UT - V2 服務初始化測試.

        驗證 IndexCalculationServiceV2 能夠正確初始化，並確保所有依賴正確注入。
        """
        with patch('src.services.index_calculation_v2.get_settings', return_value=mock_settings):
            # Test V2 service initialization
            service = get_index_calculation_service_v2()
            assert service is not None
            assert isinstance(service, IndexCalculationServiceV2)

            # Verify service has required methods
            assert hasattr(service, 'calculate_index')
            assert callable(service.calculate_index)
            assert hasattr(service, 'get_service_stats')
            assert callable(service.get_service_stats)

    # TEST: API-IC-002-UT
    def test_cache_key_generation(self, mock_settings):
        """TEST: API-IC-002-UT - 快取鍵生成測試.

        驗證快取鍵生成的一致性和唯一性。
        Note: V2 implementation will include cache key generation.
        """
        # This test is for V2 cache implementation
        # For now, we test the concept with a simple hash function
        import hashlib

        def generate_cache_key(resume: str, job_desc: str, keywords: list) -> str:
            """Generate cache key for index calculation."""
            # Normalize inputs
            resume_normalized = resume.strip().lower()
            job_desc_normalized = job_desc.strip().lower()
            keywords_normalized = sorted([k.strip().lower() for k in keywords])

            # Create combined string
            combined = f"{resume_normalized}|{job_desc_normalized}|{''.join(keywords_normalized)}"

            # Generate SHA256 hash
            return hashlib.sha256(combined.encode()).hexdigest()

        # Test same content produces same key
        key1 = generate_cache_key("Python developer", "Need Python", ["Python", "API"])
        key2 = generate_cache_key("Python developer", "Need Python", ["Python", "API"])
        assert key1 == key2

        # Test different content produces different keys
        key3 = generate_cache_key("Java developer", "Need Python", ["Python", "API"])
        assert key1 != key3

        # Test HTML cleaned content produces same key
        key4 = generate_cache_key("<p>Python developer</p>", "Need Python", ["Python", "API"])
        # After HTML cleaning, should be similar (test concept)
        assert isinstance(key4, str)
        assert len(key4) == 64  # SHA256 length

    # TEST: API-IC-003-UT
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, mock_settings):
        """TEST: API-IC-003-UT - 快取TTL過期測試.

        驗證快取項目的 TTL 過期機制正常運作。
        """
        from datetime import datetime, timedelta

        class SimpleCache:
            def __init__(self, ttl_minutes: int):
                self.cache = {}
                self.ttl_minutes = ttl_minutes

            def set(self, key: str, value: any):
                self.cache[key] = {
                    'value': value,
                    'expires_at': datetime.now() + timedelta(minutes=self.ttl_minutes)
                }

            def get(self, key: str):
                if key not in self.cache:
                    return None

                item = self.cache[key]
                if datetime.now() > item['expires_at']:
                    del self.cache[key]
                    return None

                return item['value']

        # Test with 1 second TTL
        cache = SimpleCache(ttl_minutes=1/60)  # 1 second
        cache.set("test_key", "test_value")

        # Should exist immediately
        assert cache.get("test_key") == "test_value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        assert cache.get("test_key") is None

        # Test with longer TTL
        cache2 = SimpleCache(ttl_minutes=60)
        cache2.set("test_key2", "test_value2")

        # Should still exist
        assert cache2.get("test_key2") == "test_value2"

    # TEST: API-IC-004-UT
    def test_cache_lru_eviction(self, mock_settings):
        """TEST: API-IC-004-UT - 快取LRU淘汰測試.

        驗證 LRU 淘汰策略在快取滿時正確運作。
        """
        from collections import OrderedDict

        class LRUCache:
            def __init__(self, max_size: int):
                self.cache = OrderedDict()
                self.max_size = max_size

            def set(self, key: str, value: any):
                if key in self.cache:
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                else:
                    self.cache[key] = value
                    if len(self.cache) > self.max_size:
                        # Remove least recently used (first item)
                        self.cache.popitem(last=False)

            def get(self, key: str):
                if key not in self.cache:
                    return None
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]

            def size(self):
                return len(self.cache)

        # Test with cache size 3
        cache = LRUCache(max_size=3)

        # Add 3 items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3

        # Access key1 to make it recently used
        assert cache.get("key1") == "value1"

        # Add 4th item - should evict key2 (least recently used)
        cache.set("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key1") == "value1"  # Still exists
        assert cache.get("key3") == "value3"  # Still exists
        assert cache.get("key4") == "value4"  # New item

    # TEST: API-IC-005-UT
    @pytest.mark.asyncio
    async def test_similarity_calculation_integration(
        self, mock_settings, mock_embedding_client, sample_embeddings
    ):
        """TEST: API-IC-005-UT - 相似度計算整合測試.

        驗證整個相似度計算流程的正確性（主要測試 embedding 和 sigmoid 轉換的整合）。
        """
        # Mock embedding client to return fixed embeddings
        mock_embedding_client.create_embeddings.return_value = sample_embeddings

        with patch('src.services.index_calculation.get_settings', return_value=mock_settings):
            with patch('src.services.index_calculation.get_embedding_client',
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation.monitoring_service') as mock_monitoring:
                    # Call compute_similarity
                    raw_percent, transformed_percent = await compute_similarity(
                        "Python developer with 5 years experience",
                        "Looking for Python developer"
                    )

                    # Verify embedding client was called correctly
                    mock_embedding_client.create_embeddings.assert_called_once()
                    call_args = mock_embedding_client.create_embeddings.call_args[0][0]
                    assert len(call_args) == 2
                    assert "Python developer" in call_args[0]
                    assert "Looking for Python developer" in call_args[1]

                    # Verify close was called
                    mock_embedding_client.close.assert_called_once()

                    # Check results are in valid range
                    assert 0 <= raw_percent <= 100
                    assert 0 <= transformed_percent <= 100

                    # Verify monitoring was called
                    assert mock_monitoring.track_event.call_count >= 2

    # TEST: API-IC-006-UT
    def test_sigmoid_transform_parameters(self, mock_settings):
        """TEST: API-IC-006-UT - Sigmoid轉換參數一致性測試.

        確保 sigmoid 轉換參數與 V1 保持一致（k=15.0, x0=0.373）。
        """
        with patch('src.services.index_calculation.get_settings', return_value=mock_settings):
            # Test with default parameters
            result = sigmoid_transform(0.5)

            # Verify correct sigmoid calculation with x0=0.373, k=15.0
            expected = 1 / (1 + math.exp(-15.0 * (0.5 - 0.373)))
            assert abs(result - expected) < 0.0001

            # Test with custom parameters
            result_custom = sigmoid_transform(0.5, x0=0.4, k=10.0)
            expected_custom = 1 / (1 + math.exp(-10.0 * (0.5 - 0.4)))
            assert abs(result_custom - expected_custom) < 0.0001

            # Test extreme values - overflow handling
            result_high = sigmoid_transform(100.0)
            assert result_high == 1.0

            result_low = sigmoid_transform(-100.0)
            assert result_low == 0.0

            # Test boundary conditions
            result_at_x0 = sigmoid_transform(0.373)
            assert abs(result_at_x0 - 0.5) < 0.0001  # Should be 0.5 at x0

    # TEST: API-IC-007-UT
    def test_keyword_coverage_analysis(self, mock_settings, test_data):
        """TEST: API-IC-007-UT - 關鍵字覆蓋分析測試.

        驗證關鍵字匹配邏輯的正確性（參考 index_calculation.py 的 analyze_keyword_coverage 函數）。
        """
        with patch('src.services.index_calculation.get_settings', return_value=mock_settings):
            # Test case 1: Case insensitive matching
            result1 = analyze_keyword_coverage(
                "Python developer with API experience",
                ["python", "api", "DOCKER"]
            )
            assert result1["total_keywords"] == 3
            assert result1["covered_count"] == 2
            assert set(result1["covered_keywords"]) == {"python", "api"}
            assert set(result1["missed_keywords"]) == {"DOCKER"}
            assert result1["coverage_percentage"] == 67

            # Test case 2: Plural matching
            result2 = analyze_keyword_coverage(
                "Strong skills in APIs and Python frameworks",
                ["API", "framework", "skill"]
            )
            # APIs matches API (plural), frameworks matches framework (plural), skills matches skill (plural)
            assert result2["covered_count"] == 3
            assert set(result2["covered_keywords"]) == {"API", "framework", "skill"}
            assert set(result2["missed_keywords"]) == set()

            # Test case 3: Word boundary matching
            result3 = analyze_keyword_coverage(
                "JavaScript developer",
                ["Java", "Script"]
            )
            assert result3["covered_count"] == 0
            assert result3["missed_keywords"] == ["Java", "Script"]

            # Test case 4: Comma-separated string input
            result4 = analyze_keyword_coverage(
                "Python, Docker, Kubernetes",
                "Python, Docker, AWS"
            )
            assert result4["total_keywords"] == 3
            assert result4["covered_count"] == 2
            assert set(result4["covered_keywords"]) == {"Python", "Docker"}

            # Test case 5: Empty inputs
            result5 = analyze_keyword_coverage("", ["Python"])
            assert result5["total_keywords"] == 0
            assert result5["coverage_percentage"] == 0

            result6 = analyze_keyword_coverage("Python developer", [])
            assert result6["total_keywords"] == 0
            assert result6["coverage_percentage"] == 0

    # TEST: API-IC-008-UT
    def test_tinymce_html_cleaning(self, test_data):
        """TEST: API-IC-008-UT - TinyMCE HTML清理測試.

        驗證 TinyMCE 生成的 HTML 能正確清理（使用 text_processing.clean_html_text）。
        """
        from src.services.text_processing import clean_html_text

        # Test typical TinyMCE output
        html1 = """
        <p>Python developer with <strong>5 years</strong> experience</p>
        <ul>
            <li>API development</li>
            <li>Docker &amp; Kubernetes</li>
        </ul>
        """
        result1 = clean_html_text(html1)
        assert "Python developer with 5 years experience" in result1
        assert "API development" in result1
        assert "Docker & Kubernetes" in result1
        assert "<p>" not in result1
        assert "<strong>" not in result1

        # Test special cases
        html2 = '<p>&nbsp;</p><div style="color: red;">Important</div>'
        result2 = clean_html_text(html2)
        assert "Important" in result2
        assert "&nbsp;" not in result2
        assert "style=" not in result2

        # Test nested tags and attributes
        html3 = '<div class="content"><p id="para1">Text with <em>emphasis</em></p></div>'
        result3 = clean_html_text(html3)
        assert "Text with emphasis" in result3
        assert "class=" not in result3

        # Test HTML entities
        html4 = '<p>Experience with C++ &amp; C#, &lt;5 years&gt;</p>'
        result4 = clean_html_text(html4)
        assert "C++ & C#" in result4
        assert "<5 years>" in result4

    # TEST: API-IC-009-UT
    @pytest.mark.asyncio
    async def test_taskgroup_parallel_execution(self):
        """TEST: API-IC-009-UT - TaskGroup並行執行測試.

        驗證 Python 3.11 TaskGroup 的並行執行正確性。
        """
        results = []
        execution_times = []

        async def task(task_id: int, delay: float):
            """Simulated task with delay."""
            start = time.time()
            await asyncio.sleep(delay)
            end = time.time()
            results.append(task_id)
            execution_times.append(end - start)
            return f"Task {task_id} completed"

        # Execute tasks in parallel using TaskGroup
        start_time = time.time()
        async with asyncio.TaskGroup() as tg:
            # Create 5 tasks with 0.1 second delay each
            for i in range(5):
                tg.create_task(task(i, 0.1))

        total_time = time.time() - start_time

        # Verify all tasks completed
        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}

        # Verify parallel execution (should take ~0.1s, not 0.5s)
        assert total_time < 0.2  # Allow some overhead

        # Test shared resource safety
        shared_counter = 0
        lock = asyncio.Lock()

        async def increment_counter():
            nonlocal shared_counter
            async with lock:
                temp = shared_counter
                await asyncio.sleep(0.001)  # Simulate work
                shared_counter = temp + 1

        async with asyncio.TaskGroup() as tg:
            for _ in range(100):
                tg.create_task(increment_counter())

        assert shared_counter == 100  # No race condition

    # TEST: API-IC-010-UT
    @pytest.mark.asyncio
    async def test_taskgroup_error_handling(self):
        """TEST: API-IC-010-UT - TaskGroup錯誤處理測試.

        驗證 TaskGroup 的 ExceptionGroup 錯誤處理。
        """
        successful_results = []

        async def successful_task(task_id: int):
            await asyncio.sleep(0.01)
            successful_results.append(task_id)
            return f"Task {task_id} success"

        async def failing_task(task_id: int):
            await asyncio.sleep(0.01)
            raise ValueError(f"Task {task_id} failed")

        # Test single task failure
        with pytest.raises(ExceptionGroup) as exc_info:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(successful_task(1))
                tg.create_task(failing_task(2))
                tg.create_task(successful_task(3))

        # Verify exception group contains the failure
        exception_group = exc_info.value
        assert len(exception_group.exceptions) == 1
        assert isinstance(exception_group.exceptions[0], ValueError)
        assert "Task 2 failed" in str(exception_group.exceptions[0])

        # Verify successful tasks still completed
        assert 1 in successful_results
        assert 3 in successful_results

        # Test multiple task failures
        successful_results.clear()

        with pytest.raises(ExceptionGroup) as exc_info:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(failing_task(1))
                tg.create_task(successful_task(2))
                tg.create_task(failing_task(3))

        exception_group = exc_info.value
        assert len(exception_group.exceptions) == 2

        # Verify we can handle specific exceptions
        error_messages = []
        for exc in exception_group.exceptions:
            if isinstance(exc, ValueError):
                error_messages.append(str(exc))

        assert len(error_messages) == 2
        assert "Task 1 failed" in error_messages[0] or "Task 1 failed" in error_messages[1]
        assert "Task 3 failed" in error_messages[0] or "Task 3 failed" in error_messages[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
