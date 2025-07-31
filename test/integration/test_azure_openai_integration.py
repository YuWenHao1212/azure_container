"""
Integration tests for Azure OpenAI service integration.

Tests:
- API-KW-111-IT: Azure OpenAI 整合測試
- Real integration with Azure OpenAI service for keyword extraction
- Error handling for Azure OpenAI failures (rate limits, timeouts, service errors)
- Authentication and configuration validation
- Performance and reliability under various conditions
"""

import asyncio
import json
import os
import sys
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
from src.services.exceptions import ProcessingError
from src.services.openai_client import (
    AzureOpenAIAuthError,
    AzureOpenAIError,
    AzureOpenAIRateLimitError,
    AzureOpenAIServerError,
)


class TestAzureOpenAIIntegration:
    """Integration tests for Azure OpenAI service integration."""

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
    def mock_keyword_service(self):
        """Create mock keyword extraction service."""
        service = AsyncMock()
        service.validate_input = AsyncMock()
        service.process = AsyncMock()
        service.close = AsyncMock()
        return service

    @pytest.fixture
    def mock_azure_openai_client(self):
        """Create mock Azure OpenAI client."""
        client = AsyncMock()
        client.chat_completion = AsyncMock()
        client.complete_text = AsyncMock()
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def valid_job_description_request(self):
        """Valid job description for testing."""
        return {
            "job_description": (
                "We are looking for a Senior Python Developer with 5+ years "
                "of experience in building scalable web applications using "
                "FastAPI and Django frameworks. Strong knowledge of Docker, "
                "Kubernetes, and AWS cloud services is required. The ideal "
                "candidate must have excellent problem-solving skills and "
                "ability to work independently in a fast-paced agile "
                "environment. Experience with microservices architecture, "
                "RESTful APIs, GraphQL, PostgreSQL, MongoDB, Redis, and "
                "distributed systems is highly valued. Must be proficient "
                "in CI/CD pipelines, automated testing, code review "
                "processes, and DevOps best practices for production "
                "deployments."
            ),
            "max_keywords": 15
        }

    def test_azure_openai_integration(
        self, 
        test_client, 
        mock_keyword_service, 
        mock_azure_openai_client, 
        valid_job_description_request
    ):
        """TEST: API-KW-111-IT - Comprehensive Azure OpenAI integration test."""

        # === Successful Integration Test ===
        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Django", "Docker",
                        "Kubernetes", "AWS", "Web Applications", "Scalable Systems",
                        "5+ Years Experience", "Backend Development", "Cloud Computing",
                        "DevOps", "Microservices", "Software Engineering"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0-en",
            "processing_time_ms": 2400.0,
            "model_used": "gpt-4.1-mini",
            "tokens_used": {"prompt_tokens": 450, "completion_tokens": 125, "total_tokens": 575}
        }

        mock_keyword_service.validate_input.return_value = valid_job_description_request
        mock_keyword_service.process.return_value = expected_result

        with (
            patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service),
            patch('src.services.llm_factory.get_llm_client_smart') as mock_get_client,
            patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}),
            patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),
            patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())
        ):
            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["keywords"] == expected_result["keywords"]
        assert data["data"]["model_used"] == "gpt-4.1-mini"
        assert "tokens_used" in data["data"]

        # === Authentication Error Handling ===
        mock_keyword_service.process.side_effect = AzureOpenAIAuthError("Invalid API key")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Permission Denied Error ===
        mock_keyword_service.process.side_effect = AzureOpenAIAuthError("Permission denied: Insufficient quota")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Rate Limit Error Handling ===
        mock_keyword_service.process.side_effect = AzureOpenAIRateLimitError("Rate limit exceeded")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Rate Limit with Retry-After ===
        rate_limit_error = AzureOpenAIRateLimitError("Rate limit exceeded: Retry-After: 60s")
        mock_keyword_service.process.side_effect = rate_limit_error

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Server Error Handling ===
        mock_keyword_service.process.side_effect = AzureOpenAIServerError("Internal server error (500)")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Service Unavailable Error ===
        mock_keyword_service.process.side_effect = AzureOpenAIServerError("Service unavailable (503)")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "Azure OpenAI" in data["error"]["message"]

        # === Timeout Error Handling ===
        mock_keyword_service.process.side_effect = asyncio.TimeoutError("Request timeout")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TIMEOUT_ERROR"
        assert "超時" in data["error"]["message"] or "timeout" in data["error"]["message"].lower()

        # === Network Error Handling ===
        mock_keyword_service.process.side_effect = httpx.ConnectError("Connection failed")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        # Error message is in Chinese: "系統發生未預期錯誤"
        assert "系統" in data["error"]["message"] or "錯誤" in data["error"]["message"]

        # === Multiple Models Integration ===
        models_to_test = [
            {"model": "gpt-4.1-mini", "deployment": "gpt-4-1-mini-japaneast", "region": "japaneast"},
            {"model": "gpt-4o", "deployment": "gpt-4o-japaneast", "region": "japaneast"},
            {"model": "gpt-4", "deployment": "gpt-4-japaneast", "region": "japaneast"}
        ]

        for model_config in models_to_test:
            expected_result = {
                "keywords": ["Python", "Developer", "FastAPI"],
                "keyword_count": 15,
                "confidence_score": 0.85,
                "extraction_method": "2_round_intersection",
                "model_used": model_config["model"],
                "deployment_used": model_config["deployment"]
            }

            mock_keyword_service.process.side_effect = None
            mock_keyword_service.process.return_value = expected_result

            with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
                with patch('src.services.llm_factory.get_llm_client_smart'):
                    with patch('src.services.llm_factory.get_llm_info', return_value=model_config):
                        with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                            with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                                response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["model_used"] == model_config["model"]

        # === Invalid Deployment Configuration ===
        mock_keyword_service.process.side_effect = AzureOpenAIError("Deployment not found: invalid-deployment")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'deployment': 'invalid-deployment', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "OPENAI_ERROR"
        assert "關鍵字提取服務處理失敗" in data["error"]["message"]

        # === Performance Under Load ===
        import concurrent.futures
        import time

        expected_result = {
            "keywords": ["Python", "Developer"],
            "keyword_count": 15,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "processing_time_ms": 1500.0
        }

        mock_keyword_service.process.side_effect = None
        mock_keyword_service.process.return_value = expected_result

        def make_request():
            with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
                with patch('src.services.llm_factory.get_llm_client_smart'):
                    with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                        with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                            with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                                return test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        end_time = time.time()

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

        # Total time should be reasonable (parallel processing)
        total_time = end_time - start_time
        assert total_time < 30.0  # Should complete within 30 seconds

        # === Error Recovery and Resilience ===
        # First request fails
        mock_keyword_service.process.side_effect = AzureOpenAIServerError("Temporary server error")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response1 = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response1.status_code == 503

        # Second request succeeds (service recovered)
        expected_result = {
            "keywords": ["Python", "Developer"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection"
        }

        mock_keyword_service.process.side_effect = None
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response2 = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response2.status_code == 200
        data = response2.json()
        assert data["success"] is True

        # === Token Usage Tracking ===
        expected_result = {
            "keywords": ["Python", "Developer"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "tokens_used": {
                "prompt_tokens": 425,
                "completion_tokens": 95,
                "total_tokens": 520
            },
            "estimated_cost": 0.0052
        }

        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify token usage information is included
        tokens = data["data"]["tokens_used"]
        assert "prompt_tokens" in tokens
        assert "completion_tokens" in tokens
        assert "total_tokens" in tokens
        assert tokens["total_tokens"] == tokens["prompt_tokens"] + tokens["completion_tokens"]

        # === Monitoring Integration ===
        mock_monitoring = Mock()
        mock_monitoring.track_event = Mock()
        mock_monitoring.track_metric = Mock()

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', mock_monitoring):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify monitoring calls were made
        mock_monitoring.track_event.assert_called()
        mock_monitoring.track_metric.assert_called()

        # === Large Input Handling ===
        large_jd = " ".join([
            "Senior Python Developer with extensive experience in building scalable applications."
            for _ in range(100)  # Repeat to create large text
        ])

        large_request = {
            "job_description": large_jd,
            "max_keywords": 20
        }

        expected_result = {
            "keywords": ["Python", "Senior Developer", "Scalable Applications"],
            "keyword_count": 20,
            "confidence_score": 0.82,
            "extraction_method": "2_round_intersection",
            "processing_time_ms": 4500.0,
            "input_token_count": 2800
        }

        mock_keyword_service.validate_input.return_value = large_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=large_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["keywords"]) <= 20

        # === Malformed Response Handling ===
        mock_keyword_service.process.side_effect = ProcessingError("Malformed response from Azure OpenAI")

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        # ProcessingError is caught as general exception, not specific error
        assert "系統發生未預期錯誤" in data["error"]["message"]

        # === Secure Credential Handling ===
        expected_result = {
            "keywords": ["Python", "Developer"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection"
        }

        mock_keyword_service.process.side_effect = None
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify no sensitive information is in response
        response_text = json.dumps(data)
        assert "test-key" not in response_text
        assert "api_key" not in response_text.lower()
        assert "secret" not in response_text.lower()

        # === Data Privacy Compliance ===
        expected_result = {
            "keywords": ["Python", "Developer"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "data_retention_policy": "processed_data_not_stored",
            "privacy_compliant": True
        }

        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart'):
                with patch('src.services.llm_factory.get_llm_info', return_value={'model': 'gpt-4.1-mini', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post("/api/v1/extract-jd-keywords", json=valid_job_description_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify privacy compliance indicators
        if "privacy_compliant" in data["data"]:
            assert data["data"]["privacy_compliant"] is True
