#!/bin/bash

# Real API Test Runner for Index Calculation and Gap Analysis
# Tests Performance and E2E functionality with real Azure OpenAI API
# Based on test-spec-index-cal-gap-analysis.md v1.0.1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup logging - will be set with absolute path in main()
LOG_DIR=""
LOG_FILE=""

# Test tracking arrays
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()
TEST_TIMES=()
START_TIME=$(date +%s)

# Test categorization
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

# Command line options
STAGE_EXEC=""
VERBOSE=false
SHOW_HELP=false
SPECIFIC_PERF_TESTS=""
BACKGROUND_EXEC=false

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
    echo "Real API Test Runner (Performance + E2E)"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <performance|e2e>          Run specific test stage"
    echo "  --perf-test <test-id>              Run specific performance test(s)"
    echo "  --background                       Run tests in background"
    echo "  --verbose                          Show verbose output"
    echo "  --help, -h                         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                 # Run all 8 tests (5 perf + 3 e2e)"
    echo "  $0 --stage performance             # Run only performance tests (5 tests)"
    echo "  $0 --stage e2e                     # Run only E2E tests (3 tests)"
    echo "  $0 --perf-test p50                 # Run P50 test only"
    echo "  $0 --perf-test \"p50,p95\"           # Run both P50 and P95 tests"
    echo ""
    echo "⚠️  This script uses REAL Azure OpenAI APIs and will incur costs!"
    exit 0
fi

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to log environment info
log_environment_info() {
    log_message "=== ENVIRONMENT INFORMATION ==="
    log_message "Python Version: $(python --version 2>&1)"
    log_message "Working Directory: $(pwd)"
    log_message "Script Version: Real API Test Runner v1.0"
    log_message "Test Specification: test-spec-index-cal-gap-analysis.md v1.0.1"
    log_message "API Endpoint: ${AZURE_OPENAI_ENDPOINT:-Not Set}"
    
    # LLM Configuration
    log_message "LLM Configuration:"
    log_message "  - Keywords Extraction: ${LLM_MODEL_KEYWORDS:-gpt41-mini} @ ${GPT41_MINI_JAPANEAST_ENDPOINT:-Not Set}"
    log_message "  - Gap Analysis: ${LLM_MODEL_GAP_ANALYSIS:-gpt4o-2} @ ${AZURE_OPENAI_ENDPOINT:-Not Set}"
    log_message "  - Index Calculation: ${LLM_MODEL_INDEX_CAL:-gpt4o-2} @ ${AZURE_OPENAI_ENDPOINT:-Not Set}"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Not Set}"
    log_message "  - GPT-4.1 Mini Deployment: ${GPT41_MINI_JAPANEAST_DEPLOYMENT:-Not Set}"
    
    log_message "Test Files:"
    log_message "  - Performance: test/performance/test_gap_analysis_v2_performance.py"
    log_message "  - E2E: test/e2e_standalone/test_gap_analysis_v2_e2e.py"
    log_message "Total Tests: 8 (5 Performance + 3 E2E)"
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
        "API-GAP-001-PT"|"API-GAP-002-PT"|"API-GAP-003-PT"|"API-GAP-004-PT")
            echo "P0" ;;
        "API-GAP-001-E2E")
            echo "P0" ;;
        # P1 Priority tests
        "API-GAP-002-E2E"|"API-GAP-003-E2E")
            echo "P1" ;;
        # P2 Priority tests
        "API-GAP-005-PT")
            echo "P2" ;;
        *)
            echo "Unknown" ;;
    esac
}

# Function to clean up old logs
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

# Function to run a test and track results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-180}"
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
    
    # Execute test
    if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${duration}s"
        PASSED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
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
        
        # Clean up old logs
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
            "performance") PERFORMANCE_FAILED+=("${test_id}") ;;
            "e2e") E2E_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
            "P2") P2_FAILED+=("${test_id}") ;;
        esac
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
        
        # Clean up old logs
        cleanup_old_logs "$test_id"
    fi
    echo
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running Performance Tests (5 tests)${NC}"
    echo "Testing file: test/performance/test_gap_analysis_v2_performance.py"
    echo "⚠️  Performance tests may take longer and use real Azure OpenAI APIs"
    echo
    
    # Performance test configurations
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
                    # Use longer timeout for P95 test
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
        # Run all performance tests
        for test_entry in "${performance_tests[@]}"; do
            local test_id="${test_entry%%:*}"
            local test_path="${test_entry#*:}"
            # Default timeout, longer for P95
            local timeout=180
            if [[ "$test_id" == "API-GAP-002-PT" ]]; then
                timeout=600
            fi
            run_test "$test_id" "$test_path" $timeout "performance"
        done
    fi
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}Running E2E Tests (3 tests)${NC}"
    echo "Testing file: test/e2e_standalone/test_gap_analysis_v2_e2e.py"
    echo "⚠️  E2E tests use real Azure OpenAI API"
    echo
    
    # Ensure e2e_standalone directory exists
    if [ ! -d "test/e2e_standalone" ]; then
        echo "Setting up E2E standalone environment..."
        mkdir -p test/e2e_standalone
        touch test/e2e_standalone/__init__.py
        
        # Copy test file if needed
        if [ ! -f "test/e2e_standalone/test_gap_analysis_v2_e2e.py" ]; then
            cp test/e2e/test_gap_analysis_v2_e2e.py test/e2e_standalone/
            
            # Remove skip marks and mock imports
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' '/pytestmark = pytest.mark.skip/d' test/e2e_standalone/test_gap_analysis_v2_e2e.py
                sed -i '' 's/from unittest.mock import AsyncMock, Mock, patch//g' test/e2e_standalone/test_gap_analysis_v2_e2e.py
            else
                # Linux
                sed -i '/pytestmark = pytest.mark.skip/d' test/e2e_standalone/test_gap_analysis_v2_e2e.py
                sed -i 's/from unittest.mock import AsyncMock, Mock, patch//g' test/e2e_standalone/test_gap_analysis_v2_e2e.py
            fi
        fi
    fi
    
    # Change to test directory for E2E tests
    cd test/e2e_standalone
    
    # E2E test configurations
    local e2e_tests=(
        "API-GAP-001-E2E:test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_complete_workflow"
        "API-GAP-002-E2E:test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_lightweight_monitoring_integration"
        "API-GAP-003-E2E:test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_partial_result_support"
    )
    
    # Run E2E tests with proper isolation
    for test_entry in "${e2e_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        # Use special pytest options for E2E
        export PYTEST_CURRENT_TEST_TYPE="e2e"
        export REAL_E2E_TEST="true"
        
        # Run with confcutdir to avoid global conftest
        if command -v gtimeout >/dev/null 2>&1; then
            timeout_cmd="gtimeout 180s"
        elif command -v timeout >/dev/null 2>&1; then
            timeout_cmd="timeout 180s"
        else
            timeout_cmd=""
        fi
        
        if [ -n "$timeout_cmd" ]; then
            timeout_exec_cmd="$timeout_cmd python -m pytest"
        else
            timeout_exec_cmd="python -m pytest"
        fi
        
        log_and_print "${BLUE}Running ${test_id}...${NC}"
        local test_start=$(date +%s)
        local test_output_file="$LOG_DIR/test_${test_id}_$(date +%Y%m%d_%H%M%S).log"
        
        if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 --confcutdir=. > "$test_output_file" 2>&1; then
            local test_end=$(date +%s)
            local duration=$((test_end - test_start))
            TEST_TIMES+=("${test_id}:${duration}s")
            
            echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
            log_message "TEST PASSED: $test_id - Duration: ${duration}s"
            PASSED_TESTS+=("${test_id}")
            E2E_PASSED+=("${test_id}")
            
            # Priority tracking
            if [[ "$test_id" == "API-GAP-001-E2E" ]]; then
                P0_PASSED+=("${test_id}")
            else
                P1_PASSED+=("${test_id}")
            fi
            
            if [ "$VERBOSE" = false ]; then
                rm -f "$test_output_file"
            fi
        else
            local test_end=$(date +%s)
            local duration=$((test_end - test_start))
            TEST_TIMES+=("${test_id}:${duration}s")
            
            echo -e "  ${RED}✗ FAILED${NC} (${duration}s)"
            log_message "TEST FAILED: $test_id - Duration: ${duration}s"
            FAILED_TESTS+=("${test_id}")
            E2E_FAILED+=("${test_id}")
            
            # Priority tracking
            if [[ "$test_id" == "API-GAP-001-E2E" ]]; then
                P0_FAILED+=("${test_id}")
            else
                P1_FAILED+=("${test_id}")
            fi
            
            echo "  Error details saved to: $(basename "$test_output_file")"
            if [ "$VERBOSE" = true ]; then
                echo "  Last few lines of error:"
                tail -10 "$test_output_file" | sed 's/^/    /'
            fi
        fi
        echo
    done
    
    # Clean up environment variables
    unset PYTEST_CURRENT_TEST_TYPE
    unset REAL_E2E_TEST
    
    # Return to project root
    cd "$PROJECT_ROOT"
}

# Function to read performance results
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
    
    local p50_status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-GAP-001-PT " ]]; then
        p50_status="❌"
    elif [ "$p50" != "N/A" ] && (( $(echo "$p50 > 25" | bc -l) )); then
        p50_status="❌"
    fi
    
    printf "| API-GAP-001-PT | P50 響應時間 | %.3f | %.3f | %.1f%% | < 25s | %s |\n" \
        "${p50:-0}" "${p95:-0}" "${success_rate:-0}" "$p50_status"
    
    # Other performance tests...
    echo
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Real API 測試報告 (Performance + E2E)"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: test-spec-index-cal-gap-analysis.md v1.0.1"
    echo "測試總數: 8 個測試案例 (5 Performance + 3 E2E)"
    echo "執行環境: $(python --version 2>&1 | cut -d' ' -f2)"
    echo "總執行時間: ${total_duration}s"
    echo "日誌檔案: $(basename "$LOG_FILE")"
    echo
    
    # Test summary
    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))
    local pass_rate=0
    if [ $total_tests -gt 0 ]; then
        pass_rate=$(( ${#PASSED_TESTS[@]} * 100 / total_tests ))
    fi
    
    echo "測試檔案清單"
    echo "------------"
    echo "效能測試 (5個測試):"
    echo "  - test/performance/test_gap_analysis_v2_performance.py"
    echo ""
    echo "E2E測試 (3個測試):"
    echo "  - test/e2e_standalone/test_gap_analysis_v2_e2e.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 8"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed test type statistics
    echo "測試類型統計"
    echo "------------"
    local performance_total=$((${#PERFORMANCE_PASSED[@]} + ${#PERFORMANCE_FAILED[@]}))
    local e2e_total=$((${#E2E_PASSED[@]} + ${#E2E_FAILED[@]}))
    
    local performance_rate=0
    local e2e_rate=0
    
    if [ $performance_total -gt 0 ]; then
        performance_rate=$(( ${#PERFORMANCE_PASSED[@]} * 100 / performance_total ))
    fi
    if [ $e2e_total -gt 0 ]; then
        e2e_rate=$(( ${#E2E_PASSED[@]} * 100 / e2e_total ))
    fi
    
    echo "效能測試 (Performance): ${#PERFORMANCE_PASSED[@]}/${performance_total} (${performance_rate}%)"
    echo "端對端測試 (E2E): ${#E2E_PASSED[@]}/${e2e_total} (${e2e_rate}%)"
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
    echo "| 效能測試     | ${#PERFORMANCE_PASSED[@]}/${performance_total} | ${performance_rate}% | $(IFS=','; echo "${PERFORMANCE_FAILED[*]}") |"
    echo "| 端對端測試   | ${#E2E_PASSED[@]}/${e2e_total} | ${e2e_rate}% | $(IFS=','; echo "${E2E_FAILED[*]}") |"
    echo "| **總計**     | **${#PASSED_TESTS[@]}/${total_tests}** | **${pass_rate}%** | $(IFS=','; echo "${FAILED_TESTS[*]}") |"
    echo
    
    # Show performance test results if any were run
    if [ ${#PERFORMANCE_PASSED[@]} -gt 0 ] || [ ${#PERFORMANCE_FAILED[@]} -gt 0 ]; then
        format_performance_results
    fi
    
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
        echo "1. 檢查 Azure OpenAI API 密鑰和端點配置"
        echo "2. 確認網路連接和服務可用性"
        echo "3. 檢查 API 配額和速率限制"
        echo "4. 查看詳細錯誤日誌進行除錯"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo "🎉 ${GREEN}所有 Real API 測試全部通過！${NC}"
        echo "   Performance 和 E2E 測試都成功使用真實 Azure OpenAI API"
    else
        echo "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
        if [ ${#P0_FAILED[@]} -gt 0 ]; then
            echo "   ⚠️  有 ${#P0_FAILED[@]} 個 P0 (Critical) 測試失敗，需要優先修復"
        fi
    fi
}

# Main execution
main() {
    # Get script directory and project root
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Setup logging with absolute path
    LOG_DIR="$PROJECT_ROOT/test/logs"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/real_api_perf_e2e_$(date +%Y%m%d_%H%M%S).log"
    
    # Initialize logging
    log_message "=== Real API Test Suite Started ==="
    log_message "Testing Performance and E2E with real Azure OpenAI APIs"
    
    echo -e "${BLUE}=== Real API Test Suite (Performance + E2E) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "⚠️  This uses REAL Azure OpenAI APIs and will incur costs!"
    echo
    
    # Environment check
    echo -e "${BLUE}Environment Check${NC}"
    if [ ! -f ".env" ]; then
        echo -e "  ${RED}❌ Error: .env file not found${NC}"
        log_message "ERROR: .env file not found"
        exit 1
    fi
    
    # Load environment variables
    source .env
    
    # Check API keys
    if [ -z "$AZURE_OPENAI_API_KEY" ]; then
        echo -e "  ${RED}❌ Error: AZURE_OPENAI_API_KEY not set in .env${NC}"
        log_message "ERROR: AZURE_OPENAI_API_KEY not set"
        exit 1
    fi
    
    # Log environment info after loading .env and validating
    log_environment_info
    
    echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
    echo -e "  API Key: ${GREEN}✓ Azure OpenAI key configured${NC}"
    echo -e "  Python: $(python --version 2>&1)"
    echo -e "  Working Directory: $(pwd)"
    echo
    
    # Execute based on stage or run all tests
    case "$STAGE_EXEC" in
        "performance")
            run_performance_tests
            ;;
        "e2e")
            run_e2e_tests
            ;;
        "")
            # Run all tests in order
            run_performance_tests
            run_e2e_tests
            ;;
        *)
            echo -e "${RED}Unknown stage: $STAGE_EXEC${NC}"
            echo "Valid stages: performance, e2e"
            exit 1
            ;;
    esac
    
    # Generate report
    generate_report
    
    # Log test summary before completion
    log_message "=== TEST SUMMARY ==="
    log_message "Total Tests Run: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
    log_message "Passed: ${#PASSED_TESTS[@]} - ${PASSED_TESTS[*]}"
    log_message "Failed: ${#FAILED_TESTS[@]} - ${FAILED_TESTS[*]}"
    log_message "Performance Tests: ${#PERFORMANCE_PASSED[@]} passed, ${#PERFORMANCE_FAILED[@]} failed"
    log_message "E2E Tests: ${#E2E_PASSED[@]} passed, ${#E2E_FAILED[@]} failed"
    
    # Create consolidated performance JSON if performance tests were run
    if [ ${#PERFORMANCE_PASSED[@]} -gt 0 ] || [ ${#PERFORMANCE_FAILED[@]} -gt 0 ]; then
        create_consolidated_performance_json
    fi
    
    log_message "=== Test Suite Completed ==="
    
    # Final result
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All Real API tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Function to create consolidated performance JSON
create_consolidated_performance_json() {
    local consolidated_file="$LOG_DIR/performance_summary_$(date +%Y%m%d_%H%M%S).json"
    
    echo '{' > "$consolidated_file"
    echo '  "test_suite": "Index Cal and Gap Analysis V2 Performance",' >> "$consolidated_file"
    echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$consolidated_file"
    echo '  "environment": {' >> "$consolidated_file"
    echo '    "python_version": "'$(python --version 2>&1 | cut -d' ' -f2)'",' >> "$consolidated_file"
    echo '    "api_endpoint": "'${AZURE_OPENAI_ENDPOINT:-Not Set}'"' >> "$consolidated_file"
    echo '  },' >> "$consolidated_file"
    echo '  "summary": {' >> "$consolidated_file"
    echo '    "total_tests": '$(ls -1 $LOG_DIR/performance_API-GAP-*-PT_*.json 2>/dev/null | wc -l | xargs)',' >> "$consolidated_file"
    echo '    "passed": '${#PERFORMANCE_PASSED[@]}',' >> "$consolidated_file"
    echo '    "failed": '${#PERFORMANCE_FAILED[@]} >> "$consolidated_file"
    echo '  },' >> "$consolidated_file"
    echo '  "tests": [' >> "$consolidated_file"
    
    # Add individual test results
    local first=true
    for json_file in $(ls -t $LOG_DIR/performance_API-GAP-*-PT_*.json 2>/dev/null | head -5); do
        if [ "$first" = true ]; then
            first=false
        else
            echo ',' >> "$consolidated_file"
        fi
        # Include the full JSON content of each test
        cat "$json_file" >> "$consolidated_file"
    done
    
    echo '' >> "$consolidated_file"
    echo '  ]' >> "$consolidated_file"
    echo '}' >> "$consolidated_file"
    
    log_message "Created consolidated performance summary: $(basename "$consolidated_file")"
}

# Handle background execution
if [ "$BACKGROUND_EXEC" = true ]; then
    echo "Running Real API tests in background..."
    echo "Log file: $LOG_FILE"
    echo "Monitor with: tail -f $LOG_FILE"
    main &
    echo "Background process PID: $!"
else
    main
fi