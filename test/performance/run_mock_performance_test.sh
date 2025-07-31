#!/bin/bash

# Mock performance test script for API-KW-105-PT
# Uses test environment with mocked LLM responses

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Keyword Extraction Performance Test${NC}"
echo -e "${BLUE}Test ID: API-KW-105-PT${NC}"
echo -e "${BLUE}Mode: Mock/Test Environment${NC}"
echo -e "${BLUE}========================================${NC}"

# Use test environment
export TESTING=true
export MONITORING_ENABLED=false
export LIGHTWEIGHT_MONITORING=false
export ERROR_CAPTURE_ENABLED=false

# Set test API keys
export AZURE_OPENAI_API_KEY=test-key
export GPT41_MINI_JAPANEAST_API_KEY=test-key
export LLM2_API_KEY=test-key
export EMBEDDING_API_KEY=test-key
export JWT_SECRET_KEY=test-secret
export AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com
export GPT41_MINI_JAPANEAST_ENDPOINT=https://test.openai.azure.com
export LLM2_ENDPOINT=https://test.endpoint.com
export EMBEDDING_ENDPOINT=https://test.embedding.com

echo -e "${GREEN}✅ Test environment configured${NC}"

# Kill any existing process on port 8000
echo -n "Cleaning up port 8000... "
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓${NC}"

# Start API server with test configuration
echo -n "Starting API server in test mode... "
cd /Users/yuwenhao/Documents/GitHub/azure_container

# Create a temporary test runner that patches the LLM client
cat > test/performance/mock_server.py << 'EOF'
"""Temporary server with mocked LLM responses for performance testing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set testing environment
os.environ['TESTING'] = 'true'
os.environ['MONITORING_ENABLED'] = 'false'

from unittest.mock import Mock, AsyncMock, patch
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
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")
EOF

python test/performance/mock_server.py > /tmp/api_server.log 2>&1 &
API_PID=$!

# Wait for server to start
SERVER_STARTED=false
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>/dev/null; then
        echo -e "${GREEN}✓${NC} (PID: $API_PID)"
        SERVER_STARTED=true
        break
    fi
    sleep 1
done

if [ "$SERVER_STARTED" = false ]; then
    echo -e "${RED}✗${NC}"
    echo "Server log:"
    cat /tmp/api_server.log
    exit 1
fi

echo ""
echo -e "${BLUE}Running Performance Tests...${NC}"
echo "======================================"

# Run the Python performance test
python test/performance/test_keyword_extraction_performance_simple.py

# Stop API server
echo ""
echo "Stopping API server..."
kill $API_PID 2>/dev/null || true

# Clean up
rm -f test/performance/mock_server.py

echo -e "${GREEN}✅ Performance test completed${NC}"