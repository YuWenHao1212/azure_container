#!/bin/bash

# Performance test script for API-KW-105-PT
# Based on azure_fastapi precommit.sh approach

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
echo -e "${BLUE}========================================${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please create .env file with API credentials"
    exit 1
fi

# Load environment variables
echo "📄 Loading environment from .env"
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    if [[ ! "$key" =~ ^[[:space:]]*# ]] && [[ -n "$key" ]]; then
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # Only export if key is valid
        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            export "$key"="$value"
        fi
    fi
done < .env

# Check for API keys
if [ -z "$AZURE_OPENAI_API_KEY" ] && [ -z "$LLM2_API_KEY" ] && [ -z "$GPT41_MINI_JAPANEAST_API_KEY" ]; then
    echo -e "${RED}❌ No API keys found in .env file${NC}"
    echo "Please set one of:"
    echo "  - AZURE_OPENAI_API_KEY or LLM2_API_KEY"
    echo "  - GPT41_MINI_JAPANEAST_API_KEY"
    exit 1
fi

echo -e "${GREEN}✅ API credentials found${NC}"

# Kill any existing process on port 8000
echo -n "Cleaning up port 8000... "
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓${NC}"

# Start API server
echo -n "Starting API server... "
cd /Users/yuwenhao/Documents/GitHub/azure_container
uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
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

echo -e "${GREEN}✅ Performance test completed${NC}"