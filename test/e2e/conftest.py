"""
Configuration for E2E tests.

E2E tests should use real APIs but we need to ensure proper initialization.
"""
import os
from unittest.mock import patch

import pytest

# Ensure we're using V2 implementation for E2E tests
os.environ['USE_V2_IMPLEMENTATION'] = 'true'


@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """Set up environment for E2E tests and disable global mocks."""
    # Mark this as E2E test to skip global mocks
    os.environ['PYTEST_CURRENT_TEST_TYPE'] = 'e2e'

    # Ensure resource pool is disabled for E2E tests to avoid initialization issues
    # E2E tests should test the full flow, not resource pool optimization
    os.environ['RESOURCE_POOL_ENABLED'] = 'false'

    # Ensure monitoring is enabled but not blocking
    os.environ['MONITORING_ENABLED'] = 'true'
    os.environ['LIGHTWEIGHT_MONITORING'] = 'true'

    yield

    # Clean up after tests
    if 'RESOURCE_POOL_ENABLED' in os.environ:
        del os.environ['RESOURCE_POOL_ENABLED']
    if 'PYTEST_CURRENT_TEST_TYPE' in os.environ:
        del os.environ['PYTEST_CURRENT_TEST_TYPE']


# E2E tests should use real API calls, not mocks
# If resource pool causes issues in E2E tests, it should be disabled via environment variable
