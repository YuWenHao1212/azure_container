#!/bin/bash

# ============================================================================
# Service Modules Test Runner V2
# Based on TEST_SPEC_SERVICE_MODULES.md
# Runs exactly 47 unit tests for service layer modules
# 
# Changes:
# - Unified "fail" terminology (no "error")
# - No warnings in terminal output, only summary table
# - Logs saved to test/logs with timestamps
# - Failed test details saved for troubleshooting
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test statistics
TOTAL_TESTS=47  # Pure SVC tests (helper tests merged)
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Timing
START_TIME=$(date +%s)
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')

# Log directory setup
LOG_DIR="test/logs"
LOG_FILE="$LOG_DIR/service_modules_test_${TIMESTAMP}.log"
FAIL_LOG="$LOG_DIR/service_modules_failures_${TIMESTAMP}.log"

# Create log directory if not exists
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    echo "$1" >> "$LOG_FILE"
}

# Function to log failures
log_failure() {
    echo "$1" >> "$FAIL_LOG"
}

# Function to print header
print_header() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    服務層模組測試執行報告                          ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║ 執行時間: $(date +'%Y-%m-%d %H:%M:%S')                             ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
}

# Function to run tests for a module (silent mode)
run_module_tests() {
    local module_file=$1
    local module_name=$2
    local expected_count=$3
    
    log_message ""
    log_message "=========================================="
    log_message "Testing: $module_name"
    log_message "File: $module_file"
    log_message "Expected tests: $expected_count"
    log_message "=========================================="
    
    if [ -f "$module_file" ]; then
        # Run pytest and capture output
        pytest "$module_file" -v --tb=short 2>&1 > /tmp/pytest_full_output.txt
        cat /tmp/pytest_full_output.txt >> "$LOG_FILE"
        
        # Check if pytest ran successfully
        if [ $? -eq 0 ] || [ $? -eq 1 ]; then
            # Count results
            local passed=$(grep -c "PASSED" /tmp/pytest_results.txt 2>/dev/null || echo "0")
            local failed=$(grep -c "FAILED" /tmp/pytest_results.txt 2>/dev/null || echo "0")
            local skipped=$(grep -c "SKIPPED" /tmp/pytest_results.txt 2>/dev/null || echo "0")
            
            passed=${passed:-0}
            failed=${failed:-0}
            skipped=${skipped:-0}
            
            local total=$((passed + failed + skipped))
            
            TESTS_RUN=$((TESTS_RUN + total))
            TESTS_PASSED=$((TESTS_PASSED + passed))
            TESTS_FAILED=$((TESTS_FAILED + failed))
            TESTS_SKIPPED=$((TESTS_SKIPPED + skipped))
            
            # Log summary
            log_message "Results: $passed passed, $failed failed, $skipped skipped"
            
            # If there are failures, extract and log them
            if [ "$failed" -gt 0 ]; then
                log_failure ""
                log_failure "=== $module_name Failures ==="
                log_failure "File: $module_file"
                log_failure "Failed: $failed tests"
                log_failure ""
                
                # Extract failure details from pytest output
                pytest "$module_file" -v --tb=short 2>&1 | grep -A 10 "FAILED" >> "$FAIL_LOG" 2>/dev/null || true
                
                return 1
            fi
            
            return 0
        else
            # Test execution failed completely
            log_message "FAIL: Test execution failed for $module_name"
            log_failure ""
            log_failure "=== $module_name Execution Failed ==="
            log_failure "File: $module_file"
            log_failure "Pytest command failed to execute"
            
            TESTS_FAILED=$((TESTS_FAILED + expected_count))
            TESTS_RUN=$((TESTS_RUN + expected_count))
            return 1
        fi
    else
        log_message "WARNING: $module_file not found"
        TESTS_SKIPPED=$((TESTS_SKIPPED + expected_count))
        TESTS_RUN=$((TESTS_RUN + expected_count))
        return 2
    fi
}

# Function to print test summary table
print_summary_table() {
    echo ""
    echo "📊 測試結果摘要"
    echo "═══════════════════════════════════════════════════════════════════"
    echo "| 模組               | 通過  | 失敗  | 跳過  | 總計  | 狀態     |"
    echo "|-------------------|-------|-------|-------|-------|----------|"
    
    # Read results from log and display summary
    local ld_pass=0 ld_fail=0 ld_skip=0
    local pm_pass=0 pm_fail=0 pm_skip=0
    local kw_pass=0 kw_fail=0 kw_skip=0
    local llm_pass=0 llm_fail=0 llm_skip=0
    
    # Parse module results (simplified for now)
    # In production, would parse from actual test results
    
    # Calculate status
    local overall_status="✅"
    if [ $TESTS_FAILED -gt 0 ]; then
        overall_status="❌"
    elif [ $TESTS_SKIPPED -gt 0 ]; then
        overall_status="⚠️"
    fi
    
    # Print total row
    printf "| %-17s | %5d | %5d | %5d | %5d | %-8s |\n" \
           "總計" "$TESTS_PASSED" "$TESTS_FAILED" "$TESTS_SKIPPED" "$TESTS_RUN" "$overall_status"
    echo "═══════════════════════════════════════════════════════════════════"
    
    # Calculate execution time
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo "執行時間: ${DURATION} 秒"
    echo "日誌檔案: $LOG_FILE"
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}失敗詳情: $FAIL_LOG${NC}"
    fi
}

# Main execution
main() {
    print_header
    
    # Log start
    log_message "Service Module Tests Started at $(date)"
    log_message "Total expected tests: $TOTAL_TESTS"
    
    # Check if test directory exists
    if [ ! -d "test/unit/services" ]; then
        mkdir -p test/unit/services
        log_message "Created test/unit/services directory"
    fi
    
    echo "🚀 執行服務模組測試..."
    echo ""
    
    # Module test results tracking
    MODULE_LD="PENDING"
    MODULE_PM="PENDING"
    MODULE_KW="PENDING"
    MODULE_LLM="PENDING"
    
    # 1. Language Detection Service (14 tests)
    echo -n "測試語言檢測服務 (14 tests)... "
    if run_module_tests "test/unit/services/test_language_detection_service.py" "Language Detection" 14; then
        echo -e "${GREEN}✓${NC}"
        MODULE_LD="PASS"
    else
        echo -e "${RED}✗${NC}"
        MODULE_LD="FAIL"
    fi
    
    # 2. Unified Prompt Service (15 tests)
    echo -n "測試Prompt管理服務 (15 tests)... "
    if run_module_tests "test/unit/services/test_unified_prompt_service.py" "Prompt Management" 15; then
        echo -e "${GREEN}✓${NC}"
        MODULE_PM="PASS"
    else
        echo -e "${RED}✗${NC}"
        MODULE_PM="FAIL"
    fi
    
    # 3. Keyword Service Integration (10 tests)
    echo -n "測試關鍵字服務 (10 tests)... "
    if run_module_tests "test/unit/services/test_keyword_service_integration.py" "Keyword Service" 10; then
        echo -e "${GREEN}✓${NC}"
        MODULE_KW="PASS"
    else
        echo -e "${RED}✗${NC}"
        MODULE_KW="FAIL"
    fi
    
    # 4. LLM Factory Service (8 tests)
    echo -n "測試LLM Factory服務 (8 tests)... "
    if run_module_tests "test/unit/services/test_llm_factory_service.py" "LLM Factory" 8; then
        echo -e "${GREEN}✓${NC}"
        MODULE_LLM="PASS"
    else
        echo -e "${RED}✗${NC}"
        MODULE_LLM="FAIL"
    fi
    
    # Print summary table
    print_summary_table
    
    # Log completion
    log_message ""
    log_message "Test execution completed at $(date)"
    log_message "Total: $TESTS_RUN, Passed: $TESTS_PASSED, Failed: $TESTS_FAILED, Skipped: $TESTS_SKIPPED"
    
    # Coverage report (optional, silent)
    if command -v coverage &> /dev/null; then
        coverage run -m pytest test/unit/services/ -q 2>/dev/null || true
        coverage report --include="src/services/*" >> "$LOG_FILE" 2>/dev/null || true
    fi
    
    # Exit code based on results
    if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_RUN -eq $TOTAL_TESTS ]; then
        echo ""
        echo -e "${GREEN}${BOLD}✅ 所有服務層測試通過！${NC}"
        
        # Clean up old logs (keep only last 10 runs)
        ls -t $LOG_DIR/service_modules_test_*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true
        ls -t $LOG_DIR/service_modules_failures_*.log 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
        
        exit 0
    elif [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}${BOLD}❌ 有 $TESTS_FAILED 個測試失敗${NC}"
        echo -e "${YELLOW}查看失敗詳情: cat $FAIL_LOG${NC}"
        exit 1
    else
        echo ""
        echo -e "${YELLOW}${BOLD}⚠️  部分測試未執行 (已執行: $TESTS_RUN/$TOTAL_TESTS)${NC}"
        exit 2
    fi
}

# Run main function
main "$@"