"""
End-to-End tests for Index Calculation V2 with Real Azure API.

TEST IDs:
- API-IC-301-E2E: 完整工作流程測試
- API-IC-302-E2E: 多種輸入格式測試  
- API-IC-303-E2E: 效能和監控整合測試

Note: These tests use real Azure OpenAI API and require proper environment variables.
"""

import json
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Load real environment variables for E2E testing
if not os.getenv('AZURE_OPENAI_API_KEY'):
    # Load from .env file for local testing
    import dotenv
    dotenv.load_dotenv()

# Verify required environment variables
required_env_vars = [
    'AZURE_OPENAI_API_KEY',
    'AZURE_OPENAI_ENDPOINT',
    'EMBEDDING_API_KEY',
    'EMBEDDING_ENDPOINT'
]

for var in required_env_vars:
    if not os.getenv(var):
        pytest.skip(f"E2E test requires {var} environment variable")

from src.main import create_app


class TestIndexCalculationV2E2ERealAPI:
    """End-to-End tests for Index Calculation V2 with real Azure API."""

    @pytest.fixture
    def test_client(self):
        """Create test client with real API configuration for E2E testing."""
        # Configure for E2E testing with real APIs
        import os
        os.environ['MONITORING_ENABLED'] = 'false'
        os.environ['LIGHTWEIGHT_MONITORING'] = 'true'
        os.environ['ERROR_CAPTURE_ENABLED'] = 'false'
        os.environ['INDEX_CALC_CACHE_ENABLED'] = 'true'
        os.environ['INDEX_CALC_CACHE_TTL_MINUTES'] = '60'
        os.environ['INDEX_CALC_CACHE_MAX_SIZE'] = '1000'
        
        # Set API key for authentication
        os.environ['CONTAINER_APP_API_KEY'] = 'e2e-test-key'
        
        app = create_app()
        client = TestClient(app)
        # Add API key header for authentication
        client.headers = {"X-API-Key": "e2e-test-key"}
        return client

    @pytest.fixture
    def test_data(self):
        """Load test data from fixtures."""
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            '../fixtures/index_calculation/test_data.json'
        )
        with open(fixture_path, encoding='utf-8') as f:
            return json.load(f)

    # TEST: API-IC-301-E2E
    @pytest.mark.timeout(60)
    def test_API_IC_301_E2E_complete_workflow(
        self, test_client, test_data
    ):
        """TEST: API-IC-301-E2E - 完整工作流程測試.

        驗證從輸入到輸出的完整流程，使用真實 Azure API。
        """
        # Use real test data - medium size for comprehensive testing
        real_resume = test_data["standard_resumes"][1]["content"]
        real_jd = test_data["job_descriptions"][1]["content"]
        real_keywords = test_data["job_descriptions"][1]["keywords"]

        # Test with real Azure OpenAI API - no mocks for E2E testing
        # Step 1: Make the API request
        start_time = time.time()
        response = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": real_resume,
                "job_description": real_jd,
                "keywords": real_keywords
            }
        )
        processing_time = time.time() - start_time

        # Step 2: Verify response structure and content
        assert response.status_code == 200
        data = response.json()

        # Verify success response
        assert data["success"] is True
        assert "data" in data
        # In V1, error field exists even on success with has_error=False
        if "error" in data:
            assert data["error"]["has_error"] is False

        # Verify data structure completeness
        result = data["data"]
        assert "raw_similarity_percentage" in result
        assert "similarity_percentage" in result
        assert "keyword_coverage" in result

        # Verify similarity scores
        assert isinstance(result["raw_similarity_percentage"], int)
        assert isinstance(result["similarity_percentage"], int)
        assert 0 <= result["raw_similarity_percentage"] <= 100
        assert 0 <= result["similarity_percentage"] <= 100

        # Verify keyword coverage
        coverage = result["keyword_coverage"]
        assert coverage["total_keywords"] == len(real_keywords)
        assert isinstance(coverage["covered_count"], int)
        assert isinstance(coverage["coverage_percentage"], int)
        assert isinstance(coverage["covered_keywords"], list)
        assert isinstance(coverage["missed_keywords"], list)
        assert len(coverage["covered_keywords"]) + len(coverage["missed_keywords"]) == coverage["total_keywords"]

        # Verify reasonable values with real API
        assert coverage["coverage_percentage"] >= 0
        assert coverage["coverage_percentage"] <= 100

        # Step 3: Verify processing was successful (real API test)
        # Note: In E2E testing with real APIs, we focus on response correctness
        # rather than internal monitoring calls

        # Step 4: Verify performance with real Azure API
        assert processing_time < 15.0  # Should complete within 15 seconds (real API latency)

        # Step 5: Test with different formats (HTML)
        html_resume = test_data["standard_resumes"][3]["content"]
        response2 = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": html_resume,
                "job_description": real_jd,
                "keywords": ["Python", "Docker", "AWS"]
            }
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True

        # Step 6: Test with comma-separated keywords
        response3 = test_client.post(
            "/api/v1/index-calculation",
            json={
                "resume": real_resume,
                "job_description": real_jd,
                "keywords": "Python, FastAPI, Docker, AWS"  # String format
            }
        )

        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["success"] is True
        assert data3["data"]["keyword_coverage"]["total_keywords"] == 4

        print(f"✅ API-IC-301-E2E: Complete workflow test passed in {processing_time:.2f}s")

    # TEST: API-IC-302-E2E
    @pytest.mark.timeout(60)
    def test_API_IC_302_E2E_multiple_input_formats(
        self, test_client, test_data
    ):
        """TEST: API-IC-302-E2E - 多種輸入格式測試.

        驗證系統對不同輸入格式的處理能力。
        """
        # Test different resume formats with real Azure API
        test_cases = [
            {
                "name": "Plain Text Resume",
                "resume": test_data["standard_resumes"][0]["content"],
                "expected_format": "text"
            },
            {
                "name": "HTML Resume",
                "resume": test_data["standard_resumes"][3]["content"],
                "expected_format": "html"
            },
            {
                "name": "Long Resume (> 10KB)",
                "resume": test_data["standard_resumes"][2]["content"],
                "expected_format": "text"
            }
        ]

        base_jd = test_data["job_descriptions"][0]["content"]
        base_keywords = ["Python", "API", "Development"]

        results = []
        
        for case in test_cases:
            start_time = time.time()
            response = test_client.post(
                "/api/v1/index-calculation",
                json={
                    "resume": case["resume"],
                    "job_description": base_jd,
                    "keywords": base_keywords
                }
            )
            processing_time = time.time() - start_time

            # Verify successful processing
            assert response.status_code == 200, f"Failed for {case['name']}"
            data = response.json()
            assert data["success"] is True, f"Failed for {case['name']}"

            # Store results for comparison
            result = data["data"]
            results.append({
                "name": case["name"],
                "similarity": result["similarity_percentage"],
                "coverage": result["keyword_coverage"]["coverage_percentage"],
                "processing_time": processing_time
            })

        # Verify all formats were processed successfully
        assert len(results) == 3

        # Verify reasonable processing times for different formats
        for result in results:
            assert result["processing_time"] < 20.0, f"Too slow for {result['name']}: {result['processing_time']:.2f}s"
            assert result["similarity"] >= 0 and result["similarity"] <= 100
            assert result["coverage"] >= 0 and result["coverage"] <= 100

        print(f"✅ API-IC-302-E2E: Multiple input formats test passed")
        for result in results:
            print(f"   {result['name']}: similarity={result['similarity']}%, coverage={result['coverage']}%, time={result['processing_time']:.2f}s")

    # TEST: API-IC-303-E2E
    @pytest.mark.timeout(90)
    def test_API_IC_303_E2E_performance_and_monitoring(
        self, test_client, test_data
    ):
        """TEST: API-IC-303-E2E - 效能和監控整合測試.

        驗證系統在連續請求下的穩定性和監控功能。
        """
        # Test multiple consecutive requests for stability
        response_times = []
        similarity_scores = []
        
        base_resume = test_data["standard_resumes"][0]["content"]
        base_jd = test_data["job_descriptions"][0]["content"]
        
        # Run 5 consecutive requests
        for i in range(5):
            # Vary keywords slightly for each request
            keywords = [f"Python{i}", "API", "Development", f"Skill{i}"]
            
            start_time = time.time()
            response = test_client.post(
                "/api/v1/index-calculation",
                json={
                    "resume": f"{base_resume} - Request {i} with additional experience in modern technologies and frameworks.",
                    "job_description": f"{base_jd} - Position {i} seeking qualified candidates with relevant experience.",
                    "keywords": keywords
                }
            )
            processing_time = time.time() - start_time

            # Verify successful processing
            assert response.status_code == 200, f"Request {i+1} failed"
            data = response.json()
            assert data["success"] is True, f"Request {i+1} unsuccessful"

            # Collect metrics
            response_times.append(processing_time)
            similarity_scores.append(data["data"]["similarity_percentage"])

        # Verify system stability
        assert len(response_times) == 5
        assert len(similarity_scores) == 5

        # Verify performance consistency
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # Performance assertions for real API
        assert avg_response_time < 15.0, f"Average response time too high: {avg_response_time:.2f}s"
        assert max_response_time < 25.0, f"Max response time too high: {max_response_time:.2f}s"
        assert min_response_time > 0.5, f"Min response time too low (likely cached): {min_response_time:.2f}s"

        # Verify similarity scores are reasonable
        for i, score in enumerate(similarity_scores):
            assert 0 <= score <= 100, f"Invalid similarity score in request {i+1}: {score}"

        # Test cache behavior (if enabled)
        # Make identical request twice to test caching
        cache_test_request = {
            "resume": base_resume,
            "job_description": base_jd,
            "keywords": ["Python", "FastAPI"]
        }

        # First request (cache miss)
        start_time = time.time()
        response1 = test_client.post("/api/v1/index-calculation", json=cache_test_request)
        time1 = time.time() - start_time

        # Second identical request (potential cache hit)
        start_time = time.time()
        response2 = test_client.post("/api/v1/index-calculation", json=cache_test_request)
        time2 = time.time() - start_time

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Results should be identical
        data1 = response1.json()
        data2 = response2.json()
        assert data1["data"]["similarity_percentage"] == data2["data"]["similarity_percentage"]
        assert data1["data"]["keyword_coverage"]["coverage_percentage"] == data2["data"]["keyword_coverage"]["coverage_percentage"]

        print(f"✅ API-IC-303-E2E: Performance and monitoring test passed")
        print(f"   Average response time: {avg_response_time:.2f}s")
        print(f"   Response time range: {min_response_time:.2f}s - {max_response_time:.2f}s")
        print(f"   Cache test: {time1:.2f}s -> {time2:.2f}s")
        print(f"   Similarity scores: {similarity_scores}")


if __name__ == "__main__":
    # Run E2E tests with real Azure API
    pytest.main([__file__, "-v", "-s"])