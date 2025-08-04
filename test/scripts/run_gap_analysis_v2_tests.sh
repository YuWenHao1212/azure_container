#!/bin/bash

# Gap Analysis V2 Test Suite Runner
# Tests all 43 Index Calculation and Gap Analysis V2 test cases
# Based on test-spec-index-cal-gap-analysis.md v1.0.1

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
LOG_FILE="$LOG_DIR/gap_analysis_v2_$(date +%Y%m%d_%H%M%S).log"

# Command line options
STAGE_EXEC=""
BACKGROUND_EXEC=false
VERBOSE=false
SHOW_HELP=false
PERFORMANCE_TESTS=""
SPECIFIC_PERF_TESTS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            STAGE_EXEC="$2"
            shift 2
            ;;
        --perf-test)
            SPECIFIC_PERF_TESTS="$2"
            STAGE_EXEC="performance"
            shift 2
            ;;
        --background)
            BACKGROUND_EXEC=true
            shift
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
    echo "Gap Analysis V2 Test Suite Runner"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <unit|integration|performance|e2e>  Run specific test stage"
    echo "  --perf-test <test-id>                       Run specific performance test(s)"
    echo "  --background                                Run tests in background"
    echo "  --verbose                                   Show verbose output"
    echo "  --help, -h                                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run all 43 tests"
    echo "  $0 --stage unit             # Run only unit tests (20 tests)"
    echo "  $0 --stage integration      # Run only integration tests (14 tests)"
    echo "  $0 --stage performance      # Run only performance tests (5 tests)"
    echo "  $0 --stage e2e             # Run only E2E tests (4 tests)"
    echo "  $0 --perf-test API-GAP-001-PT      # Run P50 test only"
    echo "  $0 --perf-test API-GAP-002-PT      # Run P95 test only"
    echo "  $0 --perf-test \"API-GAP-001-PT,API-GAP-002-PT\"  # Run both P50 and P95 tests"
    echo "  $0 --perf-test p50          # Shortcut for API-GAP-001-PT"
    echo "  $0 --perf-test p95          # Shortcut for API-GAP-002-PT"
    echo "  $0 --perf-test \"p50,p95\"    # Shortcut for both P50 and P95"
    echo "  $0 --background            # Run all tests in background"
    exit 0
fi

# Function to manage log files (keep only latest 6)
manage_log_files() {
    local log_files=($(ls -t "$LOG_DIR"/gap_analysis_v2_*.log 2>/dev/null || true))
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

# Function to clean up old logs (keep only latest 5)
cleanup_old_logs() {
    local test_id="$1"
    local log_pattern="$LOG_DIR/test_${test_id}_*.log"
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

# Function to check test priority based on test-spec-index-cal-gap-analysis.md
get_test_priority() {
    local test_id="$1"
    case $test_id in
        # P0 Priority tests (critical functionality)
        "API-GAP-001-UT"|"API-GAP-002-UT"|"API-GAP-005-UT"|"API-GAP-006-UT"|"API-GAP-007-UT"|"API-GAP-008-UT"|"API-GAP-009-UT"|"API-GAP-010-UT"|"API-GAP-011-UT"|"API-GAP-012-UT"|"API-GAP-014-UT"|"API-GAP-015-UT")
            echo "P0" ;;
        "API-GAP-001-IT"|"API-GAP-002-IT"|"API-GAP-003-IT"|"API-GAP-005-IT"|"API-GAP-006-IT"|"API-GAP-007-IT"|"API-GAP-008-IT"|"API-GAP-009-IT"|"API-GAP-010-IT"|"API-GAP-011-IT"|"API-GAP-014-IT")
            echo "P0" ;;
        "API-GAP-001-PT"|"API-GAP-002-PT"|"API-GAP-003-PT"|"API-GAP-004-PT")
            echo "P0" ;;
        "API-GAP-001-E2E")
            echo "P0" ;;
        # P1 Priority tests (important functionality)
        "API-GAP-013-UT"|"API-GAP-016-UT"|"API-GAP-018-UT"|"API-GAP-019-UT"|"API-GAP-020-UT")
            echo "P1" ;;
        "API-GAP-004-IT"|"API-GAP-012-IT"|"API-GAP-013-IT")
            echo "P1" ;;
        "API-GAP-002-E2E"|"API-GAP-003-E2E"|"API-GAP-004-E2E")
            echo "P1" ;;
        # P2 Priority tests (nice to have)
        "API-GAP-003-UT"|"API-GAP-004-UT"|"API-GAP-017-UT")
            echo "P2" ;;
        "API-GAP-005-PT")
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
    # Use gtimeout if available (from coreutils), otherwise use timeout, fallback to plain python
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
    
    # Execute test with correct python command
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
            "performance") PERFORMANCE_PASSED+=("${test_id}") ;;
            "e2e") E2E_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
            "P2") P2_PASSED+=("${test_id}") ;;
        esac
        
        # Clean up successful test log if not verbose
        if [ "$VERBOSE" = false ]; then
            rm -f "$test_output_file"
        fi
        
        # Clean up old logs for this test (keep only latest 5)
        cleanup_old_logs "$test_id"
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
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
        
        # Clean up old logs for this test (keep only latest 5)
        cleanup_old_logs "$test_id"
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

# Function to read performance test results from log files
read_performance_results() {
    local test_id="$1"
    local log_pattern="$LOG_DIR/performance_${test_id}_*.json"
    local latest_log=$(ls -t $log_pattern 2>/dev/null | head -n1)
    
    if [ -f "$latest_log" ]; then
        # Extract key metrics from JSON log
        local p50=$(grep -o '"p50_time_s": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        local p95=$(grep -o '"p95_time_s": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        local success_rate=$(grep -o '"success_rate": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        
        echo "${p50:-N/A}|${p95:-N/A}|${success_rate:-N/A}"
    else
        echo "N/A|N/A|N/A"
    fi
}

# Function to format performance results table
format_performance_results() {
    echo
    echo "=== 效能測試詳細結果 ==="
    echo
    echo "| 測試編號 | 測試名稱 | P50 (秒) | P95 (秒) | 成功率 | 目標 | 狀態 |"
    echo "|----------|----------|----------|----------|--------|------|------|"
    
    # API-GAP-001-PT
    local result=$(read_performance_results "API-GAP-001-PT")
    IFS='|' read -r p50 p95 success_rate <<< "$result"
    
    # Check if test actually failed
    local p50_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-001-PT " ]]; then
        p50_status="❌"
    elif [ "$p50" != "N/A" ] && (( $(echo "$p50 > 25" | bc -l) )); then
        p50_status="❌"
    fi
    
    printf "| API-GAP-001-PT | P50 響應時間 | %.3f | %.3f | %.1f%% | < 25s | %s |
" \
        "${p50:-0}" "${p95:-0}" "${success_rate:-0}" "$p50_status"
    
    # API-GAP-002-PT
    result=$(read_performance_results "API-GAP-002-PT")
    IFS='|' read -r p50 p95 success_rate <<< "$result"
    
    # Check if test actually failed
    local p95_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-002-PT " ]]; then
        p95_status="❌"
    elif [ "$p95" != "N/A" ] && (( $(echo "$p95 > 30" | bc -l) )); then
        p95_status="❌"
    fi
    
    printf "| API-GAP-002-PT | P95 響應時間 | %.3f | %.3f | %.1f%% | < 30s | %s |
" \
        "${p50:-0}" "${p95:-0}" "${success_rate:-0}" "$p95_status"
    
    # API-GAP-003-PT - Resource pool tests
    local test3_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-003-PT " ]]; then
        test3_status="❌"
    fi
    echo "| API-GAP-003-PT | 資源池重用率 | - | - | 100% | > 80% | $test3_status |"
    
    # API-GAP-004-PT
    local test4_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-004-PT " ]]; then
        test4_status="❌"
    fi
    echo "| API-GAP-004-PT | API 呼叫減少 | - | - | 100% | 40-50% | $test4_status |"
    
    # API-GAP-005-PT
    local test5_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-005-PT " ]]; then
        test5_status="❌"
    fi
    echo "| API-GAP-005-PT | 資源池擴展 | - | - | 100% | 動態擴展 | $test5_status |"
    echo
}

# Function to generate detailed report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Gap Analysis V2 測試報告"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: test-spec-index-cal-gap-analysis.md v1.0.1"
    echo "測試總數: 43 個測試案例"
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
    echo "整合測試 (14個測試):"
    echo "  - test/integration/test_gap_analysis_v2_integration.py"
    echo "  - test/integration/test_gap_analysis_v2_integration_complete.py" 
    echo "  - test/integration/test_gap_analysis_v2_integration_edge_cases.py"
    echo ""
    echo "效能測試 (5個測試):"
    echo "  - test/performance/test_gap_analysis_v2_performance.py"
    echo ""
    echo "E2E測試 (3個測試):"
    echo "  - test/e2e/test_gap_analysis_v2_e2e.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 42"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed test type statistics
    echo "測試類型統計"
    echo "------------"
    local unit_total=$((${#UNIT_PASSED[@]} + ${#UNIT_FAILED[@]}))
    local integration_total=$((${#INTEGRATION_PASSED[@]} + ${#INTEGRATION_FAILED[@]}))
    local performance_total=$((${#PERFORMANCE_PASSED[@]} + ${#PERFORMANCE_FAILED[@]}))
    local e2e_total=$((${#E2E_PASSED[@]} + ${#E2E_FAILED[@]}))
    
    local unit_rate=0
    local integration_rate=0
    local performance_rate=0
    local e2e_rate=0
    
    if [ $unit_total -gt 0 ]; then
        unit_rate=$(( ${#UNIT_PASSED[@]} * 100 / unit_total ))
    fi
    if [ $integration_total -gt 0 ]; then
        integration_rate=$(( ${#INTEGRATION_PASSED[@]} * 100 / integration_total ))
    fi
    if [ $performance_total -gt 0 ]; then
        performance_rate=$(( ${#PERFORMANCE_PASSED[@]} * 100 / performance_total ))
    fi
    if [ $e2e_total -gt 0 ]; then
        e2e_rate=$(( ${#E2E_PASSED[@]} * 100 / e2e_total ))
    fi
    
    echo "單元測試 (Unit): ${#UNIT_PASSED[@]}/${unit_total} (${unit_rate}%) - 規格要求: 20"
    echo "整合測試 (Integration): ${#INTEGRATION_PASSED[@]}/${integration_total} (${integration_rate}%) - 規格要求: 14"
    echo "效能測試 (Performance): ${#PERFORMANCE_PASSED[@]}/${performance_total} (${performance_rate}%) - 規格要求: 5"
    echo "端對端測試 (E2E): ${#E2E_PASSED[@]}/${e2e_total} (${e2e_rate}%) - 規格要求: 3"
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
    echo "| 效能測試     | ${#PERFORMANCE_PASSED[@]}/${performance_total} | ${performance_rate}% | $(IFS=','; echo "${PERFORMANCE_FAILED[*]}") |"
    echo "| 端對端測試   | ${#E2E_PASSED[@]}/${e2e_total} | ${e2e_rate}% | $(IFS=','; echo "${E2E_FAILED[*]}") |"
    echo "| **總計**     | **${#PASSED_TESTS[@]}/${total_tests}** | **${pass_rate}%** | $(IFS=','; echo "${FAILED_TESTS[*]}") |"
    echo
    
    # Show performance test results if any performance tests were run
    if [ ${#PERFORMANCE_PASSED[@]} -gt 0 ] || [ ${#PERFORMANCE_FAILED[@]} -gt 0 ]; then
        format_performance_results
    fi
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例詳情:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            local priority=$(get_test_priority "$test_id")
            local duration=$(get_test_duration "$test_id")
            echo "❌ $test_id ($priority) - 執行時間: $duration - 日誌: $LOG_DIR/test_${test_id}_*.log"
        done
        echo
        echo "修復建議:"
        echo "1. 檢查測試驗證報告中的已知問題"
        echo "2. 運行單一失敗測試進行詳細調試: pytest test/path/to/test.py::test_function -v"
        echo "3. 檢查環境變數配置和API服務狀態"
        echo "4. 參考 CLAUDE.md 中的依賴配置指南"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo "🎉 ${GREEN}所有 42 個 Gap Analysis V2 測試案例全部通過！${NC}"
        echo "   符合測試規格文檔 test-spec-index-cal-gap-analysis.md 的所有要求"
    else
        echo "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
        if [ ${#P0_FAILED[@]} -gt 0 ]; then
            echo "   ⚠️  有 ${#P0_FAILED[@]} 個 P0 (Critical) 測試失敗，需要優先修復"
        fi
    fi
}

# Function to run unit tests (20 tests)
run_unit_tests() {
    echo -e "${BLUE}Running Unit Tests (20 tests)${NC}"
    echo "Testing file: test/unit/test_gap_analysis_v2.py"
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

# Function to run integration tests (14 tests)
run_integration_tests() {
    echo -e "${BLUE}Running Integration Tests (14 tests)${NC}"
    echo "Testing files: test/integration/test_gap_analysis_v2_*.py"
    echo
    
    # Run all integration tests in batch instead of individually
    local test_start=$(date +%s)
    local test_output_file="${LOG_DIR}/integration_tests_batch_${TIMESTAMP}.log"
    
    # Run all integration tests at once
    echo -e "${BLUE}Running all integration tests in batch...${NC}"
    
    # Use virtual environment Python if available
    local python_cmd="python"
    if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
        python_cmd="venv/bin/python"
    fi
    
    if $python_cmd -m pytest test/integration/test_gap_analysis_v2_integration_complete.py -v --tb=short --durations=0 > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        
        # Parse results from pytest output
        local passed_count=$(grep -E "passed" "$test_output_file" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo "0")
        local failed_count=$(grep -E "failed" "$test_output_file" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo "0")
        
        echo -e "  ${GREEN}✓ Batch test completed${NC} (${duration}s)"
        echo -e "  Results: ${GREEN}${passed_count} passed${NC}, ${RED}${failed_count} failed${NC}"
        
        # Parse individual test results for reporting
        parse_batch_test_results "$test_output_file"
        
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        
        echo -e "  ${RED}✗ Batch test failed${NC} (${duration}s)"
        echo "  Error details saved to: $(basename "$test_output_file")"
        
        # Parse individual test results even on failure
        parse_batch_test_results "$test_output_file"
        
        if [ "$VERBOSE" = true ]; then
            echo "  Test summary:"
            grep -E "(PASSED|FAILED|ERROR)" "$test_output_file" | tail -20 | sed 's/^/    /'
        fi
    fi
}

# Function to parse batch test results and update statistics
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
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT) P1_PASSED+=("${test_id//_/-}") ;;
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
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT) P1_FAILED+=("${test_id//_/-}") ;;
            esac
        fi
    done <<< "$failed_tests"
}

# Function to run performance tests (5 tests)
run_performance_tests() {
    # All 5 performance tests from API-GAP-001-PT to API-GAP-005-PT
    local performance_tests=(
        "API-GAP-001-PT:test/performance/test_gap_analysis_v2_performance.py::TestGapAnalysisV2Performance::test_p50_response_time"
        "API-GAP-002-PT:test/performance/test_gap_analysis_v2_performance.py::TestGapAnalysisV2Performance::test_p95_response_time"
        "API-GAP-003-PT:test/performance/test_gap_analysis_v2_performance.py::TestGapAnalysisV2Performance::test_resource_pool_reuse_rate"
        "API-GAP-004-PT:test/performance/test_gap_analysis_v2_performance.py::TestGapAnalysisV2Performance::test_api_call_reduction"
        "API-GAP-005-PT:test/performance/test_gap_analysis_v2_performance.py::TestGapAnalysisV2Performance::test_resource_pool_scaling"
    )
    
    # Check if specific tests requested
    if [ -n "$SPECIFIC_PERF_TESTS" ]; then
        echo -e "${BLUE}Running Specific Performance Tests: $SPECIFIC_PERF_TESTS${NC}"
        echo "Testing file: test/performance/test_gap_analysis_v2_performance.py"
        echo "⚠️  Performance tests use real Azure OpenAI APIs"
        echo
        
        # Convert comma-separated list to array
        IFS=',' read -ra TEST_IDS <<< "$SPECIFIC_PERF_TESTS"
        
        # Run only specified tests
        for test_id in "${TEST_IDS[@]}"; do
            # Trim whitespace
            test_id=$(echo "$test_id" | xargs)
            
            # Convert shortcuts
            case "$test_id" in
                "p50"|"P50")
                    test_id="API-GAP-001-PT"
                    ;;
                "p95"|"P95")
                    test_id="API-GAP-002-PT"
                    ;;
            esac
            
            # Find matching test entry
            for test_entry in "${performance_tests[@]}"; do
                if [[ "$test_entry" == "$test_id:"* ]]; then
                    local test_path="${test_entry#*:}"
                    # Use longer timeout for P95 test (20 requests * 20s each + overhead)
                    local timeout=180
                    if [[ "$test_id" == "API-GAP-002-PT" ]]; then
                        timeout=600  # 10 minutes for P95 test
                    fi
                    run_test "$test_id" "$test_path" $timeout "performance"
                    break
                fi
            done
        done
    else
        echo -e "${BLUE}Running All Performance Tests (5 tests)${NC}"
        echo "Testing file: test/performance/test_gap_analysis_v2_performance.py"
        echo "⚠️  Performance tests may take longer (up to 120s each)"
        echo
        
        for test_entry in "${performance_tests[@]}"; do
            local test_id="${test_entry%%:*}"
            local test_path="${test_entry#*:}"
            run_test "$test_id" "$test_path" 180 "performance"
        done
    fi
}

# Function to run E2E tests (4 tests)
run_e2e_tests() {
    echo -e "${BLUE}Running E2E Tests (3 tests)${NC}"
    echo "Testing file: test/e2e/test_gap_analysis_v2_e2e.py"
    echo "⚠️  E2E tests use real data and may take longer"
    echo
    
    # All 3 E2E tests from API-GAP-001-E2E to API-GAP-003-E2E
    local e2e_tests=(
        "API-GAP-001-E2E:test/e2e/test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_complete_workflow"
        "API-GAP-002-E2E:test/e2e/test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_lightweight_monitoring_integration"
        "API-GAP-003-E2E:test/e2e/test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_partial_result_support"
    )
    
    for test_entry in "${e2e_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 180 "e2e"
    done
}

# Main execution function
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
    log_message "=== Gap Analysis V2 Test Suite Started ==="
    log_message "Based on test-spec-index-cal-gap-analysis.md v1.0.4"
    log_message "Python version: $(python --version 2>&1)"
    log_message "Stage execution: ${STAGE_EXEC:-all}"
    log_message "Background execution: $BACKGROUND_EXEC"
    
    echo -e "${BLUE}=== Gap Analysis V2 Test Suite (42 tests) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "Based on: test-spec-index-cal-gap-analysis.md v1.0.4"
    echo
    
    echo -e "${BLUE}Environment Check${NC}"
    if [ -f ".env" ]; then
        echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
        log_message "Environment: .env file found"
    else
        echo -e "  Environment: ${YELLOW}⚠ .env file not found${NC}"
        log_message "WARNING: .env file not found, using environment variables"
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
        "performance")
            run_performance_tests
            ;;
        "e2e")
            run_e2e_tests
            ;;
        "")
            # Run all tests in order
            run_unit_tests
            run_integration_tests
            run_performance_tests
            run_e2e_tests
            ;;
        *)
            echo -e "${RED}Unknown stage: $STAGE_EXEC${NC}"
            echo "Valid stages: unit, integration, performance, e2e"
            exit 1
            ;;
    esac
    
    # Generate detailed report
    generate_report
    
    log_message "=== Test Suite Completed ==="
    
    # Final result determination
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All Gap Analysis V2 tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Skip main execution if SKIP_MAIN is set (for testing)
if [ "$SKIP_MAIN" != "true" ]; then
    # Handle background execution
    if [ "$BACKGROUND_EXEC" = true ]; then
        echo "Running Gap Analysis V2 tests in background..."
        echo "Log file: $LOG_FILE"
        echo "Monitor with: tail -f $LOG_FILE"
        main &
        echo "Background process PID: $!"
    else
        main
    fi
fi