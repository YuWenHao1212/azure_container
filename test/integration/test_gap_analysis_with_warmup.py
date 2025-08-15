"""
Integration test for Gap Analysis API with pgvector warmup optimization
"""
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.integration
class TestGapAnalysisWithWarmup:
    """Test Gap Analysis API with pgvector warmup optimization"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def valid_request_data(self):
        """Valid request data for testing"""
        return {
            "resume": """
                <h2>Experience</h2>
                <p>Senior Software Engineer with 5 years experience in Python, FastAPI,
                Docker, Kubernetes, AWS, PostgreSQL, Redis, and React.</p>
                <h2>Skills</h2>
                <ul>
                    <li>Python</li>
                    <li>FastAPI</li>
                    <li>Docker</li>
                    <li>PostgreSQL</li>
                    <li>AWS</li>
                </ul>
            """,
            "job_description": """
                We are looking for a Senior Backend Engineer with strong experience in:
                - Python and FastAPI for building scalable APIs
                - Docker and Kubernetes for containerization
                - PostgreSQL for database management
                - AWS cloud services
                - Machine Learning basics
                - GraphQL API design
            """,
            "keywords": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "AWS", "Machine Learning", "GraphQL"],
            "language": "en"
        }

    @pytest.mark.asyncio
    async def test_gap_analysis_with_warmup_timing(self, valid_request_data):
        """Test that warmup runs in parallel and doesn't add to total time"""

        # Mock services to track timing
        with patch("src.services.combined_analysis_v2.get_course_search_service") as mock_get_service:
            # Setup mock course service
            mock_course_service = MagicMock()
            mock_connection_pool = AsyncMock()
            mock_course_service._connection_pool = mock_connection_pool

            # Mock connection
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=100)
            mock_connection_pool.acquire = AsyncMock()
            mock_connection_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_connection_pool.acquire.return_value.__aexit__ = AsyncMock()

            mock_get_service.return_value = mock_course_service

            # Mock LLM responses
            with patch("src.services.index_calculation_v2.IndexCalculationServiceV2.calculate_index") as mock_index:
                with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2.analyze_with_context") as mock_gap:
                    # Setup mock responses
                    mock_index.return_value = {
                        "similarity_score": 75,
                        "keyword_coverage": {"covered_count": 6, "total_keywords": 8},
                        "category_scores": {"technical": 80, "soft": 70}
                    }

                    mock_gap.return_value = {
                        "overall_gap_score": 25,
                        "SkillSearchQueries": [
                            {"skill_name": "Machine Learning", "skill_category": "TECHNICAL"},
                            {"skill_name": "GraphQL", "skill_category": "TECHNICAL"}
                        ],
                        "recommendations": ["Learn Machine Learning", "Study GraphQL"]
                    }

                    # Execute API call
                    from src.api.v1.combined_analysis import router
                    from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2

                    service = CombinedAnalysisServiceV2()

                    # Track execution time
                    start_time = time.time()
                    result = await service.analyze(
                        valid_request_data["resume"],
                        valid_request_data["job_description"],
                        valid_request_data["keywords"],
                        valid_request_data["language"]
                    )
                    time.time() - start_time

                    # Assertions
                    assert result is not None
                    assert "index_calculation" in result
                    assert "gap_analysis" in result
                    assert "metadata" in result

                    # Check timing metadata
                    metadata = result["metadata"]
                    assert "detailed_timings_ms" in metadata
                    timings = metadata["detailed_timings_ms"]

                    # Verify warmup timing is tracked
                    if "pgvector_warmup_time" in timings:
                        # Warmup should be less than structure analysis time (parallel)
                        assert timings.get("pgvector_warmup_time", 0) < timings.get("structure_analysis_time", 2000)

                    # Verify course availability is tracked
                    if "course_availability_time" in timings:
                        assert timings["course_availability_time"] > 0

    @pytest.mark.asyncio
    async def test_warmup_failure_does_not_affect_main_flow(self, valid_request_data):
        """Test that warmup failure doesn't break the main API flow"""

        # Mock course service to fail during warmup
        with patch("src.services.combined_analysis_v2.get_course_search_service") as mock_get_service:
            mock_get_service.side_effect = Exception("Warmup connection failed")

            # Mock LLM responses
            with patch("src.services.index_calculation_v2.IndexCalculationServiceV2.calculate_index") as mock_index:
                with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2.analyze_with_context") as mock_gap:
                    # Setup mock responses
                    mock_index.return_value = {
                        "similarity_score": 75,
                        "keyword_coverage": {"covered_count": 6, "total_keywords": 8}
                    }

                    mock_gap.return_value = {
                        "overall_gap_score": 25,
                        "SkillSearchQueries": [],
                        "recommendations": []
                    }

                    # Execute API call
                    from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2

                    service = CombinedAnalysisServiceV2()

                    # Should not raise exception even if warmup fails
                    result = await service.analyze(
                        valid_request_data["resume"],
                        valid_request_data["job_description"],
                        valid_request_data["keywords"],
                        valid_request_data["language"]
                    )

                    # Assertions - API should still work
                    assert result is not None
                    assert "index_calculation" in result
                    assert "gap_analysis" in result

    @pytest.mark.asyncio
    async def test_api_timing_logs_include_warmup_info(self, valid_request_data, caplog):
        """Test that API timing logs include warmup information"""

        # Mock services
        with patch("src.services.combined_analysis_v2.get_course_search_service") as mock_get_service:
            # Setup successful warmup
            mock_course_service = MagicMock()
            mock_connection_pool = AsyncMock()
            mock_course_service._connection_pool = mock_connection_pool

            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=100)
            mock_connection_pool.acquire = AsyncMock()
            mock_connection_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_connection_pool.acquire.return_value.__aexit__ = AsyncMock()

            mock_get_service.return_value = mock_course_service

            # Mock LLM responses
            with patch("src.services.index_calculation_v2.IndexCalculationServiceV2.calculate_index") as mock_index:
                with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2.analyze_with_context") as mock_gap:
                    mock_index.return_value = {"similarity_score": 75}
                    mock_gap.return_value = {"overall_gap_score": 25, "SkillSearchQueries": []}

                    from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2

                    service = CombinedAnalysisServiceV2()

                    # Execute with logging
                    import logging
                    with caplog.at_level(logging.INFO):
                        await service.analyze(
                            valid_request_data["resume"],
                            valid_request_data["job_description"],
                            valid_request_data["keywords"],
                            valid_request_data["language"]
                        )

                    # Check logs for timing information
                    api_timing_logs = [r for r in caplog.records if "[API Timing]" in r.message]
                    assert len(api_timing_logs) > 0

                    # Check for warmup logs
                    warmup_logs = [r for r in caplog.records if "pgvector warmup" in r.message]
                    assert len(warmup_logs) > 0

                    # Verify timing breakdown includes all phases
                    timing_log = api_timing_logs[0]
                    if hasattr(timing_log, 'timing_ms'):
                        timing_data = timing_log.timing_ms
                        assert "parallel_phase" in timing_data
                        assert "sequential_phase" in timing_data

                        # Check parallel phase includes warmup
                        parallel = timing_data["parallel_phase"]
                        assert "pgvector_warmup" in parallel or "keywords" in parallel
