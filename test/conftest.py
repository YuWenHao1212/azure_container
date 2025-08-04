"""
Pytest configuration for unit tests.
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

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
    """Automatically mock all Azure OpenAI clients for all tests."""
    # Skip mocking for E2E tests
    if os.environ.get('PYTEST_CURRENT_TEST_TYPE') == 'e2e':
        yield
        return
    # Mock all possible OpenAI client imports and services
    with (
        # Core OpenAI clients 
        patch('src.services.openai_client.get_azure_openai_client') as mock_openai,
        patch('src.services.openai_client_gpt41.get_gpt41_mini_client') as mock_gpt41,
        patch('src.services.embedding_client.get_azure_embedding_client') as mock_embedding,
        
        # Service-level mocks
        patch('src.services.keyword_extraction.get_keyword_extraction_service') as mock_keyword_service,
        
        # Resource pool manager
        patch('src.services.resource_pool_manager.ResourcePoolManager') as mock_resource_pool,
        
        # HTTP clients that might bypass mocks
        patch('httpx.AsyncClient') as mock_httpx,
        patch('aiohttp.ClientSession') as mock_aiohttp,
        
        # Azure SDK clients
        patch('openai.AsyncAzureOpenAI') as mock_azure_openai_direct
    ):
        # Configure OpenAI client mock
        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat_completion = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": '{"CoreStrengths": "<ol><li>Test strength</li></ol>", "KeyGaps": "<ol><li>Test gap</li></ol>", "QuickImprovements": "<ol><li>Test improvement</li></ol>", "OverallAssessment": "<p>Test assessment</p>", "SkillSearchQueries": ["Python", "Docker"]}'
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        })
        mock_openai_instance.close = AsyncMock()
        mock_openai.return_value = mock_openai_instance
        
        # Configure GPT-4.1 mini client mock
        mock_gpt41_instance = AsyncMock()
        mock_gpt41_instance.chat_completion = AsyncMock(return_value={
            "choices": [{
                "message": {
                    "content": '{"keywords": ["Python", "FastAPI", "Docker"], "keyword_count": 3, "confidence_score": 0.9, "extraction_method": "llm_based", "processing_time_ms": 250}'
                }
            }],
            "usage": {"prompt_tokens": 80, "completion_tokens": 30, "total_tokens": 110}
        })
        mock_gpt41_instance.close = AsyncMock()
        mock_gpt41.return_value = mock_gpt41_instance
        
        # Configure embedding client mock
        mock_embedding_instance = AsyncMock()
        mock_embedding_instance.create_embeddings = AsyncMock(return_value=[[0.1] * 1536, [0.2] * 1536])
        mock_embedding_instance.close = AsyncMock()
        mock_embedding.return_value = mock_embedding_instance
        
        # Configure keyword extraction service mock
        mock_keyword_instance = AsyncMock()
        mock_keyword_instance.validate_input = AsyncMock(return_value={
            "job_description": "test job description with sufficient length to pass validation requirements for testing purposes",
            "max_keywords": 15
        })
        mock_keyword_instance.process = AsyncMock(return_value={
            "keywords": ["Python", "FastAPI", "Docker", "AWS", "Git"],
            "keyword_count": 5,
            "confidence_score": 0.85,
            "extraction_method": "llm_based",
            "processing_time_ms": 200
        })
        mock_keyword_instance.close = AsyncMock()
        mock_keyword_service.return_value = mock_keyword_instance
        
        # Configure resource pool manager mock
        mock_pool_instance = Mock()
        mock_pool_instance.get_client = Mock()
        mock_pool_instance.get_client.__enter__ = Mock(return_value=mock_openai_instance)
        mock_pool_instance.get_client.__exit__ = Mock(return_value=None)
        mock_pool_instance.get_stats = Mock(return_value={
            "clients_created": 1,
            "clients_reused": 0,
            "current_pool_size": 1
        })
        mock_resource_pool.return_value = mock_pool_instance
        
        # Configure HTTP client mocks to prevent any real network calls
        mock_httpx_instance = Mock()
        mock_httpx_instance.post = Mock(side_effect=Exception("HTTP calls should be mocked"))
        mock_httpx_instance.close = Mock()
        mock_httpx.return_value = mock_httpx_instance
        
        mock_aiohttp_instance = Mock()
        mock_aiohttp_instance.post = Mock(side_effect=Exception("HTTP calls should be mocked"))
        mock_aiohttp_instance.close = Mock()
        mock_aiohttp.return_value = mock_aiohttp_instance
        
        # Configure direct Azure OpenAI client mock
        mock_azure_openai_direct_instance = Mock()
        mock_azure_openai_direct_instance.chat = Mock()
        mock_azure_openai_direct_instance.chat.completions = Mock()
        mock_azure_openai_direct_instance.chat.completions.create = Mock(return_value=Mock(
            choices=[Mock(message=Mock(content='{"test": "response"}'))],
            usage=Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        ))
        mock_azure_openai_direct_instance.embeddings = Mock()
        mock_azure_openai_direct_instance.embeddings.create = Mock(return_value=Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        ))
        mock_azure_openai_direct.return_value = mock_azure_openai_direct_instance
        
        yield
