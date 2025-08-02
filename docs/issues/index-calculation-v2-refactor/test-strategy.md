# Index Calculation V2 測試策略

## 0. 測試環境要求

### Python 版本
- **開發與測試環境**: Python 3.11.8（與專案一致）
- **CI/CD 環境**: 使用 `python:3.11.8-slim` Docker 映像
- **pytest 版本**: pytest >= 7.4.0（支援 Python 3.11 特性）

### Python 3.11 測試優勢
- 更好的錯誤訊息和堆疊追蹤
- 改進的 asyncio 測試支援
- 更快的測試執行速度

## 1. 測試目標與範圍

### 1.1 測試目標
- **覆蓋率**: 達到 80%+ 程式碼覆蓋率
- **可靠性**: 確保所有關鍵路徑 100% 測試
- **效能**: 驗證效能改善達到預期目標
- **相容性**: 確保向後相容性

### 1.2 測試範圍
| 測試類型 | 範圍 | 目標 |
|---------|------|------|
| 單元測試 | 服務類別、工具函數 | 90%+ 覆蓋率 |
| 整合測試 | API 端點、外部服務 | 關鍵流程覆蓋 |
| 效能測試 | 響應時間、並發處理 | 達到 SLA |
| 快取測試 | 快取邏輯、TTL | 100% 覆蓋 |

## 2. 單元測試策略

### 2.1 測試結構
```
tests/unit/
├── test_index_calculation_v2_service.py
├── test_cache_manager.py
├── test_parallel_processor.py
├── test_similarity_calculator.py
└── test_keyword_analyzer.py
```

### 2.2 核心服務測試

#### test_index_calculation_v2_service.py
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.services.index_calculation_v2 import IndexCalculationServiceV2

class TestIndexCalculationServiceV2:
    """Test cases for IndexCalculationServiceV2.
    
    測試 ID 對照：
    - test_calculate_index_with_cache_hit: IC-UNIT-002, IC-UNIT-003
    - test_calculate_index_with_cache_miss: IC-UNIT-005
    - test_cache_key_generation: IC-UNIT-002
    - test_cache_expiration: IC-UNIT-003
    """
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked dependencies."""
        mock_embedding_client = AsyncMock()
        return IndexCalculationServiceV2(
            embedding_client=mock_embedding_client,
            enable_cache=True,
            cache_ttl_minutes=60
        )
    
    @pytest.mark.asyncio
    async def test_calculate_index_with_cache_hit(self, service):
        """Test calculation with cache hit.
        
        Test ID: IC-UNIT-002, IC-UNIT-003
        Priority: P0
        """
        # Arrange
        request_data = {
            "resume": "Software Engineer with 5 years experience",
            "job_description": "Looking for senior developer",
            "keywords": ["Python", "FastAPI", "Azure"]
        }
        
        # Pre-populate cache
        cache_key = service._generate_cache_key(
            f"{request_data['resume']}:{request_data['job_description']}",
            "similarity"
        )
        service._cache[cache_key] = {
            "result": {"similarity_percentage": 85},
            "timestamp": datetime.utcnow()
        }
        
        # Act
        result = await service.calculate_index(**request_data)
        
        # Assert
        assert result["cache_hit"] is True
        assert service._cache_stats["hits"] == 1
        assert result["similarity_percentage"] == 85
    
    @pytest.mark.asyncio
    async def test_calculate_index_with_cache_miss(self, service):
        """Test calculation with cache miss.
        
        Test ID: IC-UNIT-005
        Priority: P0
        """
        # Arrange
        request_data = {
            "resume": "New resume content",
            "job_description": "New job description",
            "keywords": ["Docker", "Kubernetes"]
        }
        
        # Mock embedding generation
        service.embedding_client.create_embeddings.return_value = [
            [0.1, 0.2, 0.3],  # Resume embedding
            [0.2, 0.3, 0.4]   # Job description embedding
        ]
        
        # Act
        result = await service.calculate_index(**request_data)
        
        # Assert
        assert result["cache_hit"] is False
        assert service._cache_stats["misses"] == 1
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result
    
    def test_cache_key_generation(self, service):
        """Test cache key generation consistency.
        
        Test ID: IC-UNIT-002
        Priority: P0
        """
        text1 = "Test content with spaces  and   extra whitespace"
        text2 = "Test content with spaces and extra whitespace"
        
        key1 = service._generate_cache_key(text1, "embedding")
        key2 = service._generate_cache_key(text2, "embedding")
        
        # Keys should be same after normalization
        assert key1 == key2
        
    def test_cache_expiration(self, service):
        """Test cache TTL expiration.
        
        Test ID: IC-UNIT-003
        Priority: P1
        """
        cache_key = "test_key"
        
        # Add expired entry
        service._cache[cache_key] = {
            "result": {"test": "data"},
            "timestamp": datetime.utcnow() - timedelta(minutes=61)
        }
        
        # Should return None and remove entry
        result = service._get_cached_result(cache_key)
        
        assert result is None
        assert cache_key not in service._cache
        assert service._cache_stats["evictions"] == 1
```

### 2.3 快取管理測試

#### test_cache_manager.py
```python
class TestCacheManager:
    """Test cases for cache management functionality.
    
    測試 ID 對照：
    - test_lru_eviction: IC-UNIT-004
    - test_cache_statistics: IC-UNIT-001
    """
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full.
        
        Test ID: IC-UNIT-004
        Priority: P1
        """
        service = IndexCalculationServiceV2(
            enable_cache=True,
            cache_ttl_minutes=60
        )
        service._max_cache_size = 3  # Small size for testing
        
        # Fill cache
        for i in range(4):
            key = f"key_{i}"
            service._cache[key] = {
                "result": f"data_{i}",
                "timestamp": datetime.utcnow(),
                "last_accessed": datetime.utcnow()
            }
        
        # Verify oldest was evicted
        assert len(service._cache) == 3
        assert "key_0" not in service._cache
        assert "key_3" in service._cache
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        service = IndexCalculationServiceV2()
        
        # Simulate cache operations
        service._cache_stats["hits"] = 75
        service._cache_stats["misses"] = 25
        
        stats = service.get_service_stats()
        
        assert stats["cache_performance"]["hit_rate"] == 0.75
        assert stats["cache_performance"]["total_hits"] == 75
        assert stats["cache_performance"]["total_misses"] == 25
```

### 2.4 並行處理測試

#### test_parallel_processor.py
```python
class TestParallelProcessing:
    """Test parallel processing capabilities.
    
    測試 ID 對照：
    - test_parallel_execution: IC-UNIT-009
    - test_parallel_error_handling: IC-UNIT-010
    - test_python311_taskgroup: IC-UNIT-010
    """
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel vs sequential execution time."""
        service = IndexCalculationServiceV2(
            enable_parallel_processing=True
        )
        
        # Mock slow operations
        async def slow_embedding(text):
            await asyncio.sleep(0.1)
            return [0.1, 0.2, 0.3]
        
        service.embedding_client.create_embedding = slow_embedding
        
        # Measure parallel execution
        start = time.time()
        await service._calculate_parallel(
            "resume", "job_desc", ["keyword1", "keyword2"]
        )
        parallel_time = time.time() - start
        
        # Should complete in ~0.1s (parallel) not ~0.2s (sequential)
        assert parallel_time < 0.15
    
    @pytest.mark.asyncio
    async def test_parallel_error_handling(self):
        """Test error handling in parallel tasks."""
        service = IndexCalculationServiceV2(
            enable_parallel_processing=True
        )
        
        # One task fails
        service.embedding_client.create_embeddings.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await service._calculate_parallel(
                "resume", "job_desc", ["keyword"]
            )
        
        assert "API Error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_python311_taskgroup(self):
        """Test Python 3.11 TaskGroup error handling."""
        service = IndexCalculationServiceV2(
            enable_parallel_processing=True
        )
        
        # Test that TaskGroup properly handles exceptions
        async def failing_task():
            raise ValueError("Task failed")
        
        async def successful_task():
            await asyncio.sleep(0.01)
            return "Success"
        
        # TaskGroup should collect all exceptions
        with pytest.raises(ExceptionGroup) as exc_info:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(failing_task())
                tg.create_task(successful_task())
        
        # Verify Python 3.11 ExceptionGroup behavior
        assert len(exc_info.value.exceptions) == 1
        assert isinstance(exc_info.value.exceptions[0], ValueError)
```

## 3. 整合測試策略

### 3.1 API 端點測試

#### test_index_calculation_api.py
```python
from fastapi.testclient import TestClient
from unittest.mock import patch

class TestIndexCalculationAPI:
    """Integration tests for index calculation API."""
    
    def test_successful_calculation(self, client: TestClient):
        """Test successful index calculation."""
        request_data = {
            "resume": "Experienced Python developer...",
            "job_description": "Looking for Python expert...",
            "keywords": ["Python", "FastAPI", "Docker"]
        }
        
        response = client.post(
            "/api/v1/index-calculation",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "similarity_percentage" in data["data"]
        assert "keyword_coverage" in data["data"]
        assert "timing_breakdown" in data["data"]
    
    def test_cache_header_behavior(self, client: TestClient):
        """Test cache behavior through API."""
        request_data = {
            "resume": "Test resume",
            "job_description": "Test job",
            "keywords": ["test"]
        }
        
        # First request - cache miss
        response1 = client.post(
            "/api/v1/index-calculation",
            json=request_data
        )
        assert response1.json()["data"]["cache_hit"] is False
        
        # Second request - cache hit
        response2 = client.post(
            "/api/v1/index-calculation",
            json=request_data
        )
        assert response2.json()["data"]["cache_hit"] is True
        
        # Response time should be much faster
        time1 = response1.json()["data"]["processing_time_ms"]
        time2 = response2.json()["data"]["processing_time_ms"]
        assert time2 < time1 * 0.1  # 90% faster
```

### 3.2 錯誤場景測試
```python
def test_validation_errors(self, client: TestClient):
    """Test input validation errors."""
    # Empty resume
    response = client.post(
        "/api/v1/index-calculation",
        json={
            "resume": "",
            "job_description": "Valid job description",
            "keywords": ["Python"]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"

@patch('src.services.embedding_client.AzureEmbeddingClient')
def test_external_service_failure(self, mock_client, client: TestClient):
    """Test handling of external service failures."""
    mock_client.create_embeddings.side_effect = Exception("Azure API Error")
    
    response = client.post(
        "/api/v1/index-calculation",
        json={
            "resume": "Valid resume",
            "job_description": "Valid job",
            "keywords": ["Python"]
        }
    )
    
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
```

## 4. 效能測試策略

### 4.1 基準測試

#### benchmark_test.py
```python
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

class TestPerformanceBenchmark:
    """Performance benchmark tests."""
    
    @pytest.mark.benchmark
    async def test_response_time_baseline(self, service):
        """Establish response time baseline."""
        samples = []
        
        for _ in range(100):
            start = time.time()
            await service.calculate_index(
                resume="Standard test resume...",
                job_description="Standard test job...",
                keywords=["Python", "Docker", "AWS"]
            )
            samples.append((time.time() - start) * 1000)
        
        p50 = statistics.median(samples)
        p95 = statistics.quantiles(samples, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(samples, n=100)[98]  # 99th percentile
        
        # Assert performance targets
        assert p50 < 1000  # P50 < 1 second
        assert p95 < 2000  # P95 < 2 seconds
        assert p99 < 3000  # P99 < 3 seconds
        
        print(f"Performance: P50={p50:.0f}ms, P95={p95:.0f}ms, P99={p99:.0f}ms")
```

### 4.2 負載測試
```python
@pytest.mark.load
async def test_concurrent_load(self, client: TestClient):
    """Test system under concurrent load."""
    concurrent_requests = 50
    
    async def make_request():
        response = await client.post(
            "/api/v1/index-calculation",
            json={
                "resume": f"Resume {random.randint(1, 1000)}",
                "job_description": f"Job {random.randint(1, 1000)}",
                "keywords": ["Python", "Docker"]
            }
        )
        return response.status_code, response.json()
    
    # Run concurrent requests
    tasks = [make_request() for _ in range(concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    successful = sum(1 for r in results if not isinstance(r, Exception) and r[0] == 200)
    success_rate = successful / concurrent_requests
    
    assert success_rate > 0.95  # 95%+ success rate
    print(f"Load test: {successful}/{concurrent_requests} successful ({success_rate:.1%})")
```

## 5. 快取測試策略

### 5.1 快取正確性測試
```python
class TestCacheCorrectness:
    """Test cache correctness and consistency."""
    
    def test_cache_key_uniqueness(self):
        """Test that different inputs generate different keys."""
        service = IndexCalculationServiceV2()
        
        inputs = [
            ("Resume A", "Job A"),
            ("Resume B", "Job A"),
            ("Resume A", "Job B"),
            ("Resume A", "Job A"),  # Duplicate
        ]
        
        keys = []
        for resume, job in inputs:
            key = service._generate_cache_key(f"{resume}:{job}", "similarity")
            keys.append(key)
        
        # First 3 should be unique, 4th should match 1st
        assert len(set(keys[:3])) == 3
        assert keys[0] == keys[3]
    
    def test_cache_ttl_boundary(self):
        """Test cache behavior at TTL boundary."""
        service = IndexCalculationServiceV2(cache_ttl_minutes=1)
        
        # Add cache entry
        key = "test_key"
        service._cache[key] = {
            "result": {"data": "test"},
            "timestamp": datetime.utcnow() - timedelta(seconds=59)
        }
        
        # Should still be valid (59 seconds < 1 minute)
        assert service._get_cached_result(key) is not None
        
        # Update timestamp to 61 seconds ago
        service._cache[key]["timestamp"] = datetime.utcnow() - timedelta(seconds=61)
        
        # Should be expired
        assert service._get_cached_result(key) is None
```

## 6. 測試資料管理

### 6.1 測試資料集
```python
# tests/fixtures/test_data.py
TEST_RESUMES = {
    "senior_python": """
        Senior Software Engineer with 8+ years of experience in Python development.
        Expert in FastAPI, Django, and microservices architecture.
        Strong background in Azure cloud services and Docker containerization.
    """,
    "junior_frontend": """
        Junior Frontend Developer with 2 years of experience.
        Skilled in React, JavaScript, and responsive design.
        Familiar with Git and agile methodologies.
    """,
    "data_scientist": """
        Data Scientist with 5 years of experience in machine learning.
        Proficient in Python, TensorFlow, and statistical analysis.
        Experience with big data technologies and cloud platforms.
    """
}

TEST_JOB_DESCRIPTIONS = {
    "python_backend": """
        Looking for Senior Python Developer to join our backend team.
        Requirements: FastAPI, PostgreSQL, Docker, Azure experience.
        Nice to have: Kubernetes, GraphQL, Redis.
    """,
    "fullstack": """
        Full Stack Developer needed for web application development.
        Must have: React, Node.js, MongoDB, REST APIs.
        Bonus: TypeScript, AWS, CI/CD experience.
    """
}
```

## 7. 測試執行計劃

### 7.1 本地開發測試
```bash
# 執行單元測試
pytest tests/unit/test_index_calculation_v2_service.py -v

# 執行特定測試
pytest tests/unit/test_cache_manager.py::TestCacheManager::test_lru_eviction -v

# 執行覆蓋率測試
pytest tests/unit/ --cov=src.services.index_calculation_v2 --cov-report=html
```

### 7.2 CI/CD 測試流程
```yaml
# .github/workflows/test.yml
test-index-calculation:
  steps:
    - name: Run unit tests
      run: pytest tests/unit/test_index_calculation* -v
    
    - name: Run integration tests
      run: pytest tests/integration/test_index_calculation* -v
    
    - name: Check coverage
      run: pytest --cov=src.services.index_calculation_v2 --cov-fail-under=80
    
    - name: Run performance tests
      run: pytest tests/performance/test_index_calculation* -v -m benchmark
```

## 8. 測試報告

### 8.1 覆蓋率報告格式
```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/services/index_calculation_v2.py      245     12    95%
src/services/cache_manager.py              89      3    97%
src/services/parallel_processor.py         67      5    93%
-----------------------------------------------------------
TOTAL                                     401     20    95%
```

### 8.2 效能測試報告
```
Performance Test Results:
========================
Baseline (no cache):      P50=1250ms, P95=2100ms, P99=2800ms
With cache (hit):         P50=45ms,   P95=78ms,   P99=95ms
With cache (miss):        P50=980ms,  P95=1650ms, P99=2200ms
Parallel processing:      30% faster than sequential
Concurrent (50 QPS):      Success rate: 98.5%
```

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-02  
**測試負責人**: QA Team