"""
Pytest configuration for unit tests.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

# Set test environment variables before any imports
os.environ['TESTING'] = 'true'
os.environ['MONITORING_ENABLED'] = 'false'
os.environ['LIGHTWEIGHT_MONITORING'] = 'false'
os.environ['ERROR_CAPTURE_ENABLED'] = 'false'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['LLM2_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['LLM2_DEPLOYMENT'] = 'test-deployment'
os.environ['LLM2_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for asyncio tests."""
    import asyncio
    return asyncio.get_event_loop_policy()

@pytest.fixture
def mock_monitoring_service():
    """Mock monitoring service for all tests."""
    service = Mock()
    service.track_event = Mock()
    service.track_error = Mock()
    service.track_metric = Mock()
    return service

@pytest.fixture(autouse=True)
def mock_openai_clients():
    """Automatically mock OpenAI clients for all tests."""
    with (
        patch('src.services.openai_client.get_azure_openai_client'),
        patch('src.services.openai_client_gpt41.get_gpt41_mini_client'),
        patch('src.services.keyword_extraction.get_keyword_extraction_service')
    ):
        yield
