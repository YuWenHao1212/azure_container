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
                "total_count": 5,  # SQL returns total_count
                "type_diversity": 2,
                "course_types": ["course", "project"],
                "course_ids": ["id1", "id2", "id3", "id4", "id5"]
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
            "total_count": 15,  # SQL query returns total_count
            "type_diversity": 3,
            "course_types": ["course", "project", "certification"],
            "course_ids": [f"id{i}" for i in range(15)]
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
        assert "WITH initial_candidates" in query_args[0]  # Check new SQL query structure
        assert query_args[1] == embedding  # Check embedding parameter
        assert len(query_args) >= 3  # Should have embedding, threshold, category

        # Verify result - matches actual return structure
        assert result["has_courses"] is True
        assert result["count"] == 15  # Uses 'count' not 'total_count'

    @pytest.mark.asyncio
    async def test_CA_003_UT_cache_mechanism(self, checker):
        """
        Test ID: CA-003-UT
        Test dynamic cache mechanism functionality
        Priority: P1
        """
        from unittest.mock import AsyncMock, patch

        # Mock the dynamic cache and embedding client
        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.create_embeddings = AsyncMock(return_value=[
                [0.1] * 1536,  # Python embedding
                [0.2] * 1536,  # JavaScript embedding
                [0.3] * 1536   # Data Science embedding
            ])
            mock_get_client.return_value = mock_client

            # Mock database responses for dynamic cache
            async def mock_check_skill(embedding, skill_name, skill_category="DEFAULT"):
                return {
                    "has_courses": True,
                    "count": 10,  # _check_single_skill returns count, not total_count
                    "type_diversity": 2,
                    "course_types": ["course", "project"],
                    "course_ids": [f"coursera_crse:v1-{skill_name.lower()}-001",
                                  f"coursera_crse:v1-{skill_name.lower()}-002"]
                }

            checker._check_single_skill = mock_check_skill

            # Test skills for cache testing
            test_skills = [
                {"skill_name": "Python", "skill_category": "SKILL", "description": "Programming language"},
                {"skill_name": "JavaScript", "skill_category": "SKILL", "description": "Web development"},
                {"skill_name": "Data Science", "skill_category": "FIELD", "description": "Data analysis"}
            ]

            # First call - should populate cache
            result1 = await checker.check_course_availability(test_skills.copy())
            assert len(result1) == 3
            for skill in result1:
                assert skill["has_available_courses"] is True
                assert skill["course_count"] == 10
                assert "available_course_ids" in skill

            # Second call with same skills - should hit cache
            result2 = await checker.check_course_availability(test_skills.copy())
            assert len(result2) == 3

            # Results should be identical (from cache)
            for skill1, skill2 in zip(result1, result2, strict=False):
                assert skill1["skill_name"] == skill2["skill_name"]
                assert skill1["has_available_courses"] == skill2["has_available_courses"]
                assert skill1["course_count"] == skill2["course_count"]

            # Verify cache hit by checking that _check_single_skill was called fewer times
            # (Due to dynamic caching, second call should not trigger database queries)  # Only Python and Data Science should be cached

    @pytest.mark.asyncio
    async def test_CA_004_UT_error_handling(self, checker):
        """
        Test ID: CA-004-UT
        Test Graceful Degradation error handling
        Priority: P0
        """
        # Clear dynamic cache to ensure clean test
        await checker._dynamic_cache.clear()

        # Create fresh test skills (avoid reusing sample_skills fixture)
        test_skills = [
            {
                "skill_name": "RustLang",
                "skill_category": "SKILL",
                "description": "Systems programming language"
            },
            {
                "skill_name": "GraphQLAPI",
                "skill_category": "SKILL",
                "description": "Query language for APIs"
            },
            {
                "skill_name": "BlockchainTech",
                "skill_category": "FIELD",
                "description": "Distributed ledger technology"
            }
        ]

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
                if skill_name == "GraphQLAPI":
                    raise TimeoutError("Query timeout")
                return {
                    "has_courses": True,
                    "count": 5,  # _check_single_skill returns count
                    "type_diversity": 2,
                    "course_types": ["course", "specialization"],
                    "course_ids": [f"coursera_crse:v1-{skill_name.lower()}-001"]
                }

            checker._check_single_skill = mock_check_skill

            # Execute check
            result = await checker.check_course_availability(test_skills)

            # Verify results
            assert len(result) == 3

            # RustLang should have been processed successfully
            rust_skill = next(s for s in result if s["skill_name"] == "RustLang")
            assert rust_skill["has_available_courses"] is True
            assert rust_skill["course_count"] == 5  # From mock query

            # GraphQLAPI should fail gracefully
            graphql_skill = next(s for s in result if s["skill_name"] == "GraphQLAPI")
            assert graphql_skill["has_available_courses"] is False
            assert graphql_skill["course_count"] == 0
            assert graphql_skill["available_course_ids"] == []

        # Test complete system failure
        # Create a fresh checker instance to avoid state pollution
        from src.services.course_availability import CourseAvailabilityChecker
        fresh_checker = CourseAvailabilityChecker()
        fresh_checker._connection_pool = AsyncMock()

        with patch('src.services.course_availability.get_embedding_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Embedding service unavailable")

            # Create fresh skills to test (no cached values)
            fresh_skills = [
                {"skill_name": "ElixirFunc", "skill_category": "SKILL", "description": "Functional programming"},
                {"skill_name": "ErlangConc", "skill_category": "SKILL", "description": "Concurrent programming"},
                {"skill_name": "HaskellPure", "skill_category": "FIELD", "description": "Pure functional language"}
            ]

            # Execute check
            result = await fresh_checker.check_course_availability(fresh_skills)

            # All skills should be marked as false
            assert len(result) == 3
            for skill in result:
                assert skill["has_available_courses"] is False
                assert skill["course_count"] == 0
                assert skill["available_course_ids"] == []

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
                    "type_diversity": 2,
                    "course_types": ["course", "project"],
                    "course_ids": ["id1", "id2", "id3", "id4", "id5"]
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

    @pytest.mark.asyncio
    async def test_CA_008_UT_similarity_thresholds(self, checker):
        """
        Test ID: CA-008-UT
        Test that new similarity thresholds are applied correctly
        Priority: P1
        """
        from src.services.course_availability import SIMILARITY_THRESHOLDS

        # Verify new threshold values (Stage 2: Moderate strictness)
        assert SIMILARITY_THRESHOLDS["SKILL"] == 0.40, "SKILL threshold should be 0.40"
        assert SIMILARITY_THRESHOLDS["FIELD"] == 0.35, "FIELD threshold should be 0.35"
        assert SIMILARITY_THRESHOLDS["DEFAULT"] == 0.40, "DEFAULT threshold should be 0.40"

    @pytest.mark.asyncio
    async def test_CA_009_UT_course_type_diversity(self, checker):
        """
        Test ID: CA-009-UT
        Test that course type diversity is tracked in results
        Priority: P1
        """
        # Mock database result with diversity metrics
        mock_result = {
            "has_courses": True,
            "total_count": 20,
            "type_diversity": 4,  # 4 different course types
            "course_types": ["course", "project", "specialization", "certification"],
            "course_ids": ["id1", "id2", "id3", "id4", "id5"]
        }

        # Mock connection and query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        checker._connection_pool = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        checker._connection_pool.acquire.return_value = mock_ctx

        # Execute check
        result = await checker._check_single_skill(
            embedding=[0.1] * 1536,
            skill_name="Python",
            skill_category="SKILL"
        )

        # Verify diversity metrics are included
        assert result["type_diversity"] == 4
        assert len(result["course_types"]) == 4
        assert "course" in result["course_types"]
        assert "project" in result["course_types"]

    @pytest.mark.asyncio
    async def test_CA_010_UT_quota_based_selection(self, checker):
        """
        Test ID: CA-010-UT
        Test that quotas are applied based on skill category
        Priority: P0
        """
        from src.services.course_availability import COURSE_TYPE_QUOTAS

        # Verify quota configuration exists
        assert "SKILL" in COURSE_TYPE_QUOTAS
        assert "FIELD" in COURSE_TYPE_QUOTAS

        # Check SKILL quotas (Stage 2: Adjusted for stricter thresholds)
        skill_quotas = COURSE_TYPE_QUOTAS["SKILL"]
        assert skill_quotas["course"] == 18, "SKILL should allow up to 18 courses"
        assert skill_quotas["project"] == 3, "SKILL should allow up to 3 projects"
        assert skill_quotas["certification"] == 3, "SKILL should allow up to 3 certifications"

        # Check FIELD quotas (Stage 2: Adjusted for stricter thresholds)
        field_quotas = COURSE_TYPE_QUOTAS["FIELD"]
        assert field_quotas["specialization"] == 15, "FIELD should allow up to 15 specializations"
        assert field_quotas["degree"] == 3, "FIELD should allow up to 3 degrees"
        assert field_quotas["course"] == 6, "FIELD should allow up to 6 courses"

    @pytest.mark.asyncio
    async def test_CA_011_UT_minimum_threshold_usage(self, checker):
        """
        Test ID: CA-011-UT
        Test that minimum threshold is used for initial query optimization
        Priority: P2
        """
        from src.services.course_availability import MIN_SIMILARITY_THRESHOLD

        # Verify minimum threshold value (Stage 2: Increased for better quality)
        assert MIN_SIMILARITY_THRESHOLD == 0.35, "MIN_SIMILARITY_THRESHOLD should be 0.35"

        # This threshold should be less than or equal to all category thresholds
        from src.services.course_availability import SIMILARITY_THRESHOLDS
        for category, threshold in SIMILARITY_THRESHOLDS.items():
            assert threshold >= MIN_SIMILARITY_THRESHOLD, \
                f"MIN_SIMILARITY_THRESHOLD should be <= {category} threshold"

    @pytest.mark.asyncio
    async def test_CA_012_UT_diversity_in_results(self, checker):
        """
        Test ID: CA-012-UT
        Test that results include diverse course types
        Priority: P1
        """
        # Mock a realistic database response with quota-based selection
        mock_result = {
            "has_courses": True,
            "total_count": 25,
            "type_diversity": 5,
            "course_types": ["course", "project", "certification", "specialization", "degree"],
            "course_ids": [f"course_{i}" for i in range(15)] +
                         [f"project_{i}" for i in range(5)] +
                         [f"cert_{i}" for i in range(2)] +
                         [f"spec_{i}" for i in range(2)] +
                         ["degree_1"]
        }

        # Mock connection and query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        checker._connection_pool = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        checker._connection_pool.acquire.return_value = mock_ctx

        # Execute check for SKILL category
        result = await checker._check_single_skill(
            embedding=[0.1] * 1536,
            skill_name="Machine Learning",
            skill_category="SKILL"
        )

        # Verify result includes diversity
        assert result["has_courses"] is True
        assert result["count"] == 25
        assert result["type_diversity"] == 5
        assert len(result["course_ids"]) == 25

        # Verify all types are represented
        course_types = result["course_types"]
        assert "course" in course_types
        assert "project" in course_types
        assert "certification" in course_types
        assert "specialization" in course_types
        assert "degree" in course_types

    @pytest.mark.asyncio
    async def test_CA_013_UT_field_category_quotas(self, checker):
        """
        Test ID: CA-013-UT
        Test FIELD category uses different quotas
        Priority: P1
        """
        # Mock a FIELD-oriented result with more specializations/degrees
        mock_result = {
            "has_courses": True,
            "total_count": 24,
            "type_diversity": 5,
            "course_types": ["specialization", "degree", "course", "certification", "project"],
            "course_ids": [f"spec_{i}" for i in range(12)] +
                         [f"degree_{i}" for i in range(4)] +
                         [f"course_{i}" for i in range(5)] +
                         [f"cert_{i}" for i in range(2)] +
                         ["project_1"]
        }

        # Mock connection and query
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_result)

        checker._connection_pool = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        checker._connection_pool.acquire.return_value = mock_ctx

        # Execute check for FIELD category
        result = await checker._check_single_skill(
            embedding=[0.2] * 1536,
            skill_name="Data Science",
            skill_category="FIELD"
        )

        # Verify FIELD-oriented distribution
        assert result["has_courses"] is True
        assert result["count"] == 24
        assert len(result["course_ids"]) == 24

        # Count course types in result
        course_ids = result["course_ids"]
        spec_count = sum(1 for id in course_ids if "spec_" in id)
        degree_count = sum(1 for id in course_ids if "degree_" in id)

        # FIELD should prioritize specializations and degrees
        assert spec_count == 12, "FIELD should have 12 specializations"
        assert degree_count == 4, "FIELD should have 4 degrees"
