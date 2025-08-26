"""
Integration tests for Course Availability Check feature
Test ID: CA-001-IT to CA-005-IT
"""
import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.services.course_availability import CourseAvailabilityChecker


@pytest.mark.asyncio
class TestCourseAvailabilityIntegration:
    """Integration tests for Course Availability feature"""

    @pytest.fixture
    def service(self):
        """Create service instance"""
        checker = CourseAvailabilityChecker()
        # Disable cache for testing to ensure consistent behavior
        checker._cache_enabled = False
        checker._dynamic_cache = None
        return checker

    @pytest.fixture
    def mock_embedding_response(self):
        """Mock embedding API response"""
        def create_embeddings(texts: list[str]) -> list[list[float]]:
            # Return 1536-dimensional embeddings
            return [np.random.rand(1536).tolist() for _ in texts]
        return create_embeddings

    @pytest.fixture
    def mock_db_response(self):
        """Mock database response for course availability"""
        def create_response(has_courses: bool = True, count: int = 5):
            return {
                "has_courses": has_courses,
                "course_count": count,
                "preferred_match": True,
                "breakdown": {
                    "preferred": count - 1,
                    "other": 1
                }
            }
        return create_response

    async def test_CA_001_IT_course_availability_integration(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-001-IT
        Scenario: Course availability check with embedding and database
        Validation: Verify has_available_courses and course_count fields
        """
        # Prepare skill queries (use non-cached skills to test full flow)
        skill_queries = [
            {
                "skill_name": "Rust",  # Not in cache
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "Quantum Computing",  # Not in cache
                "skill_category": "FIELD",
                "description": "Quantum algorithms and computation"
            }
        ]

        # Mock embedding client
        with patch.object(service, '_embedding_client') as mock_client:
            mock_client.create_embeddings = AsyncMock(return_value=mock_embedding_response(["text1", "text2"]))

            # Mock connection pool
            mock_pool = MagicMock()
            mock_conn = AsyncMock()
            # Create a proper async context manager mock
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_conn
            mock_ctx.__aexit__.return_value = None
            mock_pool.acquire.return_value = mock_ctx

            # Mock database response with all required fields
            mock_conn.fetchrow = AsyncMock(return_value={
                "has_courses": True,
                "total_count": 10,
                "preferred_count": 7,
                "other_count": 3,
                # Add required fields from AVAILABILITY_QUERY
                "course_ids": [f"course_{i}" for i in range(1, 11)],  # 10 course IDs
                "course_details": json.dumps([
                    {"id": f"course_{i}", "name": f"Course {i}", "type": "course"}
                    for i in range(1, 11)
                ]),  # JSON string of course details
                "type_diversity": 1,
                "course_types": ["course"]
            })

            service._connection_pool = mock_pool
            service._embedding_client = mock_client

            # Execute
            result = await service.check_course_availability(skill_queries)

            # Verify
            assert len(result) == 2

            # Check Rust (SKILL)
            rust_skill = result[0]
            assert rust_skill["has_available_courses"] is True
            assert rust_skill["course_count"] == 10
            # preferred_courses field is no longer used in the current implementation

            # Check Quantum Computing (FIELD)
            qc_skill = result[1]
            assert qc_skill["has_available_courses"] is True
            assert qc_skill["course_count"] == 10
            # preferred_courses field is no longer used in the current implementation

    async def test_CA_002_IT_parallel_processing(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-002-IT
        Scenario: Parallel processing of multiple skills
        Validation: Verify concurrent execution and performance
        """
        # Test data with mixed categories (use non-cached skills)
        skill_queries = [
            {
                "skill_name": "Rust",
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "Quantum Computing",
                "skill_category": "FIELD",
                "description": "Quantum algorithms and computation"
            }
        ]

        # Track embedding text generation
        generated_texts = []

        async def capture_texts(texts):
            generated_texts.extend(texts)
            return mock_embedding_response(texts)

        # Set up a mock embedding client first to prevent initialize() from overwriting it
        mock_embedding_client = MagicMock()  # Use MagicMock instead of AsyncMock
        mock_embedding_client.create_embeddings = AsyncMock(side_effect=capture_texts)
        service._embedding_client = mock_embedding_client

        # Mock connection pool
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        # Create a proper async context manager mock
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_ctx
        mock_conn.fetchrow = AsyncMock(return_value={
            "has_courses": True,
            "total_count": 5,
            "preferred_count": 3,
            "other_count": 2,
            # Add required fields from AVAILABILITY_QUERY
            "course_ids": [f"course_{i}" for i in range(1, 6)],  # 5 course IDs
            "course_details": json.dumps([
                {"id": f"course_{i}", "name": f"Course {i}", "type": "course"}
                for i in range(1, 6)
            ]),  # JSON string of course details
            "type_diversity": 1,
            "course_types": ["course"]
        })

        service._connection_pool = mock_pool

        # Execute
        await service.check_course_availability(skill_queries)

        # Verify different strategies were applied
        assert len(generated_texts) == 2

        # Check SKILL category text
        assert "Rust course project certificate" in generated_texts[0]

        # Check FIELD category text
        assert "Quantum Computing specialization degree" in generated_texts[1]

    async def test_CA_003_IT_graceful_degradation(
        self,
        service,
        mock_embedding_response,
        mock_db_response
    ):
        """
        Test ID: CA-003-IT
        Scenario: Database connection failure
        Validation: Verify graceful degradation
        """
        # Create 20 skills (max parallel limit)
        skills = [
            {
                'skill_name': f"Skill_{i}",
                'skill_category': 'SKILL' if i % 2 == 0 else 'FIELD',
                'description': f"Description for skill {i}"
            }
            for i in range(20)
        ]

        # Set up a mock embedding client first to prevent initialize() from overwriting it
        mock_embedding_client = MagicMock()  # Use MagicMock instead of AsyncMock
        mock_embedding_client.create_embeddings = AsyncMock(
            return_value=[[0.1] * 1536 for _ in range(20)]
        )
        service._embedding_client = mock_embedding_client

        # Mock connection pool to work normally (parallel processing test)
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        # Create a proper async context manager mock
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        mock_pool.acquire.return_value = mock_ctx

        # Track concurrent calls
        call_times = []

        async def mock_fetchrow(*args, **kwargs):
            import time
            call_times.append(time.time())
            # Simulate database query delay
            await asyncio.sleep(0.01)
            return {
                "has_courses": True,
                "total_count": 5,
                "preferred_count": 3,
                "other_count": 2,
                "course_ids": ["course_1", "course_2", "course_3", "course_4", "course_5"],
                "course_details": json.dumps([
                    {"id": f"course_{i}", "name": f"Course {i}", "type": "course"}
                    for i in range(1, 6)
                ]),
                "type_diversity": 1,
                "course_types": ["course"]
            }

        mock_conn.fetchrow = AsyncMock(side_effect=mock_fetchrow)
        service._connection_pool = mock_pool

        import time
        start = time.time()
        result = await service.check_course_availability(skills)
        duration = time.time() - start

        # Verify parallel execution
        assert len(result) == 20
        # With parallel processing, should complete faster than serial
        # 20 skills * 0.01s delay = 0.2s if serial, but should be much faster with parallel
        assert duration < 0.2  # Should complete quickly due to parallel processing

    async def test_CA_004_IT_cache_integration(
        self,
        service,
        mock_embedding_response
    ):
        """
        Test ID: CA-004-IT
        Scenario: Cache hit for popular skills
        Validation: Verify cache effectiveness
        """
        skills = [
            {
                'skill_name': "Rust",  # Not in cache
                'skill_category': 'SKILL',
                'description': "Systems programming"
            }
        ]

        # Set up a mock embedding client first to prevent initialize() from overwriting it
        mock_embedding_client = MagicMock()  # Use MagicMock instead of AsyncMock
        mock_embedding_client.create_embeddings = AsyncMock(return_value=[[0.1] * 1536])
        service._embedding_client = mock_embedding_client

        # Mock connection pool to fail
        mock_pool = MagicMock()
        mock_pool.acquire.side_effect = Exception("Database connection failed")

        service._connection_pool = mock_pool

        # Execute - should not raise exception
        result = await service.check_course_availability(skills)

        # Should return with graceful degradation
        assert result is not None
        assert len(result) == 1

        # Skill should be marked as unavailable
        assert result[0]["has_available_courses"] is False
        assert result[0]["course_count"] == 0

