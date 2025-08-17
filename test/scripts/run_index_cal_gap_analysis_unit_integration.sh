#!/bin/bash

# Unit and Integration Test Runner for Index Calculation and Gap Analysis
# Tests with mocked services (no real API calls)
# Based on test-spec-index-cal-gap-analysis.md v1.0.7

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
# Generate timestamp once for consistent naming
TIMESTAMP=$(date +%Y%m%d_%H%M)
LOG_FILE="$LOG_DIR/test_suite_unit_integration_${TIMESTAMP}.log"

# Command line options
STAGE_EXEC=""
VERBOSE=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            STAGE_EXEC="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "Unit and Integration Test Runner (Mock Tests)"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <unit|integration>  Run specific test stage"
    echo "  --verbose                   Show verbose output"
    echo "  --help, -h                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                         # Run all 47 tests (20 unit + 27 integration)"
    echo "  $0 --stage unit           # Run only unit tests (20 tests)"
    echo "  $0 --stage integration    # Run only integration tests (27 tests)"
    echo ""
    echo "Note: These tests use mocks and do not require Azure OpenAI API access."
    exit 0
fi

# Function to manage log files (keep only latest 6)
manage_log_files() {
    # Clean up old main logs
    local log_files=($(ls -t "$LOG_DIR"/test_suite_unit_integration_*.log 2>/dev/null | grep -v "_batch" || true))
    if [ ${#log_files[@]} -gt 6 ]; then
        for ((i=6; i<${#log_files[@]}; i++)); do
            rm -f "${log_files[i]}"
            # Also remove corresponding batch log if exists
            local batch_log="${log_files[i]%.log}_batch.log"
            [ -f "$batch_log" ] && rm -f "$batch_log"
            echo "Removed old logs: ${log_files[i]}" >> "$LOG_FILE"
        done
    fi
}

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to log environment info
log_environment_info() {
    log_message "=== ENVIRONMENT INFORMATION ==="
    log_message "Python Version: $(python --version 2>&1)"
    log_message "Working Directory: $(pwd)"
    log_message "Script Version: Unit & Integration Test Runner v1.0"
    log_message "Test Specification: test-spec-index-cal-gap-analysis.md v1.0.7"
    log_message "Virtual Environment: ${VIRTUAL_ENV:-Not Active}"
    
    # LLM Configuration (from environment)
    log_message "LLM Configuration (Mocked):"
    log_message "  - Keywords Extraction: ${LLM_MODEL_KEYWORDS:-gpt41-mini} @ ${GPT41_MINI_JAPANEAST_ENDPOINT:-Mocked}"
    log_message "  - Gap Analysis: ${LLM_MODEL_GAP_ANALYSIS:-gpt-4.1} @ ${AZURE_OPENAI_ENDPOINT:-Mocked}"
    log_message "  - Index Calculation: Uses Embedding API only (no LLM)"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Mocked}"
    log_message "  - GPT-4.1 Mini Deployment: ${GPT41_MINI_JAPANEAST_DEPLOYMENT:-Mocked}"
    
    log_message "Test Files:"
    log_message "  - Unit Tests: test/unit/test_gap_analysis_v2.py"
    log_message "  - Integration Tests: test/integration/test_gap_analysis_v2_integration_complete.py"
    log_message "  - Integration Tests: test/integration/test_error_handling_v2.py"
    log_message "Total Tests: 47 (20 Unit + 27 Integration)"
    log_message "Mock Services: Enabled (No real API calls)"
    log_message "================================"
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
        # P0 Priority tests (critical functionality)
        "API-GAP-001-UT"|"API-GAP-002-UT"|"API-GAP-005-UT"|"API-GAP-006-UT"|"API-GAP-007-UT"|"API-GAP-008-UT"|"API-GAP-009-UT"|"API-GAP-010-UT"|"API-GAP-011-UT"|"API-GAP-012-UT"|"API-GAP-014-UT"|"API-GAP-015-UT")
            echo "P0" ;;
        "API-GAP-001-IT"|"API-GAP-002-IT"|"API-GAP-003-IT"|"API-GAP-005-IT"|"API-GAP-006-IT"|"API-GAP-007-IT"|"API-GAP-008-IT"|"API-GAP-009-IT"|"API-GAP-010-IT"|"API-GAP-011-IT"|"API-GAP-014-IT")
            echo "P0" ;;
        # P1 Priority tests (important functionality)
        "API-GAP-013-UT"|"API-GAP-016-UT"|"API-GAP-018-UT"|"API-GAP-019-UT"|"API-GAP-020-UT")
            echo "P1" ;;
        "API-GAP-004-IT"|"API-GAP-012-IT"|"API-GAP-013-IT"|"API-GAP-018-IT"|"API-GAP-019-IT"|"API-GAP-020-IT"|"API-GAP-021-IT"|"API-GAP-022-IT"|"API-GAP-023-IT"|"API-GAP-024-IT"|"API-GAP-025-IT"|"API-GAP-026-IT"|"API-GAP-027-IT"|"API-GAP-028-IT")
            echo "P1" ;;
        # P2 Priority tests (nice to have)
        "API-GAP-003-UT"|"API-GAP-004-UT"|"API-GAP-017-UT")
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
    
    # Determine timeout command
    local timeout_cmd=""
    if command -v gtimeout >/dev/null 2>&1; then
        timeout_cmd="gtimeout ${timeout}s"
    elif command -v timeout >/dev/null 2>&1; then
        timeout_cmd="timeout ${timeout}s"
    else
        timeout_cmd=""
    fi
    
    if [ -n "$timeout_cmd" ]; then
        timeout_exec_cmd="$timeout_cmd python -m pytest"
    else
        timeout_exec_cmd="python -m pytest"
    fi
    
    # Execute test with mocks enabled (default behavior)
    if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 > "$test_output_file" 2>&1; then
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
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
            "P2") P2_PASSED+=("${test_id}") ;;
        esac
        
        # Log key test info to main log
        log_message "TEST DETAILS: $test_id completed successfully"
        
        # Clean up successful test log if not verbose
        if [ "$VERBOSE" = false ]; then
            rm -f "$test_output_file"
        fi
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
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
            "P2") P2_FAILED+=("${test_id}") ;;
        esac
        
        # Log error info to main log
        log_message "TEST ERROR: $test_id failed - see $test_output_file for details"
        # Extract and log the actual error message
        local error_msg=$(grep -E "(FAILED|ERROR|AssertionError)" "$test_output_file" | head -3)
        if [ -n "$error_msg" ]; then
            log_message "Error summary: $error_msg"
        fi
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
    fi
    echo
}

# Function to run unit tests (20 tests)
run_unit_tests() {
    echo -e "${BLUE}Running Unit Tests (20 tests)${NC}"
    echo "Testing file: test/unit/test_gap_analysis_v2.py"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # All 20 unit tests from API-GAP-001-UT to API-GAP-020-UT
    local unit_tests=(
        "API-GAP-001-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_combined_analysis_service_initialization"
        "API-GAP-002-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_resource_pool_manager_initialization"
        "API-GAP-003-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_resource_pool_get_client"
        "API-GAP-004-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_resource_pool_max_capacity"
        "API-GAP-005-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_parallel_phase1_execution"
        "API-GAP-006-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_parallel_phase2_execution"
        "API-GAP-007-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_parallel_phase3_execution"
        "API-GAP-008-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_adaptive_retry_strategy_initialization"
        "API-GAP-009-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_empty_fields_error_retry"
        "API-GAP-010-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_timeout_error_retry"
        "API-GAP-011-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_rate_limit_error_retry"
        "API-GAP-012-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_partial_result_handling"
        "API-GAP-013-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_complete_failure_handling"
        "API-GAP-014-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_service_dependency_validation"
        "API-GAP-015-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_keyword_coverage_calculation"
        "API-GAP-016-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_error_classifier"
        "API-GAP-017-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_statistics_tracking"
        "API-GAP-018-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_html_text_processing_difference"
        "API-GAP-019-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_taskgroup_exception_handling"
        "API-GAP-020-UT:test/unit/test_gap_analysis_v2.py::TestGapAnalysisV2Unit::test_service_cleanup_on_error"
    )
    
    for test_entry in "${unit_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 60 "unit"
    done
}

# Function to run integration tests (27 tests)
run_integration_tests() {
    echo -e "${BLUE}Running Integration Tests (27 tests)${NC}"
    echo "Testing files:"
    echo "  - test/integration/test_gap_analysis_v2_integration_complete.py (17 tests)"
    echo "  - test/integration/test_error_handling_v2.py (10 tests)"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # Run integration tests as a batch for efficiency
    local test_start=$(date +%s)
    local test_output_file="${LOG_DIR}/test_suite_unit_integration_${TIMESTAMP}_batch.log"
    
    echo -e "${BLUE}Running all integration tests in batch...${NC}"
    
    # Use virtual environment Python if available
    local python_cmd="python"
    if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
        python_cmd="venv/bin/python"
    fi
    
    # Run integration test files separately to avoid cross-test contamination
    local gap_analysis_passed=0
    local gap_analysis_failed=0
    local error_handling_passed=0
    local error_handling_failed=0
    
    # First run gap analysis tests
    echo -e "  Running gap_analysis_v2_integration_complete.py..."
    $python_cmd -m pytest test/integration/test_gap_analysis_v2_integration_complete.py -v --tb=short --durations=0 > "${test_output_file}.gap" 2>&1
    # Always parse the output regardless of exit code
    gap_analysis_passed=$(grep -E "passed" "${test_output_file}.gap" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo "0")
    gap_analysis_failed=$(grep -E "failed" "${test_output_file}.gap" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo "0")
    
    if [ "$gap_analysis_failed" -gt 0 ]; then
        echo -e "    ${RED}✗ Some tests failed${NC}"
    elif [ "$gap_analysis_passed" -gt 0 ]; then
        echo -e "    ${GREEN}✓ All tests passed${NC}"
    else
        echo -e "    ${RED}✗ Test execution failed${NC}"
        gap_analysis_failed=17
    fi
    
    # Then run error handling tests
    echo -e "  Running error_handling_v2.py..."
    $python_cmd -m pytest test/integration/test_error_handling_v2.py -v --tb=short --durations=0 > "${test_output_file}.error" 2>&1
    # Always parse the output regardless of exit code
    error_handling_passed=$(grep -E "passed" "${test_output_file}.error" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo "0")
    error_handling_failed=$(grep -E "failed" "${test_output_file}.error" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo "0")
    
    if [ "$error_handling_failed" -gt 0 ]; then
        echo -e "    ${RED}✗ Some tests failed${NC}"
    elif [ "$error_handling_passed" -gt 0 ]; then
        echo -e "    ${GREEN}✓ All tests passed${NC}"
    else
        echo -e "    ${RED}✗ Test execution failed${NC}"
        error_handling_failed=10
    fi
    
    # Combine results into single output file
    cat "${test_output_file}.gap" "${test_output_file}.error" > "$test_output_file" 2>&1
    
    # Calculate totals
    local total_passed=$((gap_analysis_passed + error_handling_passed))
    local total_failed=$((gap_analysis_failed + error_handling_failed))
    
    local test_end=$(date +%s)
    local duration=$((test_end - test_start))
    
    echo -e "  ${BLUE}Test Results:${NC} (${duration}s)"
    echo -e "    Gap Analysis: ${GREEN}${gap_analysis_passed} passed${NC}, ${RED}${gap_analysis_failed} failed${NC}"
    echo -e "    Error Handling: ${GREEN}${error_handling_passed} passed${NC}, ${RED}${error_handling_failed} failed${NC}"
    echo -e "    Total: ${GREEN}${total_passed} passed${NC}, ${RED}${total_failed} failed${NC}"
    
    # Update global arrays based on results
    # For gap analysis tests
    if [ "$gap_analysis_failed" -eq 0 ]; then
        for i in {1..17}; do
            test_id=$(printf "API-GAP-%03d-IT" $i)
            PASSED_TESTS+=("$test_id")
            INTEGRATION_PASSED+=("$test_id")
        done
    else
        for i in {1..17}; do
            test_id=$(printf "API-GAP-%03d-IT" $i)
            FAILED_TESTS+=("$test_id")
            INTEGRATION_FAILED+=("$test_id")
        done
    fi
    
    # For error handling tests (API-GAP-018-IT to API-GAP-027-IT)
    if [ "$error_handling_failed" -eq 0 ]; then
        for i in {18..27}; do
            test_id=$(printf "API-GAP-%03d-IT" $i)
            PASSED_TESTS+=("$test_id")
            INTEGRATION_PASSED+=("$test_id")
        done
    else
        for i in {18..27}; do
            test_id=$(printf "API-GAP-%03d-IT" $i)
            FAILED_TESTS+=("$test_id")
            INTEGRATION_FAILED+=("$test_id")
        done
    fi
    
    # Clean up temp files
    rm -f "${test_output_file}.gap" "${test_output_file}.error"
    
    if [ "$total_failed" -eq 0 ]; then
        echo -e "  ${GREEN}✓ All integration tests passed${NC}"
    else
        echo -e "  ${RED}✗ Some tests failed${NC}"
        echo "  Error details saved to: $(basename "$test_output_file")"
    fi
}

# Function to parse batch test results
parse_batch_test_results() {
    local output_file="$1"
    
    # Extract passed tests
    local passed_tests=$(grep -E "test_API_GAP_[0-9]+_IT.*PASSED" "$output_file" | sed -E 's/.*test_(API_GAP_[0-9]+_IT).*/\1/' || true)
    
    # Extract failed tests
    local failed_tests=$(grep -E "test_API_GAP_[0-9]+_IT.*FAILED" "$output_file" | sed -E 's/.*test_(API_GAP_[0-9]+_IT).*/\1/' || true)
    
    # Update global arrays based on results
    while IFS= read -r test_id; do
        if [ -n "$test_id" ]; then
            PASSED_TESTS+=("${test_id//_/-}")
            INTEGRATION_PASSED+=("${test_id//_/-}")
            
            # Determine priority from test ID
            case "${test_id//_/-}" in
                API-GAP-00[1-3]-IT|API-GAP-00[5-9]-IT|API-GAP-01[0-1]-IT|API-GAP-014-IT) P0_PASSED+=("${test_id//_/-}") ;;
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT|API-GAP-01[8-9]-IT|API-GAP-02[0-7]-IT) P1_PASSED+=("${test_id//_/-}") ;;
            esac
        fi
    done <<< "$passed_tests"
    
    while IFS= read -r test_id; do
        if [ -n "$test_id" ]; then
            FAILED_TESTS+=("${test_id//_/-}")
            INTEGRATION_FAILED+=("${test_id//_/-}")
            
            # Determine priority from test ID  
            case "${test_id//_/-}" in
                API-GAP-00[1-3]-IT|API-GAP-00[5-9]-IT|API-GAP-01[0-1]-IT|API-GAP-014-IT) P0_FAILED+=("${test_id//_/-}") ;;
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT|API-GAP-01[8-9]-IT|API-GAP-02[0-7]-IT) P1_FAILED+=("${test_id//_/-}") ;;
            esac
        fi
    done <<< "$failed_tests"
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Unit & Integration 測試報告"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: test-spec-index-cal-gap-analysis.md v1.0.7"
    echo "測試總數: 47 個測試案例 (20 Unit + 27 Integration)"
    echo "執行環境: $(python --version 2>&1 | cut -d' ' -f2)"
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
    
    echo "測試檔案清單"
    echo "------------"
    echo "單元測試 (20個測試):"
    echo "  - test/unit/test_gap_analysis_v2.py"
    echo ""
    echo "整合測試 (27個測試):"
    echo "  - test/integration/test_gap_analysis_v2_integration_complete.py (17個測試)"
    echo "  - test/integration/test_error_handling_v2.py (10個測試)"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 47"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed test type statistics
    echo "測試類型統計"
    echo "------------"
    local unit_total=$((${#UNIT_PASSED[@]} + ${#UNIT_FAILED[@]}))
    local integration_total=$((${#INTEGRATION_PASSED[@]} + ${#INTEGRATION_FAILED[@]}))
    
    local unit_rate=0
    local integration_rate=0
    
    if [ $unit_total -gt 0 ]; then
        unit_rate=$(( ${#UNIT_PASSED[@]} * 100 / unit_total ))
    fi
    if [ $integration_total -gt 0 ]; then
        integration_rate=$(( ${#INTEGRATION_PASSED[@]} * 100 / integration_total ))
    fi
    
    echo "單元測試 (Unit): ${#UNIT_PASSED[@]}/${unit_total} (${unit_rate}%) - 規格要求: 20"
    echo "整合測試 (Integration): ${#INTEGRATION_PASSED[@]}/${integration_total} (${integration_rate}%) - 規格要求: 27"
    echo
    
    # Priority statistics
    echo "優先級統計"
    echo "----------"
    
    local p0_total=$((${#P0_PASSED[@]} + ${#P0_FAILED[@]}))
    local p1_total=$((${#P1_PASSED[@]} + ${#P1_FAILED[@]}))
    local p2_total=$((${#P2_PASSED[@]} + ${#P2_FAILED[@]}))
    
    local p0_rate=0
    local p1_rate=0
    local p2_rate=0
    
    if [ $p0_total -gt 0 ]; then
        p0_rate=$(( ${#P0_PASSED[@]} * 100 / p0_total ))
    fi
    if [ $p1_total -gt 0 ]; then
        p1_rate=$(( ${#P1_PASSED[@]} * 100 / p1_total ))
    fi
    if [ $p2_total -gt 0 ]; then
        p2_rate=$(( ${#P2_PASSED[@]} * 100 / p2_total ))
    fi
    
    echo "P0 (Critical): ${#P0_PASSED[@]}/${p0_total} (${p0_rate}%)"
    echo "P1 (Important): ${#P1_PASSED[@]}/${p1_total} (${p1_rate}%)"
    echo "P2 (Nice to have): ${#P2_PASSED[@]}/${p2_total} (${p2_rate}%)"
    echo
    
    # Detailed table
    echo "=== 詳細測試統計表 ==="
    echo
    echo "| 測試類型     | 通過/總數 | 成功率 | 失敗測試案例 |"
    echo "|--------------|-----------|--------|--------------|"
    echo "| 單元測試     | ${#UNIT_PASSED[@]}/${unit_total} | ${unit_rate}% | $(IFS=','; echo "${UNIT_FAILED[*]}") |"
    echo "| 整合測試     | ${#INTEGRATION_PASSED[@]}/${integration_total} | ${integration_rate}% | $(IFS=','; echo "${INTEGRATION_FAILED[*]}") |"
    echo "| **總計**     | **${#PASSED_TESTS[@]}/${total_tests}** | **${pass_rate}%** | $(IFS=','; echo "${FAILED_TESTS[*]}") |"
    echo
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例詳情:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            local priority=$(get_test_priority "$test_id")
            echo "❌ $test_id ($priority) - 日誌: $LOG_DIR/test_${test_id}_*.log"
        done
        echo
        echo "修復建議:"
        echo "1. 檢查測試驗證報告中的已知問題"
        echo "2. 運行單一失敗測試進行詳細調試: pytest test/path/to/test.py::test_function -v"
        echo "3. 檢查 mock 設定是否正確"
        echo "4. 參考 CLAUDE.md 中的依賴配置指南"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo -e "🎉 ${GREEN}所有 $total_tests 個 Unit & Integration 測試全部通過！${NC}"
        echo "   所有測試都使用 mock services，無需 Azure OpenAI API"
    else
        echo -e "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
        if [ ${#P0_FAILED[@]} -gt 0 ]; then
            echo "   ⚠️  有 ${#P0_FAILED[@]} 個 P0 (Critical) 測試失敗，需要優先修復"
        fi
    fi
}

# Main execution
main() {
    # Change to project root
    cd "$(dirname "$0")/../.."
    
    # Use virtual environment Python if available
    local python_cmd="python"
    if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
        python_cmd="venv/bin/python"
    fi
    
    # Initialize logging
    manage_log_files
    log_message "=== Unit & Integration Test Suite Started ==="
    log_message "Based on test-spec-index-cal-gap-analysis.md v1.0.7"
    log_message "Python version: $(python --version 2>&1)"
    log_message "Stage execution: ${STAGE_EXEC:-all}"
    log_environment_info
    
    echo -e "${BLUE}=== Unit & Integration Test Suite (47 tests) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "Based on: test-spec-index-cal-gap-analysis.md v1.0.7"
    echo "Note: These tests use mocked services (no real API calls)"
    echo
    
    echo -e "${BLUE}Environment Check${NC}"
    if [ -f ".env" ]; then
        echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
        log_message "Environment: .env file found"
    else
        echo -e "  Environment: ${YELLOW}⚠ .env file not found (not required for mock tests)${NC}"
        log_message "WARNING: .env file not found, but not required for mock tests"
    fi
    echo -e "  Python: $(python --version 2>&1)"
    echo -e "  Working Directory: $(pwd)"
    echo
    
    # Execute based on stage or run all tests
    case "$STAGE_EXEC" in
        "unit")
            run_unit_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "")
            # Run all tests in order
            run_unit_tests
            run_integration_tests
            ;;
        *)
            echo -e "${RED}Unknown stage: $STAGE_EXEC${NC}"
            echo "Valid stages: unit, integration"
            exit 1
            ;;
    esac
    
    # Generate detailed report
    generate_report
    
    # Log detailed test summary
    log_message "=== DETAILED TEST SUMMARY ==="
    log_message "Total Tests Executed: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
    log_message "Unit Tests - Passed: ${#UNIT_PASSED[@]}, Failed: ${#UNIT_FAILED[@]}"
    log_message "Integration Tests - Passed: ${#INTEGRATION_PASSED[@]}, Failed: ${#INTEGRATION_FAILED[@]}"
    log_message "P0 Priority - Passed: ${#P0_PASSED[@]}, Failed: ${#P0_FAILED[@]}"
    log_message "P1 Priority - Passed: ${#P1_PASSED[@]}, Failed: ${#P1_FAILED[@]}"
    log_message "P2 Priority - Passed: ${#P2_PASSED[@]}, Failed: ${#P2_FAILED[@]}"
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        log_message "=== FAILED TESTS DETAILS ==="
        for test_id in "${FAILED_TESTS[@]}"; do
            log_message "FAILED: $test_id"
            # Log last few lines of error from individual test logs
            local error_log=$(ls -t "$LOG_DIR"/test_${test_id}_*.log 2>/dev/null | head -1)
            if [ -f "$error_log" ]; then
                log_message "Error snippet from $test_id:"
                tail -5 "$error_log" | while IFS= read -r line; do
                    log_message "  $line"
                done
            fi
        done
    fi
    
    log_message "=== Test Suite Completed ==="
    
    # Final result determination
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All Unit & Integration tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Execute main function
main