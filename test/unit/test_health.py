"""
Unit tests for health check endpoint.

Tests the /health endpoint functionality including:
- Response format validation
- Version information correctness
- Status codes
- Timestamp format
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi.testclient import TestClient
import sys
import os

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


class TestHealthCheck:
    """Test suite for health check endpoint."""
    
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
    def test_health_check_success(self, test_client):
        """TEST: API-HLT-001-UT - 基本健康檢查正常回應"""
        response = test_client.get("/health")
        
        # Assert status code
        assert response.status_code == 200
        
        # Parse response
        data = response.json()
        
        # Assert response structure
        assert data["success"] is True
        assert "data" in data
        assert "timestamp" in data
        
        # Assert data fields
        assert data["data"]["status"] == "healthy"
        assert data["data"]["version"] == "1.0.0"
        assert "timestamp" in data["data"]
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            datetime.fromisoformat(data["data"]["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Invalid timestamp format")
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_response_format(self, test_client):
        """TEST: API-HLT-002-UT - 健康檢查回應格式正確性"""
        response = test_client.get("/health")
        data = response.json()
        
        # Expected structure
        expected_keys = {"success", "data", "timestamp"}
        expected_data_keys = {"status", "version", "timestamp"}
        
        # Verify top-level keys
        assert set(data.keys()) == expected_keys
        
        # Verify data keys
        assert set(data["data"].keys()) == expected_data_keys
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_version_matches_settings(self, test_client, mock_settings):
        """TEST: API-HLT-003-UT - 版本資訊正確性"""
        # The version is from the actual settings, not our mock
        response = test_client.get("/health")
        data = response.json()
        
        # Should match the actual settings.app_version which is "1.0.0"
        assert data["data"]["version"] == "1.0.0"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_always_returns_healthy(self, test_client):
        """TEST: API-HLT-004-UT - 總是回傳健康狀態"""
        # Make multiple requests
        for _ in range(5):
            response = test_client.get("/health")
            data = response.json()
            assert data["data"]["status"] == "healthy"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_timestamp_format(self, test_client):
        """TEST: API-HLT-005-UT - 時間戳記格式驗證"""
        response = test_client.get("/health")
        data = response.json()
        
        # Both timestamps should be in ISO format
        timestamp1 = data["timestamp"]
        timestamp2 = data["data"]["timestamp"]
        
        # Check format (should end with Z or have timezone)
        assert timestamp1.endswith('Z') or '+' in timestamp1 or 'T' in timestamp1
        assert timestamp2.endswith('Z') or '+' in timestamp2 or 'T' in timestamp2
        
        # Should be parseable as datetime
        dt1 = datetime.fromisoformat(timestamp1.replace('Z', '+00:00'))
        dt2 = datetime.fromisoformat(timestamp2.replace('Z', '+00:00'))
        
        # Timestamps should be recent (within last minute)
        now = datetime.utcnow()
        assert (now - dt1.replace(tzinfo=None)).total_seconds() < 60
        assert (now - dt2.replace(tzinfo=None)).total_seconds() < 60
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_method_not_allowed(self, test_client):
        """TEST: API-HLT-006-UT - HTTP 方法驗證"""
        # Test POST
        response = test_client.post("/health")
        assert response.status_code == 405
        
        # Test PUT
        response = test_client.put("/health")
        assert response.status_code == 405
        
        # Test DELETE
        response = test_client.delete("/health")
        assert response.status_code == 405
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_no_authentication_required(self, test_client):
        """TEST: API-HLT-007-UT - 不需要認證"""
        # Even with API key middleware enabled, health should be accessible
        with patch.dict(os.environ, {'CONTAINER_APP_API_KEY': 'test-key'}):
            response = test_client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_health_check_cors_headers(self, test_client):
        """TEST: API-HLT-008-UT - CORS headers 存在"""
        response = test_client.get("/health", headers={"Origin": "https://example.com"})
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    @patch('src.main.datetime')
    def test_health_check_timestamp_mocked(self, mock_datetime, test_client):
        """TEST: API-HLT-009-UT - Mock 時間戳記測試"""
        # Mock datetime to return fixed time
        fixed_time = datetime(2025, 7, 30, 12, 0, 0)
        mock_datetime.utcnow.return_value = fixed_time
        mock_datetime.fromisoformat = datetime.fromisoformat
        
        response = test_client.get("/health")
        data = response.json()
        
        # Verify timestamps match mocked time
        expected_timestamp = "2025-07-30T12:00:00"
        assert expected_timestamp in data["timestamp"]
        assert expected_timestamp in data["data"]["timestamp"]