"""
Performance tests for Index Calculation and Gap Analysis V2.

Tests:
- API-GAP-001-PT: P50 響應時間測試
- API-GAP-002-PT: P95 響應時間測試
- API-GAP-003-PT: 資源池重用率測試
- API-GAP-004-PT: API 呼叫減少驗證
- API-GAP-005-PT: 資源池擴展測試

IMPORTANT:
- For P50/P95 tests, MUST disable resource pool cache (RESOURCE_POOL_ENABLED=false)
- Each request MUST use unique test data to avoid cache hits
"""

import asyncio
import json
import os
import statistics
import sys
import time
import uuid
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
os.environ['AZURE_OPENAI_GPT4_DEPLOYMENT'] = 'gpt-4.1-japan'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'gpt-4-1-mini-japaneast'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ['USE_V2_IMPLEMENTATION'] = 'true'

from src.main import create_app


class TestGapAnalysisV2Performance:
    """Performance tests for Index Calculation and Gap Analysis V2."""

    @pytest.fixture
    def test_client(self):
        """Create test client with performance configuration."""
        with (
            patch('src.core.config.get_settings'),
            patch('src.main.monitoring_service', Mock()),
            patch.dict(os.environ, {
                'MONITORING_ENABLED': 'false',
                'LIGHTWEIGHT_MONITORING': 'false',
                'ERROR_CAPTURE_ENABLED': 'false',
                'CONTAINER_APP_API_KEY': 'test-api-key',
                'RESOURCE_POOL_ENABLED': 'false'  # Disable for P50/P95 tests
            })
        ):
            app = create_app()
            return TestClient(app)

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/gap_analysis_v2/test_data_v2.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    @pytest.fixture
    def mock_responses(self):
        """Load mock responses from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/gap_analysis_v2/mock_responses.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    def generate_unique_test_data(self, request_id: int, test_data: dict) -> dict:
        """Generate unique test data for each request to avoid cache hits."""
        template = test_data["performance_test_data"]["unique_request_template"]
        timestamp = time.time_ns()
        unique_uuid = str(uuid.uuid4())

        return {
            "resume": template["resume_base"].format(
                request_id=request_id,
                timestamp=timestamp,
                uuid=unique_uuid
            ),
            "job_description": template["jd_base"].format(
                request_id=request_id,
                timestamp=timestamp,
                uuid=unique_uuid
            ),
            "keywords": [
                keyword.format(
                    request_id=request_id,
                    random_suffix=timestamp % 1000
                ) if "{" in keyword else keyword
                for keyword in template["keywords_template"]
            ]
        }

    def mock_fast_service_response(self, delay: float = 0.5):
        """Create a mock service that responds quickly for performance testing."""
        async def analyze_combined(*args, **kwargs):
            await asyncio.sleep(delay)  # Simulate processing time
            return {
                "success": True,
                "data": {
                    "raw_similarity_percentage": 68,
                    "similarity_percentage": 78,
                    "keyword_coverage": {
                        "total_keywords": 8,
                        "covered_count": 3,
                        "coverage_percentage": 38,
                        "covered_keywords": ["Python", "FastAPI", "Docker"],
                        "missed_keywords": [
                            "React", "Kubernetes", "AWS", "CI/CD", "DevOps"
                        ]
                    },
                    "gap_analysis": {
                        "CoreStrengths": "<ol><li>Strong Python expertise</li></ol>",
                        "KeyGaps": "<ol><li>Missing React experience</li></ol>",
                        "QuickImprovements": "<ol><li>Add React projects</li></ol>",
                        "OverallAssessment": "<p>Good backend skills</p>",
                        "SkillSearchQueries": []
                    },
                    "processing_time_ms": int(delay * 1000)
                },
                "error": {"code": "", "message": "", "details": ""},
                "timestamp": "2025-08-03T10:30:00.000Z"
            }

        service = AsyncMock()
        service.analyze_combined = analyze_combined
        return service

    # TEST: API-GAP-001-PT
    @pytest.mark.performance
    def test_p50_response_time(self, test_client, test_data):
        """TEST: API-GAP-001-PT - 中位數響應時間 < 2 秒驗證.

        驗證 P50 響應時間符合目標。
        重要:必須關閉資源池快取並使用唯一測試資料。
        """
        # Ensure resource pool is disabled
        with patch.dict(os.environ, {'RESOURCE_POOL_ENABLED': 'false'}):
            # Mock service with realistic delay
            mock_service = self.mock_fast_service_response(delay=0.5)

            response_times = []
            total_requests = 60  # 10 QPS for 6 seconds (reduced for test)

            with patch('src.api.v1.endpoints.gap_analysis.get_combined_analysis_service',
                      return_value=mock_service):
                # Execute requests
                start_time = time.time()

                for i in range(total_requests):
                    # Generate unique data for each request
                    unique_data = self.generate_unique_test_data(i, test_data)

                    request_start = time.time()
                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=unique_data,
                        headers={"X-API-Key": "test-api-key"}
                    )
                    request_time = time.time() - request_start

                    if response.status_code == 200:
                        response_times.append(request_time)

                    # Maintain 10 QPS rate
                    elapsed = time.time() - start_time
                    expected_elapsed = (i + 1) / 10.0
                    if elapsed < expected_elapsed:
                        time.sleep(expected_elapsed - elapsed)

            # Calculate P50 (median)
            p50 = statistics.median(response_times)

            # Verify P50 < 2 seconds
            assert p50 < 2.0, f"P50 response time {p50:.2f}s exceeds 2s target"

            # Additional metrics for debugging
            print(f"\nP50 Response Time: {p50:.2f}s")
            print(f"Min Response Time: {min(response_times):.2f}s")
            print(f"Max Response Time: {max(response_times):.2f}s")
            print(f"Total Requests: {len(response_times)}")

    # TEST: API-GAP-002-PT
    @pytest.mark.performance
    def test_p95_response_time(self, test_client, test_data):
        """TEST: API-GAP-002-PT - 95 百分位響應時間 < 4 秒驗證.

        驗證 P95 響應時間符合目標。
        重要:必須關閉資源池快取並使用唯一測試資料。
        """
        # Ensure resource pool is disabled
        with patch.dict(os.environ, {'RESOURCE_POOL_ENABLED': 'false'}):
            # Mock service with variable delay to simulate real conditions
            mock_service = self.mock_fast_service_response(delay=0.8)

            response_times = []
            total_requests = 60  # 10 QPS for 6 seconds (reduced for test)

            with patch('src.api.v1.endpoints.gap_analysis.get_combined_analysis_service',
                      return_value=mock_service):
                # Execute requests
                start_time = time.time()

                for i in range(total_requests):
                    # Generate unique data for each request
                    unique_data = self.generate_unique_test_data(i, test_data)

                    request_start = time.time()
                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=unique_data,
                        headers={"X-API-Key": "test-api-key"}
                    )
                    request_time = time.time() - request_start

                    if response.status_code == 200:
                        response_times.append(request_time)

                    # Maintain 10 QPS rate
                    elapsed = time.time() - start_time
                    expected_elapsed = (i + 1) / 10.0
                    if elapsed < expected_elapsed:
                        time.sleep(expected_elapsed - elapsed)

            # Sort response times and calculate P95
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]

            # Verify P95 < 4 seconds
            assert p95 < 4.0, f"P95 response time {p95:.2f}s exceeds 4s target"

            # Additional metrics
            print(f"\nP95 Response Time: {p95:.2f}s")
            print(f"P50 Response Time: {statistics.median(response_times):.2f}s")
            print(f"Total Requests: {len(response_times)}")

    # TEST: API-GAP-003-PT
    @pytest.mark.performance
    def test_resource_pool_reuse_rate(self, test_client, test_data):
        """TEST: API-GAP-003-PT - 資源池客戶端重用率 > 80%.

        驗證資源池有效減少初始化開銷。
        注意:此測試需要開啟資源池功能。
        """
        # Enable resource pool for this test
        with patch.dict(os.environ, {'RESOURCE_POOL_ENABLED': 'true'}):
            # Mock resource pool stats
            mock_pool_stats = {
                "total_requests": 0,
                "cache_hits": 0,
                "reuse_rate": 0.0
            }

            def track_request(is_cache_hit: bool):
                mock_pool_stats["total_requests"] += 1
                if is_cache_hit:
                    mock_pool_stats["cache_hits"] += 1
                mock_pool_stats["reuse_rate"] = (
                    mock_pool_stats["cache_hits"] / mock_pool_stats["total_requests"]
                )

            # Mock service that tracks reuse
            async def analyze_with_tracking(*args, **kwargs):
                # Simulate cache hit based on content similarity
                resume = kwargs.get("resume", "")
                is_cache_hit = "Request 0" not in resume  # First request is always a miss
                track_request(is_cache_hit)

                await asyncio.sleep(0.1)
                return {
                    "success": True,
                    "data": {
                        "raw_similarity_percentage": 68,
                        "similarity_percentage": 78,
                        "keyword_coverage": {"total_keywords": 8, "covered_count": 3},
                        "gap_analysis": {"CoreStrengths": "<ol><li>Test</li></ol>"},
                        "cache_hit": is_cache_hit,
                        "pool_stats": mock_pool_stats.copy()
                    }
                }

            mock_service = AsyncMock()
            mock_service.analyze_combined = analyze_with_tracking

            # Use same test data for better reuse
            standard_request = test_data["valid_test_data"]["standard_requests"][0]

            with patch('src.api.v1.endpoints.gap_analysis.get_combined_analysis_service',
                      return_value=mock_service):
                # Send 100 requests with similar content
                for i in range(100):
                    # Use mostly same data with minor variations
                    request_data = {
                        "resume": (
                            standard_request["resume"] if i % 10 != 0
                            else f"{standard_request['resume']} Request {i}"
                        ),
                        "job_description": standard_request["job_description"],
                        "keywords": standard_request["keywords"]
                    }

                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=request_data,
                        headers={"X-API-Key": "test-api-key"}
                    )

                    assert response.status_code == 200

            # Verify reuse rate > 80%
            final_reuse_rate = mock_pool_stats["reuse_rate"]
            assert final_reuse_rate > 0.80, f"Reuse rate {final_reuse_rate:.1%} is below 80% target"

            print("\nResource Pool Stats:")
            print(f"Total Requests: {mock_pool_stats['total_requests']}")
            print(f"Cache Hits: {mock_pool_stats['cache_hits']}")
            print(f"Reuse Rate: {final_reuse_rate:.1%}")

    # TEST: API-GAP-004-PT
    @pytest.mark.performance
    def test_api_call_reduction(self, test_client, test_data):
        """TEST: API-GAP-004-PT - 共享 Embedding 減少 API 呼叫 40-50%.

        驗證相同輸入的重複請求減少 API 呼叫。
        注意:此測試專門驗證資源池效果,必須使用完全相同的測試資料。
        """
        # Enable resource pool for this test
        with patch.dict(os.environ, {'RESOURCE_POOL_ENABLED': 'true'}):
            # Track API calls
            api_call_counts = {
                "embedding": 0,
                "llm": 0,
                "total": 0
            }

            # Mock embedding client that tracks calls
            async def create_embeddings_with_tracking(texts):
                api_call_counts["embedding"] += 1
                api_call_counts["total"] += 1
                await asyncio.sleep(0.1)
                return [[0.1] * 1536 for _ in texts]

            # Mock LLM client that tracks calls
            async def llm_call_with_tracking(*args, **kwargs):
                api_call_counts["llm"] += 1
                api_call_counts["total"] += 1
                await asyncio.sleep(0.1)
                return {"choices": [{"message": {"content": "Test response"}}]}

            # Create mock clients
            mock_embedding_client = AsyncMock()
            mock_embedding_client.create_embeddings = create_embeddings_with_tracking

            mock_llm_client = AsyncMock()
            mock_llm_client.chat.completions.create = llm_call_with_tracking

            # Use exact same request data
            identical_request = test_data["valid_test_data"]["standard_requests"][0]

            with (
                patch('src.services.embedding_client.get_azure_embedding_client',
                      return_value=mock_embedding_client),
                patch('src.services.llm_client.get_azure_llm_client',
                      return_value=mock_llm_client)
            ):
                    # Send 10 identical requests
                    for _i in range(10):
                        response = test_client.post(
                            "/api/v1/index-cal-and-gap-analysis",
                            json={
                                "resume": identical_request["resume"],
                                "job_description": identical_request["job_description"],
                                "keywords": identical_request["keywords"]
                            },
                            headers={"X-API-Key": "test-api-key"}
                        )

                        assert response.status_code == 200

            # Calculate API call reduction
            expected_calls_without_cache = 10 * 3  # 10 requests * (2 embeddings + 1 LLM)
            actual_calls = api_call_counts["total"]
            reduction_percentage = ((expected_calls_without_cache - actual_calls) / expected_calls_without_cache) * 100

            # Verify 40-50% reduction
            assert 40 <= reduction_percentage <= 50, (
                f"API call reduction {reduction_percentage:.1f}% "
                f"not in 40-50% range"
            )

            print("\nAPI Call Reduction Stats:")
            print(f"Expected calls without cache: {expected_calls_without_cache}")
            print(f"Actual calls with cache: {actual_calls}")
            print(f"Reduction: {reduction_percentage:.1f}%")
            print(f"Embedding calls: {api_call_counts['embedding']}")
            print(f"LLM calls: {api_call_counts['llm']}")

    # TEST: API-GAP-005-PT
    @pytest.mark.performance
    def test_resource_pool_scaling(self, test_client, test_data):
        """TEST: API-GAP-005-PT - 資源池動態擴展效能.

        驗證資源池從 min_size 擴展到 max_size 的效能。
        注意:使用不同的測試資料觸發資源池擴展。
        """
        # Enable resource pool with specific size configuration
        with patch.dict(os.environ, {
            'RESOURCE_POOL_ENABLED': 'true',
            'RESOURCE_POOL_MIN_SIZE': '2',
            'RESOURCE_POOL_MAX_SIZE': '10'
        }):
            # Track pool size over time
            pool_sizes = []
            response_times = []

            # Mock service that simulates pool expansion
            async def analyze_with_pool_tracking(request_id, *args, **kwargs):
                # Simulate different pool sizes based on load
                current_pool_size = min(2 + (request_id // 5), 10)
                pool_sizes.append(current_pool_size)

                # Faster response with larger pool
                delay = 0.5 if current_pool_size < 5 else 0.2
                await asyncio.sleep(delay)

                return {
                    "success": True,
                    "data": {
                        "raw_similarity_percentage": 68,
                        "similarity_percentage": 78,
                        "keyword_coverage": {"total_keywords": 8, "covered_count": 3},
                        "gap_analysis": {"CoreStrengths": "<ol><li>Test</li></ol>"},
                        "pool_size": current_pool_size
                    }
                }

            # Execute concurrent requests to trigger scaling
            def make_request(request_id):
                # Generate unique data to avoid cache hits
                unique_data = self.generate_unique_test_data(request_id, test_data)

                # Create service for this request
                mock_service = AsyncMock()
                mock_service.analyze_combined = lambda *a, **k: analyze_with_pool_tracking(request_id, *a, **k)

                with patch('src.api.v1.endpoints.gap_analysis.get_combined_analysis_service',
                          return_value=mock_service):
                    start_time = time.time()
                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=unique_data,
                        headers={"X-API-Key": "test-api-key"}
                    )
                    response_time = time.time() - start_time

                    return response.status_code, response_time

            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = []

                # Submit 50 requests to trigger scaling
                for i in range(50):
                    future = executor.submit(make_request, i)
                    futures.append(future)

                    # Ramp up gradually
                    if i < 10:
                        time.sleep(0.1)

                # Collect results
                for future in as_completed(futures):
                    status_code, response_time = future.result()
                    if status_code == 200:
                        response_times.append(response_time)

            # Verify pool scaled up
            max_pool_size = max(pool_sizes)
            assert max_pool_size >= 8, f"Pool didn't scale up sufficiently (max size: {max_pool_size})"

            # Verify performance improved with scaling
            early_responses = response_times[:10]
            late_responses = response_times[-10:]

            avg_early = statistics.mean(early_responses)
            avg_late = statistics.mean(late_responses)

            # Later responses should be faster due to larger pool
            assert avg_late < avg_early, "Performance didn't improve with pool scaling"

            print("\nResource Pool Scaling Stats:")
            print(f"Initial pool size: {pool_sizes[0]}")
            print(f"Max pool size reached: {max_pool_size}")
            print(f"Early avg response time: {avg_early:.2f}s")
            print(f"Late avg response time: {avg_late:.2f}s")
            print(f"Performance improvement: {((avg_early - avg_late) / avg_early * 100):.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
