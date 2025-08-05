#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock environment
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['EMBEDDING_ENDPOINT'] = 'https://test.embedding.com'
os.environ['EMBEDDING_API_KEY'] = 'test-key'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ['MONITORING_ENABLED'] = 'false'
os.environ['LIGHTWEIGHT_MONITORING'] = 'false'
os.environ['ERROR_CAPTURE_ENABLED'] = 'false'
os.environ['CONTAINER_APP_API_KEY'] = ''

from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from src.main import create_app
from src.services.openai_client import AzureOpenAIRateLimitError

# Create test client
with (
    patch('src.core.config.get_settings'),
    patch('src.main.monitoring_service', Mock()),
    patch.dict(os.environ, {
        'MONITORING_ENABLED': 'false',
        'LIGHTWEIGHT_MONITORING': 'false',
        'ERROR_CAPTURE_ENABLED': 'false',
        'CONTAINER_APP_API_KEY': ''
    })
):
    app = create_app()
    client = TestClient(app)

# Set up rate limit mock
async def mock_rate_limit_error(*args, **kwargs):
    print('MOCK: Raising AzureOpenAIRateLimitError')
    raise AzureOpenAIRateLimitError('Rate limit exceeded')

mock_embed_client = AsyncMock()
mock_embed_client.create_embeddings = AsyncMock(side_effect=mock_rate_limit_error)
mock_embed_client.close = AsyncMock()
mock_embed_client.__aenter__ = AsyncMock(return_value=mock_embed_client)
mock_embed_client.__aexit__ = AsyncMock(return_value=None)

# Test with rate limit error
test_payload = {
    'resume': 'Software engineer with 5 years experience in Python development',
    'job_description': 'Looking for Python developer with backend experience', 
    'keywords': ['Python', 'Backend']
}

print("Testing AzureOpenAIRateLimitError handling...")

with patch('src.services.index_calculation_v2.get_azure_embedding_client', return_value=mock_embed_client):
    response = client.post('/api/v1/index-calculation', json=test_payload)
    print(f'Response status: {response.status_code}')
    print(f'Response body: {response.json()}')