"""
Integration tests for refactored prompts endpoint with error handler.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestPromptsEndpoint:
    """Test prompts endpoint with new error handler."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_get_prompt_version_success(self, client):
        """Test successful prompt version retrieval."""
        response = client.get("/api/v1/prompts/version?task=keyword_extraction")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_prompt_version_invalid_task(self, client):
        """Test error handling for invalid task."""
        response = client.get("/api/v1/prompts/version?task=invalid_task_name")
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_list_prompt_tasks_success(self, client):
        """Test successful listing of prompt tasks."""
        response = client.get("/api/v1/prompts/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "tasks" in data["data"]

    @patch("src.api.v1.prompts.prompt_manager")
    def test_list_prompt_tasks_with_error(self, mock_manager, client):
        """Test error handling in list_prompt_tasks."""
        # Simulate an error
        mock_manager.prompts_dir.exists.side_effect = RuntimeError("Test error")

        response = client.get("/api/v1/prompts/tasks")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
