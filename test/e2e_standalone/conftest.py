"""
Configuration for E2E standalone tests.

This conftest.py is isolated from the global test/conftest.py to avoid mock conflicts.
E2E tests should use real APIs without any mocking.
"""

import os
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """Set up E2E test environment - uses real APIs."""
    # Mark this as standalone E2E test
    os.environ['PYTEST_CURRENT_TEST_TYPE'] = 'e2e_standalone'
    os.environ['RUNNING_STANDALONE_E2E'] = 'true'
    
    # Ensure V2 implementation is used
    os.environ['USE_V2_IMPLEMENTATION'] = 'true'
    
    # Configure for real API usage
    os.environ.update({
        'ENABLE_PARTIAL_RESULTS': 'true',
        'RESOURCE_POOL_ENABLED': 'false',  # Simplify for E2E testing
        'MONITORING_ENABLED': 'true',
        'LIGHTWEIGHT_MONITORING': 'true',
        'INDEX_CALC_CACHE_ENABLED': 'true',
        'INDEX_CALC_CACHE_TTL_MINUTES': '60',
        'INDEX_CALC_CACHE_MAX_SIZE': '1000'
    })
    
    yield
    
    # Clean up
    cleanup_vars = [
        'PYTEST_CURRENT_TEST_TYPE',
        'RUNNING_STANDALONE_E2E',
        'REAL_E2E_TEST'
    ]
    for var in cleanup_vars:
        if var in os.environ:
            del os.environ[var]


@pytest.fixture
def skip_if_no_api_keys():
    """Skip tests if required API keys are not available."""
    required_keys = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'EMBEDDING_API_KEY',
        'EMBEDDING_ENDPOINT'
    ]
    
    missing_keys = [key for key in required_keys if not os.environ.get(key)]
    if missing_keys:
        pytest.skip(f"E2E tests require real API keys. Missing: {', '.join(missing_keys)}")


@pytest.fixture
def api_key_headers():
    """Provide API key headers for requests."""
    api_key = os.environ.get('CONTAINER_APP_API_KEY', 'test-api-key')
    return {"X-API-Key": api_key}