#!/bin/bash

# Unit and Integration Test Runner for Health Check and Keyword Extraction
# Tests with mocked services (no real API calls)
# Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0

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
LOG_FILE="$LOG_DIR/test_health_keyword_unit_integration_${TIMESTAMP}.log"

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
    echo "Health Check and Keyword Extraction Test Runner (Mock Tests)"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <unit|integration>  Run specific test stage"
    echo "  --verbose                   Show verbose output"
    echo "  --help, -h                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  \$0                         # Run all 19 tests (3 health + 16 keyword)"
    echo "  \$0 --stage unit           # Run only unit tests (8 tests: 2 health + 6 keyword)"
    echo "  \$0 --stage integration    # Run only integration tests (11 tests: 1 health + 10 keyword)"
    echo ""
    echo "Test Breakdown:"
    echo "  Health Check: 2 unit + 1 integration tests (API-HLT-001-UT, API-HLT-002-UT, API-HLT-101-IT)"
    echo "  Keyword Extraction: 6 unit + 10 integration tests"
    echo "  Total: 19 tests (8 unit + 11 integration)"
    echo ""
    echo "Note: These tests use mocks and do not require Azure OpenAI API access."
    exit 0
fi

# Function to manage log files (keep only latest 6)
manage_log_files() {
    # Clean up old main logs
    local log_files=($(ls -t "$LOG_DIR"/test_health_keyword_unit_integration_*.log 2>/dev/null | grep -v "_batch" || true))
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
    log_message "Script Version: Health & Keyword Test Runner v1.0"
    log_message "Test Specification: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    log_message "Virtual Environment: ${VIRTUAL_ENV:-Not Active}"
    
    # LLM Configuration (from environment - but mocked)
    log_message "LLM Configuration (Mocked):"
    log_message "  - Keywords Extraction: ${LLM_MODEL_KEYWORDS:-gpt41-mini} @ ${GPT41_MINI_JAPANEAST_ENDPOINT:-Mocked}"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Mocked}"
    log_message "  - GPT-4.1 Mini Deployment: ${GPT41_MINI_JAPANEAST_DEPLOYMENT:-Mocked}"
    
    log_message "Test Files:"
    log_message "  - Health Unit Tests: test/unit/test_health.py (2 tests)"
    log_message "  - Health Integration Tests: test/integration/test_health_integration.py (1 test)"
    log_message "  - Keyword Unit Tests: test/unit/test_keyword_extraction.py (6 tests)"
    log_message "  - Keyword Integration Tests: test/integration/test_keyword_extraction_language.py (10 tests)"
    log_message "Total Tests: 19 (8 Unit + 11 Integration)"
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

# Module tracking
HEALTH_PASSED=()
HEALTH_FAILED=()
KEYWORD_PASSED=()
KEYWORD_FAILED=()

# Priority tracking
P0_PASSED=()
P0_FAILED=()
P1_PASSED=()
P1_FAILED=()

# Test execution times
TEST_TIMES=()
START_TIME=$(date +%s)

# Function to check test priority
get_test_priority() {
    local test_id="$1"
    case $test_id in
        # P0 Priority tests (critical functionality)
        "API-HLT-001-UT"|"API-HLT-002-UT"|"API-HLT-101-IT"|"API-KW-001-UT"|"API-KW-002-UT"|"API-KW-005-UT"|"API-KW-101-IT"|"API-KW-102-IT"|"API-KW-103-IT"|"API-KW-104-IT"|"API-KW-105-IT"|"API-KW-106-IT"|"API-KW-107-IT"|"API-KW-108-IT"|"API-KW-109-IT")
            echo "P0" ;;
        # P1 Priority tests (important functionality)
        "API-KW-003-UT"|"API-KW-004-UT"|"API-KW-006-UT"|"API-KW-110-IT")
            echo "P1" ;;
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
    local module="$5"
    local priority=$(get_test_priority "$test_id")
    
    log_and_print "${BLUE}Running ${test_id} (${priority})...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s - Category: $category - Module: $module"
    
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
        
        # Categorize by module
        case $module in
            "health") HEALTH_PASSED+=("${test_id}") ;;
            "keyword") KEYWORD_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
        esac
        
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
        
        # Categorize by module
        case $module in
            "health") HEALTH_FAILED+=("${test_id}") ;;
            "keyword") KEYWORD_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
        esac
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
    fi
    echo
}

# Function to run unit tests (8 tests: 2 health + 6 keyword)
run_unit_tests() {
    echo -e "${BLUE}Running Unit Tests (8 tests: 2 health + 6 keyword)${NC}"
    echo "Testing files:"
    echo "  - test/unit/test_health.py (2 tests)"
    echo "  - test/unit/test_keyword_extraction.py (6 tests)"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # Health Check Unit Tests (2 tests)
    echo -e "${BLUE}Health Check Unit Tests (2 tests)${NC}"
    local health_unit_tests=(
        "API-HLT-001-UT:test/unit/test_health.py::TestHealthCheck::test_API_HLT_001_UT_health_check_complete_validation"
        "API-HLT-002-UT:test/unit/test_health.py::TestHealthCheck::test_API_HLT_002_UT_http_method_restriction"
    )
    
    for test_entry in "${health_unit_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 30 "unit" "health"
    done
    
    # Keyword Extraction Unit Tests (6 tests)
    echo -e "${BLUE}Keyword Extraction Unit Tests (6 tests)${NC}"
    local keyword_unit_tests=(
        "API-KW-001-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_001_UT_success_path_complete_validation"
        "API-KW-002-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_002_UT_validation_error_short_description"
        "API-KW-003-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_003_UT_invalid_max_keywords_parameter"
        "API-KW-004-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_004_UT_external_service_error_handling"
        "API-KW-005-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_005_UT_traditional_chinese_support_validation"
        "API-KW-006-UT:test/unit/test_keyword_extraction.py::TestKeywordExtraction::test_API_KW_006_UT_boundary_and_quality_warning"
    )
    
    for test_entry in "${keyword_unit_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 60 "unit" "keyword"
    done
}

# Function to run integration tests (11 tests: 1 health + 10 keyword)
run_integration_tests() {
    echo -e "${BLUE}Running Integration Tests (11 tests: 1 health + 10 keyword)${NC}"
    echo "Testing files:"
    echo "  - test/integration/test_health_integration.py (1 test)"
    echo "  - test/integration/test_keyword_extraction_language.py (10 tests)"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # Health Check Integration Test (1 test)
    echo -e "${BLUE}Health Check Integration Test (1 test)${NC}"
    run_test "API-HLT-101-IT" "test/integration/test_health_integration.py::TestHealthCheckIntegration::test_health_check_integration" 90 "integration" "health"
    
    # Keyword Language Integration Tests (10 tests)
    local keyword_integration_tests=(
        "API-KW-101-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_101_IT_azure_openai_integration"
        "API-KW-102-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_102_IT_english_jd_english_prompt"
        "API-KW-103-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_103_IT_traditional_chinese_prompt"
        "API-KW-104-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_104_IT_mixed_language_above_threshold"
        "API-KW-105-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_105_IT_mixed_language_below_threshold"
        "API-KW-106-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_106_IT_reject_simplified_chinese"
        "API-KW-107-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_107_IT_reject_japanese"
        "API-KW-108-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_108_IT_reject_korean"
        "API-KW-109-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_109_IT_reject_mixed_unsupported_language_detailed_error"
        "API-KW-110-IT:test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_API_KW_110_IT_language_parameter_override"
    )
    
    for test_entry in "${keyword_integration_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 60 "integration" "keyword"
    done
    
    # Check for existing keyword extraction integration test
    if [ -f "test/integration/test_keyword_extraction_integration.py" ]; then
        echo -e "${BLUE}Running existing keyword extraction integration test${NC}"
        run_test "API-KW-201-IT" "test/integration/test_keyword_extraction_integration.py" 60 "integration" "keyword"
    fi
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Health & Keyword Extraction 測試報告"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    echo "測試總數: 19 個測試案例 (8 Unit + 11 Integration)"
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
    echo "單元測試 (8個測試):"
    echo "  - test/unit/test_health.py (2個測試)"
    echo "  - test/unit/test_keyword_extraction.py (6個測試)"
    echo ""
    echo "整合測試 (11個測試):"
    echo "  - test/integration/test_health_integration.py (1個測試)"
    echo "  - test/integration/test_keyword_extraction_language.py (10個測試)"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 19"
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
    
    echo "單元測試 (Unit): ${#UNIT_PASSED[@]}/${unit_total} (${unit_rate}%) - 規格要求: 8"
    echo "整合測試 (Integration): ${#INTEGRATION_PASSED[@]}/${integration_total} (${integration_rate}%) - 規格要求: 11"
    echo
    
    # Module statistics
    echo "模組統計"
    echo "--------"
    local health_total=$((${#HEALTH_PASSED[@]} + ${#HEALTH_FAILED[@]}))
    local keyword_total=$((${#KEYWORD_PASSED[@]} + ${#KEYWORD_FAILED[@]}))
    
    local health_rate=0
    local keyword_rate=0
    
    if [ $health_total -gt 0 ]; then
        health_rate=$(( ${#HEALTH_PASSED[@]} * 100 / health_total ))
    fi
    if [ $keyword_total -gt 0 ]; then
        keyword_rate=$(( ${#KEYWORD_PASSED[@]} * 100 / keyword_total ))
    fi
    
    echo "健康檢查 (Health): ${#HEALTH_PASSED[@]}/${health_total} (${health_rate}%) - 規格要求: 2"
    echo "關鍵字提取 (Keyword): ${#KEYWORD_PASSED[@]}/${keyword_total} (${keyword_rate}%) - 規格要求: 17"
    echo
    
    # Priority statistics
    echo "優先級統計"
    echo "----------"
    local p0_total=$((${#P0_PASSED[@]} + ${#P0_FAILED[@]}))
    local p1_total=$((${#P1_PASSED[@]} + ${#P1_FAILED[@]}))
    
    local p0_rate=0
    local p1_rate=0
    
    if [ $p0_total -gt 0 ]; then
        p0_rate=$(( ${#P0_PASSED[@]} * 100 / p0_total ))
    fi
    if [ $p1_total -gt 0 ]; then
        p1_rate=$(( ${#P1_PASSED[@]} * 100 / p1_total ))
    fi
    
    echo "P0 (Critical): ${#P0_PASSED[@]}/${p0_total} (${p0_rate}%)"
    echo "P1 (Important): ${#P1_PASSED[@]}/${p1_total} (${p1_rate}%)"
    echo
    
    # Display test distribution matrix
    echo "=== 測試分布矩陣 ==="
    echo
    echo "| 測試               | 單元測試 | 整合測試 | 效能測試 | 總計 |"
    echo "|--------------------|----------|----------|----------|------|"
    
    # Health check row (2 UT + 1 IT = 3 total)
    echo "| 健康檢查           | 2        | 1        | 0        | 3    |"
    
    # Keyword extraction row (6 UT + 10 IT = 16 total, no PT in this script)
    echo "| 關鍵字提取         | 6        | 10       | 0        | 16   |"
    
    # Total row
    echo "| **總計**           | **8**    | **11**   | **0**    | **19** |"
    echo
    
    # Display pass/fail statistics
    echo "=== 測試執行結果 ==="
    echo
    echo "| 測試類型           | 通過 | 失敗 | 總計 | 成功率 |"
    echo "|--------------------|------|------|------|--------|"
    
    # Unit test results  
    if [ $unit_total -gt 0 ]; then
        printf "| %-18s | %4d | %4d | %4d | %5d%% |\n" "單元測試" "${#UNIT_PASSED[@]}" "${#UNIT_FAILED[@]}" "$unit_total" "$unit_rate"
    fi
    
    # Integration test results
    if [ $integration_total -gt 0 ]; then
        printf "| %-18s | %4d | %4d | %4d | %5d%% |\n" "整合測試" "${#INTEGRATION_PASSED[@]}" "${#INTEGRATION_FAILED[@]}" "$integration_total" "$integration_rate"
    fi
    
    # Total results
    printf "| %-18s | %4d | %4d | %4d | %5d%% |\n" "**總計**" "${#PASSED_TESTS[@]}" "${#FAILED_TESTS[@]}" "$total_tests" "$pass_rate"
    echo
    
    # Display failed tests if any
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗測試清單:"
        for failed_id in "${FAILED_TESTS[@]}"; do
            echo "  - $failed_id"
        done
        echo
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
        echo "1. 檢查測試驗證報告中的已知問題"
        echo "2. 運行單一失敗測試進行詳細調試: pytest test/path/to/test.py::test_function -v"
        echo "3. 檢查 mock 設定是否正確"
        echo "4. 參考 CLAUDE.md 中的依賴配置指南"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo -e "🎉 ${GREEN}所有 $total_tests 個 Health & Keyword 測試全部通過！${NC}"
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
    log_message "=== Health & Keyword Test Suite Started ==="
    log_message "Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    log_message "Python version: $(python --version 2>&1)"
    log_message "Stage execution: ${STAGE_EXEC:-all}"
    log_environment_info
    
    echo -e "${BLUE}=== Health & Keyword Test Suite (19 tests) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "Based on: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
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
    log_message "Health Tests - Passed: ${#HEALTH_PASSED[@]}, Failed: ${#HEALTH_FAILED[@]}"
    log_message "Keyword Tests - Passed: ${#KEYWORD_PASSED[@]}, Failed: ${#KEYWORD_FAILED[@]}"
    log_message "P0 Priority - Passed: ${#P0_PASSED[@]}, Failed: ${#P0_FAILED[@]}"
    log_message "P1 Priority - Passed: ${#P1_PASSED[@]}, Failed: ${#P1_FAILED[@]}"
    
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
        log_and_print "${GREEN}🎉 All Health & Keyword tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Execute main function
main