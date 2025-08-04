#!/bin/bash

# E2E Standalone Test Runner
# Tests E2E functionality without global mocks
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

# Command line options
VERBOSE=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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
    echo "E2E Standalone Test Runner"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --verbose        Show verbose output"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "This script runs E2E tests without global mocks, using real API calls."
    exit 0
fi

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

# Function to run a test and track results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-180}"
    
    log_and_print "${BLUE}Running ${test_id}...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s"
    
    local test_start=$(date +%s)
    local test_output_file="$LOG_DIR/test_${test_id}_$(date +%Y%m%d_%H%M%S).log"
    
    # Run test with output captured to log
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
    if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 --confcutdir=. > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${duration}s"
        PASSED_TESTS+=("${test_id}")
        
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
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
    fi
    echo
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "E2E Standalone 測試報告"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: test-spec-index-cal-gap-analysis.md v1.0.1"
    echo "測試總數: 3 個測試案例"
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
    
    echo "測試檔案"
    echo "--------"
    echo "E2E測試:"
    echo "  - test/e2e_standalone/test_gap_analysis_v2_e2e.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 3"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed table
    echo "=== 詳細測試結果 ==="
    echo
    echo "| 測試編號 | 測試名稱 | 執行時間 | 狀態 |"
    echo "|----------|----------|----------|------|"
    
    # Show test results
    for test_id in "API-GAP-001-E2E" "API-GAP-002-E2E" "API-GAP-003-E2E"; do
        local status="❌"
        local duration="N/A"
        
        if [[ " ${PASSED_TESTS[@]} " =~ " ${test_id} " ]]; then
            status="✅"
        fi
        
        # Get test duration
        for entry in "${TEST_TIMES[@]}"; do
            if [[ $entry == "${test_id}:"* ]]; then
                duration="${entry#*:}"
                break
            fi
        done
        
        case $test_id in
            "API-GAP-001-E2E")
                echo "| $test_id | 完整工作流程測試 | $duration | $status |"
                ;;
            "API-GAP-002-E2E")
                echo "| $test_id | 輕量級監控整合測試 | $duration | $status |"
                ;;
            "API-GAP-003-E2E")
                echo "| $test_id | 部分結果支援驗證 | $duration | $status |"
                ;;
        esac
    done
    echo
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例詳情:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            echo "❌ $test_id - 日誌: $LOG_DIR/test_${test_id}_*.log"
        done
        echo
        echo "修復建議:"
        echo "1. 檢查 API 密鑰和環境變數配置"
        echo "2. 確認 Azure OpenAI 服務正常運作"
        echo "3. 檢查網路連接和防火牆設定"
        echo "4. 查看詳細錯誤日誌進行除錯"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo "🎉 ${GREEN}所有 E2E 測試全部通過！${NC}"
        echo "   成功繞過全域 mock，使用真實 API 進行測試"
    else
        echo "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
    fi
}

# Main execution
main() {
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Setup logging with absolute path
    LOG_DIR="$PROJECT_ROOT/test/logs"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/e2e_standalone_$(date +%Y%m%d_%H%M%S).log"
    
    # Initialize logging
    log_message "=== E2E Standalone Test Suite Started ==="
    log_message "Bypassing global mocks and using real API calls"
    
    echo -e "${BLUE}=== E2E Standalone Test Suite ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "This bypasses global mocks and uses real API calls"
    echo
    
    # Environment check
    echo -e "${BLUE}Environment Check${NC}"
    if [ ! -f ".env" ]; then
        echo -e "  ${RED}❌ Error: .env file not found${NC}"
        log_message "ERROR: .env file not found"
        exit 1
    fi
    
    # Check API keys
    source .env
    if [ -z "$AZURE_OPENAI_API_KEY" ]; then
        echo -e "  ${RED}❌ Error: AZURE_OPENAI_API_KEY not set in .env${NC}"
        log_message "ERROR: AZURE_OPENAI_API_KEY not set"
        exit 1
    fi
    
    echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
    echo -e "  API Key: ${GREEN}✓ Azure OpenAI key configured${NC}"
    echo -e "  Python: $(python --version 2>&1)"
    echo -e "  Working Directory: $(pwd)"
    echo
    
    # Setup e2e_standalone directory
    if [ ! -d "test/e2e_standalone" ]; then
        echo "Creating e2e_standalone directory..."
        mkdir -p test/e2e_standalone
        touch test/e2e_standalone/__init__.py
    fi
    
    # Copy test file if needed
    if [ ! -f "test/e2e_standalone/test_gap_analysis_v2_e2e.py" ]; then
        echo "Copying E2E test file..."
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
    
    # Run E2E tests
    echo -e "${BLUE}Running E2E Tests (3 tests)${NC}"
    echo "Testing file: test/e2e_standalone/test_gap_analysis_v2_e2e.py"
    echo "⚠️  E2E tests use real Azure OpenAI API"
    echo
    
    # Change to test directory
    cd test/e2e_standalone
    
    # Run individual tests
    run_test "API-GAP-001-E2E" "test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_complete_workflow" 180
    run_test "API-GAP-002-E2E" "test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_lightweight_monitoring_integration" 120
    run_test "API-GAP-003-E2E" "test_gap_analysis_v2_e2e.py::TestGapAnalysisV2E2E::test_partial_result_support" 120
    
    # Generate report
    cd "$PROJECT_ROOT"
    generate_report
    
    log_message "=== Test Suite Completed ==="
    
    # Final result
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All E2E Standalone tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Execute main function
main