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

    @pytest.mark.asyncio
    async def test_CA_005_IT_enhancement_data_in_optimized_api_response(self):
        """
        Test ID: CA-005-IT
        Test enhancement data is included in API response with optimization enabled
        Priority: P1

        Verifies that with INCLUDE_COURSE_DETAILS=false (production setting),
        the enhancement data is still correctly generated and included in the response.
        """
        import os
        from unittest import mock
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.services.course_availability import CourseAvailabilityChecker

        # Set environment to exclude course_details from API response
        with mock.patch.dict(os.environ, {'INCLUDE_COURSE_DETAILS': 'false'}):
            # Mock database connection
            mock_conn = AsyncMock()

            # Mock database responses with course details
            mock_conn.fetchrow = AsyncMock(side_effect=[
                # Python skill response
                {
                    "has_courses": True,
                    "total_count": 5,
                    "type_diversity": 3,
                    "course_types": ["project", "certification", "specialization"],
                    "course_ids": None,  # Force course_data path
                    "course_data": [
                        {"id": "py-proj-1", "name": "Python Web App", "type": "project",
                         "provider_standardized": "Coursera", "description": "Build a web app",
                         "similarity": 0.95},
                        {"id": "py-proj-2", "name": "Python API", "type": "project",
                         "provider_standardized": "Udemy", "description": "REST API project",
                         "similarity": 0.92},
                        {"id": "py-cert-1", "name": "Python Professional", "type": "certification",
                         "provider_standardized": "Python.org", "description": "Official cert",
                         "similarity": 0.90},
                        {"id": "py-spec-1", "name": "Python Specialization", "type": "specialization",
                         "provider_standardized": "Coursera", "description": "5-course spec",
                         "similarity": 0.88},
                        {"id": "py-course-1", "name": "Python Basics", "type": "course",
                         "provider_standardized": "edX", "description": "Learn Python",
                         "similarity": 0.85}
                    ]
                },
                # Docker skill response
                {
                    "has_courses": True,
                    "total_count": 3,
                    "type_diversity": 2,
                    "course_types": ["project", "certification"],
                    "course_ids": None,
                    "course_data": [
                        {"id": "dock-proj-1", "name": "Container Project", "type": "project",
                         "provider_standardized": "Docker", "description": "Docker compose app",
                         "similarity": 0.93},
                        {"id": "dock-cert-1", "name": "Docker Certified", "type": "certification",
                         "provider_standardized": "Docker", "description": "Docker certification",
                         "similarity": 0.91},
                        {"id": "dock-cert-2", "name": "Kubernetes Admin", "type": "certification",
                         "provider_standardized": "CNCF", "description": "K8s certification",
                         "similarity": 0.89}
                    ]
                }
            ])

            # Create mock pool
            mock_pool = MagicMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_conn
            mock_ctx.__aexit__.return_value = None
            mock_pool.acquire.return_value = mock_ctx

            # Create checker and process skills
            checker = CourseAvailabilityChecker(connection_pool=mock_pool)
            # Initialize to ensure embedding client is set
            await checker.initialize()

            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL"},
                {"skill_name": "Docker", "skill_category": "SKILL"}
            ]

            # Mock embeddings
            with patch.object(checker._embedding_client, 'create_embeddings') as mock_embed:
                mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

                result = await checker.check_course_availability(test_skills)

                # Verify result structure
                assert isinstance(result, list)
                assert len(result) == 2

                # Verify course_details are included internally (for enhancement building)
                assert result[0]["course_details"] is not None
                assert len(result[0]["course_details"]) == 5  # Python courses
                assert result[1]["course_details"] is not None
                assert len(result[1]["course_details"]) == 3  # Docker courses

                # Verify enhancement data is built and attached to first skill
                assert "resume_enhancement_project" in result[0]
                assert "resume_enhancement_certification" in result[0]

                projects = result[0]["resume_enhancement_project"]
                certifications = result[0]["resume_enhancement_certification"]

                # Projects and certifications are now lists
                assert isinstance(projects, list), "Projects should be a list"
                assert isinstance(certifications, list), "Certifications should be a list"

                # Get IDs from arrays
                project_ids = [p["id"] for p in projects]
                cert_ids = [c["id"] for c in certifications]

                # Verify projects include both Python and Docker projects
                assert "py-proj-1" in project_ids
                assert "py-proj-2" in project_ids
                assert "dock-proj-1" in project_ids
                assert len(projects) == 3  # 2 Python + 1 Docker

                # Verify certifications include cert and spec types
                assert "py-cert-1" in cert_ids
                assert "py-spec-1" in cert_ids  # Specialization counted as certification
                assert "dock-cert-1" in cert_ids
                assert "dock-cert-2" in cert_ids
                assert len(certifications) == 4  # 1 cert + 1 spec from Python, 2 certs from Docker

                # Verify regular courses are NOT in enhancement
                assert "py-course-1" not in project_ids
                assert "py-course-1" not in cert_ids

    @pytest.mark.asyncio
    async def test_CA_006_IT_enhancement_data_cross_environment_consistency(self):
        """
        Test ID: CA-006-IT
        Test enhancement data consistency across different environment settings
        Priority: P2

        Verifies that enhancement data is identical whether INCLUDE_COURSE_DETAILS
        is true or false, ensuring the internal logic is unaffected by the API
        response optimization.
        """
        import os
        from unittest import mock
        from unittest.mock import AsyncMock, MagicMock, patch

        from src.services.course_availability import CourseAvailabilityChecker

        # Common test data
        test_skills = [
            {"skill_name": "FastAPI", "skill_category": "SKILL"},
            {"skill_name": "PostgreSQL", "skill_category": "SKILL"}
        ]

        # Common mock database responses
        def get_mock_responses():
            return [
                # FastAPI response
                {
                    "has_courses": True,
                    "total_count": 4,
                    "type_diversity": 3,
                    "course_types": ["project", "certification", "course"],
                    "course_ids": None,
                    "course_data": [
                        {"id": "fast-proj-1", "name": "FastAPI REST API", "type": "project",
                         "provider_standardized": "Udemy", "description": "Build REST API",
                         "similarity": 0.96},
                        {"id": "fast-proj-2", "name": "FastAPI Microservice", "type": "project",
                         "provider_standardized": "Coursera", "description": "Microservice project",
                         "similarity": 0.94},
                        {"id": "fast-cert-1", "name": "FastAPI Expert", "type": "certification",
                         "provider_standardized": "FastAPI", "description": "Official cert",
                         "similarity": 0.92},
                        {"id": "fast-course-1", "name": "FastAPI Basics", "type": "course",
                         "provider_standardized": "edX", "description": "Learn FastAPI",
                         "similarity": 0.88}
                    ]
                },
                # PostgreSQL response
                {
                    "has_courses": True,
                    "total_count": 3,
                    "type_diversity": 2,
                    "course_types": ["specialization", "certification"],
                    "course_ids": None,
                    "course_data": [
                        {"id": "pg-spec-1", "name": "PostgreSQL Advanced", "type": "specialization",
                         "provider_standardized": "Coursera", "description": "4-course spec",
                         "similarity": 0.95},
                        {"id": "pg-cert-1", "name": "PostgreSQL DBA", "type": "certification",
                         "provider_standardized": "PostgreSQL", "description": "DBA cert",
                         "similarity": 0.93},
                        {"id": "pg-cert-2", "name": "PostgreSQL Developer", "type": "certification",
                         "provider_standardized": "PostgreSQL", "description": "Developer cert",
                         "similarity": 0.91}
                    ]
                }
            ]

        async def run_test_with_env(include_course_details: str):
            """Helper to run test with specific environment setting"""
            with mock.patch.dict(os.environ, {'INCLUDE_COURSE_DETAILS': include_course_details}):
                # Mock database connection
                mock_conn = AsyncMock()
                mock_conn.fetchrow = AsyncMock(side_effect=get_mock_responses())

                # Create mock pool
                mock_pool = MagicMock()
                mock_ctx = AsyncMock()
                mock_ctx.__aenter__.return_value = mock_conn
                mock_ctx.__aexit__.return_value = None
                mock_pool.acquire.return_value = mock_ctx

                # Create checker and process
                checker = CourseAvailabilityChecker(connection_pool=mock_pool)
                # Initialize to ensure embedding client is set
                await checker.initialize()

                with patch.object(checker._embedding_client, 'create_embeddings') as mock_embed:
                    mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

                    result = await checker.check_course_availability(test_skills.copy())

                    # Extract enhancement data (now arrays)
                    projects = result[0].get("resume_enhancement_project", [])
                    certifications = result[0].get("resume_enhancement_certification", [])

                    return projects, certifications, result

        # Run with course_details excluded (production)
        projects_excluded, certs_excluded, result_excluded = await run_test_with_env("false")

        # Run with course_details included (development)
        projects_included, certs_included, result_included = await run_test_with_env("true")

        # Verify enhancement data is identical
        assert projects_excluded == projects_included, "Projects should be identical across environments"
        assert certs_excluded == certs_included, "Certifications should be identical across environments"

        # Verify specific content (arrays now)
        project_ids_excluded = [p["id"] for p in projects_excluded]
        cert_ids_excluded = [c["id"] for c in certs_excluded]

        assert "fast-proj-1" in project_ids_excluded
        assert "fast-proj-2" in project_ids_excluded
        assert len(projects_excluded) == 2  # Only 2 projects (FastAPI has 2)

        assert "fast-cert-1" in cert_ids_excluded
        assert "pg-spec-1" in cert_ids_excluded  # Specialization as certification
        assert "pg-cert-1" in cert_ids_excluded
        assert "pg-cert-2" in cert_ids_excluded
        assert len(certs_excluded) == 4  # 1 FastAPI cert + 3 PostgreSQL (1 spec + 2 certs)

        # Verify regular courses are excluded in both
        assert "fast-course-1" not in project_ids_excluded
        assert "fast-course-1" not in cert_ids_excluded

        # Verify the only difference is in SkillSearchQueries course_details field
        # (This would be checked at API response level, not here in the service)
        # The service layer always includes course_details for internal processing
