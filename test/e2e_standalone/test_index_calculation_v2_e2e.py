"""
End-to-End tests for Index Calculation V2 with Real Azure API.

TEST IDs:
- API-IC-301-E2E: 基本工作流程測試
- API-IC-302-E2E: HTML 格式測試
- API-IC-303-E2E: 字串格式關鍵字測試
- API-IC-304-E2E: 效能和監控整合測試

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

from src.main import create_app  # noqa: E402


class TestIndexCalculationV2E2ERealAPI:
    """End-to-End tests for Index Calculation V2 with real Azure API."""

    @pytest.fixture
    def app(self):
        """Create app instance with real API configuration."""
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

        return create_app()

    def create_test_client(self, app):
        """Create a new test client instance.

        Solution 2: 重新創建 client - 每次需要時創建新的 TestClient
        """
        client = TestClient(app)
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
    @pytest.mark.timeout(30)
    def test_API_IC_301_E2E_basic_workflow(self, app, test_data):
        """TEST: API-IC-301-E2E - 基本工作流程測試.

        Solution 1: 分離測試 - 基本功能測試
        """
        # Create fresh client for this test
        client = self.create_test_client(app)

        # Use real test data - medium size for comprehensive testing
        real_resume = test_data["standard_resumes"][1]["content"]
        real_jd = test_data["job_descriptions"][1]["content"]
        real_keywords = test_data["job_descriptions"][1]["keywords"]

        # Make the API request
        start_time = time.time()
        response = client.post(
            "/api/v1/index-calculation",
            json={
                "resume": real_resume,
                "job_description": real_jd,
                "keywords": real_keywords
            }
        )
        processing_time = time.time() - start_time

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Verify success response
        assert data["success"] is True
        assert "data" in data

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

        # Verify performance
        assert processing_time < 15.0

        print(f"✅ API-IC-301-E2E: Basic workflow test passed in {processing_time:.2f}s")

    # TEST: API-IC-302-E2E
    @pytest.mark.timeout(30)
    def test_API_IC_302_E2E_html_format(self, app, test_data):
        """TEST: API-IC-302-E2E - HTML格式測試.

        Solution 1: 分離測試 - HTML 格式處理
        Solution 2: 重新創建 client
        """
        # Create fresh client for this test
        client = self.create_test_client(app)

        html_resume = test_data["standard_resumes"][3]["content"]
        real_jd = test_data["job_descriptions"][1]["content"]

        response = client.post(
            "/api/v1/index-calculation",
            json={
                "resume": html_resume,
                "job_description": real_jd,
                "keywords": ["Python", "Docker", "AWS"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print("✅ API-IC-302-E2E: HTML format test passed")

    # TEST: API-IC-303-E2E
    @pytest.mark.timeout(30)
    def test_API_IC_303_E2E_string_keywords(self, app, test_data):
        """TEST: API-IC-303-E2E - 字串格式關鍵字測試.

        Solution 1: 分離測試 - 字串格式關鍵字
        Solution 2: 重新創建 client - 使用新的 TestClient
        """
        # Create fresh client for this test
        client = self.create_test_client(app)

        real_resume = test_data["standard_resumes"][1]["content"]
        real_jd = test_data["job_descriptions"][1]["content"]

        response = client.post(
            "/api/v1/index-calculation",
            json={
                "resume": real_resume,
                "job_description": real_jd,
                "keywords": "Python, FastAPI, Docker, AWS"  # String format
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["keyword_coverage"]["total_keywords"] == 4

        print("✅ API-IC-303-E2E: String keywords test passed")

    # TEST: API-IC-304-E2E - 待實作
    # @pytest.mark.timeout(90)
    # def test_API_IC_304_E2E_performance_and_monitoring(self, app, test_data):
    #     """TEST: API-IC-304-E2E - 效能和監控整合測試(待實作).
    #
    #     待實作功能:
    #     1. 監控事件追蹤驗證
    #     2. 日誌格式和內容檢查
    #     3. 錯誤處理和監控測試
    #     4. 性能指標收集(記憶體、CPU等)
    #     5. 快取監控驗證
    #
    #     注意: 目前的實作只是基本的穩定性測試, 未包含真正的監控整合驗證。
    #     需等待監控功能開發完成後實施。
    #     """
    #     pass


if __name__ == "__main__":
    # Run E2E tests with real Azure API
    pytest.main([__file__, "-v", "-s"])
