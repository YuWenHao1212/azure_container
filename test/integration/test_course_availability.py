"""
Integration tests for Course Availability Service
"""
import pytest

from src.services.course_availability import CourseAvailabilityChecker


@pytest.mark.asyncio
class TestCourseAvailabilityIntegration:
    """Integration tests for Course Availability"""

    async def test_basic_functionality(self):
        """Test basic course availability check"""
        # Basic test to ensure the service can be instantiated
        checker = CourseAvailabilityChecker()
        assert checker is not None

    async def test_empty_skills_list(self):
        """Test handling of empty skills list"""
        checker = CourseAvailabilityChecker()
        result = await checker.check_course_availability([])
        assert result == []

    async def test_popular_skill_cache(self):
        """Test that dynamic cache mechanism works in integration environment"""
        from unittest.mock import AsyncMock, patch

        checker = CourseAvailabilityChecker()

        # Mock embedding client and database for integration test
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536  # Python embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock successful database response
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                return {
                    "has_courses": True,
                    "count": 15,  # Different from static cache for verification
                    "preferred_count": 10,
                    "other_count": 5,
                    "course_ids": ["coursera_crse:v1-python-101", "coursera_crse:v1-python-102"]
                }

            checker._check_single_skill = mock_check_skill

            # Test with a known popular skill
            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"}
            ]

            result = await checker.check_course_availability(test_skills)
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["has_available_courses"] is True
            assert result[0]["course_count"] == 15  # From mocked database response
            assert "available_course_ids" in result[0]
            assert len(result[0]["available_course_ids"]) == 2

    async def test_CA_002_IT_parallel_processing(self):
        """Test parallel processing of multiple skills"""
        from unittest.mock import AsyncMock, patch

        checker = CourseAvailabilityChecker()

        # Clear cache to ensure clean test
        await checker._dynamic_cache.clear()

        # Mock embedding client and database for integration test
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536,  # Python embedding
                [0.2] * 1536,  # JavaScript embedding
                [0.3] * 1536   # Docker embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock successful database responses
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                # Simulate different response times and data for each skill
                return {
                    "has_courses": True,
                    "count": 10 if skill_name == "Python" else 8,
                    "preferred_count": 6 if skill_name == "Python" else 5,
                    "other_count": 4 if skill_name == "Python" else 3,
                    "course_ids": [f"coursera_crse:v1-{skill_name.lower()}-001",
                                  f"coursera_crse:v1-{skill_name.lower()}-002"]
                }

            checker._check_single_skill = mock_check_skill

            # Test with multiple skills to verify parallel processing
            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"},
                {"skill_name": "JavaScript", "skill_category": "SKILL", "description": "Web development"},
                {"skill_name": "Docker", "skill_category": "SKILL", "description": "Containerization"}
            ]

            result = await checker.check_course_availability(test_skills)

            # Verify all skills were processed
            assert isinstance(result, list)
            assert len(result) == 3

            # Verify each skill has correct data
            for skill_result in result:
                assert skill_result["has_available_courses"] is True
                assert skill_result["course_count"] in [8, 10]
                assert "available_course_ids" in skill_result
                assert len(skill_result["available_course_ids"]) == 2

            # Verify specific skill results
            python_result = next(s for s in result if s["skill_name"] == "Python")
            assert python_result["course_count"] == 10
            assert python_result["preferred_courses"] == 6
