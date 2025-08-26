"""
Integration tests for Course Availability Service
"""
import os
import sys

import pytest

from src.services.course_availability import CourseAvailabilityChecker

# NOTE: Diagnostic output removed after fixing CI/CD test issues (2025-08-26)
# Issue was database connection mocking, not test environment differences


@pytest.fixture(autouse=True)
async def reset_global_cache():
    """Reset global cache instance before and after each test to ensure isolation"""

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
        """Test dynamic cache mechanism in integration environment."""
        from unittest.mock import AsyncMock, MagicMock, patch

        checker = CourseAvailabilityChecker()

        # Force initialize cache to ensure consistent behavior across environments
        from src.services.dynamic_course_cache import DynamicCourseCache
        checker._dynamic_cache = DynamicCourseCache()  # Create new instance directly
        await checker._dynamic_cache.clear()  # Ensure clean state

        # Mock embedding client
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536  # Python embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock the database pool to avoid real database calls
            with patch('src.services.course_search.get_course_search_service') as mock_get_service:
                mock_service = AsyncMock()

                # Create a mock connection pool
                mock_pool = AsyncMock()
                mock_conn = AsyncMock()

                # Mock the fetchrow method to return our test data
                mock_conn.fetchrow = AsyncMock(return_value={
                    "has_courses": True,
                    "total_count": 15,
                    "type_diversity": 2,
                    "course_types": ["course", "project"],
                    "course_ids": [
                        "coursera_crse:v1-python-101", "coursera_crse:v1-python-102",
                        "coursera_crse:v1-python-103", "coursera_crse:v1-python-104",
                        "coursera_crse:v1-python-105", "coursera_crse:v1-python-106",
                        "coursera_crse:v1-python-107", "coursera_crse:v1-python-108",
                        "coursera_crse:v1-python-109", "coursera_crse:v1-python-110",
                        "coursera_crse:v1-python-111", "coursera_crse:v1-python-112",
                        "coursera_crse:v1-python-113", "coursera_crse:v1-python-114",
                        "coursera_crse:v1-python-115"
                    ],
                    "course_details": []  # Empty course_details
                })

                # Setup the connection pool acquire context manager
                mock_conn_ctx = AsyncMock()
                mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
                mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_pool.acquire = MagicMock(return_value=mock_conn_ctx)

                # Set the connection pool on the mock service
                mock_service._connection_pool = mock_pool
                mock_service.initialize = AsyncMock()

                mock_get_service.return_value = mock_service

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
                assert len(result[0]["available_course_ids"]) == 15

    async def test_CA_002_IT_parallel_processing(self):
        """Test parallel processing of multiple skills."""
        from unittest.mock import AsyncMock, MagicMock, patch

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

            # Mock the database pool to avoid real database calls
            with patch('src.services.course_search.get_course_search_service') as mock_get_service:
                mock_service = AsyncMock()

                # Create a mock connection pool
                mock_pool = AsyncMock()
                mock_conn = AsyncMock()

                # Create a counter for calls
                call_count = 0

                # Mock different responses based on call order
                async def mock_fetchrow(*args, **kwargs):
                    nonlocal call_count
                    # Extract skill category from args (should be position 3)
                    responses = [
                        {  # Python response
                            "has_courses": True,
                            "total_count": 10,
                            "type_diversity": 2,
                            "course_types": ["course", "project"],
                            "course_ids": [
                                "coursera_crse:v1-python-001", "coursera_crse:v1-python-002",
                                "coursera_crse:v1-python-003", "coursera_crse:v1-python-004",
                                "coursera_crse:v1-python-005", "coursera_crse:v1-python-006",
                                "coursera_crse:v1-python-007", "coursera_crse:v1-python-008",
                                "coursera_crse:v1-python-009", "coursera_crse:v1-python-010"
                            ],
                            "course_details": []
                        },
                        {  # JavaScript response
                            "has_courses": True,
                            "total_count": 8,
                            "type_diversity": 2,
                            "course_types": ["course", "project"],
                            "course_ids": [
                                "coursera_crse:v1-javascript-001", "coursera_crse:v1-javascript-002",
                                "coursera_crse:v1-javascript-003", "coursera_crse:v1-javascript-004",
                                "coursera_crse:v1-javascript-005", "coursera_crse:v1-javascript-006",
                                "coursera_crse:v1-javascript-007", "coursera_crse:v1-javascript-008"
                            ],
                            "course_details": []
                        },
                        {  # Docker response
                            "has_courses": True,
                            "total_count": 8,
                            "type_diversity": 2,
                            "course_types": ["course", "project"],
                            "course_ids": [
                                "coursera_crse:v1-docker-001", "coursera_crse:v1-docker-002",
                                "coursera_crse:v1-docker-003", "coursera_crse:v1-docker-004",
                                "coursera_crse:v1-docker-005", "coursera_crse:v1-docker-006",
                                "coursera_crse:v1-docker-007", "coursera_crse:v1-docker-008"
                            ],
                            "course_details": []
                        }
                    ]
                    result = responses[call_count % 3]
                    call_count += 1
                    return result

                mock_conn.fetchrow = mock_fetchrow

                # Setup the connection pool acquire context manager
                mock_conn_ctx = AsyncMock()
                mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
                mock_conn_ctx.__aexit__ = AsyncMock(return_value=None)
                mock_pool.acquire = MagicMock(return_value=mock_conn_ctx)

                # Set the connection pool on the mock service
                mock_service._connection_pool = mock_pool
                mock_service.initialize = AsyncMock()

                mock_get_service.return_value = mock_service

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
                    assert len(skill_result["available_course_ids"]) in [8, 10]

                # Verify specific skill results
                python_result = next(s for s in result if s["skill_name"] == "Python")
                assert python_result["course_count"] == 10
                # New system doesn't return preferred_courses, check for course IDs instead
                assert len(python_result["available_course_ids"]) == 10
