#!/bin/bash

# CI/CD Smoke Test with Basic Performance Check
# 測試最關鍵的 API 端點確保基本功能和效能

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_URL="${API_URL:-https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io}"
API_KEY="${CONTAINER_APP_API_KEY}"

# Performance SLAs
KEYWORD_SLA=4000  # ms
INDEX_CALC_SLA=2000  # ms
INDEX_CAL_GAP_ANALYSIS_SLA=20000  # ms (20 seconds for combined analysis)

echo -e "${BLUE}=== CI/CD Smoke Test ===${NC}"
echo "API URL: $API_URL"
echo ""

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local endpoint=$2
    local payload=$3
    local sla=$4
    
    ((TOTAL_TESTS++))
    
    echo -e "${BLUE}Testing: $name${NC}"
    
    # Record start time
    START_TIME=$(date +%s%3N)
    
    # Make request
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL$endpoint" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$payload")
    
    # Record end time
    END_TIME=$(date +%s%3N)
    RESPONSE_TIME=$((END_TIME - START_TIME))
    
    # Extract status code and body
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    # Check functionality
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "  ✅ Functionality: PASS (HTTP $HTTP_CODE)"
        
        # Check performance
        if [ $RESPONSE_TIME -lt $sla ]; then
            echo -e "  ✅ Performance: PASS (${RESPONSE_TIME}ms < ${sla}ms)"
            ((PASSED_TESTS++))
        else
            echo -e "  ❌ Performance: FAIL (${RESPONSE_TIME}ms >= ${sla}ms)"
            ((FAILED_TESTS++))
        fi
    else
        echo -e "  ❌ Functionality: FAIL (HTTP $HTTP_CODE)"
        echo -e "  Response: $BODY"
        ((FAILED_TESTS++))
    fi
    
    echo ""
}

# Test 1: Keyword Extraction (最常用的 API)
test_endpoint \
    "Keyword Extraction" \
    "/api/v1/extract-jd-keywords" \
    '{
        "job_description": "We are looking for an experienced Python developer with strong FastAPI framework knowledge to join our engineering team. The ideal candidate should have at least 3 years of experience in building RESTful APIs, microservices architecture, and cloud deployment. Required skills include Python, FastAPI, PostgreSQL, Docker, and Azure cloud services. Experience with async programming and performance optimization is a plus."
    }' \
    $KEYWORD_SLA

# Test 2: Index Calculation V2 (核心功能)
test_endpoint \
    "Index Calculation V2" \
    "/api/v1/index-calculation" \
    '{
        "resume": "Professional Summary: Experienced software engineer with 5 years of expertise in Python development and API design. Strong background in FastAPI, Django, and cloud technologies. Proven track record of building scalable microservices and RESTful APIs. Skills: Python, FastAPI, Django, PostgreSQL, MongoDB, Docker, Kubernetes, AWS, Azure, Git, CI/CD, Agile methodologies. Experience: Senior Python Developer at Tech Corp (2020-Present): Led development of microservices architecture using FastAPI. Implemented async programming patterns for high-performance APIs. Deployed applications on Azure cloud platform.",
        "job_description": "We are seeking a Python developer with FastAPI experience to build our next-generation API platform. Requirements: 3+ years Python experience, FastAPI framework knowledge, PostgreSQL database skills, Docker containerization, Azure cloud deployment experience.",
        "keywords": ["Python", "FastAPI", "PostgreSQL", "Docker", "Azure", "API", "microservices", "async programming"]
    }' \
    $INDEX_CALC_SLA

# Test 3: Index Cal and Gap Analysis (新的統一端點 - P50 效能測試)
test_endpoint \
    "Index Cal and Gap Analysis V2" \
    "/api/v1/index-cal-and-gap-analysis" \
    '{
        "resume": "Professional Summary: Experienced software engineer with 5 years of expertise in Python development and API design. Strong background in FastAPI, Django, and cloud technologies. Proven track record of building scalable microservices and RESTful APIs. Skills: Python, FastAPI, Django, PostgreSQL, MongoDB, Docker, Kubernetes, AWS, Azure, Git, CI/CD, Agile methodologies. Experience: Senior Python Developer at Tech Corp (2020-Present): Led development of microservices architecture using FastAPI. Implemented async programming patterns for high-performance APIs. Deployed applications on Azure cloud platform.",
        "job_description": "We are seeking a Python developer with FastAPI experience to build our next-generation API platform. Requirements: 3+ years Python experience, FastAPI framework knowledge, PostgreSQL database skills, Docker containerization, Azure cloud deployment experience.",
        "keywords": ["Python", "FastAPI", "PostgreSQL", "Docker", "Azure", "API", "microservices", "async programming"],
        "language": "en"
    }' \
    $INDEX_CAL_GAP_ANALYSIS_SLA

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ All smoke tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some smoke tests failed!${NC}"
    exit 1
fi