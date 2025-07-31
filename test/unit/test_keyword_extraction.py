"""
Unit tests for keyword extraction endpoint.

Tests the /api/v1/extract-jd-keywords endpoint functionality including:
- Input validation
- Response format validation
- Error handling scenarios
- Mocked OpenAI interactions
- Edge cases
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException
import sys
import os
import asyncio
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables before imports
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['LLM2_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['LLM2_DEPLOYMENT'] = 'test-deployment'
os.environ['LLM2_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

# Mock services before importing main
with patch('src.services.openai_client.get_azure_openai_client'):
    with patch('src.services.openai_client_gpt41.get_gpt41_mini_client'):
        with patch('src.services.keyword_extraction.get_keyword_extraction_service'):
            from src.main import create_app
            from src.core.config import Settings
            from src.models.keyword_extraction import KeywordExtractionRequest, KeywordExtractionData
            from src.services.openai_client import (
                AzureOpenAIError, 
                AzureOpenAIRateLimitError,
                AzureOpenAIAuthError,
                AzureOpenAIServerError
            )


class TestKeywordExtraction:
    """Test suite for keyword extraction endpoint."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for tests."""
        settings = Mock(spec=Settings)
        settings.app_name = "AI Resume Advisor API"
        settings.app_version = "2.0.0"
        settings.api_v1_prefix = "/api/v1"
        settings.cors_origins_list = ["*"]
        settings.cors_allow_credentials = True
        settings.cors_allow_methods_list = ["*"]
        settings.cors_allow_headers_list = ["*"]
        settings.debug = False
        return settings
    
    @pytest.fixture
    def mock_keyword_service(self):
        """Create mock keyword extraction service."""
        service = AsyncMock()
        service.validate_input = AsyncMock()
        service.process = AsyncMock()
        service.close = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock()
        return client
    
    @pytest.fixture
    def test_client(self, mock_settings):
        """Create test client with mocked dependencies."""
        with patch('src.core.config.get_settings', return_value=mock_settings):
            with patch('src.main.settings', mock_settings):
                # Mock monitoring service
                with patch('src.main.monitoring_service', Mock()):
                    # Mock environment variables
                    with patch.dict(os.environ, {
                        'MONITORING_ENABLED': 'false',
                        'LIGHTWEIGHT_MONITORING': 'false',
                        'ERROR_CAPTURE_ENABLED': 'false',
                        'CONTAINER_APP_API_KEY': ''
                    }):
                        app = create_app()
                        return TestClient(app)
    
    @pytest.fixture
    def valid_request_data(self):
        """Valid request data for keyword extraction."""
        return {
            "job_description": "We are looking for a Senior Python Developer with experience in FastAPI, "
                             "Docker, and Azure cloud services. The ideal candidate should have strong "
                             "knowledge of microservices architecture and RESTful APIs. Experience with "
                             "CI/CD pipelines and test-driven development is highly desired.",
            "max_keywords": 15,
            "prompt_version": "latest"
        }
    
    @pytest.fixture
    def successful_extraction_result(self):
        """Mock successful extraction result."""
        return {
            "keywords": [
                "Python", "FastAPI", "Docker", "Azure", "Microservices",
                "RESTful APIs", "CI/CD", "Test-driven development",
                "Senior Developer", "Cloud services", "Architecture",
                "Pipelines", "Development", "Experience", "Knowledge"
            ],
            "keyword_count": 15,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0",
            "intersection_stats": {
                "round1_keywords": 16,
                "round2_keywords": 15,
                "intersection_count": 15,
                "final_count": 15,
                "supplemented_count": 0,
                "warning": False
            },
            "processing_time_ms": 2500.0
        }
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_success(self, test_client, mock_keyword_service, 
                                    mock_llm_client, valid_request_data, 
                                    successful_extraction_result):
        """TEST: API-KW-101-UT - 基本關鍵字提取"""
        # Setup mocks
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.return_value = successful_extraction_result
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["success"] is True
        assert "data" in data
        assert "error" in data
        assert "timestamp" in data
        
        # Check data content
        assert data["data"]["keywords"] == successful_extraction_result["keywords"]
        assert data["data"]["keyword_count"] == 15
        assert data["data"]["confidence_score"] == 0.85
        assert data["data"]["extraction_method"] == "2_round_intersection"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_validation_error_short_description(self, test_client, 
                                                               mock_keyword_service,
                                                               mock_llm_client):
        """TEST: API-KW-102-UT - 驗證錯誤處理（描述過短）"""
        request_data = {
            "job_description": "This job description is intentionally too short to meet the minimum 200 character requirement.",
            "max_keywords": 15
        }
        
        # This will be caught by Pydantic validation, not service validation
        response = test_client.post(
            "/api/v1/extract-jd-keywords",
            json=request_data
        )
        
        # Pydantic validation returns 422
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "Job description must be at least 200 characters" in str(data["error"])
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_invalid_max_keywords(self, test_client, mock_keyword_service, 
                                             mock_llm_client, valid_request_data):
        """TEST: API-KW-103-UT - 無效的 max_keywords 參數"""
        # Test too low
        request_data = valid_request_data.copy()
        request_data["max_keywords"] = 3
        
        response = test_client.post("/api/v1/extract-jd-keywords", json=request_data)
        assert response.status_code == 422
        
        # Test too high
        request_data["max_keywords"] = 30
        response = test_client.post("/api/v1/extract-jd-keywords", json=request_data)
        assert response.status_code == 422
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_azure_rate_limit_error(self, test_client, 
                                                    mock_keyword_service,
                                                    mock_llm_client,
                                                    valid_request_data):
        """TEST: API-KW-104-UT - Azure OpenAI 速率限制錯誤處理"""
        # Mock service to raise rate limit error
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.side_effect = AzureOpenAIRateLimitError(
            "Rate limit exceeded"
        )
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        # Assert service unavailable response
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_timeout_error(self, test_client, 
                                          mock_keyword_service,
                                          mock_llm_client,
                                          valid_request_data):
        """TEST: API-KW-105-UT - 逾時錯誤處理"""
        # Mock service to raise timeout
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.side_effect = asyncio.TimeoutError()
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        # Assert timeout error response
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TIMEOUT_ERROR"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_with_warning(self, test_client, 
                                         mock_keyword_service,
                                         mock_llm_client,
                                         valid_request_data):
        """TEST: API-KW-106-UT - 品質警告偵測"""
        # Create result with warning
        result_with_warning = {
            "keywords": ["Python", "Developer", "Experience", "Skills", "Team"],
            "keyword_count": 5,
            "confidence_score": 0.60,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0",
            "intersection_stats": {
                "round1_keywords": 8,
                "round2_keywords": 7,
                "intersection_count": 5,
                "final_count": 5,
                "supplemented_count": 0,
                "warning": True,
                "warning_message": "Low keyword count detected"
            },
            "processing_time_ms": 2100.0
        }
        
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.return_value = result_with_warning
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        # Assert response with warning
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["warning"]["has_warning"] is True
        assert "Low keyword count detected" in data["warning"]["message"]
        assert data["warning"]["expected_minimum"] == 12
        assert data["warning"]["actual_extracted"] == 5
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_response_format(self, test_client, 
                                            mock_keyword_service,
                                            mock_llm_client,
                                            valid_request_data,
                                            successful_extraction_result):
        """TEST: API-KW-107-UT - 回應格式驗證"""
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.return_value = successful_extraction_result
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        data = response.json()
        
        # Check all required fields are present
        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert "timestamp" in data
        
        # Check data fields
        data_fields = data["data"]
        required_fields = [
            "keywords", "keyword_count", "confidence_score", 
            "extraction_method", "processing_time_ms"
        ]
        for field in required_fields:
            assert field in data_fields
        
        # Check error structure (should be empty on success)
        assert data["error"]["code"] == ""
        assert data["error"]["message"] == ""
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_chinese_job_description(self, test_client, 
                                                    mock_keyword_service,
                                                    mock_llm_client):
        """TEST: API-KW-108-UT - 中文職缺描述支援"""
        chinese_request = {
            "job_description": "我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，"
                             "熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，"
                             "並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。"
                             "同時需要熟悉分散式系統設計，具備系統架構規劃能力。"
                             "有大型專案開發經驗和團隊領導經驗者優先考慮。"
                             "需要良好的溝通能力和問題解決能力，能夠在快節奏的環境中工作。",
            "max_keywords": 12,
            "prompt_version": "latest"
        }
        
        chinese_result = {
            "keywords": [
                "Python", "FastAPI", "Docker", "Azure", "微服務架構",
                "RESTful API", "CI/CD", "測試驅動開發", "資深工程師",
                "雲端服務", "容器技術", "開發經驗"
            ],
            "keyword_count": 12,
            "confidence_score": 0.82,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",
            "prompt_version_used": "v1.4.0",
            "intersection_stats": {
                "round1_keywords": 13,
                "round2_keywords": 12,
                "intersection_count": 12,
                "final_count": 12,
                "supplemented_count": 0,
                "warning": False
            },
            "processing_time_ms": 2800.0
        }
        
        mock_keyword_service.validate_input.return_value = chinese_request
        mock_keyword_service.process.return_value = chinese_result
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=chinese_request
                            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"
        assert len(data["data"]["keywords"]) == 12
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_service_cleanup(self, test_client, 
                                            mock_keyword_service,
                                            mock_llm_client,
                                            valid_request_data):
        """TEST: API-KW-109-UT - 錯誤時的服務清理"""
        # Mock service to raise an error
        mock_keyword_service.validate_input.return_value = valid_request_data
        mock_keyword_service.process.side_effect = Exception("Test error")
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=valid_request_data
                            )
        
        # Service cleanup should have been called
        mock_keyword_service.close.assert_called_once()
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_extract_keywords_edge_case_max_length(self, test_client, 
                                                  mock_keyword_service,
                                                  mock_llm_client):
        """TEST: API-KW-110-UT - 長職缺描述的邊界案例"""
        # Create a very long job description
        long_description = "Python " * 1000  # 6000 characters
        request_data = {
            "job_description": long_description,
            "max_keywords": 25,  # Maximum allowed
            "prompt_version": "latest"
        }
        
        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = {
            "keywords": ["Python"] * 25,
            "keyword_count": 25,
            "confidence_score": 0.75,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0",
            "intersection_stats": {
                "round1_keywords": 30,
                "round2_keywords": 30,
                "intersection_count": 30,
                "final_count": 30,
                "supplemented_count": 0,
                "warning": False
            },
            "processing_time_ms": 3500.0
        }
        
        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2', 
                  return_value=mock_keyword_service):
            with patch('src.services.llm_factory.get_llm_client_smart', 
                      return_value=mock_llm_client):
                with patch('src.services.llm_factory.get_llm_info', 
                          return_value={'model': 'gpt-4', 'region': 'japaneast'}):
                    with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                        with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                            response = test_client.post(
                                "/api/v1/extract-jd-keywords",
                                json=request_data
                            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["keyword_count"] == 25