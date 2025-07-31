#!/bin/bash

# Real performance test with actual Azure OpenAI API keys

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
echo -e "${BLUE}Mode: Real Azure OpenAI API${NC}"
echo -e "${BLUE}========================================${NC}"

# Set environment variables directly
export ENVIRONMENT=development
export DEBUG=false
export MONITORING_ENABLED=false
export LIGHTWEIGHT_MONITORING=true
export ERROR_CAPTURE_ENABLED=false

# Primary LLM Service Configuration (GPT-4.1 Japan East)
export AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com
export AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY:-"your-api-key-here"}
export AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan
export AZURE_OPENAI_API_VERSION=2025-01-01-preview

# GPT-4.1 mini Japan East Configuration (High Performance)
export GPT41_MINI_JAPANEAST_ENDPOINT=https://airesumeadvisor.openai.azure.com/
export GPT41_MINI_JAPANEAST_API_KEY=${GPT41_MINI_JAPANEAST_API_KEY:-"your-api-key-here"}
export GPT41_MINI_JAPANEAST_DEPLOYMENT=gpt-4-1-mini-japaneast
export GPT41_MINI_JAPANEAST_API_VERSION=2025-01-01-preview

# Other required settings
export LLM2_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com
export LLM2_API_KEY=${LLM2_API_KEY:-"your-api-key-here"}
export EMBEDDING_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15
export EMBEDDING_API_KEY=${EMBEDDING_API_KEY:-"your-api-key-here"}
export JWT_SECRET_KEY=test-secret-key
export CONTAINER_APP_API_KEY=test-api-key

# LLM Model Selection
export LLM_MODEL_KEYWORDS=gpt41-mini

# CORS Settings
export CORS_ORIGINS=http://localhost:8080,http://localhost:3000,https://airesumeadvisor.com

echo -e "${GREEN}✅ Real API credentials configured${NC}"
echo "  Using GPT-4.1 mini for keyword extraction"

# Kill any existing process on port 8000
echo -n "Cleaning up port 8000... "
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓${NC}"

# Check if dependencies are installed
echo -n "Checking dependencies... "
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt > /tmp/pip_install.log 2>&1
fi
echo -e "${GREEN}✓${NC}"

# Start API server
echo -n "Starting API server... "
cd /Users/yuwenhao/Documents/GitHub/azure_container
python -m uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
API_PID=$!

# Wait for server to start
SERVER_STARTED=false
for i in {1..30}; do
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
    tail -20 /tmp/api_server.log
    exit 1
fi

echo ""
echo -e "${BLUE}Running Real Performance Tests...${NC}"
echo "======================================"

# Run the Python performance test
python test/performance/test_keyword_extraction_performance_simple.py

# Stop API server
echo ""
echo "Stopping API server..."
kill $API_PID 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Real performance test completed${NC}"
echo ""
echo "Note: These results reflect actual Azure OpenAI API performance"
echo "in your current network environment."