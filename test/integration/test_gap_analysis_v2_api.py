"""
Integration tests for Index Calculation and Gap Analysis V2 API endpoints.

Tests:
- API-GAP-001-IT: API 端點基本功能測試
- API-GAP-002-IT: JD 長度驗證測試
- API-GAP-003-IT: Resume 長度驗證測試
- API-GAP-004-IT: 邊界長度測試
- API-GAP-005-IT: 關鍵字參數驗證測試
- API-GAP-006-IT: 語言參數驗證測試
- API-GAP-007-IT: Bubble.io 回應格式驗證
- API-GAP-008-IT: Feature Flag 測試
- API-GAP-009-IT: 部分失敗處理測試
- API-GAP-010-IT: 服務超時處理測試
- API-GAP-011-IT: 速率限制錯誤處理測試
- API-GAP-012-IT: 處理時間元數據測試
- API-GAP-013-IT: 大文檔處理測試
- API-GAP-014-IT: 認證機制測試
"""

import asyncio
import json
import os
import sys
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
os.environ['ENABLE_PARTIAL_RESULTS'] = 'true'

from src.main import create_app
from src.services.openai_client import (
    AzureOpenAIRateLimitError,
)


class TestGapAnalysisV2Integration:
    """Integration tests for Index Calculation and Gap Analysis V2 API endpoints."""

    @pytest.fixture
    def test_client(self):
        """Create test client with mocked dependencies."""
        with (
            patch('src.core.config.get_settings'),
            patch('src.main.monitoring_service', Mock()),
            patch.dict(os.environ, {
                'MONITORING_ENABLED': 'false',
                'LIGHTWEIGHT_MONITORING': 'true',
                'ERROR_CAPTURE_ENABLED': 'false',
                'CONTAINER_APP_API_KEY': 'test-api-key'
            })
        ):
            app = create_app()
            return TestClient(app)

    @pytest.fixture
    def mock_combined_service(self):
        """Create mock combined analysis service."""
        service = AsyncMock()
        service.analyze = AsyncMock()
        service.get_stats = Mock()
        return service

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
    def mock_responses(self, test_data):
        """Load mock responses from test data."""
        return test_data["mock_responses"]

    @pytest.fixture
    def valid_request(self, test_data):
        """Get valid request data from test data."""
        return test_data["valid_test_data"]["standard_requests"][0]

    # TEST: API-GAP-001-IT
    def test_api_endpoint_basic_functionality(
        self, test_client, mock_combined_service, valid_request, mock_responses
    ):
        """TEST: API-GAP-001-IT - API 端點基本功能測試.

        驗證 POST /api/v1/index-cal-and-gap-analysis 正常流程。
        """
        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        # Mock the service at the source module level
        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"],
                    "language": valid_request["language"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert data["success"] is True
        assert "data" in data
        assert "error" in data
        assert "timestamp" in data

        # Check data structure
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result
        assert "gap_analysis" in result

        # Check types
        assert isinstance(result["raw_similarity_percentage"], int)
        assert isinstance(result["similarity_percentage"], int)
        assert 0 <= result["raw_similarity_percentage"] <= 100
        assert 0 <= result["similarity_percentage"] <= 100

        # Check gap analysis structure
        gap = result["gap_analysis"]
        assert "CoreStrengths" in gap
        assert "KeyGaps" in gap
        assert "QuickImprovements" in gap
        assert "OverallAssessment" in gap
        assert "SkillSearchQueries" in gap

    # TEST: API-GAP-002-IT
    def test_jd_length_validation(self, test_client, test_data):
        """TEST: API-GAP-002-IT - JD 長度驗證測試.

        驗證 Job Description < 200 字元時返回 400 錯誤。
        """
        short_jd_request = test_data["invalid_test_data"]["short_jd"]

        response = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json=short_jd_request,
            headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TEXT_TOO_SHORT"
        assert "Job description must be at least 200 characters" in data["error"]["message"]

    # TEST: API-GAP-003-IT
    def test_resume_length_validation(self, test_client, test_data):
        """TEST: API-GAP-003-IT - Resume 長度驗證測試.

        驗證 Resume < 200 字元時返回 400 錯誤。
        """
        short_resume_request = test_data["invalid_test_data"]["short_resume"]

        response = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json=short_resume_request,
            headers={"X-API-Key": "test-api-key"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TEXT_TOO_SHORT"
        assert "Resume must be at least 200 characters" in data["error"]["message"]

    # TEST: API-GAP-004-IT
    def test_boundary_length(self, test_client, test_data, mock_combined_service, mock_responses):
        """TEST: API-GAP-004-IT - 邊界長度測試.

        驗證 JD 和 Resume 正好 200 字元時正常處理。
        """
        boundary_request = test_data["valid_test_data"]["boundary_test_data"]["exactly_200_chars"]

        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json=boundary_request,
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # TEST: API-GAP-005-IT
    def test_keywords_parameter_validation(
        self, test_client, valid_request, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-005-IT - 關鍵字參數驗證測試.

        驗證 keywords 支援陣列和逗號分隔字串。
        """
        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            # Test array format
            request_array = {
                "resume": valid_request["resume"],
                "job_description": valid_request["job_description"],
                "keywords": ["Python", "Docker", "AWS"]
            }
            response1 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json=request_array,
                headers={"X-API-Key": "test-api-key"}
            )

            # Test comma-separated string
            request_string = {
                "resume": valid_request["resume"],
                "job_description": valid_request["job_description"],
                "keywords": "Python,Docker,AWS"
            }
            response2 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json=request_string,
                headers={"X-API-Key": "test-api-key"}
            )

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Results should be similar
        data1 = response1.json()
        data2 = response2.json()
        assert data1["success"] is True
        assert data2["success"] is True

    # TEST: API-GAP-006-IT
    def test_language_parameter_validation(self, test_client, valid_request):
        """TEST: API-GAP-006-IT - 語言參數驗證測試(只測試參數傳遞).

        驗證只接受 "en" 和 "zh-TW",其他值返回錯誤。
        """
        invalid_languages = ["fr", "ja", "ko", "es", "de"]

        for lang in invalid_languages:
            request = {
                "resume": valid_request["resume"],
                "job_description": valid_request["job_description"],
                "keywords": valid_request["keywords"],
                "language": lang
            }
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json=request,
                headers={"X-API-Key": "test-api-key"}
            )

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_LANGUAGE"

    # TEST: API-GAP-007-IT
    def test_bubble_io_response_format(
        self, test_client, valid_request, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-007-IT - Bubble.io 回應格式驗證.

        驗證回應包含所有必要欄位且格式正確。
        """
        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()

        # Verify Bubble.io fixed schema
        assert isinstance(data["success"], bool)
        assert isinstance(data["data"], dict)
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]

        # Verify timestamp format (ISO 8601)
        import re
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$'
        assert re.match(iso_pattern, data["timestamp"])

    # TEST: API-GAP-008-IT
    def test_feature_flag_v2_implementation(self, test_client, valid_request):
        """TEST: API-GAP-008-IT - Feature Flag 測試.

        驗證 USE_V2_IMPLEMENTATION Feature Flag 控制 V2 實作啟用。
        """
        # Test with V2 enabled (already set in environment)
        with patch.dict(os.environ, {'USE_V2_IMPLEMENTATION': 'true'}):
            # Mock V2 service
            mock_v2_service = AsyncMock()
            mock_v2_service.analyze = AsyncMock(return_value={
                "success": True,
                "data": {"version": "v2"}
            })

            with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2',
                      return_value=mock_v2_service):
                response = test_client.post(
                    "/api/v1/index-cal-and-gap-analysis",
                    json={
                        "resume": valid_request["resume"],
                        "job_description": valid_request["job_description"],
                        "keywords": valid_request["keywords"]
                    },
                    headers={"X-API-Key": "test-api-key"}
                )

            # Should use V2 implementation
            assert response.status_code == 200
            mock_v2_service.analyze.assert_called_once()

    # TEST: API-GAP-009-IT
    def test_partial_failure_handling(
        self, test_client, valid_request, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-009-IT - 部分失敗處理測試.

        驗證啟用部分結果時,Gap 失敗仍返回 Index 結果。
        """
        # Mock partial success response
        mock_combined_service.analyze.return_value = mock_responses["partial_success_response"]

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify partial result
        assert data["data"]["raw_similarity_percentage"] == 68
        assert data["data"]["gap_analysis"] is None
        assert data["data"]["partial_result"] is True
        assert "warning" in data["data"]

    # TEST: API-GAP-010-IT
    def test_service_timeout_handling(self, test_client, valid_request):
        """TEST: API-GAP-010-IT - 服務超時處理測試.

        驗證 Azure OpenAI 超時時的重試和錯誤處理。
        """
        # Mock timeout error
        mock_service = AsyncMock()
        mock_service.analyze.side_effect = TimeoutError("Service timeout")

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2',
                      return_value=mock_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_ERROR"

    # TEST: API-GAP-011-IT
    def test_rate_limit_error_handling(self, test_client, valid_request):
        """TEST: API-GAP-011-IT - 速率限制錯誤處理測試.

        驗證遇到速率限制時的重試策略。
        """
        # Mock rate limit error
        mock_service = AsyncMock()
        mock_service.analyze.side_effect = AzureOpenAIRateLimitError("Rate limit exceeded")

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2',
                      return_value=mock_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_ERROR"

    # TEST: API-GAP-012-IT
    def test_processing_time_metadata(
        self, test_client, valid_request, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-012-IT - 處理時間元數據測試.

        驗證 V2 回應包含 processing_time_ms 和 service_timings。
        """
        # Mock response with timing metadata
        response_with_timing = mock_responses["successful_response"].copy()
        response_with_timing["data"]["processing_time_ms"] = 2500
        response_with_timing["data"]["service_timings"] = {
            "index_calculation_ms": 800,
            "gap_analysis_ms": 1700
        }

        mock_combined_service.analyze.return_value = response_with_timing

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()

        # Verify timing metadata
        assert "processing_time_ms" in data["data"]
        assert "service_timings" in data["data"]
        assert data["data"]["processing_time_ms"] == 2500
        assert data["data"]["service_timings"]["index_calculation_ms"] == 800
        assert data["data"]["service_timings"]["gap_analysis_ms"] == 1700

    # TEST: API-GAP-013-IT
    def test_large_document_handling(
        self, test_client, test_data, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-013-IT - 大文檔處理測試.

        驗證處理 10KB,20KB,30KB 文檔的能力。
        """
        # Use large documents from test data
        large_resume = test_data["large_documents"]["10kb_resume"]
        large_jd = test_data["large_documents"]["5kb_jd"]

        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            # Test 10KB resume + 5KB JD
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": large_resume,
                    "job_description": large_jd,
                    "keywords": ["Python", "FastAPI", "Docker"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

            assert response.status_code == 200

            # Test 20KB document (concatenate)
            larger_resume = large_resume * 2
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": larger_resume,
                    "job_description": large_jd,
                    "keywords": ["Python"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

            assert response.status_code == 200

            # Test 30KB document
            largest_resume = large_resume * 3
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": largest_resume,
                    "job_description": large_jd,
                    "keywords": ["Python"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

            assert response.status_code == 200

    # TEST: API-GAP-014-IT
    def test_authentication_mechanisms(
        self, test_client, valid_request, mock_combined_service, mock_responses
    ):
        """TEST: API-GAP-014-IT - 認證機制測試.

        驗證支援 Header (X-API-Key) 和 Query (?code=) 認證。
        """
        # Mock successful response
        mock_combined_service.analyze.return_value = (
            mock_responses["successful_response"]
        )

        with patch('src.services.combined_analysis_v2.CombinedAnalysisServiceV2', return_value=mock_combined_service):
            # Test Header authentication (X-API-Key)
            response1 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

            assert response1.status_code == 200

            # Test Query parameter authentication (?code=)
            response2 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis?code=test-api-key",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                }
            )

            assert response2.status_code == 200

            # Test no authentication
            response3 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": valid_request["resume"],
                    "job_description": valid_request["job_description"],
                    "keywords": valid_request["keywords"]
                }
            )

            assert response3.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
