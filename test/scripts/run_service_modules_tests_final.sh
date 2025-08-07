#!/bin/bash

# ============================================================================
# Service Modules Test Runner - Final Version
# 
# Requirements met:
# 1. Use "fail" instead of "error" 
# 2. No warnings in terminal output, only summary table
# 3. Logs saved to test/logs with failure details for troubleshooting
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
LOG_DIR="test/logs"
LOG_FILE="$LOG_DIR/service_modules_${TIMESTAMP}.log"
FAIL_LOG="$LOG_DIR/service_modules_failures_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Test files
declare -a TEST_FILES=(
    "test/unit/services/test_language_detection_service.py:語言檢測:14"
    "test/unit/services/test_unified_prompt_service.py:Prompt管理:15"
    "test/unit/services/test_keyword_service_integration.py:關鍵字服務:10"
    "test/unit/services/test_llm_factory_service.py:LLM Factory:8"
)

# Initialize results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_TESTS=47

# Function to run a single test module
run_test_module() {
    local test_file=$1
    local module_name=$2
    local expected_count=$3
    
    # Log header
    echo "===========================================" >> "$LOG_FILE"
    echo "Testing: $module_name" >> "$LOG_FILE"
    echo "File: $test_file" >> "$LOG_FILE"
    echo "===========================================" >> "$LOG_FILE"
    
    # Run pytest with minimal output
    pytest "$test_file" --tb=short -q 2>&1 > /tmp/test_out_$$.txt
    local exit_code=$?
    
    # Save full output to log
    cat /tmp/test_out_$$.txt >> "$LOG_FILE"
    
    # Parse summary line (e.g., "5 failed, 9 passed, 10 warnings in 0.52s")
    local summary_line=$(grep -E "^[0-9]+ (failed|passed|skipped|error)" /tmp/test_out_$$.txt | tail -1)
    
    local passed=0
    local failed=0
    
    if [ -n "$summary_line" ]; then
        # Extract passed count
        if echo "$summary_line" | grep -q "passed"; then
            passed=$(echo "$summary_line" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+")
        fi
        
        # Extract failed count (includes errors)
        if echo "$summary_line" | grep -q "failed"; then
            failed=$(echo "$summary_line" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+")
        fi
        
        # Count errors as failures
        if echo "$summary_line" | grep -q "error"; then
            local errors=$(echo "$summary_line" | grep -oE "[0-9]+ error" | grep -oE "[0-9]+")
            failed=$((failed + errors))
        fi
    else
        # If no summary line, count from test markers
        passed=$(grep -c "PASSED" /tmp/test_out_$$.txt 2>/dev/null || echo "0")
        failed=$(grep -c -E "(FAILED|ERROR)" /tmp/test_out_$$.txt 2>/dev/null || echo "0")
    fi
    
    # Save failure details
    if [ "$failed" -gt 0 ]; then
        echo "" >> "$FAIL_LOG"
        echo "=== $module_name 失敗詳情 ===" >> "$FAIL_LOG"
        echo "失敗數量: $failed" >> "$FAIL_LOG"
        echo "" >> "$FAIL_LOG"
        
        # Extract failure information
        grep -A 5 -E "(FAILED|ERROR|AssertionError)" /tmp/test_out_$$.txt >> "$FAIL_LOG" 2>/dev/null || true
        echo "" >> "$FAIL_LOG"
    fi
    
    # Clean up
    rm -f /tmp/test_out_$$.txt
    
    # Return results
    echo "$passed:$failed"
}

# Main execution
main() {
    # Header
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                    服務層模組測試執行報告                          ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║ 執行時間: $(date +'%Y-%m-%d %H:%M:%S')                             ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    echo "🚀 執行測試中..."
    echo ""
    
    # Arrays to store results
    declare -a MODULE_NAMES=()
    declare -a MODULE_PASSED=()
    declare -a MODULE_FAILED=()
    
    # Run each test module
    for test_spec in "${TEST_FILES[@]}"; do
        IFS=':' read -r test_file module_name expected_count <<< "$test_spec"
        
        echo -n "  $module_name ($expected_count tests)... "
        
        # Run test and get results
        result=$(run_test_module "$test_file" "$module_name" "$expected_count")
        IFS=':' read -r passed failed <<< "$result"
        
        # Store results
        MODULE_NAMES+=("$module_name")
        MODULE_PASSED+=("$passed")
        MODULE_FAILED+=("$failed")
        
        # Update totals
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        
        # Show status
        if [ "$failed" -eq 0 ]; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    done
    
    # Summary table
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "📊 測試結果摘要"
    echo "═══════════════════════════════════════════════════════════════════"
    printf "| %-18s | %-6s | %-6s | %-6s | %-8s |\n" "模組" "通過" "失敗" "總計" "狀態"
    echo "|--------------------|--------|--------|--------|----------|"
    
    # Print each module's results
    for i in "${!MODULE_NAMES[@]}"; do
        local name="${MODULE_NAMES[$i]}"
        local passed="${MODULE_PASSED[$i]}"
        local failed="${MODULE_FAILED[$i]}"
        local total=$((passed + failed))
        local status="✅"
        [ "$failed" -gt 0 ] && status="❌"
        
        printf "| %-18s | %6s | %6s | %6s | %-8s |\n" \
               "$name" "$passed" "$failed" "$total" "$status"
    done
    
    echo "|--------------------|--------|--------|--------|----------|"
    
    # Total row
    local total_run=$((TOTAL_PASSED + TOTAL_FAILED))
    local overall_status="✅"
    [ "$TOTAL_FAILED" -gt 0 ] && overall_status="❌"
    
    printf "| ${BOLD}%-18s${NC} | ${BOLD}%6s${NC} | ${BOLD}%6s${NC} | ${BOLD}%6s${NC} | ${BOLD}%-8s${NC} |\n" \
           "總計" "$TOTAL_PASSED" "$TOTAL_FAILED" "$total_run" "$overall_status"
    echo "═══════════════════════════════════════════════════════════════════"
    
    # Log files info
    echo ""
    echo "📁 日誌檔案："
    echo "   完整日誌: $LOG_FILE"
    [ "$TOTAL_FAILED" -gt 0 ] && echo "   失敗詳情: $FAIL_LOG"
    
    # Clean up old logs
    find "$LOG_DIR" -name "service_modules_2*.log" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    find "$LOG_DIR" -name "service_modules_failures_2*.log" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null || true
    
    # Exit with appropriate code
    echo ""
    if [ "$TOTAL_FAILED" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ 所有測試通過！${NC}"
        exit 0
    else
        echo -e "${RED}${BOLD}❌ 有 $TOTAL_FAILED 個測試失敗${NC}"
        echo ""
        echo "💡 除錯提示："
        echo "   1. 查看失敗詳情: cat $FAIL_LOG"
        echo "   2. 查看完整日誌: cat $LOG_FILE"
        echo "   3. 單獨執行失敗模組: pytest <test_file> -xvs"
        exit 1
    fi
}

# Run main
main "$@"