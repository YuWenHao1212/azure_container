"""
Integration tests for Index Calculation V2 API endpoints.

Tests:
- API-IC-101-IT: API端點基本功能測試
- API-IC-102-IT: 快取行為整合測試
- API-IC-103-IT: 輸入驗證測試
- API-IC-104-IT: Azure OpenAI服務失敗測試
- API-IC-105-IT: 並發請求處理測試
- API-IC-106-IT: 大文檔處理測試
- API-IC-107-IT: 服務統計端點測試
- API-IC-108-IT: 跨語言內容測試
- API-IC-109-IT: 高並發功能測試（應用層）
- API-IC-110-IT: 記憶體管理測試（無洩漏）
- API-IC-111-IT: 快取LRU功能測試
- API-IC-112-IT: 錯誤恢復機制測試
"""

import asyncio
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from openai import AuthenticationError, InternalServerError, RateLimitError

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables before imports
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ['INDEX_CALC_CACHE_ENABLED'] = 'true'
os.environ['INDEX_CALC_CACHE_TTL_MINUTES'] = '60'
os.environ['INDEX_CALC_CACHE_MAX_SIZE'] = '1000'

from src.main import create_app
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
)


class TestIndexCalculationV2Integration:
    """Integration tests for Index Calculation V2 API endpoints."""

    @pytest.fixture(autouse=True)
    def reset_service_singleton(self):
        """Reset service singleton before each test."""
        import src.services.index_calculation_v2
        src.services.index_calculation_v2._index_calculation_service_v2 = None
        yield
        # Clean up after test
        src.services.index_calculation_v2._index_calculation_service_v2 = None

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
                'CONTAINER_APP_API_KEY': ''
            })
        ):
            app = create_app()
            return TestClient(app)

    @pytest.fixture
    def mock_index_calc_service(self):
        """Create mock index calculation service."""
        service = AsyncMock()
        service.calculate_index = AsyncMock()
        return service

    @pytest.fixture
    def mock_embedding_client(self):
        """Create mock embedding client."""
        client = AsyncMock()
        client.create_embeddings = AsyncMock()
        client.close = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def valid_index_calc_request(self):
        """Valid index calculation request for testing."""
        return {
            "resume": "Python developer with 5+ years of experience in FastAPI, Django, and cloud technologies. Experienced in building scalable web applications, RESTful APIs, and microservices architecture. Strong background in software engineering best practices and agile development.",
            "job_description": "Looking for senior Python developer with FastAPI experience to join our engineering team. Must have strong skills in backend development, API design, database optimization, and cloud deployment. Experience with Docker, Kubernetes, and CI/CD pipelines is highly desired.",
            "keywords": ["Python", "FastAPI", "Django", "Docker"]
        }

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/index_calculation/test_data.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    # TEST: API-IC-101-IT
    def test_api_endpoint_basic_functionality(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-101-IT - API端點基本功能測試.

        驗證 POST /api/v1/index-calculation 端點正常運作。
        """
        # Use the valid_index_calc_request fixture
        response = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)

        # Verify successful response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        # Verify expected fields in data
        assert "raw_similarity_percentage" in data["data"]
        assert "keyword_coverage" in data["data"]
        assert "cache_hit" in data["data"]
        assert "processing_time_ms" in data["data"]

        # Verify data types and ranges
        assert isinstance(data["data"]["raw_similarity_percentage"], (int, float))
        assert 0 <= data["data"]["raw_similarity_percentage"] <= 100
        assert isinstance(data["data"]["keyword_coverage"], dict)
        assert isinstance(data["data"]["cache_hit"], bool)
        assert isinstance(data["data"]["processing_time_ms"], (int, float))

        # Verify keyword coverage structure
        coverage = data["data"]["keyword_coverage"]
        assert "coverage_percentage" in coverage
        assert "covered_count" in coverage
        assert "covered_keywords" in coverage
        assert isinstance(coverage["covered_keywords"], list)

        print("Basic API endpoint functionality verified")

    # TEST: API-IC-102-IT
    def test_cache_behavior_integration(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-102-IT - 快取行為整合測試.
        
        驗證快取在 API 層級的正確行為。
        """
        # First request - should miss cache
        response1 = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["success"] is True
        assert data1["data"]["cache_hit"] is False

        # Second identical request - should hit cache
        response2 = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True
        assert data2["data"]["cache_hit"] is True

        # Cache hit should be faster (< 50ms)
        assert data2["data"]["processing_time_ms"] < 50

        print("Cache behavior integration verified")

    # TEST: API-IC-103-IT
    def test_input_validation(self, test_client):
        """TEST: API-IC-103-IT - 輸入驗證測試.
        
        驗證各種無效輸入的錯誤處理。
        """
        # Test empty resume
        empty_resume_request = {
            "resume": "",
            "job_description": "Valid job description with more than 200 characters to meet the minimum length requirement. This is a detailed job description that includes various technical skills and requirements for the position.",
            "keywords": ["Python", "FastAPI"]
        }
        response = test_client.post("/api/v1/index-calculation", json=empty_resume_request)
        assert response.status_code == 422

        # Test empty job description
        empty_jd_request = {
            "resume": "Valid resume with more than 200 characters to meet the minimum length requirement. Experienced developer with strong background in Python, FastAPI, and web development technologies.",
            "job_description": "",
            "keywords": ["Python", "FastAPI"]
        }
        response = test_client.post("/api/v1/index-calculation", json=empty_jd_request)
        assert response.status_code == 422

        # Test short resume (< 10 chars minimum)
        short_resume_request = {
            "resume": "Short",  # Only 5 chars - less than minimum 10
            "job_description": "Valid job description with sufficient length for processing. This meets the minimum requirements.",
            "keywords": ["Python", "FastAPI"]
        }
        response = test_client.post("/api/v1/index-calculation", json=short_resume_request)
        assert response.status_code == 422

        print("Input validation tests verified")

    # TEST: API-IC-104-IT
    def test_azure_openai_rate_limit_error(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-104-IT - Azure OpenAI 速率限制錯誤測試."""
        with patch('src.services.index_calculation_v2.IndexCalculationServiceV2._compute_embeddings_parallel') as mock_compute:
            # Mock rate limit error
            mock_compute.side_effect = AzureOpenAIRateLimitError("Rate limit exceeded")

            response = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)

            assert response.status_code == 429
            data = response.json()
            assert data["success"] is False
            assert "rate limit" in data["error"]["message"].lower()

        print("Azure OpenAI rate limit error handling verified")

    # TEST: API-IC-105-IT
    def test_azure_openai_auth_error(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-105-IT - Azure OpenAI 認證錯誤測試."""
        with patch('src.services.index_calculation_v2.IndexCalculationServiceV2._compute_embeddings_parallel') as mock_compute:
            # Mock authentication error - raise our custom AuthenticationError
            from src.services.exceptions import AuthenticationError
            mock_compute.side_effect = AuthenticationError("Authentication failed", status_code=401)

            response = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)

            assert response.status_code == 401  # Authentication errors now return 401
            data = response.json()
            assert data["success"] is False
            assert "authentication" in data["error"]["message"].lower()

        print("Azure OpenAI authentication error handling verified")

    # TEST: API-IC-106-IT
    def test_azure_openai_server_error(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-106-IT - Azure OpenAI 伺服器錯誤測試."""
        with patch('src.services.index_calculation_v2.IndexCalculationServiceV2._compute_embeddings_parallel') as mock_compute:
            # Mock server error - raise our custom ExternalServiceError
            from src.services.exceptions import ExternalServiceError
            mock_compute.side_effect = ExternalServiceError("Azure OpenAI server error")

            response = test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)

            assert response.status_code == 502  # External service errors return 502
            data = response.json()
            assert data["success"] is False
            assert "external service error" in data["error"]["message"].lower()

        print("Azure OpenAI server error handling verified")

    # TEST: API-IC-107-IT
    def test_concurrent_request_handling(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-107-IT - 並發請求處理測試."""
        import concurrent.futures

        def make_request():
            return test_client.post("/api/v1/index-calculation", json=valid_index_calc_request)

        # Test 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

        print("Concurrent request handling verified")

    # TEST: API-IC-108-IT
    def test_large_document_handling(self, test_client, mock_embedding_client):
        """TEST: API-IC-108-IT - 大文檔處理測試."""
        # Create large documents
        large_resume = "Experienced software developer. " * 500  # ~10KB
        large_jd = "Looking for senior developer with extensive experience. " * 400  # ~20KB

        large_doc_request = {
            "resume": large_resume,
            "job_description": large_jd,
            "keywords": ["Python", "FastAPI", "Django", "Docker"]
        }

        start_time = time.time()
        response = test_client.post("/api/v1/index-calculation", json=large_doc_request)
        end_time = time.time()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # P95 response time should be < 2 seconds
        response_time = end_time - start_time
        assert response_time < 2.0

        print(f"Large document handling verified - Response time: {response_time:.2f}s")

    # TEST: API-IC-109-IT
    def test_service_stats_endpoint(self, test_client):
        """TEST: API-IC-109-IT - 服務統計端點測試."""
        # Mock the service stats method directly
        with patch('src.services.index_calculation_v2.IndexCalculationServiceV2.get_service_stats') as mock_get_stats:
            mock_get_stats.return_value = {
                "calculation_stats": {
                    "total_calculations": 100,
                    "successful_calculations": 95,
                    "failed_calculations": 5,
                    "average_processing_time_ms": 150.5
                },
                "cache_performance": {
                    "hit_rate": 0.8,
                    "total_hits": 80,
                    "total_requests": 100,
                    "cache_size": 50
                },
                "service_name": "IndexCalculationServiceV2",
                "performance_optimizations": {
                    "cache_enabled": True,
                    "parallel_processing": True
                }
            }

            # Test stats endpoint
            response = test_client.get("/api/v1/index-calculation/stats")

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Verify expected structure
            assert "calculation_stats" in data
            assert "cache_performance" in data
            assert data["calculation_stats"]["total_calculations"] == 100
            assert data["cache_performance"]["hit_rate"] == 0.8

        print("Service stats endpoint test completed")

    # TEST: API-IC-110-IT
    def test_cross_language_content(self, test_client, mock_embedding_client):
        """TEST: API-IC-110-IT - 跨語言內容測試."""
        mixed_language_request = {
            "resume": "Experienced Python開發者 with strong background in FastAPI and Django框架. Skilled in building scalable web applications and RESTful APIs. 熟悉資料庫設計和雲端部署技術。",
            "job_description": "Looking for senior Python engineer精通FastAPI框架開發. Must have experience with Docker containers and cloud deployment on AWS or Azure雲端平台. Strong knowledge of database design and API development必須具備。",
            "keywords": ["Python", "FastAPI", "Django", "Docker", "雲端", "API"]
        }

        response = test_client.post("/api/v1/index-calculation", json=mixed_language_request)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "raw_similarity_percentage" in data["data"]
        assert data["data"]["raw_similarity_percentage"] >= 0

        print("Cross-language content handling verified")

    # TEST: API-IC-111-IT
    def test_high_concurrency_functionality(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-111-IT - 高並發功能測試（應用層）."""
        import concurrent.futures

        def make_concurrent_request(request_id):
            # Modify request slightly to avoid cache hits
            modified_request = valid_index_calc_request.copy()
            modified_request["resume"] = f"{valid_index_calc_request['resume']} Request {request_id}"
            return test_client.post("/api/v1/index-calculation", json=modified_request)

        # Test 20 concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(20)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()

        # All requests should succeed
        success_count = 0
        for response in responses:
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    success_count += 1

        # At least 95% success rate
        success_rate = success_count / len(responses)
        assert success_rate >= 0.95

        print(f"High concurrency test verified - Success rate: {success_rate:.2%}")

    # TEST: API-IC-112-IT
    def test_memory_management(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-112-IT - 記憶體管理測試（無洩漏）."""
        import gc
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make multiple requests
        for i in range(50):
            modified_request = valid_index_calc_request.copy()
            modified_request["resume"] = f"{valid_index_calc_request['resume']} Iteration {i}"
            response = test_client.post("/api/v1/index-calculation", json=modified_request)
            assert response.status_code == 200

        # Force garbage collection
        gc.collect()

        # Check memory usage after GC
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB)
        memory_increase_mb = memory_increase / (1024 * 1024)
        assert memory_increase_mb < 50

        print(f"Memory management verified - Memory increase: {memory_increase_mb:.2f}MB")

    # TEST: API-IC-113-IT
    def test_cache_lru_functionality(
        self, test_client, mock_embedding_client
    ):
        """TEST: API-IC-113-IT - 快取LRU功能測試."""
        # Create multiple different requests to test LRU
        base_request = {
            "job_description": "Looking for senior Python developer with FastAPI experience to join our engineering team. Must have strong skills in backend development, API design, database optimization, and cloud deployment. Experience with Docker, Kubernetes, and CI/CD pipelines is highly desired.",
            "keywords": ["Python", "FastAPI", "Django", "Docker"]
        }

        requests = []
        for i in range(5):
            req = base_request.copy()
            req["resume"] = f"Python developer with {i+1} years of experience in FastAPI, Django, and cloud technologies. Experienced in building scalable web applications, RESTful APIs, and microservices architecture. Strong background in software engineering best practices."
            requests.append(req)

        # Fill cache with requests
        for i, req in enumerate(requests):
            response = test_client.post("/api/v1/index-calculation", json=req)
            assert response.status_code == 200
            print(f"Request {i+1} processed")

        # Access first request again to make it recently used
        response = test_client.post("/api/v1/index-calculation", json=requests[0])
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["cache_hit"] is True

        print("Cache LRU functionality verified")

    # TEST: API-IC-114-IT
    def test_error_recovery_mechanism(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-114-IT - 錯誤恢復機制測試（重試邏輯）."""
        with patch('src.services.index_calculation_v2.IndexCalculationServiceV2._compute_embeddings_parallel') as mock_compute:
            # First call fails, second call succeeds
            mock_compute.side_effect = [
                Exception("Temporary failure"),
                ([0.1, 0.2, 0.3], [0.2, 0.3, 0.4])  # Mock successful embeddings
            ]

            # Make two requests with different payloads to avoid cache
            request1 = valid_index_calc_request.copy()
            request1["resume"] = f"{valid_index_calc_request['resume']} - Test 1"

            request2 = valid_index_calc_request.copy()
            request2["resume"] = f"{valid_index_calc_request['resume']} - Test 2"

            # First request should fail
            response1 = test_client.post("/api/v1/index-calculation", json=request1)
            assert response1.status_code in [500, 503]  # Server error expected

            # Second request should succeed (recovery)
            response2 = test_client.post("/api/v1/index-calculation", json=request2)
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["success"] is True

        print("Error recovery mechanism verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
