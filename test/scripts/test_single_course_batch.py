#!/usr/bin/env python
"""Test single Course Batch Query test to diagnose CI failure."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")

# Import test dependencies
import pytest

from src.models.course_batch_simple import CourseDetailsBatchRequest
from src.services.course_search import CourseSearchService

# Load fixtures manually
fixture_path = Path("test/fixtures/course_batch")
print(f"\nFixture path: {fixture_path.absolute()}")
print(f"Exists: {fixture_path.exists()}")

try:
    with open(fixture_path / "test_data.json") as f:
        test_data = json.load(f)
    print(f"✅ Loaded test_data.json: {len(test_data)} keys")

    with open(fixture_path / "mock_courses.json") as f:
        mock_courses_data = json.load(f)
    mock_courses = mock_courses_data["courses"]
    print(f"✅ Loaded mock_courses.json: {len(mock_courses)} courses")
except Exception as e:
    print(f"❌ Error loading fixtures: {e}")
    sys.exit(1)

# Run the test manually
async def test_basic_batch_query():
    """Manually run the basic batch query test."""
    print("\n=== Running test manually ===")

    # Arrange
    test_case = test_data["basic_test"]
    request = CourseDetailsBatchRequest(**test_case)
    print(f"Request created with {len(request.course_ids)} course IDs")

    # Create service with mocked connection
    service = CourseSearchService()
    service._connection_pool = AsyncMock()

    # Mock database response
    mock_db_courses = [
        mock_courses[1],  # coursera_crse:v1-2599
        mock_courses[0],  # coursera_crse:v1-2598
        mock_courses[2],  # coursera_crse:v1-2600
    ]

    # Mock connection and query
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_db_courses)

    # Create async context manager mock
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    service._connection_pool.acquire = MagicMock(return_value=mock_context_manager)

    # Act
    try:
        result = await service.get_courses_by_ids(request)
        print("✅ Test completed successfully")
        print(f"   Result: success={result.success}, found={result.total_found}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the async test
import asyncio

success = asyncio.run(test_basic_batch_query())
sys.exit(0 if success else 1)
