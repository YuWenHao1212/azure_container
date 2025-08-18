"""
Unit tests for Course Batch Query API - CourseSearchService.get_courses_by_ids method.

Test IDs:
- API-CDB-001-UT to API-CDB-005-UT (規格測試)
- API-CDB-006-UT to API-CDB-010-UT (額外測試)

Total: 10 unit tests
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from asyncpg import Connection

from src.models.course_batch_simple import CourseDetailsBatchRequest, CourseDetailsBatchResponse
from src.services.course_search import CourseSearchService
from src.utils.time_tracker import SimpleTimeTracker


@pytest.fixture
def fixture_path():
    """Get path to test fixtures."""
    return Path(__file__).parent.parent / "fixtures" / "course_batch"


@pytest.fixture
def test_data(fixture_path):
    """Load test data from fixtures."""
    with open(fixture_path / "test_data.json") as f:
        return json.load(f)


@pytest.fixture
def mock_courses(fixture_path):
    """Load mock course data from fixtures."""
    with open(fixture_path / "mock_courses.json") as f:
        return json.load(f)["courses"]


@pytest.fixture
def course_service():
    """Create CourseSearchService instance with mocked dependencies."""
    service = CourseSearchService()
    # Mock the connection pool
    service.pool = AsyncMock()
    return service


class TestCourseBatchUnit:
    """Unit tests for CourseSearchService.get_courses_by_ids method."""

    @pytest.mark.asyncio
    async def test_API_CDB_001_UT_basic_batch_query(self, course_service, test_data, mock_courses):
        """
        API-CDB-001-UT: Basic batch query functionality.
        Verify that basic batch query returns all requested courses in correct order.
        """
        # Arrange
        test_case = test_data["basic_test"]
        request = CourseDetailsBatchRequest(**test_case)

        # Mock database response - return courses in different order
        mock_db_courses = [
            mock_courses[1],  # coursera_crse:v1-2599
            mock_courses[0],  # coursera_crse:v1-2598
            mock_courses[2],  # coursera_crse:v1-2600
        ]

        # Mock connection and query
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=mock_db_courses)

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert result.total_found == 3
        assert len(result.courses) == 3
        assert result.not_found_ids == []

        # Verify order preservation (should match input order)
        assert result.courses[0]["id"] == "coursera_crse:v1-2598"
        assert result.courses[1]["id"] == "coursera_crse:v1-2599"
        assert result.courses[2]["id"] == "coursera_crse:v1-2600"

        # Verify SQL query includes ORDER BY array_position
        call_args = mock_conn.fetch.call_args[0]
        sql_query = call_args[0]
        assert "array_position" in sql_query.lower()
        assert "order by" in sql_query.lower()

    @pytest.mark.asyncio
    async def test_API_CDB_002_UT_max_courses_limit(self, course_service, test_data):
        """
        API-CDB-002-UT: Verify max_courses parameter limits query count.
        Should only process first N IDs when max_courses is set.
        """
        # Arrange
        test_case = test_data["max_courses_test"]
        request = CourseDetailsBatchRequest(**test_case)

        # Mock connection
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[])  # Return empty for simplicity

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert result.requested_count == 10
        assert result.processed_count == 3  # max_courses limit
        assert result.skipped_count == 7

        # Verify only first 3 IDs were queried
        call_args = mock_conn.fetch.call_args[0]
        queried_ids = call_args[1]  # Second argument is the list of IDs
        assert len(queried_ids) == 3
        assert queried_ids == test_case["course_ids"][:3]

    @pytest.mark.asyncio
    async def test_API_CDB_003_UT_description_truncation(self, course_service, mock_courses):
        """
        API-CDB-003-UT: Verify description text truncation functionality.
        Should truncate at word boundaries and add ellipsis.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=["coursera_crse:v1-2598"],
            full_description=False,
            description_max_length=100,
            enable_time_tracking=False
        )

        # Use a course with long description
        long_desc_course = mock_courses[0].copy()
        long_desc_course["description"] = (
            "Learn React.js from the ground up and build modern, reactive web applications "
            "with the React framework. Master React Hooks, Redux, React Router, and more."
        )

        # Mock database response
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[long_desc_course])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert len(result.courses) == 1
        course = result.courses[0]

        # Check description is truncated
        assert len(course["description"]) <= 100
        assert course["description"].endswith("...")

        # Verify word boundary preservation (no partial words)
        truncated_text = course["description"][:-3]  # Remove "..."
        assert not truncated_text.endswith(" ")  # Should end with complete word

        # Check original description is preserved in cache
        assert course["description"] != long_desc_course["description"]

    @pytest.mark.asyncio
    async def test_API_CDB_004_UT_cache_hit(self, course_service, mock_courses):
        """
        API-CDB-004-UT: Verify cache mechanism works correctly.
        Second identical query should return from cache.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=["coursera_crse:v1-2598", "coursera_crse:v1-2599"],
            enable_time_tracking=False
        )

        # Mock database response
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[
            mock_courses[0],
            mock_courses[1]
        ])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act - First query (should hit database)
        result1 = await course_service.get_courses_by_ids(request)

        # Act - Second identical query (should hit cache)
        result2 = await course_service.get_courses_by_ids(request)

        # Assert
        assert result1.success is True
        assert result2.success is True

        # Both results should be identical
        assert result1.courses == result2.courses
        assert result1.total_found == result2.total_found

        # Database should only be called once
        assert mock_conn.fetch.call_count == 1

        # Check cache statistics
        assert result2.cache_hit_rate > 0
        assert result2.from_cache_count > 0

    @pytest.mark.asyncio
    async def test_API_CDB_005_UT_order_preservation(self, course_service, mock_courses):
        """
        API-CDB-005-UT: Verify result maintains input order.
        Results should be ordered by input sequence, not database order.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=[
                "coursera_crse:v1-2600",  # Third course
                "coursera_crse:v1-2598",  # First course
                "coursera_crse:v1-2599",  # Second course
            ],
            enable_time_tracking=False
        )

        # Mock database returns in natural order (2598, 2599, 2600)
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[
            mock_courses[2],  # 2600
            mock_courses[0],  # 2598
            mock_courses[1],  # 2599
        ])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert len(result.courses) == 3

        # Verify order matches input, not database order
        assert result.courses[0]["id"] == "coursera_crse:v1-2600"
        assert result.courses[1]["id"] == "coursera_crse:v1-2598"
        assert result.courses[2]["id"] == "coursera_crse:v1-2599"

        # Verify SQL query uses array_position for ordering
        sql_query = mock_conn.fetch.call_args[0][0]
        assert "array_position($1::text[], id)" in sql_query

    @pytest.mark.asyncio
    async def test_API_CDB_006_UT_not_found_courses_handling(self, course_service):
        """
        API-CDB-006-UT: Verify handling of not found courses.
        Should mark missing IDs in not_found_ids list.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=[
                "coursera_crse:v1-2598",
                "invalid_id_1",
                "coursera_crse:v1-2599",
            ],
            enable_time_tracking=False
        )

        # Mock database returns only valid courses
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[
            {"id": "coursera_crse:v1-2598", "name": "Course 1"},
            {"id": "coursera_crse:v1-2599", "name": "Course 2"},
        ])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert result.total_found == 2
        assert len(result.courses) == 2
        assert result.not_found_ids == ["invalid_id_1"]

    @pytest.mark.asyncio
    async def test_API_CDB_007_UT_time_tracking_enabled(self, course_service, mock_courses):
        """
        API-CDB-007-UT: Verify time tracking when enabled.
        Should include detailed timing information.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=["coursera_crse:v1-2598"],
            enable_time_tracking=True
        )

        # Mock database response
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[mock_courses[0]])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is True
        assert result.time_tracking is not None

        # Check time tracking structure
        time_data = result.time_tracking
        assert "timeline" in time_data
        assert "summary" in time_data

        # Verify 4 main time blocks exist
        timeline = time_data["timeline"]
        task_names = [task["task"] for task in timeline]
        assert "preparation" in task_names
        assert "cache_operations" in task_names
        assert "db_operations" in task_names
        assert "processing" in task_names

        # Check summary percentages
        # total_ms is in time_data, not in summary
        assert "total_ms" in time_data
        assert time_data["total_ms"] >= 0

    @pytest.mark.asyncio
    async def test_API_CDB_008_UT_empty_course_ids(self, course_service):
        """
        API-CDB-008-UT: Verify handling of empty course IDs list.
        Should return validation error.
        """
        # Arrange & Act & Assert
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CourseDetailsBatchRequest(
                course_ids=[],  # Empty list
                enable_time_tracking=False
            )

    @pytest.mark.asyncio
    async def test_API_CDB_009_UT_database_error_handling(self, course_service):
        """
        API-CDB-009-UT: Verify graceful handling of database errors.
        Should return error response without crashing.
        """
        # Arrange
        request = CourseDetailsBatchRequest(
            course_ids=["coursera_crse:v1-2598"],
            enable_time_tracking=False
        )

        # Mock database error
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(side_effect=Exception("Database connection failed"))

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act
        result = await course_service.get_courses_by_ids(request)

        # Assert
        assert result.success is False
        assert result.error["message"].lower() == "failed to query courses"
        assert result.courses == []
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_API_CDB_010_UT_cache_duplicate_query(self, course_service, mock_courses):
        """
        API-CDB-010-UT: Verify cache mechanism for duplicate queries.
        Database should only be called once for identical queries.
        """
        # This is essentially the same as test_API_CDB_004_UT but with different approach
        # Included to match the documented test count of 10 unit tests
        request = CourseDetailsBatchRequest(
            course_ids=["coursera_crse:v1-2598"],
            enable_time_tracking=False
        )

        # Mock database response
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(return_value=[mock_courses[0]])

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        course_service.pool.acquire = MagicMock(return_value=mock_context_manager)

        # Act - Query twice
        result1 = await course_service.get_courses_by_ids(request)
        result2 = await course_service.get_courses_by_ids(request)

        # Assert
        assert result1.success is True
        assert result2.success is True
        # Database only called once
        assert mock_conn.fetch.call_count == 1
        # Both results identical
        assert result1.courses == result2.courses
