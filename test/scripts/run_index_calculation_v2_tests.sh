#!/bin/bash

# Index Calculation V2 Test Suite Runner
# Tests all 26 Index Calculation V2 test cases
# Based on TEST_MATRIX.md testing framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup logging
LOG_DIR="test/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/index_calculation_v2_$(date +%Y%m%d_%H%M%S).log"

# Function to manage log files (keep only latest 6)
manage_log_files() {
    local log_files=($(ls -t "$LOG_DIR"/index_calculation_v2_*.log 2>/dev/null || true))
    if [ ${#log_files[@]} -gt 6 ]; then
        for ((i=6; i<${#log_files[@]}; i++)); do
            rm -f "${log_files[i]}"
            echo "Removed old log: ${log_files[i]}" >> "$LOG_FILE"
        done
    fi
}

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to log and print
log_and_print() {
    local message="$1"
    echo -e "$message"
    log_message "$message"
}

# Test tracking arrays
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()

# Test categorization
UNIT_PASSED=()
UNIT_FAILED=()
INTEGRATION_PASSED=()
INTEGRATION_FAILED=()
PERFORMANCE_PASSED=()
PERFORMANCE_FAILED=()
E2E_PASSED=()
E2E_FAILED=()

# Priority tracking
P0_PASSED=()
P0_FAILED=()
P1_PASSED=()
P1_FAILED=()
P2_PASSED=()
P2_FAILED=()

# Test execution times
TEST_TIMES=()
START_TIME=$(date +%s)

# Function to check test priority
get_test_priority() {
    local test_id="$1"
    case $test_id in
        "API-IC-001-UT"|"API-IC-002-UT"|"API-IC-007-UT"|"API-IC-009-UT"|"API-IC-101-IT"|"API-IC-102-IT"|"API-IC-103-IT"|"API-IC-104-IT"|"API-IC-201-PT"|"API-IC-202-PT"|"API-IC-203-PT"|"API-IC-301-E2E")
            echo "P0" ;;
        "API-IC-003-UT"|"API-IC-004-UT"|"API-IC-006-UT"|"API-IC-008-UT"|"API-IC-010-UT"|"API-IC-105-IT"|"API-IC-106-IT"|"API-IC-108-IT"|"API-IC-204-PT"|"API-IC-205-PT"|"API-IC-302-E2E")
            echo "P1" ;;
        "API-IC-005-UT"|"API-IC-107-IT"|"API-IC-303-E2E")
            echo "P2" ;;
        *)
            echo "Unknown" ;;
    esac
}

# Function to run a test and track detailed results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-120}"
    local category="$4"
    local priority=$(get_test_priority "$test_id")
    
    log_and_print "${BLUE}Running ${test_id} (${priority})...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s - Category: $category"
    
    local test_start=$(date +%s)
    local test_output_file="$LOG_DIR/test_${test_id}_$(date +%Y%m%d_%H%M%S).log"
    
    # Run test with output captured to log
    if ./venv/bin/python -m pytest "${test_path}" -v --tb=short --durations=0 --timeout=${timeout} > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${duration}s"
        PASSED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "unit") UNIT_PASSED+=("${test_id}") ;;
            "integration") INTEGRATION_PASSED+=("${test_id}") ;;
            "performance") PERFORMANCE_PASSED+=("${test_id}") ;;
            "e2e") E2E_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
            "P2") P2_PASSED+=("${test_id}") ;;
        esac
        
        # Clean up successful test log
        rm -f "$test_output_file"
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${RED}✗ FAILED${NC} (${duration}s)"
        log_message "TEST FAILED: $test_id - Duration: ${duration}s"
        log_message "ERROR LOG saved to: $test_output_file"
        FAILED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "unit") UNIT_FAILED+=("${test_id}") ;;
            "integration") INTEGRATION_FAILED+=("${test_id}") ;;
            "performance") PERFORMANCE_FAILED+=("${test_id}") ;;
            "e2e") E2E_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
            "P2") P2_FAILED+=("${test_id}") ;;
        esac
        
        # Show brief error info in terminal but keep full log in file
        echo "  Error details saved to: $(basename "$test_output_file")"
    fi
    echo
}

# Function to get test duration
get_test_duration() {
    local test_id="$1"
    for entry in "${TEST_TIMES[@]}"; do
        if [[ $entry == "${test_id}:"* ]]; then
            echo "${entry#*:}"
            return
        fi
    done
    echo "N/A"
}

# Function to generate detailed report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "Index Calculation V2 測試報告"
    echo "============================"
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "執行環境: 本地"
    echo "Python版本: $(python --version 2>&1 | cut -d' ' -f2)"
    echo "總執行時間: ${total_duration}s"
    echo "日誌檔案: $(basename "$LOG_FILE")"
    echo
    
    # Log the full report
    log_message "=== FINAL REPORT ==="
    log_message "Total Duration: ${total_duration}s"
    log_message "Total Tests: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))"
    log_message "Passed: ${#PASSED_TESTS[@]}"
    log_message "Failed: ${#FAILED_TESTS[@]}"
    log_message "Skipped: ${#SKIPPED_TESTS[@]}"
    
    # Test summary
    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))
    local pass_rate=0
    if [ $total_tests -gt 0 ]; then
        pass_rate=$(( ${#PASSED_TESTS[@]} * 100 / total_tests ))
    fi
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Priority statistics
    echo "優先級統計"
    echo "----------"
    
    local p0_total=$((${#P0_PASSED[@]} + ${#P0_FAILED[@]}))
    local p1_total=$((${#P1_PASSED[@]} + ${#P1_FAILED[@]}))
    local p2_total=$((${#P2_PASSED[@]} + ${#P2_FAILED[@]}))
    
    local p0_rate=$(( p0_total > 0 ? ${#P0_PASSED[@]} * 100 / p0_total : 0 ))
    local p1_rate=$(( p1_total > 0 ? ${#P1_PASSED[@]} * 100 / p1_total : 0 ))
    local p2_rate=$(( p2_total > 0 ? ${#P2_PASSED[@]} * 100 / p2_total : 0 ))
    
    echo "P0: ${#P0_PASSED[@]}/${p0_total} (${p0_rate}%)"
    echo "P1: ${#P1_PASSED[@]}/${p1_total} (${p1_rate}%)"
    echo "P2: ${#P2_PASSED[@]}/${p2_total} (${p2_rate}%)"
    echo
    
    # Detailed module statistics
    echo "=== 詳細測試統計 ==="
    echo
    echo "| 模組              | 單元測試 | 整合測試 | 效能測試 | E2E測試 | 總計 |"
    echo "|-------------------|----------|----------|----------|---------|------|"
    
    local total_passed=$((${#UNIT_PASSED[@]} + ${#INTEGRATION_PASSED[@]} + ${#PERFORMANCE_PASSED[@]} + ${#E2E_PASSED[@]}))
    local total_failed=$((${#UNIT_FAILED[@]} + ${#INTEGRATION_FAILED[@]} + ${#PERFORMANCE_FAILED[@]} + ${#E2E_FAILED[@]}))
    
    echo "| Index Calculation V2 | ${#UNIT_PASSED[@]}/${#UNIT_FAILED[@]} | ${#INTEGRATION_PASSED[@]}/${#INTEGRATION_FAILED[@]} | ${#PERFORMANCE_PASSED[@]}/${#PERFORMANCE_FAILED[@]} | ${#E2E_PASSED[@]}/${#E2E_FAILED[@]} | ${total_passed}/${total_failed} |"
    echo
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            echo "❌ $test_id - 查看日誌: $LOG_DIR/test_${test_id}_*.log"
        done
        echo
    fi
}

# Change to project root
cd "$(dirname "$0")/../.."

# Initialize logging
manage_log_files
log_message "=== Index Calculation V2 Test Suite Started ==="
log_message "Based on TEST_MATRIX.md v1.1.0"
log_message "Python version: $(python --version 2>&1)"

echo -e "${BLUE}=== Index Calculation V2 Test Suite (26 tests) ===${NC}"
echo "Timestamp: $(date)"
echo "Log file: $(basename "$LOG_FILE")"
echo

echo -e "${BLUE}1. Environment Check${NC}"
if [ -f ".env" ]; then
    echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
    log_message "Environment: .env file found"
else
    echo -e "  Environment: ${YELLOW}⚠ .env file not found${NC}"
    log_message "WARNING: .env file not found, using environment variables"
fi
echo -e "  Python: $(python --version 2>&1)"
echo

# Unit Tests (10 tests)
echo -e "${BLUE}2. Running Unit Tests (10 tests)${NC}"

run_test "API-IC-001-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_service_initialization" 30 "unit"
run_test "API-IC-002-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_key_generation" 30 "unit"
run_test "API-IC-003-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_ttl_expiration" 30 "unit"
run_test "API-IC-004-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_lru_eviction" 30 "unit"
run_test "API-IC-005-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_similarity_calculation_integration" 30 "unit"
run_test "API-IC-006-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_sigmoid_transform_parameters" 30 "unit"
run_test "API-IC-007-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_keyword_coverage_analysis" 30 "unit"
run_test "API-IC-008-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_tinymce_html_cleaning" 30 "unit"
run_test "API-IC-009-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_taskgroup_parallel_execution" 30 "unit"
run_test "API-IC-010-UT" "test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_taskgroup_error_handling" 30 "unit"

# Integration Tests (8 tests)
echo -e "${BLUE}3. Running Integration Tests (8 tests)${NC}"

run_test "API-IC-101-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_api_endpoint_basic_functionality" 60 "integration"
run_test "API-IC-102-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_cache_behavior_integration" 60 "integration"
run_test "API-IC-103-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_input_validation" 60 "integration"
run_test "API-IC-104-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_azure_openai_service_failure" 60 "integration"
run_test "API-IC-105-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_concurrent_request_handling" 60 "integration"
run_test "API-IC-106-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_large_document_handling" 60 "integration"
run_test "API-IC-107-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_service_stats_endpoint" 60 "integration"
run_test "API-IC-108-IT" "test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_cross_language_content" 60 "integration"

# Performance Tests (5 tests)
echo -e "${BLUE}4. Running Performance Tests (5 tests)${NC}"

run_test "API-IC-201-PT" "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_response_time_benchmark" 90 "performance"
run_test "API-IC-202-PT" "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_cache_performance" 90 "performance"
run_test "API-IC-203-PT" "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_high_concurrency_load" 120 "performance"
run_test "API-IC-204-PT" "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_memory_efficiency" 90 "performance"
run_test "API-IC-205-PT" "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_cache_size_limits" 90 "performance"

# E2E Tests (3 tests)
echo -e "${BLUE}5. Running E2E Tests (3 tests)${NC}"

run_test "API-IC-301-E2E" "test/e2e/test_index_calculation_v2_e2e.py::TestIndexCalculationV2E2E::test_complete_workflow" 90 "e2e"
run_test "API-IC-302-E2E" "test/e2e/test_index_calculation_v2_e2e.py::TestIndexCalculationV2E2E::test_error_recovery" 90 "e2e"
run_test "API-IC-303-E2E" "test/e2e/test_index_calculation_v2_e2e.py::TestIndexCalculationV2E2E::test_monitoring_and_logging_integration" 90 "e2e"

# Generate detailed report
generate_report

log_message "=== Test Suite Completed ==="

# Final result determination
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    log_and_print "${GREEN}🎉 All 26 Index Calculation V2 tests passed!${NC}"
    exit 0
else
    log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
    exit 1
fi