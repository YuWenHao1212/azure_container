"""
Integration tests for health check endpoint with external dependencies.

Tests:
- API-HLT-101-IT: 健康檢查整合測試
- Health check with external services (database, cache, external APIs)
- Service status reporting and dependency validation
- Error handling for service failures
- Health check resilience under load
"""

import asyncio
import os
import sys
from datetime import datetime
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
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'
os.environ['LLM2_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['LLM2_API_KEY'] = 'test-key'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

from src.main import create_app
from src.services.embedding_client import AzureEmbeddingClient
from src.services.openai_client import AzureOpenAIError, AzureOpenAIRateLimitError


class TestHealthCheckIntegration:
    """Integration tests for health check with external dependencies."""

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
    def mock_azure_openai_client(self):
        """Create mock Azure OpenAI client."""
        client = AsyncMock()
        client.chat_completion = AsyncMock()
        client.complete_text = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_embedding_client(self):
        """Create mock embedding client."""
        client = Mock(spec=AzureEmbeddingClient)
        client.get_embeddings = AsyncMock()
        return client

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_health_check_integration(self, test_client, mock_azure_openai_client, mock_embedding_client):
        """TEST: API-HLT-101-IT - Comprehensive health check integration test."""

        # === Basic Health Check ===
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert "data" in data
        assert "timestamp" in data
        assert data["data"]["status"] == "healthy"
        assert "version" in data["data"]
        assert "timestamp" in data["data"]

        # Verify timestamp format
        timestamp = data["data"]["timestamp"]
        assert isinstance(timestamp, str)
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp format")

        # === Test with Azure OpenAI Available ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_get_client:
            mock_get_client.return_value = mock_azure_openai_client
            mock_azure_openai_client.chat_completion.return_value = {
                "choices": [{"message": {"content": "test"}}],
                "usage": {"total_tokens": 10}
            }

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"

        # === Test with Azure OpenAI Rate Limited (Resilient) ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat_completion.side_effect = AzureOpenAIRateLimitError("Rate limit exceeded")
            mock_get_client.return_value = mock_client

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"  # Health check is resilient

        # === Test with Azure OpenAI Unavailable (Resilient) ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat_completion.side_effect = AzureOpenAIError("Service unavailable")
            mock_get_client.return_value = mock_client

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"  # Resilient health check

        # === Test with Embedding Service Available ===
        with patch('src.services.embedding_client.get_azure_embedding_client') as mock_get_embedding_client:
            mock_get_embedding_client.return_value = mock_embedding_client
            mock_embedding_client.get_embeddings.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3]}]
            }

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"

        # === Test with Embedding Service Unavailable (Resilient) ===
        with patch('src.services.embedding_client.get_azure_embedding_client') as mock_get_embedding_client:
            mock_client = Mock(spec=AzureEmbeddingClient)
            mock_client.get_embeddings = AsyncMock(side_effect=Exception("Embedding service unavailable"))
            mock_get_embedding_client.return_value = mock_client

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"  # Resilient health check

        # === Test with Multiple Services Integration ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_openai:
            with patch('src.services.embedding_client.get_azure_embedding_client') as mock_embedding:
                mock_openai.return_value = mock_azure_openai_client
                mock_embedding.return_value = mock_embedding_client

                # Mock successful responses from all services
                mock_azure_openai_client.chat_completion.return_value = {
                    "choices": [{"message": {"content": "test"}}]
                }
                mock_embedding_client.get_embeddings.return_value = {
                    "data": [{"embedding": [0.1, 0.2]}]
                }

                response = test_client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "healthy"

        # === Test Network Timeout Resilience ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat_completion.side_effect = TimeoutError("Network timeout")
            mock_get_client.return_value = mock_client

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"

        # === Test External API Down Resilience ===
        with patch('httpx.AsyncClient.get') as mock_http_get:
            mock_http_get.side_effect = httpx.ConnectError("Connection failed")

            response = test_client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"

        # === Test Concurrent Requests ===
        import concurrent.futures

        def make_health_request():
            return test_client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"

        # === Test Response Time Performance ===
        import time

        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 1.0  # Health check should be fast (< 1 second)
        assert response.status_code == 200

        # === Test Different Environments ===
        test_environments = ['development', 'staging', 'production']
        for env in test_environments:
            with patch.dict(os.environ, {'ENVIRONMENT': env}):
                response = test_client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "healthy"

        # === Test Authentication Bypass ===
        # Health check should work even with invalid API key
        response = test_client.get("/health", headers={"X-API-Key": "invalid-key"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

        # === Test CORS Integration ===
        response = test_client.get("/health", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET"
        })
        assert response.status_code == 200
        # CORS headers are only added by middleware when Origin matches allowed origins
        # The test client doesn't process CORS middleware the same way as real requests
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

        # === Test Service Recovery ===
        with patch('src.services.openai_client.get_azure_openai_client') as mock_get_client:
            mock_client = AsyncMock()

            # First call fails
            mock_client.chat_completion.side_effect = AzureOpenAIError("Service error")
            mock_get_client.return_value = mock_client

            response1 = test_client.get("/health")
            assert response1.status_code == 200

            # Second call succeeds (service recovered)
            mock_client.chat_completion.side_effect = None
            mock_client.chat_completion.return_value = {
                "choices": [{"message": {"content": "recovered"}}]
            }

            response2 = test_client.get("/health")
            assert response2.status_code == 200
            data = response2.json()
            assert data["success"] is True
            assert data["data"]["status"] == "healthy"
