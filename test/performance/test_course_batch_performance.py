"""
Performance tests for Course Batch Query API.

Test IDs: API-CDB-001-PT and API-CDB-002-PT
"""

import asyncio
import json
import os
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
import pytest
import pytest_asyncio
from matplotlib import pyplot as plt

from src.models.course_batch_simple import CourseDetailsBatchRequest, CourseDetailsBatchResponse
from src.services.course_search import CourseSearchService


class TestCourseBatchPerformance:
    """Performance tests for course batch query functionality."""

    @pytest_asyncio.fixture
    async def real_course_ids(self) -> dict[str, Any]:
        """
        Fetch real course IDs from database for performance testing.
        This fixture runs once per test class.
        """
        # Check if we have cached performance test data
        cache_file = Path("test/fixtures/course_batch/performance_course_ids.json")

        # If cache exists and is recent (< 24 hours), use it
        if cache_file.exists():
            with open(cache_file) as f:
                cached_data = json.load(f)
                # Check if data is recent
                if "generated_at" in cached_data:
                    generated_time = datetime.fromisoformat(cached_data["generated_at"])
                    if (datetime.now() - generated_time).days < 1:
                        print(f"Using cached course IDs from {cached_data['generated_at']}")
                        return cached_data

        # Otherwise, fetch from database
        print("Fetching real course IDs from database...")

        # Get database connection info from environment
        conn_info = {
            'host': os.getenv('POSTGRES_HOST'),
            'database': os.getenv('POSTGRES_DATABASE'),
            'user': os.getenv('POSTGRES_USER'),
            'password': os.getenv('POSTGRES_PASSWORD')
        }

        # Skip if no database config
        if not all(conn_info.values()):
            pytest.skip("Database configuration not available for performance tests")

        try:
            # Connect to database
            conn = await asyncpg.connect(
                **conn_info,
                ssl='require'
            )

            # Fetch 5 course IDs for P50 test
            small_batch_rows = await conn.fetch("""
                SELECT id, name FROM courses
                WHERE platform = 'coursera'
                AND embedding IS NOT NULL
                LIMIT 5
            """)

            # Fetch 100 course IDs for batch test
            large_batch_rows = await conn.fetch("""
                SELECT id, name FROM courses
                WHERE platform = 'coursera'
                AND embedding IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 100
            """)

            await conn.close()

            # Prepare test data
            test_data = {
                "small_batch": {
                    "description": "5 course IDs for P50 response time test",
                    "course_ids": [row['id'] for row in small_batch_rows],
                    "course_names": {row['id']: row['name'] for row in small_batch_rows}
                },
                "large_batch": {
                    "description": "100 course IDs for batch performance test",
                    "course_ids": [row['id'] for row in large_batch_rows],
                    "count": len(large_batch_rows)
                },
                "generated_at": datetime.now().isoformat(),
                "database": conn_info['database']
            }

            # Save to cache file
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(test_data, f, indent=2)

            print(f"✅ Fetched and cached {len(small_batch_rows)} + {len(large_batch_rows)} course IDs")
            return test_data

        except Exception as e:
            pytest.skip(f"Could not fetch real course IDs: {e}")

    @pytest_asyncio.fixture
    async def course_service(self) -> CourseSearchService:
        """Initialize CourseSearchService with mocked database for performance testing."""
        from unittest.mock import AsyncMock, MagicMock

        from asyncpg import Connection

        service = CourseSearchService()

        # Mock the connection pool for performance testing
        service.pool = AsyncMock()

        # Create realistic mock responses that simulate database latency
        async def mock_fetch(*args, **kwargs):
            # Simulate database query time (10-50ms)
            import random
            import time
            await asyncio.sleep(random.uniform(0.01, 0.05))  # 10-50ms  # noqa: S311

            # Return mock course data based on query
            course_ids = args[1] if len(args) > 1 else []
            mock_courses = []
            for course_id in course_ids:
                mock_courses.append({
                    'id': course_id,
                    'name': f'Mock Course {course_id.split("-")[-1]}',
                    'description': f'This is a mock course description for {course_id}. ' * 10,
                    'provider': 'Mock Provider',
                    'provider_standardized': 'Mock Provider',
                    'provider_logo_url': 'https://example.com/logo.png',
                    'price': 49.99,
                    'currency': 'USD',
                    'image_url': 'https://example.com/course.jpg',
                    'affiliate_url': f'https://example.com/course/{course_id}',
                    'course_type': 'course',
                    'duration': '40 hours',
                    'difficulty': 'Intermediate',
                    'rating': 4.7,
                    'enrollment_count': 150000
                })
            return mock_courses

        # Mock connection setup
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(side_effect=mock_fetch)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        service.pool.acquire = MagicMock(return_value=mock_context_manager)

        return service

    def _setup_mock_service(self) -> CourseSearchService:
        """Helper method to set up a mock service for testing."""
        from unittest.mock import AsyncMock, MagicMock

        from asyncpg import Connection

        service = CourseSearchService()

        # Mock the connection pool for performance testing
        service.pool = AsyncMock()

        # Create realistic mock responses that simulate database latency
        async def mock_fetch(*args, **kwargs):
            # Simulate database query time (10-50ms)
            import random
            await asyncio.sleep(random.uniform(0.01, 0.05))  # 10-50ms  # noqa: S311

            # Return mock course data based on query
            course_ids = args[1] if len(args) > 1 else []
            mock_courses = []
            for course_id in course_ids:
                mock_courses.append({
                    'id': course_id,
                    'name': f'Mock Course {course_id.split("-")[-1]}',
                    'description': f'This is a mock course description for {course_id}. ' * 10,
                    'provider': 'Mock Provider',
                    'provider_standardized': 'Mock Provider',
                    'provider_logo_url': 'https://example.com/logo.png',
                    'price': 49.99,
                    'currency': 'USD',
                    'image_url': 'https://example.com/course.jpg',
                    'affiliate_url': f'https://example.com/course/{course_id}',
                    'course_type': 'course',
                    'duration': '40 hours',
                    'difficulty': 'Intermediate',
                    'rating': 4.7,
                    'enrollment_count': 150000
                })
            return mock_courses

        # Mock connection setup
        mock_conn = AsyncMock(spec=Connection)
        mock_conn.fetch = AsyncMock(side_effect=mock_fetch)

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        service.pool.acquire = MagicMock(return_value=mock_context_manager)

        return service

    @pytest.mark.asyncio
    async def test_API_CDB_001_PT_p50_response_time(self, course_service, real_course_ids):
        """
        API-CDB-001-PT: Test median response time with cache hits.
        Target: P50 < 150ms for cached queries.
        """
        # Get test course IDs
        course_ids = real_course_ids["small_batch"]["course_ids"]

        print(f"\n🔬 Testing P50 response time with {len(course_ids)} courses")
        print(f"Course IDs: {course_ids[:2]}...")  # Show first 2 IDs

        # Phase 1: Warm-up query (populate cache)
        print("\n📊 Phase 1: Warm-up (populating cache)")

        request = CourseDetailsBatchRequest(
            course_ids=course_ids,
            enable_time_tracking=True,
            full_description=True
        )

        warmup_result = await course_service.get_courses_by_ids(request)
        assert warmup_result.success is True
        assert warmup_result.cache_hit_rate == 0.0  # First query, no cache

        print(f"  - Found {warmup_result.total_found} courses")
        print(f"  - Cache hit rate: {warmup_result.cache_hit_rate}")
        print(f"  - Initial query time: {self._extract_total_time(warmup_result)}ms")

        # Phase 2: Performance testing (20 iterations)
        print("\n📊 Phase 2: Performance testing (20 iterations)")

        response_times = []
        cache_hit_rates = []

        for i in range(20):
            start = time.perf_counter()
            result = await course_service.get_courses_by_ids(request)
            end = time.perf_counter()

            response_time_ms = (end - start) * 1000
            response_times.append(response_time_ms)
            cache_hit_rates.append(result.cache_hit_rate)

            if i % 5 == 0:
                print(f"  - Iteration {i+1}: {response_time_ms:.2f}ms (cache hit: {result.cache_hit_rate})")

        # Phase 3: Analysis
        print("\n📊 Phase 3: Performance Analysis")

        # Calculate percentiles
        p50 = statistics.median(response_times)
        p90 = sorted(response_times)[int(len(response_times) * 0.9)]
        p95 = sorted(response_times)[int(len(response_times) * 0.95)]
        avg_cache_hit = statistics.mean(cache_hit_rates[1:])  # Exclude first warmup

        print("\n✨ Performance Results:")
        print(f"  - P50 (median): {p50:.2f}ms")
        print(f"  - P90: {p90:.2f}ms")
        print(f"  - P95: {p95:.2f}ms")
        print(f"  - Min: {min(response_times):.2f}ms")
        print(f"  - Max: {max(response_times):.2f}ms")
        print(f"  - Avg cache hit rate: {avg_cache_hit:.2f}")

        # Assertions
        assert p50 < 150, f"P50 ({p50:.2f}ms) exceeds target of 150ms"
        assert p90 < 200, f"P90 ({p90:.2f}ms) exceeds target of 200ms"
        assert avg_cache_hit >= 0.95, f"Cache hit rate ({avg_cache_hit:.2f}) below expected 0.95"

        print("\n✅ Performance test passed!")

    @pytest.mark.asyncio
    async def test_API_CDB_002_PT_large_batch_query(self, course_service, real_course_ids):
        """
        API-CDB-002-PT: Test performance with 100 course IDs.
        Tests three scenarios: cold start, partial cache, full cache.
        """
        # Get test course IDs
        course_ids = real_course_ids["large_batch"]["course_ids"]

        print(f"\n🔬 Testing large batch performance with {len(course_ids)} courses")

        # Clear cache by creating a new mock service
        if hasattr(course_service, 'cache'):
            course_service.cache.clear()
        if hasattr(course_service, 'batch_cache'):
            course_service.batch_cache.clear()

        # Sub-test 1: Cold start performance
        print("\n📊 Sub-test 1: Cold Start Performance")

        request_full = CourseDetailsBatchRequest(
            course_ids=course_ids,
            enable_time_tracking=True,
            full_description=False,
            description_max_length=200
        )

        start = time.perf_counter()
        cold_result = await course_service.get_courses_by_ids(request_full)
        cold_time = (time.perf_counter() - start) * 1000

        print(f"  - Total time: {cold_time:.2f}ms")
        print(f"  - Cache hit rate: {cold_result.cache_hit_rate}")
        print(f"  - Courses found: {cold_result.total_found}")

        if cold_result.time_tracking:
            self._print_time_breakdown(cold_result.time_tracking)

        # Assertions for cold start
        assert cold_time < 500, f"Cold start time ({cold_time:.2f}ms) exceeds 500ms limit"
        assert cold_result.cache_hit_rate == 0.0, "Expected no cache hits on cold start"

        # Sub-test 2: Partial cache hit (50%)
        print("\n📊 Sub-test 2: Partial Cache Hit Performance (50%)")

        # Clear cache for partial test
        if hasattr(course_service, 'cache'):
            course_service.cache.clear()
        if hasattr(course_service, 'batch_cache'):
            course_service.batch_cache.clear()

        request_half = CourseDetailsBatchRequest(
            course_ids=course_ids[:50],
            enable_time_tracking=True,
            full_description=False,
            description_max_length=200
        )

        # Populate cache with first 50
        await course_service.get_courses_by_ids(request_half)

        # Now query all 100 (50 cached, 50 not)
        start = time.perf_counter()
        partial_result = await course_service.get_courses_by_ids(request_full)
        partial_time = (time.perf_counter() - start) * 1000

        print(f"  - Total time: {partial_time:.2f}ms")
        print(f"  - Cache hit rate: {partial_result.cache_hit_rate}")
        print(f"  - From cache: {partial_result.from_cache_count}")

        if partial_result.time_tracking:
            self._print_time_breakdown(partial_result.time_tracking)

        # Assertions for partial cache
        assert partial_time < 300, f"Partial cache time ({partial_time:.2f}ms) exceeds 300ms limit"
        assert 0.4 <= partial_result.cache_hit_rate <= 0.6, f"Cache hit rate ({partial_result.cache_hit_rate}) not around 50%"

        # Sub-test 3: Full cache hit
        print("\n📊 Sub-test 3: Full Cache Hit Performance (100%)")

        # Query again - all should be cached now
        start = time.perf_counter()
        cached_result = await course_service.get_courses_by_ids(request_full)
        cached_time = (time.perf_counter() - start) * 1000

        print(f"  - Total time: {cached_time:.2f}ms")
        print(f"  - Cache hit rate: {cached_result.cache_hit_rate}")
        print(f"  - From cache: {cached_result.from_cache_count}")

        if cached_result.time_tracking:
            self._print_time_breakdown(cached_result.time_tracking)

        # Assertions for full cache
        assert cached_time < 100, f"Full cache time ({cached_time:.2f}ms) exceeds 100ms limit"
        assert cached_result.cache_hit_rate >= 0.95, f"Cache hit rate ({cached_result.cache_hit_rate}) below expected 0.95"

        # Performance comparison
        print("\n📊 Performance Comparison:")
        print(f"  - Cold start: {cold_time:.2f}ms (baseline)")
        print(f"  - Partial cache (50%): {partial_time:.2f}ms ({(partial_time/cold_time)*100:.1f}% of cold)")
        print(f"  - Full cache (100%): {cached_time:.2f}ms ({(cached_time/cold_time)*100:.1f}% of cold)")
        print(f"  - Speed improvement: {cold_time/cached_time:.1f}x faster with full cache")

        print("\n✅ All performance sub-tests passed!")

    def _extract_total_time(self, result: CourseDetailsBatchResponse) -> float:
        """Extract total time from response."""
        if result.time_tracking and "summary" in result.time_tracking:
            return result.time_tracking["summary"].get("total_ms", 0)
        return 0

    def _print_time_breakdown(self, time_tracking: dict[str, Any]):
        """Print time breakdown from tracking data."""
        if "summary" in time_tracking:
            summary = time_tracking["summary"]
            print("  - Time breakdown:")
            print(f"    • Preparation: {summary.get('preparation_pct', 0):.1f}%")
            print(f"    • Cache ops: {summary.get('cache_operations_pct', 0):.1f}%")
            print(f"    • DB ops: {summary.get('db_operations_pct', 0):.1f}%")
            print(f"    • Processing: {summary.get('processing_pct', 0):.1f}%")

    @pytest.mark.asyncio
    async def test_generate_gantt_chart(self, course_service, real_course_ids):
        """
        Generate Gantt chart visualization for time breakdown analysis.
        This is a helper test to visualize performance data.
        """
        course_ids = real_course_ids["small_batch"]["course_ids"][:3]

        request = CourseDetailsBatchRequest(
            course_ids=course_ids,
            enable_time_tracking=True,
            full_description=False
        )

        # Get timing data
        result = await course_service.get_courses_by_ids(request)

        if not result.time_tracking or "timeline" not in result.time_tracking:
            pytest.skip("No timing data available for visualization")

        timeline = result.time_tracking["timeline"]

        # Create Gantt chart
        fig, ax = plt.subplots(figsize=(10, 4))

        # Define colors for each task
        colors = {
            "preparation": "#3498db",      # Blue
            "cache_operations": "#2ecc71", # Green
            "db_operations": "#e67e22",    # Orange
            "processing": "#9b59b6"        # Purple
        }

        # Plot each task as a horizontal bar
        for i, task in enumerate(timeline):
            task_name = task["task"]
            start = task.get("start_time", 0)
            duration = task["duration_ms"]

            ax.barh(
                i, duration, left=start,
                height=0.5,
                color=colors.get(task_name, "#95a5a6"),
                label=f"{task_name} ({duration}ms)"
            )

            # Add task label
            ax.text(
                start + duration/2, i,
                f"{duration}ms",
                ha='center', va='center',
                color='white', fontweight='bold'
            )

        # Customize chart
        ax.set_yticks(range(len(timeline)))
        ax.set_yticklabels([t["task"] for t in timeline])
        ax.set_xlabel("Time (milliseconds)")
        total_ms = result.time_tracking.get('total_ms', result.time_tracking.get('summary', {}).get('total_ms', 0))
        ax.set_title(f"Course Batch Query Time Breakdown\nTotal: {total_ms}ms")
        ax.legend(loc='upper right')
        ax.grid(axis='x', alpha=0.3)

        # Save chart
        output_dir = Path("test/performance/charts")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"gantt_chart_{timestamp}.png"

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"\n📊 Gantt chart saved to: {output_file}")

        # Also create a detailed performance report
        self._generate_performance_report(result, output_dir / f"performance_report_{timestamp}.json")

    def _generate_performance_report(self, result: CourseDetailsBatchResponse, output_file: Path):
        """Generate detailed performance report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_id": "API-CDB-002-PT",
            "courses_requested": result.requested_count,
            "courses_found": result.total_found,
            "cache_metrics": {
                "hit_rate": result.cache_hit_rate,
                "from_cache": result.from_cache_count
            },
            "time_tracking": result.time_tracking,
            "performance_targets": {
                "p50_target_ms": 150,
                "p90_target_ms": 200,
                "p95_target_ms": 300,
                "cold_start_target_ms": 500,
                "full_cache_target_ms": 100
            }
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Performance report saved to: {output_file}")
