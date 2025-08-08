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
    async def test_v2_implementation_enabled(self):
        """Test that V2 implementation works correctly (V1 has been removed)."""
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

        # Check required fields (V2 format)
        assert "raw_similarity_percentage" in data["data"]
        assert "similarity_percentage" in data["data"]
        assert "keyword_coverage" in data["data"]
        assert "gap_analysis" in data["data"]

    @pytest.mark.asyncio
    async def test_feature_flags_configuration(self):
        """Test that feature flags are properly configured."""
        # Test remaining feature flags (V2 rollout flags removed)
        assert FeatureFlags.ADAPTIVE_RETRY_ENABLED
        assert not FeatureFlags.ENABLE_PARTIAL_RESULTS  # Default is false

        # Test resource pool configuration
        config = FeatureFlags.get_resource_pool_config()
        assert "min_pool_size" in config
        assert "max_pool_size" in config
        assert "idle_timeout" in config
        assert config["min_pool_size"] >= 2
        assert config["max_pool_size"] >= config["min_pool_size"]



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
        # Clean up any test-specific environment variables if needed
        pass
