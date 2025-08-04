"""
Configuration for E2E tests.

E2E tests should use real APIs but we need to ensure proper initialization.
"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Ensure we're using V2 implementation for E2E tests
os.environ['USE_V2_IMPLEMENTATION'] = 'true'


@pytest.fixture(autouse=True)
def setup_e2e_environment():
    """Set up environment for E2E tests."""
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


@pytest.fixture
def mock_resource_pool():
    """Create a mock resource pool for tests that need it."""
    mock_pool = Mock()
    
    # Create mock client context manager
    class MockClientContext:
        async def __aenter__(self):
            # Return a mock OpenAI client
            mock_client = AsyncMock()
            mock_client.chat = AsyncMock()
            mock_client.chat.completions = AsyncMock()
            mock_client.chat.completions.create = AsyncMock()
            return mock_client
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    mock_pool.get_client = Mock(return_value=MockClientContext())
    mock_pool.initialized = True
    mock_pool.initialize = AsyncMock()
    mock_pool.get_stats = Mock(return_value={
        "pool_stats": {
            "clients_created": 0,
            "clients_reused": 0,
            "current_pool_size": 0
        },
        "efficiency": {
            "reuse_rate": 0.0,
            "pool_utilization": 0.0
        }
    })
    
    return mock_pool