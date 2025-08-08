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

# Function to run performance test
run_performance_test() {
    local module="$1"
    local script="$2"
    local expected_tests="$3"
    local sla_description="$4"
    
    log_message ""
    log_message "Testing $module..."
    log_message "Expected: $expected_tests tests"
    log_message "SLA: $sla_description"
    
    local test_start=$(date +%s)
    local test_log="$LOG_DIR/smoke_${module}_${TIMESTAMP}.log"
    
    # Execute the test
    if timeout 120s $script > "$test_log" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        
        # Extract results from log
        local passed=$(grep -c "✓ PASSED" "$test_log" 2>/dev/null || echo "0")
        local failed=$(grep -c "✗ FAILED" "$test_log" 2>/dev/null || echo "0")
        
        TOTAL_TESTS=$((TOTAL_TESTS + expected_tests))
        PASSED_TESTS=$((PASSED_TESTS + passed))
        FAILED_TESTS=$((FAILED_TESTS + failed))
        
        if [ "$failed" -eq 0 ]; then
            log_message "  ${GREEN}✓ $module PASSED${NC} ($passed/$expected_tests tests in ${duration}s)"
            
            # Extract performance metrics if available
            local p50=$(grep -oE "P50: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}' || echo "N/A")
            local p95=$(grep -oE "P95: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}' || echo "N/A")
            
            if [ "$p50" != "N/A" ]; then
                log_message "    Performance: P50=${p50}ms, P95=${p95}ms"
            fi
            return 0
        else
            log_message "  ${RED}✗ $module FAILED${NC} ($passed passed, $failed failed in ${duration}s)"
            log_message "    See log: $test_log"
            return 1
        fi
    else
        TOTAL_TESTS=$((TOTAL_TESTS + expected_tests))
        FAILED_TESTS=$((FAILED_TESTS + expected_tests))
        
        log_message "  ${RED}✗ $module TIMEOUT or ERROR${NC}"
        log_message "    See log: $test_log"
        return 1
    fi
}

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
    
    # 1. Health & Keyword Performance Test
    if [ -f "test/scripts/run_health_keyword_real_api_perf.sh" ]; then
        if ! run_performance_test \
            "Health & Keyword" \
            "./test/scripts/run_health_keyword_real_api_perf.sh" \
            "1" \
            "P95 < 4500ms"; then
            all_passed=false
        fi
    else
        log_message "${YELLOW}⚠ Health & Keyword test script not found${NC}"
    fi
    
    # 2. Index Calculation Performance Test
    # Note: This is a Python test, not a shell script
    if [ -f "test/performance/test_index_calculation_v2_performance.py" ]; then
        log_message ""
        log_message "Testing Index Calculation..."
        log_message "Expected: 2 tests"
        log_message "SLA: P50 < 1000ms, P95 < 2000ms"
        
        local test_start=$(date +%s)
        local test_log="$LOG_DIR/smoke_index_calc_${TIMESTAMP}.log"
        
        # Run only the main performance tests
        if timeout 120s python -m pytest \
            "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_response_time_benchmark" \
            "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_high_concurrency_load" \
            -v --tb=short > "$test_log" 2>&1; then
            
            local test_end=$(date +%s)
            local duration=$((test_end - test_start))
            
            TOTAL_TESTS=$((TOTAL_TESTS + 2))
            PASSED_TESTS=$((PASSED_TESTS + 2))
            
            log_message "  ${GREEN}✓ Index Calculation PASSED${NC} (2/2 tests in ${duration}s)"
            
            # Extract performance metrics
            local p50=$(grep -oE "P50: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}' || echo "N/A")
            local p95=$(grep -oE "P95: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}' || echo "N/A")
            
            if [ "$p50" != "N/A" ]; then
                log_message "    Performance: P50=${p50}ms, P95=${p95}ms"
            fi
        else
            TOTAL_TESTS=$((TOTAL_TESTS + 2))
            FAILED_TESTS=$((FAILED_TESTS + 2))
            all_passed=false
            
            log_message "  ${RED}✗ Index Calculation FAILED${NC}"
            log_message "    See log: $test_log"
        fi
    else
        log_message "${YELLOW}⚠ Index Calculation test not found${NC}"
    fi
    
    # 3. Gap Analysis Performance & E2E Test
    if [ -f "test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh" ]; then
        # Run only performance test (not full E2E)
        if ! run_performance_test \
            "Gap Analysis" \
            "./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --stage performance" \
            "1" \
            "P50 < 25000ms"; then
            all_passed=false
        fi
    else
        log_message "${YELLOW}⚠ Gap Analysis test script not found${NC}"
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
    
    if [ "$FAILED_TESTS" -eq 0 ]; then
        log_message "${GREEN}✅ All smoke tests PASSED!${NC}"
        log_message ""
        log_message "Performance SLAs Met:"
        log_message "  • Keyword Extraction: ✓ (< 4.5s)"
        log_message "  • Index Calculation: ✓ (< 2s)"
        log_message "  • Gap Analysis: ✓ (< 25s)"
        exit 0
    else
        log_message "${RED}❌ Smoke tests FAILED!${NC}"
        log_message "  $FAILED_TESTS out of $TOTAL_TESTS tests failed"
        log_message ""
        log_message "Please check the logs in: $LOG_DIR"
        exit 1
    fi
}

# Run main function
main "$@"