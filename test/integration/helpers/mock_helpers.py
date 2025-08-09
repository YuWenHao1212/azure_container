"""
Helper utilities for creating standardized mock objects for integration tests.

This module provides consistent mock patterns to avoid test isolation issues.
"""
from typing import Any
from unittest.mock import AsyncMock, Mock


def create_async_context_manager_mock(return_value: Any) -> Any:
    """
    Create a proper async context manager mock.

    This helper ensures consistent async context manager behavior across tests,
    preventing issues with ResourcePoolManager and similar async context managers.

    Args:
        return_value: The value to return from __aenter__

    Returns:
        An object that properly implements the async context manager protocol
    """
    class AsyncContextManager:
        def __init__(self, value):
            self.value = value
            self._entered = False

        async def __aenter__(self):
            self._entered = True
            return self.value

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self._entered = False
            return None

        def __call__(self):
            # Make it callable for compatibility
            return self

    return AsyncContextManager(return_value)


def create_resource_pool_mock() -> Mock:
    """
    Create a properly configured ResourcePoolManager mock.

    This ensures consistent behavior across all tests that need to mock
    the ResourcePoolManager, preventing test isolation issues.

    Returns:
        A configured Mock object for ResourcePoolManager
    """
    pool_mock = Mock()

    # Create a mock client that will be returned from get_client
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Configure get_client to return an async context manager
    pool_mock.get_client = lambda: create_async_context_manager_mock(mock_client)

    # Configure get_stats
    pool_mock.get_stats = Mock(return_value={
        "total_clients": 1,
        "active_clients": 0,
        "available_clients": 1,
        "clients_created": 1,
        "clients_reused": 0,
        "current_pool_size": 1,
        "peak_pool_size": 1
    })

    # Configure other methods
    pool_mock.initialize = AsyncMock()
    pool_mock.cleanup = AsyncMock()

    return pool_mock


def create_embedding_client_mock() -> AsyncMock:
    """
    Create a properly configured embedding client mock.

    Returns:
        An AsyncMock configured for embedding client usage
    """
    mock = AsyncMock()

    # Configure create_embeddings to return proper format
    mock.create_embeddings = AsyncMock(return_value=[
        [0.1] * 1536,  # Resume embedding
        [0.2] * 1536   # Job description embedding
    ])

    # Configure close method
    mock.close = AsyncMock()

    # Make it work as async context manager
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)

    return mock


def create_llm_client_mock() -> AsyncMock:
    """
    Create a properly configured LLM client mock.

    Returns:
        An AsyncMock configured for LLM client usage
    """
    mock = AsyncMock()

    # Configure chat completion
    mock.chat_completion = AsyncMock(return_value={
        "choices": [{
            "message": {
                "content": '{"keywords": ["Python", "FastAPI"], "confidence": 0.9}'
            }
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    })

    # Configure text completion
    mock.complete_text = AsyncMock(return_value={
        "text": '{"keywords": ["Python"], "confidence": 0.85}'
    })

    # Configure close method
    mock.close = AsyncMock()

    # Make it work as async context manager
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)

    return mock
