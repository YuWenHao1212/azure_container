"""
Integration tests for DynamicCourseCache with CourseAvailabilityChecker.

Tests real integration scenarios including:
- Cache integration with course availability checks
- End-to-end Gap Analysis with caching
- Cache monitoring API endpoints
- Error handling with cache failures
"""
import asyncio
import contextlib
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.services.course_availability import CourseAvailabilityChecker
from src.services.dynamic_course_cache import get_course_cache


@pytest.fixture
def sample_skill_queries():
    """Sample skill queries for testing"""
    return [
        {
            "skill_name": "Python",
            "description": "Programming language for web development and data science",
            "skill_category": "SKILL"
        },
        {
            "skill_name": "Machine Learning",
            "description": "AI and data analysis techniques",
            "skill_category": "FIELD"
        },
        {
            "skill_name": "Docker",
            "description": "Containerization platform",
            "skill_category": "SKILL"
        }
    ]


@pytest.fixture
def mock_course_results():
    """Mock course search results"""
    return [
        {
            "has_courses": True,
            "count": 8,
            "preferred_count": 5,
            "other_count": 3,
            "course_ids": [
                "coursera_crse:v1-python-basics",
                "coursera_crse:v1-python-advanced",
                "coursera_prjt:v1-python-project",
                "coursera_cert:v1-python-cert",
                "coursera_crse:v1-python-web"
            ]
        },
        {
            "has_courses": True,
            "count": 12,
            "preferred_count": 8,
            "other_count": 4,
            "course_ids": [
                "coursera_spzn:v1-ml-specialization",
                "coursera_dgre:v1-ml-masters",
                "coursera_cert:v1-ml-certificate",
                "coursera_crse:v1-ml-intro"
            ]
        },
        {
            "has_courses": True,
            "count": 6,
            "preferred_count": 4,
            "other_count": 2,
            "course_ids": [
                "coursera_crse:v1-docker-basics",
                "coursera_prjt:v1-docker-project",
                "coursera_cert:v1-docker-cert"
            ]
        }
    ]


class TestDynamicCacheIntegration:
    """Integration tests for dynamic cache system"""

    @pytest.mark.asyncio
    async def test_course_availability_cache_integration(
        self, sample_skill_queries, mock_course_results
    ):
        """Test cache integration with CourseAvailabilityChecker"""
        # Clear cache before test
        cache = get_course_cache()
        await cache.clear()

        # Create checker instance
        checker = CourseAvailabilityChecker()

        with patch.object(checker, '_check_single_skill', new_callable=AsyncMock) as mock_check:
            with patch.object(checker, '_embedding_client') as mock_embedding:
                # Mock embedding generation
                mock_embedding.create_embeddings = AsyncMock(return_value=[
                    [0.1] * 1536,  # Mock embedding vectors
                    [0.2] * 1536,
                    [0.3] * 1536
                ])

                # Mock course search results
                mock_check.side_effect = mock_course_results

                # First call - should hit database and cache results
                result1 = await checker.check_course_availability(sample_skill_queries.copy())

                # Verify results
                assert len(result1) == 3
                assert all(skill["has_available_courses"] for skill in result1)
                assert result1[0]["available_course_ids"][0] == "coursera_crse:v1-python-basics"

                # Verify database was called
                assert mock_check.call_count == 3
                assert mock_embedding.create_embeddings.call_count == 1

                # Reset mocks
                mock_check.reset_mock()
                mock_embedding.reset_mock()

                # Second call with same queries - should hit cache
                result2 = await checker.check_course_availability(sample_skill_queries.copy())

                # Results should be identical
                assert result1 == result2

                # Database should NOT be called (cache hit)
                assert mock_check.call_count == 0
                assert mock_embedding.create_embeddings.call_count == 0

                # Verify cache statistics
                stats = await cache.get_stats()
                assert stats.cache_hits > 0
                assert stats.hit_rate > 0

    @pytest.mark.asyncio
    async def test_partial_cache_hit(self, sample_skill_queries, mock_course_results):
        """Test scenario with partial cache hits"""
        cache = get_course_cache()
        await cache.clear()

        checker = CourseAvailabilityChecker()

        with patch.object(checker, '_check_single_skill', new_callable=AsyncMock) as mock_check:
            with patch.object(checker, '_embedding_client') as mock_embedding:
                mock_embedding.create_embeddings = AsyncMock(return_value=[[0.1] * 1536])
                mock_check.return_value = mock_course_results[0]

                # Cache first skill only
                first_skill = [sample_skill_queries[0]]
                await checker.check_course_availability(first_skill)

                # Reset mocks
                mock_check.reset_mock()
                mock_embedding.reset_mock()

                # Check all skills - first should hit cache, others should hit database
                all_skills = sample_skill_queries.copy()
                result = await checker.check_course_availability(all_skills)

                # Verify results
                assert len(result) == 3
                assert all(skill["has_available_courses"] for skill in result)

                # Database should be called only for uncached skills (2 out of 3)
                assert mock_check.call_count == 2
                assert mock_embedding.create_embeddings.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_with_different_categories(self):
        """Test cache keys are different for different skill categories"""
        cache = get_course_cache()
        await cache.clear()

        # Same skill name, different categories
        skill_base = {
            "skill_name": "Python",
            "description": "Programming language"
        }

        skill_as_skill = {**skill_base, "skill_category": "SKILL"}
        skill_as_field = {**skill_base, "skill_category": "FIELD"}

        # Generate cache keys
        key_skill = cache.generate_cache_key(skill_as_skill, "SKILL", 0.30)
        key_field = cache.generate_cache_key(skill_as_field, "FIELD", 0.30)

        # Keys should be different
        assert key_skill != key_field

        # Cache different data for each
        await cache.set(key_skill, {"type": "skill", "course_count": 5})
        await cache.set(key_field, {"type": "field", "course_count": 10})

        # Retrieve and verify
        result_skill = await cache.get(key_skill)
        result_field = await cache.get(key_field)

        assert result_skill["type"] == "skill"
        assert result_field["type"] == "field"
        assert result_skill["course_count"] == 5
        assert result_field["course_count"] == 10

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, sample_skill_queries):
        """Test cache behavior when database operations fail"""
        cache = get_course_cache()
        await cache.clear()

        checker = CourseAvailabilityChecker()

        with patch.object(checker, '_check_single_skill', new_callable=AsyncMock) as mock_check:
            with patch.object(checker, '_embedding_client') as mock_embedding:
                mock_embedding.create_embeddings = AsyncMock(return_value=[[0.1] * 1536] * 3)

                # Mock database error
                mock_check.side_effect = Exception("Database connection failed")

                # Should handle errors gracefully
                result = await checker.check_course_availability(sample_skill_queries.copy())

                # Verify error handling
                assert len(result) == 3
                assert all(not skill["has_available_courses"] for skill in result)
                assert all(skill["course_count"] == 0 for skill in result)
                assert all(skill["available_course_ids"] == [] for skill in result)

    def test_cache_monitoring_api_stats(self):
        """Test cache monitoring API endpoints"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Test cache stats endpoint
        response = client.get("/api/v1/debug/course-cache/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "cache_stats" in data
        assert "performance" in data
        assert "health" in data

        # Verify required fields
        cache_stats = data["cache_stats"]
        assert "hit_rate" in cache_stats
        assert "total_requests" in cache_stats
        assert "memory_usage_mb" in cache_stats

    def test_cache_monitoring_api_top_items(self):
        """Test top items API endpoint"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Test top items endpoint
        response = client.get("/api/v1/debug/course-cache/top-items?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "top_cached_items" in data
        assert "total_items" in data
        assert data["limit"] == 5

    def test_cache_monitoring_api_health(self):
        """Test cache health API endpoint"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Test health endpoint
        response = client.get("/api/v1/debug/course-cache/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "health" in data
        assert "metrics" in data
        assert "thresholds" in data

        # Verify health structure
        health = data["health"]
        assert "status" in health
        assert "score" in health
        assert "issues" in health
        assert "recommendations" in health

    def test_cache_monitoring_api_cleanup(self):
        """Test cache cleanup API endpoint"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Test cleanup endpoint
        response = client.post("/api/v1/debug/course-cache/cleanup")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "expired_items_removed" in data
        assert "cache_stats" in data

    def test_cache_monitoring_api_clear(self):
        """Test cache clear API endpoint"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Test clear endpoint
        response = client.post("/api/v1/debug/course-cache/clear")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "items_removed" in data
        assert "warning" in data

    @pytest.mark.asyncio
    async def test_gap_analysis_end_to_end_with_cache(self):
        """Test end-to-end Gap Analysis API with caching"""
        from src.main import create_app

        app = create_app()
        client = TestClient(app)

        # Mock data for Gap Analysis
        test_request = {
            "jd": "We are looking for a Python developer with machine learning experience. " * 10,  # >200 chars
            "resume": "Experienced software engineer with Python and data science background. " * 10  # >200 chars
        }

        with patch('src.services.combined_analysis_v2.LLMFactory') as mock_llm_factory:
            with patch('src.services.course_availability.CourseAvailabilityChecker._check_single_skill') as mock_check:
                # Mock LLM responses
                mock_llm_client = AsyncMock()
                mock_llm_factory.get_llm_client.return_value = mock_llm_client

                # Mock Gap Analysis LLM response
                mock_llm_client.create_chat_completion.return_value = {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "skill_queries": [
                                    {
                                        "skill_name": "Python",
                                        "description": "Programming language",
                                        "skill_category": "SKILL"
                                    }
                                ],
                                "summary": "Test summary"
                            })
                        }
                    }]
                }

                # Mock course availability
                mock_check.return_value = {
                    "has_courses": True,
                    "count": 5,
                    "course_ids": ["coursera_crse:v1-python-test"],
                    "preferred_count": 3,
                    "other_count": 2
                }

                # Mock embedding client
                with patch('src.services.course_availability.get_embedding_client') as mock_embedding:
                    mock_embedding_instance = AsyncMock()
                    mock_embedding.return_value = mock_embedding_instance
                    mock_embedding_instance.create_embeddings.return_value = [[0.1] * 1536]

                    # First request - should cache results
                    response1 = client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=test_request,
                        headers={"X-API-Key": "test-key"}
                    )

                    # Second request - should use cached results
                    response2 = client.post(
                        "/api/v1/index-cal-and-gap-analysis",
                        json=test_request,
                        headers={"X-API-Key": "test-key"}
                    )

                    # Both should succeed
                    assert response1.status_code == 200
                    assert response2.status_code == 200

                    # Verify skill queries have course IDs
                    data1 = response1.json()
                    data2 = response2.json()

                    if "skill_queries" in data1:
                        skill_queries1 = data1["skill_queries"]
                        skill_queries2 = data2["skill_queries"]

                        # Should have real course IDs (not empty arrays)
                        assert len(skill_queries1) > 0
                        assert len(skill_queries2) > 0

                        for skill in skill_queries1:
                            if skill.get("has_available_courses"):
                                assert len(skill.get("available_course_ids", [])) > 0

                        # Results should be consistent
                        assert skill_queries1 == skill_queries2

    @pytest.mark.asyncio
    async def test_cache_background_cleanup_task(self):
        """Test that background cleanup task is properly integrated"""
        # This test verifies the cleanup task can be started without errors
        from src.services.dynamic_course_cache import start_background_cleanup

        # Create task but cancel immediately to avoid long-running test
        task = asyncio.create_task(start_background_cleanup())
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task  # Expected to be cancelled

    @pytest.mark.asyncio
    async def test_cache_memory_management(self):
        """Test cache memory management under load"""
        cache = get_course_cache()
        await cache.clear()

        # Add many items to test memory management
        for i in range(50):
            skill_query = {
                "skill_name": f"Skill{i}",
                "description": f"Description for skill {i}" * 10,  # Larger descriptions
                "skill_category": "SKILL"
            }

            cache_key = cache.generate_cache_key(skill_query, "SKILL", 0.30)
            cache_data = {
                "has_available_courses": True,
                "course_count": i % 10,
                "available_course_ids": [f"coursera_crse:v1-{i}-{j}" for j in range(i % 5)],
                "extra_data": "x" * 1000  # Add bulk data
            }

            await cache.set(cache_key, cache_data)

        # Check memory estimation
        stats = await cache.get_stats()
        assert stats.memory_usage_mb > 0
        assert stats.active_items <= cache._max_size  # Should respect max size

    @pytest.mark.asyncio
    async def test_cache_consistency_across_requests(self, sample_skill_queries):
        """Test cache consistency across multiple concurrent requests"""
        cache = get_course_cache()
        await cache.clear()

        checker = CourseAvailabilityChecker()

        with patch.object(checker, '_check_single_skill', new_callable=AsyncMock) as mock_check:
            with patch.object(checker, '_embedding_client') as mock_embedding:
                mock_embedding.create_embeddings = AsyncMock(return_value=[[0.1] * 1536] * 3)
                mock_check.return_value = {
                    "has_courses": True,
                    "count": 5,
                    "course_ids": ["coursera_crse:v1-test"],
                    "preferred_count": 3,
                    "other_count": 2
                }

                # Run multiple concurrent requests
                tasks = [
                    checker.check_course_availability(sample_skill_queries.copy())
                    for _ in range(5)
                ]

                results = await asyncio.gather(*tasks)

                # All results should be identical
                first_result = results[0]
                for result in results[1:]:
                    assert result == first_result

                # Database should be called only once (first request)
                # Subsequent requests should hit cache
                assert mock_check.call_count <= 3  # At most once per skill
