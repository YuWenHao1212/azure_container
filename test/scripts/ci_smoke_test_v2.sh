#!/bin/bash

# CI Smoke Test v2 - Real API Performance Testing
# Tests all three modules with real Azure OpenAI API
# Used after deployment to verify production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration from environment
API_URL="${API_URL:-https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io}"
API_KEY="${CONTAINER_APP_API_KEY}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="test/logs"
SUMMARY_LOG="$LOG_DIR/smoke_test_${TIMESTAMP}.log"

# Create log directory if not exists
mkdir -p "$LOG_DIR"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

# Function to log message
log_message() {
    echo "$1" | tee -a "$SUMMARY_LOG"
}

# Function removed - using direct curl commands instead

# Function to check if API is healthy
check_api_health() {
    log_message "Checking API health at $API_URL/health..."
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        "$API_URL/health")
    
    if [ "$response" -eq 200 ]; then
        log_message "  ${GREEN}✓ API is healthy${NC}"
        return 0
    else
        log_message "  ${RED}✗ API health check failed (HTTP $response)${NC}"
        return 1
    fi
}

# Main execution
main() {
    log_message "========================================="
    log_message "CI Smoke Test v2 - Real API Performance"
    log_message "========================================="
    log_message "Timestamp: $(date)"
    log_message "API URL: $API_URL"
    log_message "Environment: Production"
    log_message ""
    
    # Check API key
    if [ -z "$API_KEY" ]; then
        log_message "${RED}ERROR: CONTAINER_APP_API_KEY not set${NC}"
        exit 1
    fi
    
    # Check API health first
    if ! check_api_health; then
        log_message "${RED}Aborting: API is not healthy${NC}"
        exit 1
    fi
    
    log_message ""
    log_message "Running Performance Tests"
    log_message "========================="
    
    # Export API configuration for test scripts
    export AZURE_OPENAI_API_KEY="$API_KEY"
    export API_BASE_URL="$API_URL"
    
    # Test results tracking
    local all_passed=true
    
    # Simplified performance tests for CI - just make API calls directly
    # 1. Test Keyword Extraction
    log_message ""
    log_message "Testing Keyword Extraction..."
    log_message "Expected: Quick API response test"
    log_message "SLA: Response < 4500ms"
    
    local test_start=$(date +%s)
    local test_log="$LOG_DIR/smoke_keyword_${TIMESTAMP}.log"
    
    # Simple keyword extraction test - using single line JSON to avoid parsing issues
    local keyword_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -X POST "$API_URL/api/v1/extract-jd-keywords" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"jd_description":"We are looking for a Senior Software Engineer with expertise in Python, Django, and PostgreSQL. The ideal candidate should have at least 5 years of experience in web development, strong knowledge of RESTful APIs, and experience with cloud platforms like AWS or Azure. Knowledge of Docker and Kubernetes is a plus."}' 2>&1 | tee "$test_log")
    
    local http_code=$(echo "$keyword_response" | tail -2 | head -1)
    local response_time=$(echo "$keyword_response" | tail -1)
    local response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 4500 ]; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "  ${GREEN}✓ Keyword Extraction PASSED${NC} (${response_time_ms}ms < 4500ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ${RED}✗ Keyword Extraction FAILED${NC} (HTTP $http_code, ${response_time_ms}ms)"
        all_passed=false
    fi
    
    # 2. Test Index Calculation
    log_message ""
    log_message "Testing Index Calculation..."
    log_message "Expected: Quick API response test"
    log_message "SLA: Response < 2000ms"
    
    test_start=$(date +%s)
    test_log="$LOG_DIR/smoke_index_${TIMESTAMP}.log"
    
    # Simple index calculation test - using single line JSON
    local index_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -X POST "$API_URL/api/v1/index-calculation" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"jd_info":"Looking for a Python developer with Django experience. Must have strong skills in PostgreSQL, REST APIs, and cloud platforms.","cv_info":"Experienced Python developer with 5 years of Django development. Proficient in PostgreSQL, RESTful API design, and AWS cloud services."}' 2>&1 | tee "$test_log")
    
    http_code=$(echo "$index_response" | tail -2 | head -1)
    response_time=$(echo "$index_response" | tail -1)
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 2000 ]; then
        test_end=$(date +%s)
        duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "  ${GREEN}✓ Index Calculation PASSED${NC} (${response_time_ms}ms < 2000ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ${RED}✗ Index Calculation FAILED${NC} (HTTP $http_code, ${response_time_ms}ms)"
        all_passed=false
    fi
    
    # 3. Test Gap Analysis (longer timeout)
    log_message ""
    log_message "Testing Gap Analysis..."
    log_message "Expected: API response test"
    log_message "SLA: Response < 25000ms"
    
    test_start=$(date +%s)
    test_log="$LOG_DIR/smoke_gap_${TIMESTAMP}.log"
    
    # Simple gap analysis test - using single line JSON
    local gap_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        --max-time 30 \
        -X POST "$API_URL/api/v1/index-cal-and-gap-analysis" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"jd_info":"We need a Senior Full Stack Developer with expertise in React, Node.js, and MongoDB. The ideal candidate should have experience with microservices architecture, GraphQL, and containerization technologies.","cv_info":"Full Stack Developer with 3 years of experience in React and Node.js. Familiar with MongoDB and REST APIs. Some exposure to Docker."}' 2>&1 | tee "$test_log")
    
    http_code=$(echo "$gap_response" | tail -2 | head -1)
    response_time=$(echo "$gap_response" | tail -1)
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 25000 ]; then
        test_end=$(date +%s)
        duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "  ${GREEN}✓ Gap Analysis PASSED${NC} (${response_time_ms}ms < 25000ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ${RED}✗ Gap Analysis FAILED${NC} (HTTP $http_code, ${response_time_ms}ms)"
        all_passed=false
    fi
    
    # Calculate total time
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    # Generate summary
    log_message ""
    log_message "========================================="
    log_message "Test Summary"
    log_message "========================================="
    log_message "Total Tests: $TOTAL_TESTS"
    log_message "Passed: $PASSED_TESTS"
    log_message "Failed: $FAILED_TESTS"
    log_message "Total Time: ${total_duration}s"
    log_message ""
    
    if [ "$FAILED_TESTS" -eq 0 ] && [ "$TOTAL_TESTS" -eq 3 ]; then
        log_message "${GREEN}✅ All smoke tests PASSED!${NC}"
        log_message ""
        log_message "Performance SLAs Met:"
        log_message "  • Keyword Extraction: ✓ (< 4.5s)"
        log_message "  • Index Calculation: ✓ (< 2s)"
        log_message "  • Gap Analysis: ✓ (< 25s)"
        exit 0
    else
        log_message "${RED}❌ Smoke tests FAILED!${NC}"
        if [ "$TOTAL_TESTS" -ne 3 ]; then
            log_message "  Warning: Expected 3 tests but ran $TOTAL_TESTS"
        fi
        if [ "$FAILED_TESTS" -gt 0 ]; then
            log_message "  $FAILED_TESTS out of $TOTAL_TESTS tests failed"
        fi
        log_message ""
        log_message "Please check the logs in: $LOG_DIR"
        exit 1
    fi
}

# Run main function
main "$@"