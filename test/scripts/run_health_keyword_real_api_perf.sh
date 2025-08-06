#!/bin/bash

##############################################################################
# Health & Keyword Real API Performance Test Runner
# 
# Description:
#   Runs performance tests for Health Check and Keyword Extraction modules
#   using REAL Azure OpenAI API calls
#
# Tests:
#   Performance (PT): 1 test
#   - API-KW-201-PT: Keyword extraction response time test (P50/P95 metrics)
#
# Usage:
#   ./test/scripts/run_health_keyword_real_api_perf.sh [options]
#
# Options:
#   --help            Show this help message
#   --background      Run tests in background
#   --perf-test keyword  Run specific performance test
#
# Requirements:
#   - .env file with Azure OpenAI credentials
#   - Python 3.8+ with pytest installed
#   - Real Azure OpenAI API access
#
# Output:
#   - Console output with test results and performance metrics
#   - Log files in test/logs/ directory
#   - Performance JSON reports
#
# Note: This script uses REAL Azure OpenAI APIs and will incur costs
##############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$PROJECT_ROOT"

# Test configuration
PYTHON=${PYTHON:-python}
PYTEST="$PYTHON -m pytest"
LOG_DIR="test/logs"
ENV_FILE=".env"
API_PORT=8000
API_PID=""

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Timestamp for log files
TIMESTAMP=$(date '+%Y%m%d_%H%M')
LOG_FILE="$LOG_DIR/test_health_keyword_real_api_${TIMESTAMP}.log"

# Test result tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0
TEST_RESULTS=()
FAILED_TEST_IDS=()

# Performance test tracking
PERF_TESTS_RUN=0
PERF_P50_TOTAL=0
PERF_P95_TOTAL=0
PERF_SUCCESS_RATE_TOTAL=0

# Module counters
HEALTH_TOTAL=0
HEALTH_PASSED=0
KEYWORD_TOTAL=0
KEYWORD_PASSED=0
PERFORMANCE_TOTAL=0
PERFORMANCE_PASSED=0

# Priority counters
P0_TOTAL=0
P0_PASSED=0
P1_TOTAL=0
P1_PASSED=0

# Parse command line arguments
BACKGROUND=false
PERF_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --background)
            BACKGROUND=true
            shift
            ;;
        --perf-test)
            PERF_TEST="$2"
            shift 2
            ;;
        --help)
            echo "Health & Keyword Real API Performance Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --help                     Show this help message"
            echo "  --background               Run tests in background"
            echo "  --perf-test keyword        Run specific performance test"
            echo ""
            echo "Available Tests:"
            echo "  Performance:"
            echo "    - API-KW-201-PT: Keyword extraction response time (< 15s target)"
            echo ""
            echo "⚠️  This script uses REAL Azure OpenAI APIs and will incur costs!"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to log with timestamp
log_message() {
    # Strip ANSI color codes from log messages for clean file output
    local clean_message
    clean_message=$(echo "$1" | sed $'s/\033\[[0-9;]*m//g')
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $clean_message" >> "$LOG_FILE"
}

# Function to log environment info
log_environment_info() {
    log_message "=== ENVIRONMENT INFORMATION ==="
    log_message "Python Version: $(python --version 2>&1)"
    log_message "Working Directory: $(pwd)"
    log_message "Script Version: Health & Keyword Real API Performance Test Runner v2.0"
    log_message "Test Specification: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    log_message "API Endpoint: ${AZURE_OPENAI_ENDPOINT:-Not Set}"
    
    # LLM Configuration
    log_message "LLM Configuration:"
    log_message "  - Keywords Extraction: ${LLM_MODEL_KEYWORDS:-gpt41-mini} @ ${GPT41_MINI_JAPANEAST_ENDPOINT:-Not Set}"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Not Set}"
    log_message "  - GPT-4.1 Mini Deployment: ${GPT41_MINI_JAPANEAST_DEPLOYMENT:-Not Set}"
    
    log_message "Test Files:"
    log_message "  - Performance: test/performance/test_keyword_extraction_performance.py"
    log_message "Total Tests: 1 (Performance only)"
    log_message "================================"
}

# Function to log and print
log_and_print() {
    local message="$1"
    echo -e "$message"
    log_message "$message"
}

# Function to check test priority
get_test_priority() {
    local test_id="$1"
    case $test_id in
        # P0 Priority tests
        "API-KW-201-PT")
            echo "P0" ;;
        *)
            echo "Unknown" ;;
    esac
}

# Function to clean up old logs
cleanup_old_logs() {
    local test_id="$1"
    local log_pattern="$LOG_DIR/test_health_keyword_real_api_*_${test_id}.log"
    local performance_pattern="$LOG_DIR/performance_${test_id}_*.json"
    
    # Clean test logs
    local logs=($(ls -t $log_pattern 2>/dev/null))
    if [ ${#logs[@]} -gt 5 ]; then
        for i in $(seq 5 $((${#logs[@]} - 1))); do
            rm -f "${logs[$i]}"
            log_message "Removed old log: ${logs[$i]}"
        done
    fi
    
    # Clean performance logs
    local perf_logs=($(ls -t $performance_pattern 2>/dev/null))
    if [ ${#perf_logs[@]} -gt 5 ]; then
        for i in $(seq 5 $((${#perf_logs[@]} - 1))); do
            rm -f "${perf_logs[$i]}"
            log_message "Removed old performance log: ${perf_logs[$i]}"
        done
    fi
}

# Function to run a test and track results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-120}"
    local category="$4"
    local module="$5"
    local priority=$(get_test_priority "$test_id")
    
    log_and_print "${BLUE}Running ${test_id} (${priority})...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s - Category: $category - Module: $module"
    
    local test_start=$(date +%s)
    local test_log="${LOG_DIR}/test_health_keyword_real_api_${TIMESTAMP}_${test_id}.log"
    
    # Clean up old logs for this test
    cleanup_old_logs "$test_id"
    
    # Increment counters
    ((TOTAL_TESTS++))
    
    # Module tracking
    case $module in
        "health") ((HEALTH_TOTAL++)) ;;
        "keyword") ((KEYWORD_TOTAL++)) ;;
    esac
    
    # Category tracking
    case $category in
        "performance") ((PERFORMANCE_TOTAL++)) ;;
    esac
    
    # Priority tracking  
    case $priority in
        "P0") ((P0_TOTAL++)) ;;
        "P1") ((P1_TOTAL++)) ;;
    esac
    
    # Set environment variable to enable real API calls
    export USE_REAL_API=true
    
    # Run the test with timeout
    if timeout "$timeout" $PYTEST "$test_path" -xvs > "$test_log" 2>&1; then
        local test_end=$(date +%s)
        local test_duration=$((test_end - test_start))
        
        log_and_print "  ${GREEN}✓ PASSED${NC} (${test_duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${test_duration}s"
        
        ((PASSED_TESTS++))
        TEST_RESULTS+=("${GREEN}✓${NC} $test_id - ${test_duration}s")
        
        # Module tracking
        case $module in
            "health") ((HEALTH_PASSED++)) ;;
            "keyword") ((KEYWORD_PASSED++)) ;;
        esac
        
        # Category tracking
        case $category in
            "performance") ((PERFORMANCE_PASSED++)) ;;
        esac
        
        # Priority tracking
        case $priority in
            "P0") ((P0_PASSED++)) ;;
            "P1") ((P1_PASSED++)) ;;
        esac
        
        # Extract performance metrics if this is a performance test
        if [[ "$category" == "performance" ]]; then
            if ! extract_performance_metrics "$test_log" "$test_id"; then
                # P95 exceeded target, mark test as failed
                ((PASSED_TESTS--))
                ((FAILED_TESTS++))
                ((PERFORMANCE_PASSED--))
                
                # Update test result
                TEST_RESULTS[-1]="${RED}✗${NC} $test_id - ${test_duration}s (P95 exceeded target)"
                FAILED_TEST_IDS+=("$test_id")
                
                log_and_print "  ${YELLOW}⚠️  P95 exceeded target (> 4500ms)${NC}"
            fi
        fi
        
    else
        local test_end=$(date +%s)
        local test_duration=$((test_end - test_start))
        
        log_and_print "  ${RED}✗ FAILED${NC} (${test_duration}s)"
        log_and_print "  Error details saved to: $(basename "$test_log")"
        log_message "TEST FAILED: $test_id - Duration: ${test_duration}s"
        
        # Extract error message
        local error_msg=$(grep -E "(FAILED|ERROR|AssertionError)" "$test_log" | head -n 3 | sed 's/^/    /')
        if [ ! -z "$error_msg" ]; then
            log_message "Error details: $error_msg"
        fi
        
        ((FAILED_TESTS++))
        TEST_RESULTS+=("${RED}✗${NC} $test_id - ${test_duration}s")
        FAILED_TEST_IDS+=("$test_id")
    fi
    
    echo
}

# Function to extract performance metrics from test output
extract_performance_metrics() {
    local test_log="$1"
    local test_id="$2"
    
    # Try to extract P50, P95, and success rate from the log
    local p50=$(grep -oE "P50: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}')
    local p95=$(grep -oE "P95: [0-9.]+" "$test_log" | tail -1 | awk '{print $2}')
    local success_rate=$(grep -oE "Success Rate: [0-9.]+%" "$test_log" | tail -1 | awk '{print $3}' | tr -d '%')
    
    if [ ! -z "$p50" ] && [ ! -z "$p95" ]; then
        PERF_TESTS_RUN=$((PERF_TESTS_RUN + 1))
        PERF_P50_TOTAL=$(echo "$PERF_P50_TOTAL + $p50" | bc)
        PERF_P95_TOTAL=$(echo "$PERF_P95_TOTAL + $p95" | bc)
        
        if [ ! -z "$success_rate" ]; then
            PERF_SUCCESS_RATE_TOTAL=$(echo "$PERF_SUCCESS_RATE_TOTAL + $success_rate" | bc)
        fi
        
        # Check if P95 meets target (4500ms = 4.5s)
        local p95_passed=$(echo "$p95 < 4500" | bc)
        if [ "$p95_passed" -eq 0 ]; then
            # P95 exceeded target, mark as failed
            return 1
        fi
        
        log_message "Performance metrics for $test_id: P50=${p50}ms, P95=${p95}ms, Success=${success_rate}%"
    fi
    return 0
}

# Function to check environment
check_environment() {
    echo -e "${BLUE}Environment Check${NC}"
    
    # Check for .env file
    if [ -f "$ENV_FILE" ]; then
        log_and_print "  Environment: ${GREEN}✓ .env file found${NC}"
        # Load environment variables
        set -a
        source "$ENV_FILE"
        set +a
    else
        log_and_print "  Environment: ${RED}✗ .env file not found${NC}"
        echo "  Please create a .env file with Azure OpenAI credentials"
        exit 1
    fi
    
    # Check for required API keys
    if [ ! -z "$AZURE_OPENAI_API_KEY" ]; then
        log_and_print "  API Key: ${GREEN}✓ Azure OpenAI key configured${NC}"
    else
        log_and_print "  API Key: ${RED}✗ Azure OpenAI key not found${NC}"
        echo "  Please set AZURE_OPENAI_API_KEY in .env file"
        exit 1
    fi
    
    # Display Python version
    echo "  Python: $($PYTHON --version 2>&1)"
    echo "  Working Directory: $(pwd)"
    echo
}

# Function to start API server
start_api_server() {
    echo -e "${BLUE}Starting API Server${NC}"
    echo "  Starting API server on port $API_PORT..."
    
    # Kill any existing server on the port
    if lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  Killing existing process on port $API_PORT..."
        lsof -Pi :$API_PORT -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Start the API server in background
    nohup uvicorn src.main:app --host 0.0.0.0 --port $API_PORT > /tmp/api_test.log 2>&1 &
    API_PID=$!
    
    # Wait for API to be ready
    echo -n "  Waiting for API to be ready."
    for i in {1..30}; do
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            echo -e "  ${GREEN}✓${NC} API server started (PID: $API_PID)"
            log_message "API server started successfully on port $API_PORT (PID: $API_PID)"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    echo -e " ${RED}✗${NC}"
    echo "  ${RED}✗ Failed to start API server${NC}"
    echo "  Check /tmp/api_test.log for details"
    cat /tmp/api_test.log
    exit 1
}

# Function to stop API server
stop_api_server() {
    if [ ! -z "$API_PID" ]; then
        echo -e "${BLUE}Cleaning up...${NC}"
        kill $API_PID 2>/dev/null || true
        sleep 1
        # Force kill if still running
        kill -9 $API_PID 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} API server stopped"
        log_message "API server stopped (PID: $API_PID)"
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running Performance Tests (1 test)${NC}"
    echo "Testing file: test/performance/test_keyword_extraction_performance.py"
    echo "⚠️  Performance tests may take longer and use real Azure OpenAI APIs"
    echo
    
    # Performance test configurations - Using TestClient now, no need for API server
    local perf_tests=(
        "API-KW-201-PT:test/performance/test_keyword_extraction_performance.py::TestKeywordExtractionPerformance::test_keyword_extraction_performance"
    )
    
    for test_config in "${perf_tests[@]}"; do
        IFS=':' read -r test_id test_path <<< "$test_config"
        
        # Skip if specific test requested and doesn't match
        if [ ! -z "$PERF_TEST" ] && [ "$PERF_TEST" != "keyword" ]; then
            continue
        fi
        
        run_test "$test_id" "$test_path" 120 "performance" "keyword"
    done
}

# Function to display summary report
display_summary() {
    local end_time=$(date '+%Y-%m-%d %H:%M:%S')
    local python_version=$($PYTHON --version 2>&1 | awk '{print $2}')
    
    # Calculate total duration
    local script_end=$(date +%s)
    local script_duration=$((script_end - SCRIPT_START))
    
    echo
    echo "==============================================="
    echo "Health & Keyword Real API 測試報告 (Performance)"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    echo "測試總數: 1 個測試案例 (Performance only)"
    echo "執行環境: $python_version"
    echo "總執行時間: ${script_duration}s"
    echo "日誌檔案: $(basename "$LOG_FILE")"
    echo
    
    echo "測試檔案清單"
    echo "------------"
    echo "效能測試 (1個測試):"
    echo "  - test/performance/test_keyword_extraction_performance.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $PASSED_TESTS / $TOTAL_TESTS"
    
    # Calculate pass rate
    if [ $TOTAL_TESTS -gt 0 ]; then
        local pass_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo "通過: $PASSED_TESTS (${pass_rate}%)"
    else
        echo "通過: 0"
    fi
    
    echo "失敗: $FAILED_TESTS"
    echo "跳過: $SKIPPED_TESTS"
    echo
    
    echo "測試類型統計"
    echo "------------"
    if [ $PERFORMANCE_TOTAL -gt 0 ]; then
        local perf_rate=$((PERFORMANCE_PASSED * 100 / PERFORMANCE_TOTAL))
        echo "效能測試 (Performance): $PERFORMANCE_PASSED/$PERFORMANCE_TOTAL (${perf_rate}%)"
    fi
    echo
    
    echo "模組統計"
    echo "--------"
    if [ $HEALTH_TOTAL -gt 0 ]; then
        local health_rate=$((HEALTH_PASSED * 100 / HEALTH_TOTAL))
        echo "健康檢查 (Health): $HEALTH_PASSED/$HEALTH_TOTAL (${health_rate}%)"
    fi
    if [ $KEYWORD_TOTAL -gt 0 ]; then
        local keyword_rate=$((KEYWORD_PASSED * 100 / KEYWORD_TOTAL))
        echo "關鍵字提取 (Keyword): $KEYWORD_PASSED/$KEYWORD_TOTAL (${keyword_rate}%)"
    fi
    echo
    
    echo "優先級統計"
    echo "----------"
    if [ $P0_TOTAL -gt 0 ]; then
        local p0_rate=$((P0_PASSED * 100 / P0_TOTAL))
        echo "P0 (Critical): $P0_PASSED/$P0_TOTAL (${p0_rate}%)"
    fi
    if [ $P1_TOTAL -gt 0 ]; then
        local p1_rate=$((P1_PASSED * 100 / P1_TOTAL))
        echo "P1 (Important): $P1_PASSED/$P1_TOTAL (${p1_rate}%)"
    fi
    echo
    
    # Display test distribution matrix
    echo "=== 測試分布矩陣 ==="
    echo
    echo "| 測試               | 單元測試 | 整合測試 | 效能測試 | 總計 |"
    echo "|--------------------|----------|----------|----------|------|"
    
    # Health check row (no tests in this script)
    echo "| 健康檢查           | 0        | 0        | 0        | 0    |"
    
    # Keyword extraction row (only 1 PT in this script)
    echo "| 關鍵字提取         | 0        | 0        | 1        | 1    |"
    
    # Total row
    echo "| **總計**           | **0**    | **0**    | **1**    | **1**  |"
    echo
    
    # Display pass/fail statistics
    echo "=== 測試執行結果 ==="
    echo
    echo "| 測試類型           | 通過 | 失敗 | 總計 | 成功率 |"
    echo "|--------------------|------|------|------|--------|"
    
    # Performance test results only (this script only runs PT)
    if [ $PERFORMANCE_TOTAL -gt 0 ]; then
        local perf_rate=$((PERFORMANCE_PASSED * 100 / PERFORMANCE_TOTAL))
        printf "| %-18s | %4d | %4d | %4d | %5d%% |\n" "效能測試" "$PERFORMANCE_PASSED" "$((PERFORMANCE_TOTAL - PERFORMANCE_PASSED))" "$PERFORMANCE_TOTAL" "$perf_rate"
    fi
    
    # Total results
    local total_rate=0
    if [ $TOTAL_TESTS -gt 0 ]; then
        total_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    printf "| %-18s | %4d | %4d | %4d | %5d%% |\n" "**總計**" "$PASSED_TESTS" "$FAILED_TESTS" "$TOTAL_TESTS" "$total_rate"
    echo
    
    # Display failed tests if any
    if [ ${#FAILED_TEST_IDS[@]} -gt 0 ]; then
        echo "失敗測試清單:"
        for failed_id in "${FAILED_TEST_IDS[@]}"; do
            echo "  - $failed_id"
        done
        echo
    fi
    
    # Display performance metrics summary if available
    if [ $PERF_TESTS_RUN -gt 0 ]; then
        echo
        echo "=== 效能測試詳細結果 ==="
        echo
        echo "| 測試編號 | 測試名稱 | P50 (秒) | P95 (秒) | 成功率 | P95目標 | 狀態 |"
        echo "|----------|----------|----------|----------|--------|---------|------|"
        
        # Calculate averages
        local avg_p50=$(echo "scale=3; $PERF_P50_TOTAL / $PERF_TESTS_RUN / 1000" | bc)
        local avg_p95=$(echo "scale=3; $PERF_P95_TOTAL / $PERF_TESTS_RUN / 1000" | bc)
        local avg_success=$(echo "scale=1; $PERF_SUCCESS_RATE_TOTAL / $PERF_TESTS_RUN" | bc)
        
        # Determine status based on P95 target (4.5 seconds)
        local status="✅"
        if (( $(echo "$avg_p95 > 4.5" | bc -l) )); then
            status="❌"
        fi
        
        printf "| %-8s | %-8s | %8.3f | %8.3f | %6.1f%% | < 4.5s | %s |\n" \
            "API-KW-201-PT" "關鍵字提取響應時間" "$avg_p50" "$avg_p95" "$avg_success" "$status"
        echo
    fi
    
    # Log summary to file
    {
        echo "=== TEST SUMMARY ==="
        echo "End Time: $end_time"
        echo "Total Tests: $TOTAL_TESTS"
        echo "Passed: $PASSED_TESTS"
        echo "Failed: $FAILED_TESTS"
        echo "Skipped: $SKIPPED_TESTS"
        echo "Duration: ${script_duration}s"
        
        if [ ${#FAILED_TEST_IDS[@]} -gt 0 ]; then
            echo "Failed Test IDs: ${FAILED_TEST_IDS[@]}"
        fi
        
        echo "===================="
    } >> "$LOG_FILE"
}

# Trap to ensure cleanup on exit
trap stop_api_server EXIT

# Main execution
main() {
    SCRIPT_START=$(date +%s)
    
    # Run in background if requested
    if [ "$BACKGROUND" = true ]; then
        echo "Running tests in background..."
        echo "Log file: $LOG_FILE"
        nohup "$0" "${@/--background/}" > "$LOG_FILE" 2>&1 &
        echo "Background PID: $!"
        exit 0
    fi
    
    # Display header
    echo -e "${BLUE}=== Health & Keyword Real API Test Suite (Performance) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "⚠️  This uses REAL Azure OpenAI APIs and will incur costs!"
    echo
    
    # Log environment information
    log_environment_info
    
    # Check environment
    check_environment
    
    # Note: Performance tests now use TestClient, no need to start API server
    # The test will create its own app instance internally
    
    # Run performance tests
    run_performance_tests
    
    # Display summary report
    display_summary
}

# Run main function
main "$@"