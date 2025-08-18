"""
Integration tests for Course Batch Query API endpoint.

Test IDs:
- API-CDB-001-IT to API-CDB-005-IT (規格測試)
- API-CDB-006-IT to API-CDB-009-IT (額外測試)

Total: 9 integration tests (5 spec + 4 additional)
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.course_batch_simple import CourseDetailsBatchRequest, CourseDetailsBatchResponse


@pytest.fixture
def valid_api_key():
    """Provide valid API key for testing."""
    # For integration tests, we need to set a test API key
    # This ensures the middleware authentication is active
    test_key = "test-api-key-for-integration"
    os.environ["CONTAINER_APP_API_KEY"] = test_key
    yield test_key
    # Clean up after test
    if "CONTAINER_APP_API_KEY" in os.environ:
        del os.environ["CONTAINER_APP_API_KEY"]


@pytest.fixture
def client(valid_api_key):
    """Create test client for FastAPI app with API key set."""
    # Import app after API key is set
    from src.main import app
    return TestClient(app)


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


class TestCourseBatchIntegration:
    """Integration tests for /api/v1/courses/get-by-ids endpoint."""

    def test_API_CDB_001_IT_api_endpoint_basic_functionality(self, client, test_data, mock_courses, valid_api_key):
        """
        API-CDB-001-IT: POST /api/v1/courses/get-by-ids basic functionality.
        Verify API endpoint works correctly with time tracking.
        """
        # Arrange
        test_case = {
            "course_ids": ["coursera_crse:v1-2598", "coursera_crse:v1-2599"],
            "enable_time_tracking": True
        }

        # Mock the CourseSearchService to return predictable data
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            mock_response = CourseDetailsBatchResponse(
                success=True,
                courses=[mock_courses[0], mock_courses[1]],
                total_found=2,
                requested_count=2,
                processed_count=2,
                skipped_count=0,
                not_found_ids=[],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=False,
                fallback_url=None,
                time_tracking={
                    "timeline": [
                        {"task_name": "preparation", "start_time": 0, "end_time": 5, "duration_ms": 5},
                        {"task_name": "cache_operations", "start_time": 5, "end_time": 15, "duration_ms": 10},
                        {"task_name": "db_operations", "start_time": 15, "end_time": 45, "duration_ms": 30},
                        {"task_name": "processing", "start_time": 45, "end_time": 50, "duration_ms": 5}
                    ],
                    "summary": {
                        "total_ms": 50,
                        "preparation_pct": 10.0,
                        "cache_operations_pct": 20.0,
                        "db_operations_pct": 60.0,
                        "processing_pct": 10.0
                    },
                    "metadata": {
                        "courses_requested": 2,
                        "courses_found": 2
                    }
                },
                error={"code": "", "message": "", "details": ""}
            )
            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=mock_response)
            mock_get_instance.return_value = mock_service

            # Act
            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=test_case,
                headers={"X-API-Key": valid_api_key}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert len(data["courses"]) == 2
            assert data["total_found"] == 2
            assert data["time_tracking"] is not None

            # Verify time tracking structure
            time_data = data["time_tracking"]
            assert "timeline" in time_data
            assert "summary" in time_data
            assert "metadata" in time_data

            # Check 4 time blocks exist
            timeline = time_data["timeline"]
            assert len(timeline) == 4
            task_names = [task["task_name"] for task in timeline]
            assert "preparation" in task_names
            assert "cache_operations" in task_names
            assert "db_operations" in task_names
            assert "processing" in task_names

    def test_API_CDB_002_IT_boundary_value_testing(self, client, valid_api_key):
        """
        API-CDB-002-IT: Test 1-100 ID boundary cases.
        Verify min and max input limits.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            # Test case 1: Single ID (minimum)
            single_id_request = {
                "course_ids": ["coursera_crse:v1-2598"],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[{"id": "coursera_crse:v1-2598", "name": "Test Course"}],
                total_found=1,
                requested_count=1,
                processed_count=1,
                skipped_count=0,
                not_found_ids=[],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=False,
                fallback_url=None,
                time_tracking=None,
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=single_id_request,
                headers={"X-API-Key": valid_api_key}
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert len(response.json()["courses"]) == 1

            # Test case 2: 100 IDs (maximum)
            max_ids_request = {
                "course_ids": [f"coursera_crse:v1-{i}" for i in range(1000, 1100)],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[],  # Empty for simplicity
                total_found=0,
                requested_count=100,
                processed_count=100,
                skipped_count=0,
                not_found_ids=[],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=False,
                fallback_url=None,
                time_tracking=None,
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=max_ids_request,
                headers={"X-API-Key": valid_api_key}
            )
            assert response.status_code == 200

            # Test case 3: 101 IDs (over limit - should fail validation)
            over_limit_request = {
                "course_ids": [f"coursera_crse:v1-{i}" for i in range(1000, 1101)],
                "enable_time_tracking": False
            }

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=over_limit_request,
                headers={"X-API-Key": valid_api_key}
            )
            assert response.status_code == 422  # Validation error

            # Test case 4: Empty list (should fail validation)
            empty_request = {
                "course_ids": [],
                "enable_time_tracking": False
            }

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=empty_request,
                headers={"X-API-Key": valid_api_key}
            )
            assert response.status_code == 422  # Validation error

    def test_API_CDB_003_IT_error_handling(self, client, valid_api_key):
        """
        API-CDB-003-IT: Verify error handling for various error conditions.
        Test invalid IDs, not found courses, and mixed scenarios.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            # Test case 1: All invalid/not found IDs
            not_found_request = {
                "course_ids": ["invalid_id_1", "invalid_id_2", "not_exist_id"],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[],
                total_found=0,
                requested_count=3,
                processed_count=3,
                skipped_count=0,
                not_found_ids=["invalid_id_1", "invalid_id_2", "not_exist_id"],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=True,
                fallback_url="https://coursera.org/search",
                time_tracking=None,
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=not_found_request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200  # Still returns 200 for Bubble.io compatibility
            data = response.json()
            assert data["success"] is True
            assert len(data["courses"]) == 0
            assert data["all_not_found"] is True
            assert len(data["not_found_ids"]) == 3
            assert data["fallback_url"] is not None

            # Test case 2: Mixed valid and invalid IDs
            mixed_request = {
                "course_ids": [
                    "coursera_crse:v1-2598",
                    "invalid_id_1",
                    "coursera_crse:v1-2599",
                    "not_exist_id"
                ],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[
                    {"id": "coursera_crse:v1-2598", "name": "Course 1"},
                    {"id": "coursera_crse:v1-2599", "name": "Course 2"}
                ],
                total_found=2,
                requested_count=4,
                processed_count=4,
                skipped_count=0,
                not_found_ids=["invalid_id_1", "not_exist_id"],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=False,
                fallback_url=None,
                time_tracking=None,
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=mixed_request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["courses"]) == 2
            assert len(data["not_found_ids"]) == 2

            # Test case 3: Database error simulation
            error_request = {
                "course_ids": ["coursera_crse:v1-2598"],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=False,
                courses=[],
                total_found=0,
                requested_count=1,
                processed_count=0,
                skipped_count=0,
                not_found_ids=[],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=False,
                fallback_url=None,
                time_tracking=None,
                error={
                    "code": "DB_ERROR",
                    "message": "Database connection failed",
                    "details": "Connection pool exhausted"
                }
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=error_request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200  # Still 200 for Bubble.io
            data = response.json()
            assert data["success"] is False
            assert data["error"]["code"] == "DB_ERROR"
            assert "database" in data["error"]["message"].lower()

    def test_API_CDB_004_IT_time_tracking_completeness(self, client, valid_api_key):
        """
        API-CDB-004-IT: Verify time tracking information completeness.
        Check all time tracking components are present and valid.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            request = {
                "course_ids": ["coursera_crse:v1-2598"],
                "enable_time_tracking": True
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[{"id": "coursera_crse:v1-2598", "name": "Test Course"}],
                total_found=1,
                requested_count=1,
                processed_count=1,
                skipped_count=0,
                not_found_ids=[],
                cache_hit_rate=0.5,
                from_cache_count=1,
                all_not_found=False,
                fallback_url=None,
                time_tracking={
                    "timeline": [
                        {
                            "task_name": "preparation",
                            "description": "Request validation and setup",
                            "start_time": 0,
                            "end_time": 2,
                            "duration_ms": 2
                        },
                        {
                            "task_name": "cache_operations",
                            "description": "Cache lookup and retrieval",
                            "start_time": 2,
                            "end_time": 5,
                            "duration_ms": 3
                        },
                        {
                            "task_name": "db_operations",
                            "description": "Database query execution",
                            "start_time": 5,
                            "end_time": 25,
                            "duration_ms": 20
                        },
                        {
                            "task_name": "processing",
                            "description": "Result processing and formatting",
                            "start_time": 25,
                            "end_time": 30,
                            "duration_ms": 5
                        }
                    ],
                    "summary": {
                        "total_ms": 30,
                        "preparation_pct": 6.67,
                        "cache_operations_pct": 10.0,
                        "db_operations_pct": 66.67,
                        "processing_pct": 16.67
                    },
                    "metadata": {
                        "courses_requested": 1,
                        "courses_found": 1,
                        "cache_hits": 1,
                        "db_queries": 0
                    }
                },
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200
            data = response.json()

            # Verify time tracking structure
            assert data["time_tracking"] is not None
            time_data = data["time_tracking"]

            # Check timeline
            assert "timeline" in time_data
            timeline = time_data["timeline"]
            assert len(timeline) == 4

            for task in timeline:
                assert "task_name" in task
                assert "description" in task
                assert "start_time" in task
                assert "end_time" in task
                assert "duration_ms" in task
                assert task["duration_ms"] >= 0
                assert task["end_time"] >= task["start_time"]

            # Check summary
            assert "summary" in time_data
            summary = time_data["summary"]
            assert "total_ms" in summary
            assert summary["total_ms"] > 0

            # Verify percentage fields
            assert "preparation_pct" in summary
            assert "cache_operations_pct" in summary
            assert "db_operations_pct" in summary
            assert "processing_pct" in summary

            # Sum of percentages should be approximately 100
            total_pct = (
                summary["preparation_pct"] +
                summary["cache_operations_pct"] +
                summary["db_operations_pct"] +
                summary["processing_pct"]
            )
            assert 99 <= total_pct <= 101  # Allow small rounding difference

            # Check metadata
            assert "metadata" in time_data
            metadata = time_data["metadata"]
            assert metadata["courses_requested"] == 1
            assert metadata["courses_found"] == 1

    def test_API_CDB_005_IT_all_not_found_handling(self, client, valid_api_key):
        """
        API-CDB-005-IT: Verify handling when all courses are not found.
        Should return success with fallback URL.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            request = {
                "course_ids": ["invalid_id_1", "invalid_id_2"],
                "enable_time_tracking": False
            }

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(return_value=CourseDetailsBatchResponse(
                success=True,
                courses=[],
                total_found=0,
                requested_count=2,
                processed_count=2,
                skipped_count=0,
                not_found_ids=["invalid_id_1", "invalid_id_2"],
                cache_hit_rate=0.0,
                from_cache_count=0,
                all_not_found=True,
                fallback_url="https://www.coursera.org/search?query=programming",
                time_tracking=None,
                error={"code": "", "message": "", "details": ""}
            ))
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200
            data = response.json()

            # Should still return success for Bubble.io compatibility
            assert data["success"] is True
            assert data["all_not_found"] is True
            assert data["fallback_url"] is not None
            assert "coursera.org" in data["fallback_url"]
            assert len(data["courses"]) == 0
            assert data["total_found"] == 0
            assert len(data["not_found_ids"]) == 2

    def test_API_CDB_006_IT_authentication_required(self, client):
        """
        API-CDB-006-IT: Verify API key authentication is required.
        """
        # 這個測試需要完全獨立的環境來避免與其他測試的狀態干擾
        import json
        import os
        import subprocess
        import sys
        import tempfile

        import pytest

        # 創建獨立的測試腳本來避免環境變數干擾
        test_script = '''
import os
import sys
sys.path.insert(0, ".")

# 確保沒有 API key
if "CONTAINER_APP_API_KEY" in os.environ:
    del os.environ["CONTAINER_APP_API_KEY"]

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

request = {
    "course_ids": ["coursera_crse:v1-2598"],
    "enable_time_tracking": False
}

# Test 1: No API key
response = client.post("/api/v1/courses/get-by-ids", json=request)
assert response.status_code == 401, f"Expected 401, got {response.status_code}"
data = response.json()
assert data["success"] is False
assert data["error"]["code"] == "MISSING_API_KEY"

# Test 2: Invalid API key
os.environ["CONTAINER_APP_API_KEY"] = "correct-key"
# 重新載入應用以使用新的環境變數
import importlib
import src.main
importlib.reload(src.main)
from src.main import app
client = TestClient(app)

response = client.post(
    "/api/v1/courses/get-by-ids",
    json=request,
    headers={"X-API-Key": "wrong-key"}
)
assert response.status_code == 401, f"Expected 401, got {response.status_code}"
data = response.json()
assert data["success"] is False
assert data["error"]["code"] == "INVALID_API_KEY"

print("All authentication tests passed")
'''

        # 在臨時檔案中運行測試
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name

        try:
            # 運行獨立的測試腳本
            result = subprocess.run(  # noqa: S603
                [sys.executable, temp_script],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
                timeout=30
            )

            # 檢查結果
            if result.returncode != 0:
                pytest.fail(f"Authentication test failed: {result.stderr}\n{result.stdout}")

        finally:
            # 清理臨時檔案
            os.unlink(temp_script)

    def test_API_CDB_007_IT_request_validation(self, client, valid_api_key):
        """
        API-CDB-007-IT: Verify request validation works correctly.
        """
        # Test invalid description_max_length
        invalid_request = {
            "course_ids": ["coursera_crse:v1-2598"],
            "description_max_length": 49  # Below minimum of 50
        }

        response = client.post(
            "/api/v1/courses/get-by-ids",
            json=invalid_request,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422

        # Test invalid max_courses
        invalid_request = {
            "course_ids": ["coursera_crse:v1-2598"],
            "max_courses": 0  # Below minimum of 1
        }

        response = client.post(
            "/api/v1/courses/get-by-ids",
            json=invalid_request,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422

        # Test invalid max_courses (over limit)
        invalid_request = {
            "course_ids": ["coursera_crse:v1-2598"],
            "max_courses": 101  # Above maximum of 100
        }

        response = client.post(
            "/api/v1/courses/get-by-ids",
            json=invalid_request,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422

    def test_API_CDB_008_IT_default_values(self, client, valid_api_key):
        """
        API-CDB-008-IT: Verify default values are applied correctly.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            # Minimal request with only required field
            minimal_request = {
                "course_ids": ["coursera_crse:v1-2598"]
            }

            # Capture the actual request passed to the service
            actual_request = None

            async def capture_request(req):
                nonlocal actual_request
                actual_request = req
                return CourseDetailsBatchResponse(
                    success=True,
                    courses=[{"id": "coursera_crse:v1-2598", "name": "Test"}],
                    total_found=1,
                    requested_count=1,
                    processed_count=1,
                    skipped_count=0,
                    not_found_ids=[],
                    cache_hit_rate=0.0,
                    from_cache_count=0,
                    all_not_found=False,
                    fallback_url=None,
                    time_tracking=None,
                    error={"code": "", "message": "", "details": ""}
                )

            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(side_effect=capture_request)
            mock_get_instance.return_value = mock_service

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=minimal_request,
                headers={"X-API-Key": valid_api_key}
            )

            assert response.status_code == 200

            # Verify defaults were applied
            assert actual_request is not None
            assert actual_request.max_courses is None
            assert actual_request.full_description is True
            assert actual_request.description_max_length == 500
            assert actual_request.enable_time_tracking is True

    def test_API_CDB_009_IT_error_handler_integration(self, client, valid_api_key):
        """
        API-CDB-009-IT: Verify unified error handling with @handle_api_errors decorator.
        Should return standardized error response format.
        """
        with patch("src.services.course_search_singleton.CourseSearchSingleton.get_instance") as mock_get_instance:
            # Mock service to raise an exception
            mock_service = AsyncMock()
            mock_service.get_courses_by_ids = AsyncMock(side_effect=Exception("Simulated service error"))
            mock_get_instance.return_value = mock_service

            request = {
                "course_ids": ["coursera_crse:v1-2598"],
                "enable_time_tracking": False
            }

            response = client.post(
                "/api/v1/courses/get-by-ids",
                json=request,
                headers={"X-API-Key": valid_api_key}
            )

            # The @handle_api_errors decorator should catch the exception
            # and return a standardized error response format
            assert response.status_code == 200  # Still 200 for Bubble.io compatibility
            data = response.json()

            # Verify standardized error structure
            assert "success" in data
            assert "error" in data
            assert isinstance(data["error"], dict)

            # The decorator should format the error consistently
            if not data["success"]:
                assert "code" in data["error"]
                assert "message" in data["error"]
