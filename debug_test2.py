#!/usr/bin/env python3

# 只測試 Test 2 的行為
import sys
import os
sys.path.insert(0, 'src')

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
os.environ['INDEX_CALC_CACHE_ENABLED'] = 'true'
os.environ['INDEX_CALC_CACHE_TTL_MINUTES'] = '60'
os.environ['INDEX_CALC_CACHE_MAX_SIZE'] = '1000'

from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from src.main import create_app
from src.services.openai_client import AzureOpenAIRateLimitError
import json

# Create test client with same patches as in test
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

# Reset singleton
import src.services.index_calculation_v2
src.services.index_calculation_v2._index_calculation_service_v2 = None

# Load test data
with open('test/fixtures/index_calculation/test_data.json', 'r', encoding='utf-8') as f:
    test_data = json.load(f)

test_payload = {
    'resume': test_data['standard_resumes'][0]['content'],
    'job_description': test_data['job_descriptions'][0]['content'],
    'keywords': test_data['job_descriptions'][0]['keywords'][:5]
}

print('Test 2: Rate limit error handling...')

async def mock_rate_limit_error(*args, **kwargs):
    print('Mock: AzureOpenAIRateLimitError raised')
    raise AzureOpenAIRateLimitError('Rate limit exceeded')

mock_embed_client2 = AsyncMock()
mock_embed_client2.create_embeddings = AsyncMock(side_effect=mock_rate_limit_error)
mock_embed_client2.close = AsyncMock()
mock_embed_client2.__aenter__ = AsyncMock(return_value=mock_embed_client2)
mock_embed_client2.__aexit__ = AsyncMock(return_value=None)

with patch('src.services.index_calculation_v2.get_azure_embedding_client', return_value=mock_embed_client2):
    response = client.post('/api/v1/index-calculation', json=test_payload)
    print(f'Response status: {response.status_code}')
    if response.status_code != 429:
        print('Response body:', response.json())
        print('Expected 429 but got', response.status_code)
    else:
        print('SUCCESS: Got expected 429 status code')