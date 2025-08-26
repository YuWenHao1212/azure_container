"""
Integration tests for Course Availability Service
"""
import os
import sys

# ============================================================
# DIAGNOSTIC CODE FOR CI/CD DEBUGGING
# ============================================================
print("\n" + "="*60)
print("COURSE AVAILABILITY TEST DIAGNOSTICS")
print("="*60)
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")
print(f"Working Dir: {os.getcwd()}")
print(f"ENABLE_COURSE_CACHE: {os.environ.get('ENABLE_COURSE_CACHE', 'NOT SET')}")
print(f"CI: {os.environ.get('CI', 'NOT SET')}")
print(f"GITHUB_ACTIONS: {os.environ.get('GITHUB_ACTIONS', 'NOT SET')}")

# Check if cache module is already loaded
if 'src.services.dynamic_course_cache' in sys.modules:
    import src.services.dynamic_course_cache as cache_module_check
    print("\nWARNING: Cache module already loaded before test!")
    print(f"    Cache instance: {cache_module_check._cache_instance}")
    print(f"    Instance ID: {id(cache_module_check._cache_instance) if cache_module_check._cache_instance else 'None'}")
    print(f"    Module file: {cache_module_check.__file__}")
else:
    print("\nOK: Cache module not yet loaded (clean state)")

# List loaded test modules
test_modules = [m for m in sys.modules if 'test' in m]
if test_modules:
    print(f"\nLoaded test modules ({len(test_modules)}):")
    for m in sorted(test_modules)[:10]:
        print(f"  - {m}")
        
# List src modules that might affect cache
src_modules = [m for m in sys.modules if 'src.services' in m]
if src_modules:
    print(f"\nLoaded src.services modules ({len(src_modules)}):")
    for m in sorted(src_modules):
        print(f"  - {m}")

print("="*60 + "\n")
# ============================================================
# END DIAGNOSTIC CODE
# ============================================================

import pytest

from src.services.course_availability import CourseAvailabilityChecker


@pytest.fixture(autouse=True)
async def reset_global_cache():
    """Reset global cache instance before and after each test to ensure isolation"""
    import os
    import sys

    import src.services.dynamic_course_cache as cache_module

    # Save original state
    original_instance = cache_module._cache_instance
    original_env = os.environ.get('ENABLE_COURSE_CACHE')

    # Force disable cache for test isolation
    os.environ['ENABLE_COURSE_CACHE'] = 'false'
    cache_module._cache_instance = None

    # Clear module cache to force re-initialization
    modules_to_clear = ['src.services.course_availability']
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]

    yield

    # Restore original state
    cache_module._cache_instance = original_instance
    if original_env is not None:
        os.environ['ENABLE_COURSE_CACHE'] = original_env
    else:
        os.environ.pop('ENABLE_COURSE_CACHE', None)


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

        # Force initialize cache to ensure consistent behavior across environments
        from src.services.dynamic_course_cache import DynamicCourseCache
        checker._dynamic_cache = DynamicCourseCache()  # Create new instance directly
        await checker._dynamic_cache.clear()  # Ensure clean state

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
                    "total_count": 15,  # Different from static cache for verification
                    "course_ids": ["coursera_crse:v1-python-101", "coursera_crse:v1-python-102"],
                    "course_details": []  # Add course_details field
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

        # Force initialize cache to ensure consistent behavior across environments
        from src.services.dynamic_course_cache import DynamicCourseCache
        checker._dynamic_cache = DynamicCourseCache()  # Create new instance directly
        await checker._dynamic_cache.clear()  # Ensure clean state

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
                    "total_count": 10 if skill_name == "Python" else 8,
                    "type_diversity": 2,
                    "course_types": ["course", "project"],
                    "course_ids": [f"coursera_crse:v1-{skill_name.lower()}-001",
                                  f"coursera_crse:v1-{skill_name.lower()}-002"],
                    "course_details": []  # Add course_details field
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
            # New system doesn't return preferred_courses, check for course IDs instead
            assert len(python_result["available_course_ids"]) == 2
