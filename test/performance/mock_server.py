"""Temporary server with mocked LLM responses for performance testing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set testing environment
os.environ['TESTING'] = 'true'
os.environ['MONITORING_ENABLED'] = 'false'

from unittest.mock import AsyncMock, Mock, patch

import uvicorn

from src.main import app

# Mock the LLM clients
mock_response = Mock()
mock_response.choices = [Mock(message=Mock(content="""
{
    "keywords": [
        {"keyword": "Python", "relevance": 0.95},
        {"keyword": "Senior Developer", "relevance": 0.90},
        {"keyword": "FastAPI", "relevance": 0.88},
        {"keyword": "Azure", "relevance": 0.85},
        {"keyword": "Cloud Services", "relevance": 0.82},
        {"keyword": "Machine Learning", "relevance": 0.80},
        {"keyword": "API Development", "relevance": 0.78},
        {"keyword": "Backend", "relevance": 0.75},
        {"keyword": "Software Engineering", "relevance": 0.73},
        {"keyword": "Experience", "relevance": 0.70}
    ]
}
"""))]

async_mock_client = AsyncMock()
async_mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

# Patch all OpenAI clients
with patch('src.services.openai_client.get_azure_openai_client', return_value=async_mock_client):
    with patch('src.services.openai_client_gpt41.get_gpt41_mini_client', return_value=async_mock_client):
        # Start the server
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")  # noqa: S104
