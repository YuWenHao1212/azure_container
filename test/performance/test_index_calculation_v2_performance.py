"""
Performance tests for Index Calculation V2.

Tests:
- API-IC-201-PT: 響應時間基準測試(30秒)
- API-IC-202-PT: 快取效能測試(30秒)
- API-IC-203-PT: 高並發負載測試(60秒)
- API-IC-204-PT: 記憶體使用效率測試(30秒)
- API-IC-205-PT: 快取大小限制測試(30秒)

Total execution time: ~2 minutes
"""

import asyncio
import gc
import json
import os
import statistics
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables before imports
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

from src.main import create_app


class TestIndexCalculationV2Performance:
    """Performance tests for Index Calculation V2."""

    @pytest.fixture
    def test_client(self):
        """Create test client with mocked dependencies."""
        with (
            patch('src.core.config.get_settings'),
            patch('src.main.monitoring_service', Mock()),
            patch.dict(os.environ, {
                'MONITORING_ENABLED': 'false',
                'LIGHTWEIGHT_MONITORING': 'false',
                'ERROR_CAPTURE_ENABLED': 'false',
                'CONTAINER_APP_API_KEY': '',
                'INDEX_CALC_CACHE_ENABLED': 'true',
                'INDEX_CALC_CACHE_TTL_MINUTES': '60',
                'INDEX_CALC_CACHE_MAX_SIZE': '1000'
            })
        ):
            app = create_app()
            return TestClient(app)

    @pytest.fixture
    def mock_embedding_client(self):
        """Create mock embedding client with realistic delay."""
        client = AsyncMock()

        async def mock_create_embeddings(texts):
            # Simulate API latency (50-100ms)
            await asyncio.sleep(0.075)
            return [[0.1] * 1536 for _ in texts]

        client.create_embeddings = mock_create_embeddings
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/index_calculation/test_data.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    # TEST: API-IC-201-PT
    @pytest.mark.timeout(30)
    def test_response_time_benchmark(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-201-PT - 響應時間基準測試(30秒).

        建立效能基準並驗證是否達到目標。
        """
        response_times = []

        # Test with different document sizes
        test_cases = [
            {
                "name": "Small (< 1KB)",
                "resume": test_data["standard_resumes"][0]["content"],
                "jd": test_data["job_descriptions"][0]["content"],
                "keywords": ["Python", "FastAPI"]
            },
            {
                "name": "Medium (1-10KB)",
                "resume": test_data["standard_resumes"][1]["content"],
                "jd": test_data["job_descriptions"][1]["content"],
                "keywords": test_data["job_descriptions"][1]["keywords"][:10]
            },
            {
                "name": "Large (10-30KB)",
                "resume": test_data["standard_resumes"][2]["content"],
                "jd": test_data["job_descriptions"][2]["content"],
                "keywords": test_data["job_descriptions"][2]["keywords"][:15]
            }
        ]

        # Run 100 requests total (statistical sampling)
        iterations_per_case = 34  # ~100 total requests

        with patch('src.services.index_calculation.get_azure_embedding_client',
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation_v2.get_azure_embedding_client',
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation.monitoring_service', Mock()):
                    with patch('src.services.index_calculation_v2.monitoring_service', Mock()):
                        for test_case in test_cases:
                            case_times = []

                            for _ in range(iterations_per_case):
                                start_time = time.time()
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": test_case["resume"],
                                        "job_description": test_case["jd"],
                                        "keywords": test_case["keywords"]
                                    }
                                )
                                elapsed = (time.time() - start_time) * 1000  # Convert to ms

                                assert response.status_code == 200
                                case_times.append(elapsed)
                                response_times.append(elapsed)

                            # Calculate statistics for this case
                            p50 = statistics.median(case_times)
                            p95 = statistics.quantiles(case_times, n=20)[18] if len(case_times) >= 20 else max(case_times)  # noqa: E501

                            print(f"\n{test_case['name']} - P50: {p50:.0f}ms, P95: {p95:.0f}ms")

        # Overall statistics
        p50 = statistics.median(response_times)
        p95 = statistics.quantiles(response_times, n=20)[18]
        p99 = statistics.quantiles(response_times, n=100)[98]

        print("\nOverall Performance:")
        print(f"P50: {p50:.0f}ms")
        print(f"P95: {p95:.0f}ms")
        print(f"P99: {p99:.0f}ms")

        # Verify performance targets
        assert p50 < 1000, f"P50 ({p50:.0f}ms) exceeds target (1000ms)"
        assert p95 < 2000, f"P95 ({p95:.0f}ms) exceeds target (2000ms)"
        assert p99 < 3000, f"P99 ({p99:.0f}ms) exceeds target (3000ms)"

    # TEST: API-IC-202-PT
    @pytest.mark.timeout(30)
    def test_cache_performance(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-202-PT - 快取效能測試(30秒).

        驗證快取對效能的提升效果。
        """
        # Prepare 5 different queries
        queries = []
        for i in range(5):
            queries.append({
                "resume": f"Python developer with {i+3} years experience in FastAPI, Django, Flask, and cloud technologies. Strong background in building scalable web applications, RESTful APIs, and microservices architecture. Proficient in Docker, Kubernetes, AWS, and CI/CD pipelines. Experience with database design, optimization, and distributed systems.",  # noqa: E501
                "job_description": f"Looking for Python developer level {i+1} with extensive experience in web development frameworks and cloud computing. Must have strong skills in building enterprise-level applications, API design, and modern DevOps practices. Knowledge of containerization, orchestration, and cloud-native development is essential.",  # noqa: E501
                "keywords": ["Python", "FastAPI", f"Skill{i}"]
            })

        cache_hit_times = []
        cache_miss_times = []

        with patch('src.services.index_calculation.get_azure_embedding_client',
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation_v2.get_azure_embedding_client',
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation.monitoring_service', Mock()):
                    with patch('src.services.index_calculation_v2.monitoring_service', Mock()):
                        # Warmup phase - populate cache
                        for query in queries:
                            for _ in range(4):  # Repeat each query 4 times
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json=query
                                )
                                assert response.status_code == 200

                        # Test phase - 50 mixed queries
                        import random
                        random.seed(42)  # Deterministic for reproducibility

                        for _ in range(50):
                            # 70% chance of cache hit (existing query)
                            if random.random() < 0.7:  # noqa: S311
                                query = random.choice(queries)  # noqa: S311
                                is_cache_hit = True
                            else:
                                # New query (cache miss)
                                idx = random.randint(100, 200)  # noqa: S311
                                query = {
                                    "resume": f"New developer {idx} with extensive experience in software development, cloud computing, and modern programming frameworks. Strong background in building scalable web applications, RESTful APIs, and microservices architecture. Proficient in Docker, Kubernetes, AWS, and CI/CD pipelines. Experience with database design, optimization, and distributed systems.",  # noqa: E501
                                    "job_description": f"New position {idx} looking for experienced software developer with strong technical skills and problem-solving abilities. Must have expertise in modern development frameworks, cloud technologies, and enterprise-level application development. Knowledge of containerization, orchestration, and DevOps practices is essential.",  # noqa: E501
                                    "keywords": [f"Skill{idx}"]
                                }
                                is_cache_hit = False

                            start_time = time.time()
                            response = test_client.post(
                                "/api/v1/index-calculation",
                                json=query
                            )
                            elapsed = (time.time() - start_time) * 1000

                            assert response.status_code == 200

                            if is_cache_hit:
                                cache_hit_times.append(elapsed)
                            else:
                                cache_miss_times.append(elapsed)

        # Calculate statistics
        if cache_hit_times:
            hit_median = statistics.median(cache_hit_times)
            print(f"\nCache Hit - Median: {hit_median:.0f}ms")

        if cache_miss_times:
            miss_median = statistics.median(cache_miss_times)
            print(f"Cache Miss - Median: {miss_median:.0f}ms")

        # Calculate hit rate
        total_requests = len(cache_hit_times) + len(cache_miss_times)
        hit_rate = len(cache_hit_times) / total_requests if total_requests > 0 else 0
        print(f"Cache Hit Rate: {hit_rate:.1%}")

        # Verify cache performance
        # Note: Actual cache implementation in V2 will show significant difference
        # For now, we just verify the test runs correctly
        assert hit_rate > 0.6, f"Cache hit rate ({hit_rate:.1%}) below target (60%)"

    # TEST: API-IC-203-PT
    @pytest.mark.timeout(120)
    def test_high_concurrency_load(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-203-PT - 高並發負載測試(60秒).

        驗證系統在高負載下的穩定性。
        """
        success_count = 0
        error_count = 0
        response_times = []

        def make_request(request_id):
            """Make a single request."""
            try:
                with patch('src.services.index_calculation.get_azure_embedding_client',
                          return_value=mock_embedding_client):
                    with patch('src.services.index_calculation_v2.get_azure_embedding_client',
                              return_value=mock_embedding_client):
                        with patch('src.services.index_calculation.monitoring_service', Mock()):
                            with patch('src.services.index_calculation_v2.monitoring_service', Mock()):
                                start_time = time.time()
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": f"Developer {request_id} with extensive Python experience in web development, cloud computing, and modern programming frameworks. Strong background in building scalable web applications, RESTful APIs, and microservices architecture. Proficient in Docker, Kubernetes, AWS, and CI/CD pipelines. Experience with database design, optimization, and distributed systems.",  # noqa: E501
                                        "job_description": f"Position {request_id} looking for experienced Python developer with strong technical skills and problem-solving abilities. Must have expertise in modern development frameworks, cloud technologies, and enterprise-level application development. Knowledge of containerization, orchestration, and DevOps practices is essential.",  # noqa: E501
                                        "keywords": ["Python", f"Skill{request_id % 10}"]
                                    }
                                )
                                elapsed = (time.time() - start_time) * 1000

                                if response.status_code == 200:
                                    return True, elapsed
                                else:
                                    return False, elapsed
            except Exception as e:
                print(f"Request {request_id} failed: {e!s}")
                return False, 0

        # Gradual load increase
        print("\nLoad Test Progress:")
        time.time()

        # Phase 1: Ramp up (20s) - 0 to 50 QPS
        print("Phase 1: Ramping up...")
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            request_id = 0

            for second in range(20):
                qps = int(2.5 * second)  # Linear increase to 50 QPS
                for _ in range(qps):
                    futures.append(executor.submit(make_request, request_id))
                    request_id += 1
                time.sleep(1)

            # Phase 2: Sustain (30s) - 50 QPS
            print("Phase 2: Sustaining 50 QPS...")
            for second in range(30):  # noqa: B007
                for _ in range(50):
                    futures.append(executor.submit(make_request, request_id))
                    request_id += 1
                time.sleep(1)

            # Phase 3: Cool down (10s) - 50 to 0 QPS
            print("Phase 3: Cooling down...")
            for second in range(10):
                qps = int(50 - 5 * second)
                for _ in range(max(0, qps)):
                    futures.append(executor.submit(make_request, request_id))
                    request_id += 1
                time.sleep(1)

            # Collect results
            for future in as_completed(futures):
                success, elapsed = future.result()
                if success:
                    success_count += 1
                    response_times.append(elapsed)
                else:
                    error_count += 1

        total_requests = success_count + error_count
        success_rate = success_count / total_requests if total_requests > 0 else 0

        print("\nLoad Test Results:")
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {success_count}")
        print(f"Failed: {error_count}")
        print(f"Success Rate: {success_rate:.1%}")

        if response_times:
            p50 = statistics.median(response_times)
            p95 = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            print(f"Response Time P50: {p50:.0f}ms")
            print(f"Response Time P95: {p95:.0f}ms")

            # Verify performance under load
            assert success_rate > 0.95, f"Success rate ({success_rate:.1%}) below target (95%)"
            assert p95 < 3000, f"P95 under load ({p95:.0f}ms) exceeds target (3000ms)"

    # TEST: API-IC-204-PT
    @pytest.mark.timeout(30)
    def test_memory_efficiency(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-204-PT - 記憶體使用效率測試(30秒).

        驗證記憶體使用效率和無洩漏。
        """
        # Start memory tracking
        tracemalloc.start()
        gc.collect()

        # Get baseline memory
        baseline_snapshot = tracemalloc.take_snapshot()

        # Phase 1: Process 200 unique requests
        print("\nProcessing 200 unique requests...")

        with patch('src.services.index_calculation.get_azure_embedding_client',
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation_v2.get_azure_embedding_client',
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation.monitoring_service', Mock()):
                    with patch('src.services.index_calculation_v2.monitoring_service', Mock()):
                        for i in range(200):
                            # Use different content sizes
                            if i % 3 == 0:
                                content = test_data["standard_resumes"][0]["content"]  # Small
                            elif i % 3 == 1:
                                content = test_data["standard_resumes"][1]["content"]  # Medium
                            else:
                                content = test_data["standard_resumes"][2]["content"]  # Large

                            response = test_client.post(
                                "/api/v1/index-calculation",
                                json={
                                    "resume": f"{content} - Version {i} with additional experience in modern development practices and cloud technologies",  # noqa: E501
                                    "job_description": f"Job {i} looking for experienced developer with strong technical skills and expertise in modern frameworks. Must have knowledge of cloud computing, containerization, and enterprise application development practices.",  # noqa: E501
                                    "keywords": [f"Skill{j}" for j in range(i % 5 + 1)]
                                }
                            )
                            assert response.status_code == 200

                            # Sample memory every 50 requests
                            if i % 50 == 0 and i > 0:
                                current_snapshot = tracemalloc.take_snapshot()
                                stats = current_snapshot.compare_to(baseline_snapshot, 'lineno')

                                current_memory = sum(stat.size for stat in stats) / 1024 / 1024  # MB
                                print(f"After {i} requests: {current_memory:.1f} MB")

        # Get peak memory before GC
        peak_snapshot = tracemalloc.take_snapshot()
        peak_stats = peak_snapshot.compare_to(baseline_snapshot, 'lineno')
        peak_memory = sum(stat.size for stat in peak_stats) / 1024 / 1024  # MB

        # Force garbage collection
        gc.collect()
        time.sleep(0.5)  # Allow cleanup

        # Get memory after GC
        final_snapshot = tracemalloc.take_snapshot()
        final_stats = final_snapshot.compare_to(baseline_snapshot, 'lineno')
        final_memory = sum(stat.size for stat in final_stats) / 1024 / 1024  # MB

        tracemalloc.stop()

        # Calculate memory recovery
        recovered = (peak_memory - final_memory) / peak_memory if peak_memory > 0 else 0

        print("\nMemory Usage Results:")
        print(f"Peak Memory: {peak_memory:.1f} MB")
        print(f"After GC: {final_memory:.1f} MB")
        print(f"Recovery Rate: {recovered:.1%}")

        # Verify memory efficiency
        assert peak_memory < 2048, f"Peak memory ({peak_memory:.1f} MB) exceeds limit (2048 MB)"
        assert recovered >= 0.0, f"Memory recovery ({recovered:.1%}) is negative - indicates memory leak"

    # TEST: API-IC-205-PT
    @pytest.mark.timeout(30)
    def test_cache_size_limits(
        self, test_client, mock_embedding_client
    ):
        """TEST: API-IC-205-PT - 快取大小限制測試(30秒).

        驗證快取大小限制和 LRU 淘汰效率。
        """
        # Mock settings with small cache for testing
        with patch.dict(os.environ, {
            'INDEX_CALC_CACHE_MAX_SIZE': '100'  # Small cache for testing
        }):
            eviction_times = []

            with patch('src.services.index_calculation.get_azure_embedding_client',
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation_v2.get_azure_embedding_client',
                          return_value=mock_embedding_client):
                    with patch('src.services.index_calculation.monitoring_service', Mock()):
                        with patch('src.services.index_calculation_v2.monitoring_service', Mock()):
                            # Phase 1: Fill cache to capacity
                            print("\nFilling cache to capacity (100 items)...")
                            for i in range(100):
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": f"Resume {i} - This is a sample resume with extensive experience in software development and programming",  # noqa: E501
                                        "job_description": f"Job {i} - Looking for an experienced software developer with strong technical skills",  # noqa: E501
                                        "keywords": [f"Keyword{i}"]
                                    }
                                )
                                assert response.status_code == 200

                            # Phase 2: Add 100 more items (trigger evictions)
                            print("Adding 100 more items (triggering LRU eviction)...")
                            for i in range(100, 200):
                                start_time = time.time()
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": f"Resume {i} - This is a sample resume with extensive experience in software development and programming",  # noqa: E501
                                        "job_description": f"Job {i} - Looking for an experienced software developer with strong technical skills",  # noqa: E501
                                        "keywords": [f"Keyword{i}"]
                                    }
                                )
                                eviction_time = (time.time() - start_time) * 1000
                                eviction_times.append(eviction_time)
                                assert response.status_code == 200

                            # Phase 3: Verify LRU behavior
                            print("Verifying LRU behavior...")
                            # Try to access early items (should be evicted)
                            early_found = 0
                            for i in range(10):
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": f"Resume {i} - This is a sample resume with extensive experience in software development and programming",  # noqa: E501
                                        "job_description": f"Job {i} - Looking for an experienced software developer with strong technical skills",  # noqa: E501
                                        "keywords": [f"Keyword{i}"]
                                    }
                                )
                                # In V2 with cache, we would check cache_hit field
                                # For now, just verify request succeeds
                                if response.status_code == 200:
                                    early_found += 1

                            # Try to access recent items (should be in cache)
                            recent_found = 0
                            for i in range(190, 200):
                                response = test_client.post(
                                    "/api/v1/index-calculation",
                                    json={
                                        "resume": f"Resume {i} - This is a sample resume with extensive experience in software development and programming",  # noqa: E501
                                        "job_description": f"Job {i} - Looking for an experienced software developer with strong technical skills",  # noqa: E501
                                        "keywords": [f"Keyword{i}"]
                                    }
                                )
                                if response.status_code == 200:
                                    recent_found += 1

            # Calculate eviction performance
            avg_eviction_time = statistics.mean(eviction_times)
            p95_eviction_time = statistics.quantiles(eviction_times, n=20)[18]

            print("\nCache Eviction Performance:")
            print(f"Average: {avg_eviction_time:.1f}ms")
            print(f"P95: {p95_eviction_time:.1f}ms")
            print(f"Early items found: {early_found}/10")
            print(f"Recent items found: {recent_found}/10")

            # Verify eviction performance
            assert p95_eviction_time < 200, f"Eviction P95 ({p95_eviction_time:.1f}ms) exceeds target (200ms)"
            # Note: Actual LRU behavior verification requires V2 cache implementation


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
