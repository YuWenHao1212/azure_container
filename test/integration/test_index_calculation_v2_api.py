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
"""

import asyncio
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, Mock, patch

import httpx
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
os.environ['INDEX_CALC_CACHE_ENABLED'] = 'true'
os.environ['INDEX_CALC_CACHE_TTL_MINUTES'] = '60'
os.environ['INDEX_CALC_CACHE_MAX_SIZE'] = '1000'

from src.main import create_app
from src.services.exceptions import ProcessingError
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
)


class TestIndexCalculationV2Integration:
    """Integration tests for Index Calculation V2 API endpoints."""

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
        return client

    @pytest.fixture
    def valid_index_calc_request(self):
        """Valid index calculation request for testing."""
        return {
            "resume": "Python developer with 5+ years of experience in FastAPI and Django",
            "job_description": "Looking for Python developer with FastAPI experience",
            "keywords": ["Python", "FastAPI", "Django", "Docker"]
        }

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__), 
            '../fixtures/index_calculation/test_data.json'
        )
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # TEST: API-IC-101-IT
    def test_api_endpoint_basic_functionality(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-101-IT - API端點基本功能測試.
        
        驗證 POST /api/v1/index-calculation 端點正常運作。
        """
        # Mock successful embeddings
        mock_embedding_client.create_embeddings.return_value = [
            [0.1] * 1536,  # Resume embedding
            [0.1] * 1536   # Job description embedding
        ]

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation.monitoring_service', Mock()):
                response = test_client.post(
                    "/api/v1/index-calculation",
                    json=valid_index_calc_request
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert data["success"] is True
        assert "data" in data
        
        # Check data structure
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result
        
        # Check keyword coverage structure
        coverage = result["keyword_coverage"]
        assert "total_keywords" in coverage
        assert "covered_count" in coverage
        assert "coverage_percentage" in coverage
        assert "covered_keywords" in coverage
        assert "missed_keywords" in coverage
        
        # Verify types
        assert isinstance(result["raw_similarity_percentage"], int)
        assert isinstance(result["similarity_percentage"], int)
        assert 0 <= result["raw_similarity_percentage"] <= 100
        assert 0 <= result["similarity_percentage"] <= 100

    # TEST: API-IC-102-IT
    def test_cache_behavior_integration(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-102-IT - 快取行為整合測試.
        
        驗證快取在 API 層級的正確行為。
        Note: V2 implementation will include cache functionality.
        """
        # Mock embeddings
        mock_embedding_client.create_embeddings.return_value = [
            [0.1] * 1536,
            [0.1] * 1536
        ]

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation.monitoring_service', Mock()):
                # First request - cache miss
                start_time1 = time.time()
                response1 = test_client.post(
                    "/api/v1/index-calculation",
                    json=valid_index_calc_request
                )
                time1 = time.time() - start_time1

                assert response1.status_code == 200
                data1 = response1.json()
                
                # For V2, check cache_hit field when implemented
                # assert data1["data"].get("cache_hit") is False
                
                # Second request - should be cache hit (much faster)
                start_time2 = time.time()
                response2 = test_client.post(
                    "/api/v1/index-calculation",
                    json=valid_index_calc_request
                )
                time2 = time.time() - start_time2

                assert response2.status_code == 200
                data2 = response2.json()
                
                # Results should be identical
                assert data1["data"]["raw_similarity_percentage"] == data2["data"]["raw_similarity_percentage"]
                assert data1["data"]["similarity_percentage"] == data2["data"]["similarity_percentage"]
                assert data1["data"]["keyword_coverage"] == data2["data"]["keyword_coverage"]
                
                # For V2, check cache_hit field when implemented
                # assert data2["data"].get("cache_hit") is True
                # assert time2 < time1 * 0.1  # Cache hit should be much faster

    # TEST: API-IC-103-IT
    def test_input_validation(self, test_client):
        """TEST: API-IC-103-IT - 輸入驗證測試.
        
        驗證各種無效輸入的錯誤處理。
        """
        # Test empty resume
        response = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": "",
                "job_description": "Python developer",
                "keywords": ["Python"]
            }
        )
        assert response.status_code == 400
        assert response.json()["success"] is False
        assert "error" in response.json()
        
        # Test missing fields
        response = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": "Python developer"
                # Missing job_description and keywords
            }
        )
        assert response.status_code == 422  # FastAPI validation error
        
        # Test invalid JSON
        response = test_client.post(
            "/api/v1/index-calculation",
            data="invalid json"
        )
        assert response.status_code == 422
        
        # Test extremely short text (< 100 characters total)
        response = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": "Python",
                "job_description": "Dev",
                "keywords": ["Python"]
            }
        )
        assert response.status_code == 400
        assert "too short" in response.json()["error"]["message"].lower()
        
        # Test extremely long text (> 500KB)
        large_text = "x" * 600000
        response = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": large_text,
                "job_description": "Python developer",
                "keywords": ["Python"]
            }
        )
        assert response.status_code == 400
        assert "too long" in response.json()["error"]["message"].lower()

    # TEST: API-IC-104-IT
    def test_azure_openai_service_failure(
        self, test_client, mock_embedding_client, valid_index_calc_request
    ):
        """TEST: API-IC-104-IT - Azure OpenAI服務失敗測試.
        
        驗證 embedding 服務失敗時的錯誤處理。
        """
        # Test rate limit error
        mock_embedding_client.create_embeddings.side_effect = AzureOpenAIRateLimitError(
            "Rate limit exceeded"
        )

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            response = test_client.post(
                "/api/v1/index-calculation",
                json=valid_index_calc_request
            )

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        
        # Test authentication error
        mock_embedding_client.create_embeddings.side_effect = AzureOpenAIAuthError(
            "Invalid API key"
        )

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            response = test_client.post(
                "/api/v1/index-calculation",
                json=valid_index_calc_request
            )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
        
        # Test server error
        mock_embedding_client.create_embeddings.side_effect = AzureOpenAIServerError(
            "Internal server error"
        )

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            response = test_client.post(
                "/api/v1/index-calculation",
                json=valid_index_calc_request
            )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
        
        # Test timeout
        mock_embedding_client.create_embeddings.side_effect = asyncio.TimeoutError()

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            response = test_client.post(
                "/api/v1/index-calculation",
                json=valid_index_calc_request
            )

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "TIMEOUT_ERROR"

    # TEST: API-IC-105-IT
    def test_concurrent_request_handling(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-105-IT - 並發請求處理測試.
        
        驗證高並發請求下的系統穩定性。
        """
        # Mock embeddings to return quickly
        mock_embedding_client.create_embeddings.return_value = [
            [0.1] * 1536,
            [0.1] * 1536
        ]

        def make_request(index):
            """Make a single request with unique content."""
            with patch('src.services.index_calculation.get_azure_embedding_client', 
                      return_value=mock_embedding_client):
                with patch('src.services.index_calculation.monitoring_service', Mock()):
                    response = test_client.post(
                        "/api/v1/index-calculation",
                        json={
                            "resume": f"Python developer with experience {index}",
                            "job_description": f"Looking for developer {index}",
                            "keywords": ["Python", f"Skill{index}"]
                        }
                    )
                    return response

        # Execute 10 concurrent requests
        successful_requests = 0
        failed_requests = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            
            for future in as_completed(futures):
                try:
                    response = future.result()
                    if response.status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                except Exception:
                    failed_requests += 1

        # All requests should succeed
        assert successful_requests == 10
        assert failed_requests == 0

    # TEST: API-IC-106-IT
    def test_large_document_handling(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-106-IT - 大文檔處理測試.
        
        驗證大文檔的處理能力和效能。
        """
        # Use large resume from test data
        large_resume = test_data["standard_resumes"][2]["content"]  # 10KB resume
        large_jd = test_data["job_descriptions"][2]["content"]  # 5KB job description
        
        # Mock embeddings
        mock_embedding_client.create_embeddings.return_value = [
            [0.1] * 1536,
            [0.1] * 1536
        ]

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation.monitoring_service', Mock()):
                start_time = time.time()
                response = test_client.post(
                    "/api/v1/index-calculation",
                    json={
                        "resume": large_resume,
                        "job_description": large_jd,
                        "keywords": ["Python", "FastAPI", "Docker", "Kubernetes"]
                    }
                )
                processing_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Should process within reasonable time (< 5 seconds for test)
        assert processing_time < 5.0
        
        # Test maximum size (30KB)
        very_large_resume = large_resume * 3  # ~30KB
        
        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation.monitoring_service', Mock()):
                response = test_client.post(
                    "/api/v1/index-calculation",
                    json={
                        "resume": very_large_resume,
                        "job_description": large_jd,
                        "keywords": ["Python"]
                    }
                )

        assert response.status_code == 200

    # TEST: API-IC-107-IT
    def test_service_stats_endpoint(self, test_client):
        """TEST: API-IC-107-IT - 服務統計端點測試.
        
        驗證 GET /api/v1/index-calculation/stats 端點。
        Note: This endpoint will be implemented in V2.
        """
        # For V2 implementation
        response = test_client.get("/api/v1/index-calculation/stats")
        
        # Expected to return 404 until implemented
        # When implemented, should return:
        # assert response.status_code == 200
        # data = response.json()
        # assert "total_requests" in data
        # assert "cache_hit_rate" in data
        # assert "average_processing_time_ms" in data
        # assert "error_rate" in data
        
        # For now, just verify the endpoint doesn't crash the app
        assert response.status_code in [200, 404]

    # TEST: API-IC-108-IT
    def test_cross_language_content(
        self, test_client, mock_embedding_client, test_data
    ):
        """TEST: API-IC-108-IT - 跨語言內容測試.
        
        驗證中英文混合內容的處理。
        """
        # Get Chinese and mixed language content from test data
        chinese_resume = test_data["standard_resumes"][4]["content"]
        mixed_jd = test_data["job_descriptions"][4]["content"]
        
        # Mock embeddings
        mock_embedding_client.create_embeddings.return_value = [
            [0.1] * 1536,
            [0.1] * 1536
        ]

        with patch('src.services.index_calculation.get_azure_embedding_client', 
                  return_value=mock_embedding_client):
            with patch('src.services.index_calculation.monitoring_service', Mock()):
                # Test Chinese resume with English JD
                response1 = test_client.post(
                    "/api/v1/index-calculation",
                    json={
                        "resume": chinese_resume,
                        "job_description": "Looking for Python developer",
                        "keywords": ["Python", "FastAPI", "雲端"]
                    }
                )

                assert response1.status_code == 200
                data1 = response1.json()
                assert data1["success"] is True
                
                # Test mixed language content
                response2 = test_client.post(
                    "/api/v1/index-calculation",
                    json={
                        "resume": test_data["standard_resumes"][5]["content"],  # Mixed language
                        "job_description": mixed_jd,
                        "keywords": ["Backend", "後端", "Docker", "K8s"]
                    }
                )

                assert response2.status_code == 200
                data2 = response2.json()
                assert data2["success"] is True
                
                # Verify keyword matching works with mixed languages
                coverage = data2["data"]["keyword_coverage"]
                assert coverage["total_keywords"] == 4
                assert coverage["covered_count"] >= 2  # At least Backend and Docker


if __name__ == "__main__":
    pytest.main([__file__, "-v"])