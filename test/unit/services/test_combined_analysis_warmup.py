"""
Unit tests for pgvector warmup functionality in CombinedAnalysisServiceV2
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2


@pytest.mark.asyncio
class TestPgvectorWarmup:
    """Test pgvector warmup optimization"""

    async def test_warmup_pgvector_success(self):
        """Test successful pgvector warmup"""
        # Arrange
        service = CombinedAnalysisServiceV2()

        # Mock course search service
        mock_course_service = MagicMock()
        mock_connection_pool = AsyncMock()
        mock_course_service._connection_pool = mock_connection_pool

        # Mock connection acquisition
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=100)

        # Create a proper async context manager mock
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, *args):
                pass

        mock_connection_pool.acquire.return_value = AsyncContextManagerMock()

        with patch("src.services.course_search_singleton.get_course_search_service") as mock_get_service:
            # Mock the async function to return the service
            async def mock_async():
                return mock_course_service
            mock_get_service.side_effect = mock_async

            # Act
            result = await service._warmup_pgvector()

            # Assert
            assert result["completed"] is True
            assert result["duration_ms"] > 0
            assert result["connections_warmed"] > 0
            assert result["error"] is None

            # Verify warmup queries were executed
            assert mock_conn.fetchval.call_count == 2  # Two test vectors

    async def test_warmup_pgvector_no_connection_pool(self):
        """Test warmup when connection pool is not available"""
        # Arrange
        service = CombinedAnalysisServiceV2()

        # Mock course search service without connection pool
        mock_course_service = MagicMock()
        mock_course_service._connection_pool = None

        with patch("src.services.course_search_singleton.get_course_search_service") as mock_get_service:
            # Mock the async function to return the service
            async def mock_async():
                return mock_course_service
            mock_get_service.side_effect = mock_async

            # Act
            result = await service._warmup_pgvector()

            # Assert
            assert result["completed"] is False
            assert result["duration_ms"] > 0
            assert result["connections_warmed"] == 1  # Only service initialization
            assert result["error"] is None

    async def test_warmup_pgvector_exception_handling(self):
        """Test warmup handles exceptions gracefully"""
        # Arrange
        service = CombinedAnalysisServiceV2()

        with patch("src.services.course_search_singleton.get_course_search_service") as mock_get_service:
            mock_get_service.side_effect = Exception("Connection failed")

            # Act
            result = await service._warmup_pgvector()

            # Assert
            assert result["completed"] is False
            assert result["duration_ms"] > 0
            assert result["error"] == "Connection failed"
            assert result["connections_warmed"] == 0

    async def test_warmup_runs_in_parallel(self):
        """Test that warmup runs in parallel with other tasks"""
        # Arrange
        service = CombinedAnalysisServiceV2()

        # Mock course search service
        mock_course_service = MagicMock()
        mock_connection_pool = AsyncMock()
        mock_course_service._connection_pool = mock_connection_pool

        # Mock connection with delay
        mock_conn = AsyncMock()
        async def delayed_fetchval(*args):
            await asyncio.sleep(0.1)  # Simulate query time
            return 100
        mock_conn.fetchval = delayed_fetchval

        mock_connection_pool.acquire = AsyncMock()
        mock_connection_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_connection_pool.acquire.return_value.__aexit__ = AsyncMock()

        with patch("src.services.course_search_singleton.get_course_search_service") as mock_get_service:
            # Mock the async function to return the service
            async def mock_async():
                return mock_course_service
            mock_get_service.side_effect = mock_async

            # Act - Run warmup in parallel with another task
            start_time = time.time()

            async def other_task():
                """Simulated parallel task"""
                await asyncio.sleep(0.2)
                return "done"

            # Run both tasks in parallel
            warmup_task = asyncio.create_task(service._warmup_pgvector())
            other = asyncio.create_task(other_task())

            warmup_result, other_result = await asyncio.gather(warmup_task, other)

            elapsed = time.time() - start_time

            # Assert
            assert warmup_result["completed"] is True
            assert other_result == "done"
            # Both tasks should complete in ~0.2s (not 0.3s if sequential)
            assert elapsed < 0.25  # Allow some overhead

    async def test_warmup_with_query_failure(self):
        """Test warmup continues even if some queries fail"""
        # Arrange
        service = CombinedAnalysisServiceV2()

        # Mock course search service
        mock_course_service = MagicMock()
        mock_connection_pool = AsyncMock()
        mock_course_service._connection_pool = mock_connection_pool

        # Mock connection with one failing query
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=[100, Exception("Query failed")])

        mock_connection_pool.acquire = AsyncMock()
        mock_connection_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_connection_pool.acquire.return_value.__aexit__ = AsyncMock()

        with patch("src.services.course_search_singleton.get_course_search_service") as mock_get_service:
            # Mock the async function to return the service
            async def mock_async():
                return mock_course_service
            mock_get_service.side_effect = mock_async

            # Act
            result = await service._warmup_pgvector()

            # Assert
            assert result["completed"] is False
            assert result["error"] == "Query failed"
            assert result["duration_ms"] > 0
