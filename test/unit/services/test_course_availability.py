"""
Unit tests for Course Availability Check Service
Test ID: CA-001-UT to CA-005-UT
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.course_availability import CourseAvailabilityChecker


class TestCourseAvailability:
    """Unit tests for course availability checker"""

    @pytest.fixture
    def mock_pool(self):
        """Mock connection pool"""
        pool = MagicMock()
        return pool

    @pytest.fixture
    def mock_embedding_client(self):
        """Mock embedding client"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def checker(self, mock_pool):
        """Create checker instance with mock pool"""
        return CourseAvailabilityChecker(connection_pool=mock_pool)

    @pytest.fixture
    def sample_skills(self):
        """Sample skill queries from Gap Analysis"""
        return [
            {
                "skill_name": "Rust",
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "GraphQL",
                "skill_category": "SKILL",
                "description": "Query language for APIs"
            },
            {
                "skill_name": "Blockchain",
                "skill_category": "FIELD",
                "description": "Distributed ledger technology"
            }
        ]

    @pytest.mark.asyncio
    async def test_CA_001_UT_batch_embedding_generation(self, checker, sample_skills):
        """
        Test ID: CA-001-UT
        Test batch embedding generation functionality
        Priority: P0
        """
        # Mock embedding client
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536,  # Mock embedding for skill 1 (correct dimension)
                [0.2] * 1536,  # Mock embedding for skill 2
                [0.3] * 1536   # Mock embedding for skill 3
            ])
            mock_get_client.return_value = mock_client

            # Mock database query with proper async context manager
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "has_courses": True,
                "total_count": 5,
                "preferred_count": 3,
                "other_count": 2
            })

            # Create proper async context manager
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_conn
            mock_ctx.__aexit__.return_value = None
            checker._connection_pool.acquire.return_value = mock_ctx

            # Execute check
            result = await checker.check_course_availability(sample_skills)

            # Verify batch embedding call
            mock_client.create_embeddings.assert_called_once()
            embeddings_input = mock_client.create_embeddings.call_args[0][0]
            assert len(embeddings_input) == 3
            # Check that embedding text follows new strategy
            assert "Rust" in embeddings_input[0]  # Rust is not in cache
            assert "GraphQL" in embeddings_input[1]
            assert "Blockchain" in embeddings_input[2]

            # Verify results
            assert len(result) == 3
            for skill in result:
                assert "has_available_courses" in skill
                assert "course_count" in skill

    @pytest.mark.asyncio
    async def test_CA_002_UT_single_skill_query(self, checker):
        """
        Test ID: CA-002-UT
        Test single skill database query functionality
        Priority: P0
        """
        # Test data
        embedding = [0.1] * 1536  # Correct dimension
        skill_name = "Python"
        skill_category = "SKILL"

        # Mock connection
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "has_courses": True,
            "total_count": 15,  # Test count > 10
            "preferred_count": 10,
            "other_count": 5
        })

        checker._connection_pool = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        checker._connection_pool.acquire.return_value = mock_ctx

        # Execute single skill check with category
        result = await checker._check_single_skill(embedding, skill_name, skill_category)

        # Verify query execution
        mock_conn.fetchrow.assert_called_once()
        query_args = mock_conn.fetchrow.call_args[0]
        assert "WITH ranked_courses" in query_args[0]  # Check SQL query
        assert query_args[1] == embedding  # Check embedding parameter
        assert len(query_args) >= 3  # Should have embedding, threshold, category

        # Verify result
        assert result["has_courses"] is True
        assert result["count"] == 15  # Should return actual count when < 25
        assert result["preferred_count"] == 10
        assert result["other_count"] == 5

    @pytest.mark.asyncio
    async def test_CA_003_UT_cache_mechanism(self, checker):
        """
        Test ID: CA-003-UT
        Test popular skills cache functionality
        Priority: P1
        """
        # Test with cached skills
        cached_skills = [
            {"skill_name": "Python", "skill_category": "SKILL"},
            {"skill_name": "JavaScript", "skill_category": "SKILL"},
            {"skill_name": "Data Science", "skill_category": "FIELD"}
        ]

        # Test with mix of cached and uncached
        mixed_skills = [
            {"skill_name": "Python", "skill_category": "SKILL"},  # Cached
            {"skill_name": "Rust", "skill_category": "SKILL"},    # Not cached
            {"skill_name": "Data Science", "skill_category": "FIELD"}  # Cached
        ]

        # Check cache for fully cached skills
        cached_results = checker._check_cache(cached_skills)
        assert len(cached_results) == 3
        assert "Python" in cached_results
        assert cached_results["Python"]["has_courses"] is True
        assert cached_results["Python"]["count"] == 10

        # Verify cached skills have been updated
        for skill in cached_skills:
            if skill["skill_name"] in ["Python", "JavaScript", "Data Science"]:
                assert skill["has_available_courses"] is True
                assert skill["course_count"] == 10

        # Check cache for mixed skills
        checker._check_cache(mixed_skills)
        cached_count = sum(1 for s in mixed_skills if "has_available_courses" in s)
        assert cached_count == 2  # Only Python and Data Science should be cached

    @pytest.mark.asyncio
    async def test_CA_004_UT_error_handling(self, checker, sample_skills):
        """
        Test ID: CA-004-UT
        Test Graceful Degradation error handling
        Priority: P0
        """
        # Test single skill failure
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536,  # Corrected to 1536 dimensions
                [0.2] * 1536,
                [0.3] * 1536
            ])
            mock_get_client.return_value = mock_client

            # Mock one successful and one failed query
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                if skill_name == "GraphQL":
                    raise TimeoutError("Query timeout")
                return {
                    "has_courses": True,
                    "count": 5,
                    "preferred_count": 3,
                    "other_count": 2
                }

            checker._check_single_skill = mock_check_skill

            # Execute check
            result = await checker.check_course_availability(sample_skills)

            # Verify results
            assert len(result) == 3

            # Rust should have been processed successfully
            rust_skill = next(s for s in result if s["skill_name"] == "Rust")
            assert rust_skill["has_available_courses"] is True
            assert rust_skill["course_count"] == 5  # From mock query

            # GraphQL should fail gracefully
            graphql_skill = next(s for s in result if s["skill_name"] == "GraphQL")
            assert graphql_skill["has_available_courses"] is False
            assert graphql_skill["course_count"] == 0

        # Test complete system failure
        # Create a fresh checker instance to avoid state pollution
        from src.services.course_availability import CourseAvailabilityChecker
        fresh_checker = CourseAvailabilityChecker()
        fresh_checker._connection_pool = AsyncMock()

        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Embedding service unavailable")

            # Create fresh skills to test (no cached values)
            fresh_skills = [
                {"skill_name": "Elixir", "skill_category": "SKILL", "description": "Functional programming"},
                {"skill_name": "Erlang", "skill_category": "SKILL", "description": "Concurrent programming"},
                {"skill_name": "Haskell", "skill_category": "FIELD", "description": "Pure functional language"}
            ]

            # Execute check
            result = await fresh_checker.check_course_availability(fresh_skills)

            # All skills should be marked as false
            assert len(result) == 3
            for skill in result:
                assert skill["has_available_courses"] is False
                assert skill["course_count"] == 0

    @pytest.mark.asyncio
    async def test_CA_005_UT_parallel_processing(self, checker):
        """
        Test ID: CA-005-UT
        Test asyncio.gather parallel execution
        Priority: P0
        """
        # Test skills (more than 3 to test parallel processing)
        test_skills = [
            {"skill_name": f"Skill{i}", "skill_category": "SKILL", "description": f"Test skill {i}"}
            for i in range(6)
        ]

        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1 * i] * 1536 for i in range(6)  # Correct dimension
            ])
            mock_get_client.return_value = mock_client

            # Track query execution order
            query_order = []

            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                query_order.append(skill_name)
                await asyncio.sleep(0.01)  # Simulate query time
                return {
                    "has_courses": True,
                    "count": 5,
                    "preferred_count": 3,
                    "other_count": 2
                }

            checker._check_single_skill = mock_check_skill

            # Execute check
            import time
            start_time = time.time()
            result = await checker.check_course_availability(test_skills)
            elapsed_time = time.time() - start_time

            # Verify all queries executed
            assert len(query_order) == 6
            assert all(f"Skill{i}" in query_order for i in range(6))

            # Verify parallel execution (should be much faster than sequential)
            # Sequential would take 6 * 0.01 = 0.06s minimum
            # Parallel should complete in roughly 0.01s + overhead
            assert elapsed_time < 0.05  # Allow some overhead

            # Verify results
            assert len(result) == 6
            for skill in result:
                assert skill["has_available_courses"] is True
                assert skill["course_count"] == 5

    @pytest.mark.asyncio
    async def test_empty_skill_list(self, checker):
        """Test handling of empty skill list"""
        result = await checker.check_course_availability([])
        assert result == []

    @pytest.mark.asyncio
    async def test_timeout_handling(self, checker):
        """Test query timeout handling"""
        embedding = [0.1] * 1536  # Correct dimension
        skill_name = "TestSkill"
        skill_category = "SKILL"

        # Mock slow database query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=TimeoutError())

        checker._connection_pool = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        checker._connection_pool.acquire.return_value = mock_ctx

        # Should raise timeout error
        with pytest.raises(TimeoutError):
            await checker._check_single_skill(embedding, skill_name, skill_category, timeout=0.001)
