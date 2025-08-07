"""
Performance test specific configuration.

This conftest.py OVERRIDES the global conftest.py to enable REAL API testing
for performance tests by completely disabling the autouse mock fixtures.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# CRITICAL: Override the global mock fixture by defining an empty one
@pytest.fixture(autouse=True)
def mock_openai_clients():
    """Override the global mock fixture to disable mocks for performance tests."""
    # This empty fixture replaces the global one, allowing real API calls
    yield

# Load real environment variables from .env FIRST
from dotenv import load_dotenv

load_dotenv(override=True)

# Performance test environment setup - SET AFTER loading .env
os.environ['TESTING'] = 'false'  # Disable global mocks
os.environ['PERFORMANCE_TESTING'] = 'true'  # Enable performance mode
os.environ['RESOURCE_POOL_ENABLED'] = 'false'  # Disable for P50/P95 tests
os.environ['MONITORING_ENABLED'] = 'false'     # Reduce overhead
os.environ['LIGHTWEIGHT_MONITORING'] = 'false'  # Completely disable for clean tests
os.environ['ERROR_CAPTURE_ENABLED'] = 'false'  # Reduce overhead
os.environ['CONTAINER_APP_API_KEY'] = 'test-api-key'  # Test API key
os.environ['USE_V2_IMPLEMENTATION'] = 'true'  # Enable V2 for performance tests

# Verify critical Azure OpenAI environment variables are loaded
assert os.environ.get('AZURE_OPENAI_ENDPOINT'), "AZURE_OPENAI_ENDPOINT not loaded from .env"
assert os.environ.get('AZURE_OPENAI_API_KEY'), "AZURE_OPENAI_API_KEY not loaded from .env"
assert os.environ.get('AZURE_OPENAI_GPT4_DEPLOYMENT'), "AZURE_OPENAI_GPT4_DEPLOYMENT not loaded from .env"
assert os.environ.get('EMBEDDING_ENDPOINT'), "EMBEDDING_ENDPOINT not loaded from .env"

print("🎯 Performance testing mode: REAL API calls enabled, mocks disabled")

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for asyncio tests."""
    import asyncio
    return asyncio.get_event_loop_policy()

@pytest.fixture
def mock_monitoring_service():
    """Mock only monitoring service for performance tests."""
    service = Mock()
    service.track_event = Mock()
    service.track_error = Mock()
    service.track_metric = Mock()
    return service

# NO autouse fixture here - we want REAL API clients for performance testing!
# The global mock_openai_clients fixture from test/conftest.py will be disabled
# by setting TESTING=false in the environment
