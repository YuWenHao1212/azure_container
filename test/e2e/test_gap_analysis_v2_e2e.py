"""
End-to-end tests for Index Calculation and Gap Analysis V2.

Tests:
- API-GAP-001-E2E: 完整工作流程測試
- API-GAP-002-E2E: 輕量級監控整合測試
- API-GAP-003-E2E: 部分結果支援驗證
- API-GAP-004-E2E: 真實數據綜合測試
"""

import asyncio
import json
import os
import sys
import time
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
os.environ['LIGHTWEIGHT_MONITORING'] = 'true'

from src.main import create_app
from src.services.openai_client import AzureOpenAIError


class TestGapAnalysisV2E2E:
    """End-to-end tests for Index Calculation and Gap Analysis V2."""

    @pytest.fixture
    def test_client(self):
        """Create test client with E2E configuration."""
        with (
            patch('src.core.config.get_settings'),
            patch('src.main.monitoring_service') as mock_monitoring,
            patch.dict(os.environ, {
                'MONITORING_ENABLED': 'true',
                'LIGHTWEIGHT_MONITORING': 'true',
                'ERROR_CAPTURE_ENABLED': 'true',
                'CONTAINER_APP_API_KEY': 'test-api-key'
            })
        ):
            # Configure monitoring mock
            mock_monitoring.track_event = Mock()
            mock_monitoring.track_error = Mock()
            mock_monitoring.track_metric = Mock()

            app = create_app()
            client = TestClient(app)
            client.monitoring = mock_monitoring
            return client

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
    def mock_e2e_services(self, mock_responses):
        """Create comprehensive mocks for E2E testing."""
        # Mock embedding client
        async def create_embeddings(texts):
            await asyncio.sleep(0.3)  # Simulate network delay
            return [[0.1 + i * 0.01] * 1536 for i in range(len(texts))]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings
        mock_embedding.close = AsyncMock()

        # Mock LLM client
        async def create_completion(*args, **kwargs):
            await asyncio.sleep(0.5)  # Simulate LLM delay
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

    # TEST: API-GAP-001-E2E
    @pytest.mark.e2e
    def test_complete_workflow(self, test_client, test_data, mock_e2e_services):
        """TEST: API-GAP-001-E2E - 完整工作流程測試.

        從請求到回應的完整流程驗證,使用真實數據驗證完整工作流程。
        """
        # Use realistic test data (500+ characters)
        large_resume = test_data["large_documents"]["10kb_resume"][:2000]  # Use first 2KB
        large_jd = test_data["large_documents"]["5kb_jd"][:1000]  # Use first 1KB

        # Mock all external services
        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_e2e_services["embedding"]),
            patch('src.services.llm_client.get_azure_llm_client',
                  return_value=mock_e2e_services["llm"])
        ):
                # Execute complete workflow
                start_time = time.time()

                response = test_client.post(
                    "/api/v1/index-cal-and-gap-analysis",
                    json={
                        "resume": large_resume,
                        "job_description": large_jd,
                        "keywords": [
                            "Python", "FastAPI", "Docker", "Kubernetes",
                            "AWS", "React", "PostgreSQL", "Redis"
                        ],
                        "language": "en"
                    },
                    headers={"X-API-Key": "test-api-key"}
                )

                total_time = time.time() - start_time

        # Verify successful completion
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify complete response structure
        result = data["data"]
        assert all(key in result for key in [
            "raw_similarity_percentage",
            "similarity_percentage",
            "keyword_coverage",
            "gap_analysis"
        ])

        # Verify gap analysis completeness
        gap = result["gap_analysis"]
        assert all(key in gap for key in [
            "CoreStrengths",
            "KeyGaps",
            "QuickImprovements",
            "OverallAssessment",
            "SkillSearchQueries"
        ])

        # Verify HTML formatting in gap analysis
        assert "<ol>" in gap["CoreStrengths"]
        assert "<li>" in gap["KeyGaps"]
        assert "<p>" in gap["OverallAssessment"]

        # Verify keyword coverage calculation
        coverage = result["keyword_coverage"]
        assert coverage["total_keywords"] == 8
        assert isinstance(coverage["covered_keywords"], list)
        assert isinstance(coverage["missed_keywords"], list)
        assert len(coverage["covered_keywords"]) + len(coverage["missed_keywords"]) == coverage["total_keywords"]

        # Verify performance
        assert total_time < 5.0, f"E2E workflow took {total_time:.2f}s, exceeding 5s limit"

        print("\nE2E Workflow Stats:")
        print(f"Total execution time: {total_time:.2f}s")
        print(
            f"Similarity scores: Raw={result['raw_similarity_percentage']}%, "
            f"Transformed={result['similarity_percentage']}%"
        )
        print(f"Keyword coverage: {coverage['coverage_percentage']}%")

    # TEST: API-GAP-002-E2E
    @pytest.mark.e2e
    def test_lightweight_monitoring_integration(self, test_client, test_data, mock_e2e_services):
        """TEST: API-GAP-002-E2E - 輕量級監控整合測試.

        驗證 LIGHTWEIGHT_MONITORING=true 監控正確記錄關鍵指標。
        """
        # Use standard test data
        valid_request = test_data["valid_test_data"]["standard_requests"][0]

        # Mock all external services
        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_e2e_services["embedding"]),
            patch('src.services.llm_client.get_azure_llm_client',
                  return_value=mock_e2e_services["llm"])
        ):
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

        # Verify monitoring events were tracked
        monitoring = test_client.monitoring

        # Check for key events
        track_event_calls = monitoring.track_event.call_args_list
        event_names = [call[0][0] for call in track_event_calls]

        # Verify expected events
        assert any("IndexCalAndGapAnalysisV2" in name for name in event_names)

        # Verify event properties
        for call in track_event_calls:
            event_name = call[0][0]
            if "IndexCalAndGapAnalysisV2Completed" in event_name:
                properties = call[1].get("properties", {})
                assert "processing_time_ms" in properties
                assert "version" in properties
                assert properties["version"] == "v2"
                break

        # Verify metrics tracked
        track_metric_calls = monitoring.track_metric.call_args_list
        if track_metric_calls:
            metric_names = [call[0][0] for call in track_metric_calls]
            assert any("processing_time" in name.lower() for name in metric_names)

    # TEST: API-GAP-003-E2E
    @pytest.mark.e2e
    def test_partial_result_support(self, test_client, test_data):
        """TEST: API-GAP-003-E2E - 部分結果支援驗證.

        驗證生產環境中部分失敗時的行為,實際場景的部分結果功能。
        """
        # Mock embedding service (successful)
        async def create_embeddings(texts):
            await asyncio.sleep(0.2)
            return [[0.1] * 1536 for _ in texts]

        mock_embedding = AsyncMock()
        mock_embedding.create_embeddings = create_embeddings
        mock_embedding.close = AsyncMock()

        # Mock LLM service (failing)
        async def create_completion_failing(*args, **kwargs):
            await asyncio.sleep(0.3)
            raise AzureOpenAIError("Gap analysis service temporarily unavailable")

        mock_llm = AsyncMock()
        mock_llm.chat.completions.create = create_completion_failing
        mock_llm.close = AsyncMock()

        # Use standard test data
        valid_request = test_data["valid_test_data"]["standard_requests"][0]

        # Execute with gap analysis failure
        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_embedding),
            patch('src.services.llm_client.get_azure_llm_client',
                  return_value=mock_llm),
            patch.dict(os.environ, {'ENABLE_PARTIAL_RESULTS': 'true'})
        ):
                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json={
                            "resume": valid_request["resume"],
                            "job_description": valid_request["job_description"],
                            "keywords": valid_request["keywords"]
                        },
                        headers={"X-API-Key": "test-api-key"}
                    )

        # Should still return 200 with partial results
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify partial result structure
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result

        # Gap analysis should be null or contain error info
        assert result.get("gap_analysis") is None or "error" in str(result.get("gap_analysis", "")).lower()

        # Should indicate partial result
        assert result.get("partial_result") is True or "warning" in result

        print("\nPartial Result Support:")
        print(f"Index calculation succeeded: {result['raw_similarity_percentage']}%")
        print("Gap analysis failed as expected")
        print(f"Partial result flag: {result.get('partial_result', False)}")

    # TEST: API-GAP-004-E2E
    @pytest.mark.e2e
    def test_real_data_comprehensive(self, test_client, test_data, mock_e2e_services):
        """TEST: API-GAP-004-E2E - 真實數據綜合測試.

        使用多樣化真實數據的綜合測試,驗證各種真實履歷和職缺的處理。
        """
        # Define test scenarios with different profiles
        test_scenarios = [
            {
                "name": "Junior Developer",
                "resume": """<article>
                    <h2>Junior Software Developer</h2>
                    <p>Recent computer science graduate with <strong>2 years</strong> of internship experience.</p>
                    <h3>Technical Skills</h3>
                    <ul>
                        <li>Languages: Python, JavaScript, Java</li>
                        <li>Web: HTML, CSS, React basics</li>
                        <li>Tools: Git, VS Code, Docker basics</li>
                    </ul>
                    <p>Eager to learn and grow in a professional environment. Completed several academic projects.</p>
                </article>""",
                "job_description": (
                    "Seeking a Junior Full Stack Developer to join our growing team. "
                    "Requirements include 1-3 years of experience with Python and JavaScript. "
                    "Knowledge of React, Docker, and cloud services is a plus. "
                    "We offer mentorship and learning opportunities for motivated individuals. "
                    "Must have strong problem-solving skills."
                ),
                "keywords": ["Python", "JavaScript", "React", "Docker", "Cloud"],
                "expected_coverage": 60  # Junior should match most basic requirements
            },
            {
                "name": "Senior Backend Specialist",
                "resume": test_data["multilingual_content"]["chinese_resume"],
                "job_description": (
                    "We need a Senior Backend Engineer with 5+ years of Python experience. "
                    "Must have expertise in FastAPI, microservices, and cloud platforms "
                    "(AWS/Azure). Experience with Docker, Kubernetes, and CI/CD pipelines "
                    "required. Knowledge of frontend technologies is a plus but not required."
                ),
                "keywords": ["Python", "FastAPI", "Microservices", "AWS", "Docker", "Kubernetes"],
                "expected_coverage": 50  # Backend specialist missing some DevOps skills
            },
            {
                "name": "Full Stack Expert",
                "resume": test_data["large_documents"]["10kb_resume"][:1500],
                "job_description": test_data["large_documents"]["5kb_jd"][:800],
                "keywords": ["Python", "React", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis", "CI/CD"],
                "expected_coverage": 75  # Expert should match most requirements
            }
        ]

        # Mock all external services
        with (
            patch('src.services.embedding_client.get_azure_embedding_client',
                  return_value=mock_e2e_services["embedding"]),
            patch('src.services.llm_client.get_azure_llm_client',
                  return_value=mock_e2e_services["llm"])
        ):
                # Test each scenario
                for scenario in test_scenarios:
                    print(f"\nTesting scenario: {scenario['name']}")

                    response = test_client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json={
                            "resume": scenario["resume"],
                            "job_description": scenario["job_description"],
                            "keywords": scenario["keywords"]
                        },
                        headers={"X-API-Key": "test-api-key"}
                    )

                    # Verify successful processing
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True

                    # Verify results make sense for the scenario
                    result = data["data"]
                    coverage = result["keyword_coverage"]["coverage_percentage"]

                    # Coverage should be within reasonable range
                    assert coverage >= scenario["expected_coverage"] - 20
                    assert coverage <= scenario["expected_coverage"] + 20

                    # Verify gap analysis provides relevant feedback
                    gap = result["gap_analysis"]
                    assert len(gap["CoreStrengths"]) > 0
                    assert len(gap["KeyGaps"]) > 0
                    assert len(gap["SkillSearchQueries"]) > 0

                    print(f"  - Similarity: {result['similarity_percentage']}%")
                    print(f"  - Coverage: {coverage}% (expected ~{scenario['expected_coverage']}%)")
                    print(f"  - Skills to develop: {len(gap['SkillSearchQueries'])}")

        print("\nAll scenarios processed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
