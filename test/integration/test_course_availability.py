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
        """Test that popular skills return from cache"""
        checker = CourseAvailabilityChecker()
        # Test with a known popular skill
        test_skills = [
            {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"}
        ]
        result = await checker.check_course_availability(test_skills)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["has_available_courses"] is True
        assert result[0]["course_count"] == 10  # Python is in cache with count 10
