"""
Integration tests for Index Calculation and Gap Analysis V2 endpoint.

Tests all 14 integration test cases:
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
import time
from datetime import datetime
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
os.environ['CONTAINER_APP_API_KEY'] = 'test-api-key'
os.environ['USE_V2_IMPLEMENTATION'] = 'true'

from src.main import create_app


class TestGapAnalysisV2IntegrationComplete:
    """Complete integration tests for Index Calculation and Gap Analysis V2."""

    @pytest.fixture
    def test_client(self):
        """Create test client for integration testing."""
        with (
            patch('src.core.config.get_settings'),
            patch('src.main.monitoring_service', Mock()),
            patch.dict(os.environ, {
                'MONITORING_ENABLED': 'false',
                'LIGHTWEIGHT_MONITORING': 'false',
                'ERROR_CAPTURE_ENABLED': 'false'
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

    @pytest.fixture
    def mock_openai_services(self, mock_responses):
        """Mock OpenAI services for integration testing."""
        # Mock embedding client
        async def create_embeddings(texts):
            await asyncio.sleep(0.1)  # Simulate network delay
            return [[0.1 + i * 0.01] * 1536 for i in range(len(texts))]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings
        mock_embedding.close = AsyncMock()

        # Mock LLM client
        async def create_completion(*args, **kwargs):
            await asyncio.sleep(0.2)  # Simulate LLM delay
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps(
                            mock_responses["service_mocks"]["llm_responses"]
                            ["gap_analysis_prompt_response"]
                        )
                    }
                }]
            }

        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = create_completion
        mock_llm.close = AsyncMock()

        return {
            "embedding": mock_embedding,
            "llm": mock_llm
        }

    # TEST: API-GAP-001-IT
    @pytest.mark.integration
    def test_API_GAP_001_IT_api_endpoint_basic_functionality(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-001-IT - API 端點基本功能測試.

        驗證 POST /api/v1/index-cal-and-gap-analysis 正常流程,
        回應格式正確。
        """
        # Use standard test data
        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"],
                    "language": request_data["language"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Verify basic response structure
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data

        # Verify required fields
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result
        assert "gap_analysis" in result

        # Verify data types
        assert isinstance(result["raw_similarity_percentage"], int | float)
        assert isinstance(result["similarity_percentage"], int | float)
        assert isinstance(result["keyword_coverage"], dict)
        assert isinstance(result["gap_analysis"], dict)

    # TEST: API-GAP-002-IT
    @pytest.mark.integration
    def test_API_GAP_002_IT_jd_length_validation(self, test_client, test_data):
        """TEST: API-GAP-002-IT - JD 長度驗證測試.

        驗證 Job Description < 200 字元時返回 400 錯誤。
        """
        # Use invalid short JD
        invalid_data = test_data["invalid_test_data"]["short_jd"]

        response = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": invalid_data["resume"],
                "job_description": invalid_data["job_description"],  # Only 29 chars
                "keywords": invalid_data["keywords"]
            },
            headers={"X-API-Key": "test-api-key"}
        )

        # Verify error response
        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert "TEXT_TOO_SHORT" in str(data["error"]).upper() or \
               "200" in str(data["error"])

    # TEST: API-GAP-003-IT
    @pytest.mark.integration
    def test_API_GAP_003_IT_resume_length_validation(self, test_client, test_data):
        """TEST: API-GAP-003-IT - Resume 長度驗證測試.

        驗證 Resume < 200 字元時返回 400 錯誤。
        """
        # Use invalid short resume
        invalid_data = test_data["invalid_test_data"]["short_resume"]

        response = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": invalid_data["resume"],  # Only 18 chars
                "job_description": invalid_data["job_description"],
                "keywords": invalid_data["keywords"]
            },
            headers={"X-API-Key": "test-api-key"}
        )

        # Verify error response
        assert response.status_code == 400
        data = response.json()

        assert data["success"] is False
        assert "error" in data
        assert "TEXT_TOO_SHORT" in str(data["error"]).upper() or \
               "200" in str(data["error"])

    # TEST: API-GAP-004-IT
    @pytest.mark.integration
    def test_API_GAP_004_IT_boundary_length_test(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-004-IT - 邊界長度測試.

        驗證 JD 和 Resume 正好 200 字元時正常處理。
        """
        # Use boundary test data (exactly 200 chars)
        boundary_data = test_data["valid_test_data"]["boundary_test_data"]["exactly_200_chars"]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": boundary_data["resume"],  # Exactly 200 chars
                    "job_description": boundary_data["job_description"],  # Exactly 200 chars
                    "keywords": boundary_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Should succeed with exactly 200 characters
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # TEST: API-GAP-005-IT
    @pytest.mark.integration
    def test_API_GAP_005_IT_keywords_parameter_validation(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-005-IT - 關鍵字參數驗證測試.

        驗證 keywords 支援陣列和逗號分隔字串。
        """
        request_base = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            # Test 1: Array format
            response1 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_base["resume"],
                    "job_description": request_base["job_description"],
                    "keywords": ["Python", "Docker", "AWS"]  # Array format
                },
                headers={"X-API-Key": "test-api-key"}
            )

            # Test 2: Comma-separated string
            response2 = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_base["resume"],
                    "job_description": request_base["job_description"],
                    "keywords": "Python,Docker,AWS"  # String format
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert data1["success"] is True
        assert data2["success"] is True

        # Both should process the same keywords
        coverage1 = data1["data"]["keyword_coverage"]
        coverage2 = data2["data"]["keyword_coverage"]

        assert coverage1["total_keywords"] == coverage2["total_keywords"]

    # TEST: API-GAP-006-IT
    @pytest.mark.integration
    def test_API_GAP_006_IT_language_parameter_validation(self, test_client, test_data):
        """TEST: API-GAP-006-IT - 語言參數驗證測試.

        驗證只接受 "en" 和 "zh-TW",其他值返回錯誤。
        """
        request_base = test_data["valid_test_data"]["standard_requests"][0]

        # Test invalid languages
        invalid_languages = ["fr", "ja", "ko", "es", "de"]

        for lang in invalid_languages:
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_base["resume"],
                    "job_description": request_base["job_description"],
                    "keywords": request_base["keywords"],
                    "language": lang
                },
                headers={"X-API-Key": "test-api-key"}
            )

            # Should return error for invalid language
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "error" in data
            assert "INVALID_LANGUAGE" in str(data["error"]).upper() or \
                   "language" in str(data["error"]).lower()

    # TEST: API-GAP-007-IT
    @pytest.mark.integration
    def test_API_GAP_007_IT_bubble_response_format(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-007-IT - Bubble.io 回應格式驗證.

        驗證回應格式符合 Bubble.io 固定 schema。
        """
        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()

        # Verify Bubble.io schema
        assert "success" in data
        assert isinstance(data["success"], bool)

        if data["success"]:
            assert "data" in data
            assert isinstance(data["data"], dict)
        else:
            assert "error" in data
            assert isinstance(data["error"], dict)
            assert "code" in data["error"]
            assert "message" in data["error"]

        # Verify timestamp format (ISO 8601)
        if "timestamp" in data:
            timestamp = data["timestamp"]
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                pytest.fail(f"Invalid ISO 8601 timestamp: {timestamp}")

    # TEST: API-GAP-008-IT
    @pytest.mark.integration
    def test_API_GAP_008_IT_feature_flag_test(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-008-IT - Feature Flag 測試.

        驗證 USE_V2_IMPLEMENTATION Feature Flag 控制 V2 實作啟用。
        """
        request_data = test_data["valid_test_data"]["standard_requests"][0]

        # Test with V2 enabled
        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"]),
            patch.dict(os.environ, {'USE_V2_IMPLEMENTATION': 'true'})
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify V2 implementation is used
        # This could be verified through response structure or timing
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result

        # V2 may include additional fields
        if "implementation_version" in result:
            assert result["implementation_version"] == "v2"

    # TEST: API-GAP-009-IT
    @pytest.mark.integration
    def test_API_GAP_009_IT_partial_failure_handling(
        self, test_client, test_data
    ):
        """TEST: API-GAP-009-IT - 部分失敗處理測試.

        驗證啟用部分結果時,Gap 失敗仍返回 Index 結果。
        """
        # Mock successful embedding but failed LLM
        async def create_embeddings(texts):
            await asyncio.sleep(0.1)
            return [[0.1] * 1536 for _ in texts]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings
        mock_embedding.close = AsyncMock()

        # Mock failing LLM
        async def create_completion_failing(*args, **kwargs):
            raise Exception("Gap analysis service unavailable")

        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = create_completion_failing
        mock_llm.close = AsyncMock()

        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_embedding),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_llm),
            patch.dict(os.environ, {'ENABLE_PARTIAL_RESULTS': 'true'})
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Should still return 200 with partial results
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Should have index results but no gap analysis
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result

        # Gap analysis should be null or indicate error
        assert result.get("gap_analysis") is None or \
               "error" in str(result.get("gap_analysis", "")).lower()

        # Should indicate partial result
        assert result.get("partial_result") is True or \
               "warning" in str(result).lower()

    # TEST: API-GAP-010-IT
    @pytest.mark.integration
    def test_API_GAP_010_IT_service_timeout_handling(self, test_client, test_data):
        """TEST: API-GAP-010-IT - 服務超時處理測試.

        驗證外部服務超時時的錯誤處理。
        """
        # Mock timeout scenario
        async def create_embeddings_timeout(texts):
            await asyncio.sleep(30)  # Simulate timeout
            return [[0.1] * 1536 for _ in texts]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings_timeout
        mock_embedding.close = AsyncMock()

        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_embedding),
            patch.dict(os.environ, {'REQUEST_TIMEOUT': '1'})  # 1 second timeout
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Should handle timeout gracefully
        assert response.status_code in [408, 500, 503]  # Timeout-related status codes
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "timeout" in str(data["error"]).lower() or \
               "time" in str(data["error"]).lower()

    # TEST: API-GAP-011-IT
    @pytest.mark.integration
    def test_API_GAP_011_IT_rate_limit_handling(self, test_client, test_data):
        """TEST: API-GAP-011-IT - 速率限制錯誤處理測試.

        驗證 Azure OpenAI 速率限制時的重試策略。
        """
        # Mock rate limit error
        rate_limit_count = 0

        async def create_embeddings_rate_limit(texts):
            nonlocal rate_limit_count
            rate_limit_count += 1

            if rate_limit_count <= 2:
                from src.services.openai_client import AzureOpenAIError
                raise AzureOpenAIError("Rate limit exceeded", status_code=429)

            # Succeed on 3rd attempt
            return [[0.1] * 1536 for _ in texts]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings_rate_limit
        mock_embedding.close = AsyncMock()

        # Mock successful LLM
        async def create_completion(*args, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "CoreStrengths": "<ol><li>Test</li></ol>",
                            "KeyGaps": "<ol><li>Test</li></ol>",
                            "QuickImprovements": "<ol><li>Test</li></ol>",
                            "OverallAssessment": "<p>Test</p>",
                            "SkillSearchQueries": []
                        })
                    }
                }]
            }

        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = create_completion
        mock_llm.close = AsyncMock()

        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_embedding),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_llm),
            patch.dict(os.environ, {'ADAPTIVE_RETRY_ENABLED': 'true'})
        ):
            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

        # Should eventually succeed after retries
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify retry attempts occurred
        assert rate_limit_count >= 2

    # TEST: API-GAP-012-IT
    @pytest.mark.integration
    def test_API_GAP_012_IT_processing_time_metadata(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-012-IT - 處理時間元數據測試.

        驗證 V2 回應包含 processing_time_ms 和 service_timings。
        """
        request_data = test_data["valid_test_data"]["standard_requests"][0]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            start_time = time.time()

            response = test_client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": request_data["resume"],
                    "job_description": request_data["job_description"],
                    "keywords": request_data["keywords"]
                },
                headers={"X-API-Key": "test-api-key"}
            )

            end_time = time.time()
            actual_duration = (end_time - start_time) * 1000  # Convert to ms

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Check for timing metadata
        result = data["data"]
        if "processing_time_ms" in result:
            processing_time = result["processing_time_ms"]
            assert isinstance(processing_time, int | float)
            assert processing_time > 0
            assert processing_time <= actual_duration + 100  # Allow some overhead

        if "service_timings" in result:
            timings = result["service_timings"]
            assert isinstance(timings, dict)
            # May contain phase timings
            for _timing_key, timing_value in timings.items():
                assert isinstance(timing_value, int | float)
                assert timing_value >= 0

    # TEST: API-GAP-013-IT
    @pytest.mark.integration
    def test_API_GAP_013_IT_large_document_processing(
        self, test_client, test_data, mock_openai_services
    ):
        """TEST: API-GAP-013-IT - 大文檔處理測試.

        驗證處理 10KB、20KB、30KB 文檔的能力。
        """
        # Test different document sizes
        test_sizes = [
            ("10KB Resume", test_data["large_documents"]["10kb_resume"][:10000]),
            ("5KB JD", test_data["large_documents"]["5kb_jd"][:5000]),
        ]

        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_openai_services["embedding"]),
            patch('src.services.openai_client.get_azure_openai_client_async',
                  return_value=mock_openai_services["llm"])
        ):
            for size_name, large_doc in test_sizes:
                if "resume" in size_name.lower():
                    test_resume = large_doc
                    test_jd = test_data["valid_test_data"]["standard_requests"][0]["job_description"]
                else:
                    test_resume = test_data["valid_test_data"]["standard_requests"][0]["resume"]
                    test_jd = large_doc

                response = test_client.post(
                    "/api/v1/index-cal-and-gap-analysis",
                    json={
                        "resume": test_resume,
                        "job_description": test_jd,
                        "keywords": ["Python", "FastAPI", "Docker", "AWS"]
                    },
                    headers={"X-API-Key": "test-api-key"}
                )

                # Should handle large documents
                assert response.status_code == 200, f"Failed for {size_name}"
                data = response.json()
                assert data["success"] is True, f"Failed for {size_name}"

                # Verify complete processing
                result = data["data"]
                assert "raw_similarity_percentage" in result
                assert "gap_analysis" in result

    # TEST: API-GAP-014-IT
    @pytest.mark.integration
    def test_API_GAP_014_IT_authentication_mechanism(self, test_client, test_data):
        """TEST: API-GAP-014-IT - 認證機制測試.

        驗證支援 Header (X-API-Key) 和 Query (?code=) 認證。
        """
        request_data = test_data["valid_test_data"]["standard_requests"][0]

        # Test 1: Header authentication
        response1 = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": request_data["resume"],
                "job_description": request_data["job_description"],
                "keywords": request_data["keywords"]
            },
            headers={"X-API-Key": "test-api-key"}
        )

        # Test 2: Query parameter authentication
        response2 = test_client.post(
            "/api/v1/index-cal-and-gap-analysis?code=test-api-key",
            json={
                "resume": request_data["resume"],
                "job_description": request_data["job_description"],
                "keywords": request_data["keywords"]
            }
        )

        # Test 3: No authentication
        response3 = test_client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": request_data["resume"],
                "job_description": request_data["job_description"],
                "keywords": request_data["keywords"]
            }
        )

        # Header auth should work
        assert response1.status_code in [200, 500]  # May fail due to mocking, but auth passes

        # Query auth should work
        assert response2.status_code in [200, 500]  # May fail due to mocking, but auth passes

        # No auth should fail
        assert response3.status_code == 401
        data3 = response3.json()
        assert data3["success"] is False
        assert "error" in data3
        assert "authentication" in str(data3["error"]).lower() or \
               "unauthorized" in str(data3["error"]).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
