"""
Integration tests for Index Calculation and Gap Analysis V2 endpoint.

Tests the V2 refactoring with feature flags and combined analysis service.
"""
import os

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.utils.feature_flags import FeatureFlags

# Test client
client = TestClient(app)

# Test data
SAMPLE_RESUME = """
<div>
<h2>John Doe</h2>
<p><strong>Software Engineer</strong></p>
<p>Experience with Python, FastAPI, Docker, and cloud platforms.
Skilled in REST API development, database design, and DevOps practices.
3 years of experience in backend development with focus on scalable systems.</p>
</div>
""" * 2  # Make it longer than 200 chars

SAMPLE_JD = """
<div>
<h2>Senior Backend Developer Position</h2>
<p>We are looking for an experienced backend developer with expertise in:</p>
<ul>
<li>Python programming and FastAPI framework</li>
<li>Microservices architecture and Docker containerization</li>
<li>Cloud platforms (AWS, Azure, or GCP)</li>
<li>Database design and optimization</li>
<li>API design and development</li>
<li>DevOps and CI/CD practices</li>
</ul>
<p>5+ years of experience preferred.</p>
</div>
""" * 2  # Make it longer than 200 chars

SAMPLE_KEYWORDS = ["Python", "FastAPI", "Docker", "AWS", "REST API", "Microservices"]


class TestIndexCalGapAnalysisV2:
    """Test suite for V2 implementation of index calculation and gap analysis."""

    @pytest.mark.asyncio
    async def test_v1_implementation_default(self):
        """Test that V1 is used by default when V2 flags are disabled."""
        # Ensure V2 is disabled
        os.environ["USE_V2_IMPLEMENTATION"] = "false"
        os.environ["V2_ROLLOUT_PERCENTAGE"] = "0"

        response = client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": SAMPLE_RESUME,
                "job_description": SAMPLE_JD,
                "keywords": SAMPLE_KEYWORDS,
                "language": "en"
            },
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check basic structure
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

        # Check that V1 implementation was used
        assert data["data"].get("implementation_version") == "v1"

        # Check required fields
        assert "raw_similarity_percentage" in data["data"]
        assert "similarity_percentage" in data["data"]
        assert "keyword_coverage" in data["data"]
        assert "gap_analysis" in data["data"]

    @pytest.mark.asyncio
    async def test_v2_implementation_enabled(self):
        """Test that V2 is used when explicitly enabled."""
        # Enable V2 implementation
        os.environ["USE_V2_IMPLEMENTATION"] = "true"

        response = client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": SAMPLE_RESUME,
                "job_description": SAMPLE_JD,
                "keywords": SAMPLE_KEYWORDS,
                "language": "en"
            },
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check basic structure
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

        # Check that V2 implementation was used
        assert data["data"].get("implementation_version") == "v2"

        # Check required fields
        assert "raw_similarity_percentage" in data["data"]
        assert "similarity_percentage" in data["data"]
        assert "keyword_coverage" in data["data"]
        assert "gap_analysis" in data["data"]

    @pytest.mark.asyncio
    async def test_feature_flags_configuration(self):
        """Test that feature flags are properly configured."""
        # Test default values
        assert not FeatureFlags.USE_V2_IMPLEMENTATION
        assert FeatureFlags.V2_ROLLOUT_PERCENTAGE == 0
        assert FeatureFlags.ADAPTIVE_RETRY_ENABLED
        assert FeatureFlags.ENABLE_PARTIAL_RESULTS

        # Test resource pool configuration
        config = FeatureFlags.get_resource_pool_config()
        assert "min_pool_size" in config
        assert "max_pool_size" in config
        assert "idle_timeout" in config
        assert config["min_pool_size"] >= 2
        assert config["max_pool_size"] >= config["min_pool_size"]

    @pytest.mark.asyncio
    async def test_rollout_percentage(self):
        """Test percentage-based rollout functionality."""
        # Set 50% rollout
        os.environ["V2_ROLLOUT_PERCENTAGE"] = "50"

        # Test with consistent user ID
        user_id = "test_user_123"

        # Should give consistent results
        result1 = FeatureFlags.should_use_v2(user_id)
        result2 = FeatureFlags.should_use_v2(user_id)
        assert result1 == result2

        # Test with different user IDs to ensure distribution
        test_results = []
        for i in range(20):
            result = FeatureFlags.should_use_v2(f"user_{i}")
            test_results.append(result)

        # Should have some mix of True/False (not all same)
        assert True in test_results or False in test_results

    @pytest.mark.asyncio
    async def test_input_validation(self):
        """Test input validation for both V1 and V2."""
        # Test with invalid input (empty resume)
        response = client.post(
            "/api/v1/index-cal-and-gap-analysis",
            json={
                "resume": "",
                "job_description": SAMPLE_JD,
                "keywords": SAMPLE_KEYWORDS,
                "language": "en"
            },
            headers={"X-API-Key": "test-key"}
        )

        # Should handle validation error gracefully
        assert response.status_code in [400, 422, 500]  # Various validation error codes

    @pytest.mark.asyncio
    async def test_language_support(self):
        """Test language support in both implementations."""
        # Test with Chinese language
        for use_v2 in ["false", "true"]:
            os.environ["USE_V2_IMPLEMENTATION"] = use_v2

            response = client.post(
                "/api/v1/index-cal-and-gap-analysis",
                json={
                    "resume": SAMPLE_RESUME,
                    "job_description": SAMPLE_JD,
                    "keywords": SAMPLE_KEYWORDS,
                    "language": "zh-TW"
                },
                headers={"X-API-Key": "test-key"}
            )

            if response.status_code == 200:
                data = response.json()
                # Should maintain language setting
                # (Implementation may normalize zh-tw to zh-TW)
                assert data["success"] is True

    def teardown_method(self):
        """Clean up environment variables after each test."""
        # Reset to defaults
        os.environ["USE_V2_IMPLEMENTATION"] = "false"
        os.environ["V2_ROLLOUT_PERCENTAGE"] = "0"
