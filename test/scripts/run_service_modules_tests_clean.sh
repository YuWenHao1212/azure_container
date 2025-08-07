#!/bin/bash

# ============================================================================
# Service Modules Test Runner - Clean Version
# Runs exactly 47 unit tests for service layer modules
# 
# Features:
# - No warnings in terminal output
# - Saves logs to test/logs directory
# - Failed test details saved for troubleshooting
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test configuration
TOTAL_TESTS=47
TIMESTAMP=$(date +'%Y%m%d_%H%M%S')

# Log directory setup
LOG_DIR="test/logs"
LOG_FILE="$LOG_DIR/service_modules_${TIMESTAMP}.log"
FAIL_LOG="$LOG_DIR/service_modules_failures_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TESTS_RUN=0

# Function to run tests for a module
run_module_tests() {
    local module_file=$1
    local module_name=$2
    local expected_count=$3
    
    echo "===========================================" >> "$LOG_FILE"
    echo "Testing: $module_name" >> "$LOG_FILE"
    echo "File: $module_file" >> "$LOG_FILE"
    echo "===========================================" >> "$LOG_FILE"
    
    if [ ! -f "$module_file" ]; then
        echo "File not found: $module_file" >> "$LOG_FILE"
        TESTS_SKIPPED=$((TESTS_SKIPPED + expected_count))
        TESTS_RUN=$((TESTS_RUN + expected_count))
        return 2
    fi
    
    # Run pytest and capture output
    pytest "$module_file" -xvs --tb=short --no-header -q 2>&1 > /tmp/test_output_$$.txt
    local test_exit_code=$?
    
    # Append full output to log
    cat /tmp/test_output_$$.txt >> "$LOG_FILE"
    
    # Parse results from output
    local passed=0
    local failed=0
    local errors=0
    local skipped=0
    
    # Count occurrences
    passed=$(grep -c " PASSED" /tmp/test_output_$$.txt 2>/dev/null || true)
    failed=$(grep -c " FAILED" /tmp/test_output_$$.txt 2>/dev/null || true)
    errors=$(grep -c " ERROR" /tmp/test_output_$$.txt 2>/dev/null || true)
    skipped=$(grep -c " SKIPPED" /tmp/test_output_$$.txt 2>/dev/null || true)
    
    # Ensure numeric values
    passed=${passed:-0}
    failed=${failed:-0}
    errors=${errors:-0}
    skipped=${skipped:-0}
    
    # Count errors as failures
    failed=$((failed + errors))
    
    # Update global counters
    TESTS_PASSED=$((TESTS_PASSED + passed))
    TESTS_FAILED=$((TESTS_FAILED + failed))
    TESTS_SKIPPED=$((TESTS_SKIPPED + skipped))
    TESTS_RUN=$((TESTS_RUN + passed + failed + skipped))
    
    # Log failures for troubleshooting
    if [ "$failed" -gt 0 ]; then
        echo "" >> "$FAIL_LOG"
        echo "=== $module_name Failures ===" >> "$FAIL_LOG"
        echo "Failed: $failed tests" >> "$FAIL_LOG"
        grep -E "(FAILED|ERROR|AssertionError|TypeError)" /tmp/test_output_$$.txt >> "$FAIL_LOG" 2>/dev/null || true
    fi
    
    # Clean up temp file
    rm -f /tmp/test_output_$$.txt
    
    # Return status
    if [ "$failed" -gt 0 ]; then
        return 1
    else
        return 0
    fi
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
    
    echo "開始測試執行..." >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # Progress indicator
    echo "🚀 執行測試中..."
    echo ""
    
    # Test each module
    echo -n "  語言檢測服務 (14 tests)... "
    if run_module_tests "test/unit/services/test_language_detection_service.py" "Language Detection" 14; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  Prompt管理服務 (15 tests)... "
    if run_module_tests "test/unit/services/test_unified_prompt_service.py" "Prompt Management" 15; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  關鍵字服務 (10 tests)... "
    if run_module_tests "test/unit/services/test_keyword_service_integration.py" "Keyword Service" 10; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  LLM Factory服務 (8 tests)... "
    if run_module_tests "test/unit/services/test_llm_factory_service.py" "LLM Factory" 8; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    # Summary table
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "📊 測試結果摘要"
    echo "═══════════════════════════════════════════════════════════════════"
    printf "| %-10s | %-6s | %-6s | %-6s | %-6s | %-8s |\n" "項目" "通過" "失敗" "跳過" "總計" "狀態"
    echo "|------------|--------|--------|--------|--------|----------|"
    
    # Determine overall status
    if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_RUN -eq $TOTAL_TESTS ]; then
        STATUS="✅ 通過"
    elif [ $TESTS_FAILED -gt 0 ]; then
        STATUS="❌ 失敗"
    else
        STATUS="⚠️  部分"
    fi
    
    printf "| %-10s | %6d | %6d | %6d | %6d | %-8s |\n" \
           "總計" "$TESTS_PASSED" "$TESTS_FAILED" "$TESTS_SKIPPED" "$TESTS_RUN" "$STATUS"
    echo "═══════════════════════════════════════════════════════════════════"
    
    # Timing
    echo ""
    echo "測試日誌: $LOG_FILE"
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${YELLOW}失敗詳情: $FAIL_LOG${NC}"
    fi
    
    # Clean up old logs (keep last 10)
    find "$LOG_DIR" -name "service_modules_*.log" -type f | sort -r | tail -n +11 | xargs rm -f 2>/dev/null || true
    find "$LOG_DIR" -name "service_modules_failures_*.log" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null || true
    
    # Exit code
    if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_RUN -eq $TOTAL_TESTS ]; then
        echo ""
        echo -e "${GREEN}✅ 所有測試通過！${NC}"
        exit 0
    elif [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}❌ 有 $TESTS_FAILED 個測試失敗${NC}"
        echo ""
        echo "💡 提示: 使用以下命令查看失敗詳情："
        echo "   cat $FAIL_LOG"
        exit 1
    else
        echo ""
        echo -e "${YELLOW}⚠️  部分測試未執行${NC}"
        exit 2
    fi
}

# Run main
main "$@"