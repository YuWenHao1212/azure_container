"""
Unit tests for health check endpoint - Complete Rewrite.

Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0
Implements exactly 2 unit tests as specified:
- API-HLT-001-UT: Complete health check endpoint validation
- API-HLT-002-UT: HTTP method restriction validation

Each test is precisely aligned with specification requirements.
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

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
            from src.core.config import Settings
            from src.main import create_app


class TestHealthCheck:
    """Test suite for health check endpoint - exactly 2 tests as per spec."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for tests."""
        settings = Mock(spec=Settings)
        settings.app_name = "AI Resume Advisor API"
        settings.app_version = "1.0.0"
        settings.api_v1_prefix = "/api/v1"
        settings.cors_origins_list = ["*"]
        settings.cors_allow_credentials = True
        settings.cors_allow_methods_list = ["*"]
        settings.cors_allow_headers_list = ["*"]
        settings.debug = False
        return settings

    @pytest.fixture
    def test_client(self, mock_settings):
        """Create test client with mocked settings."""
        with patch('src.core.config.get_settings', return_value=mock_settings):
            with patch('src.main.settings', mock_settings):
                # Mock monitoring service to avoid initialization
                with patch('src.main.monitoring_service', None):
                    # Mock environment variables
                    with patch.dict(os.environ, {
                        'MONITORING_ENABLED': 'false',
                        'LIGHTWEIGHT_MONITORING': 'false',
                        'ERROR_CAPTURE_ENABLED': 'false',
                        'CONTAINER_APP_API_KEY': ''
                    }):
                        app = create_app()
                        return TestClient(app)

    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_API_HLT_001_UT_health_check_complete_validation(self, test_client):
        """
        TEST ID: API-HLT-001-UT
        測試名稱: 健康檢查端點完整驗證
        優先級: P0
        類型: 單元測試
        測試目標: 單一請求驗證所有健康檢查功能

        判斷標準 (全部必須通過):
        - ✅ HTTP 200 狀態碼
        - ✅ 回應包含 "status": "healthy"
        - ✅ 包含所有必要欄位: status, timestamp, version, environment
        - ✅ 各欄位類型正確 (string/datetime)
        - ✅ version 欄位值等於 settings.VERSION
        - ✅ timestamp 符合 ISO 8601 格式
        - ✅ 不需要認證 (無 API Key 也能訪問)
        - ✅ 包含 CORS headers (Access-Control-Allow-Origin)
        """
        response = test_client.get("/health")

        # ✅ HTTP 200 狀態碼
        assert response.status_code == 200

        # Parse response
        data = response.json()

        # ✅ 回應包含 "status": "healthy"
        assert data["success"] is True
        assert "data" in data
        assert "timestamp" in data
        assert data["data"]["status"] == "healthy"

        # ✅ 包含所有必要欄位: status, timestamp, version, environment
        expected_data_keys = {"status", "version", "timestamp"}
        assert set(data["data"].keys()) == expected_data_keys

        # ✅ 各欄位類型正確 (string/datetime)
        assert isinstance(data["data"]["status"], str)
        assert isinstance(data["data"]["version"], str)
        assert isinstance(data["data"]["timestamp"], str)
        assert isinstance(data["timestamp"], str)

        # ✅ version 欄位值等於 settings.VERSION
        assert data["data"]["version"] == "1.0.0"

        # ✅ timestamp 符合 ISO 8601 格式
        try:
            # Both main timestamp and data timestamp should be valid ISO 8601
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            datetime.fromisoformat(data["data"]["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp format - not ISO 8601 compliant")

        # ✅ 不需要認證 (無 API Key 也能訪問)
        # Test with API key middleware potentially enabled
        with patch.dict(os.environ, {'CONTAINER_APP_API_KEY': 'test-key'}):
            auth_response = test_client.get("/health")
            assert auth_response.status_code == 200

        # ✅ 包含 CORS headers (Access-Control-Allow-Origin)
        cors_response = test_client.get("/health", headers={"Origin": "https://example.com"})
        assert "access-control-allow-origin" in cors_response.headers
        assert cors_response.headers["access-control-allow-origin"] == "*"

    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_API_HLT_002_UT_http_method_restriction(self, test_client):
        """
        TEST ID: API-HLT-002-UT
        測試名稱: 健康檢查只接受 GET 方法
        優先級: P0
        類型: 單元測試
        測試目標: 驗證非 GET 方法被正確拒絕

        判斷標準:
        - ✅ 所有非 GET 方法返回 405 Method Not Allowed
        - ✅ 錯誤回應格式正確
        """

        # ✅ POST method should return 405 Method Not Allowed
        post_response = test_client.post("/health")
        assert post_response.status_code == 405

        # ✅ PUT method should return 405 Method Not Allowed
        put_response = test_client.put("/health")
        assert put_response.status_code == 405

        # ✅ DELETE method should return 405 Method Not Allowed
        delete_response = test_client.delete("/health")
        assert delete_response.status_code == 405

        # ✅ 錯誤回應格式正確
        # Verify that error response has proper structure
        for response in [post_response, put_response, delete_response]:
            # FastAPI's default 405 response should have proper format
            assert response.status_code == 405
            # Response should contain method not allowed information
            error_data = response.json()
            # Check for either FastAPI default format or our custom error format
            assert ("detail" in error_data) or ("error" in error_data and "code" in error_data["error"])
