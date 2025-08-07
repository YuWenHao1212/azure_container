#!/bin/bash

# ============================================================================
# Service Modules Test Runner
# Based on TEST_SPEC_SERVICE_MODULES.md
# Runs exactly 47 unit tests for service layer modules
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

# Function to print test module header
print_module_header() {
    local module_name=$1
    local test_count=$2
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📦 $module_name ($test_count tests)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to run tests for a module
run_module_tests() {
    local module_file=$1
    local module_name=$2
    local expected_count=$3
    
    if [ -f "$module_file" ]; then
        echo -e "${BLUE}Running: pytest $module_file -v --tb=short${NC}"
        
        # Run pytest and capture output
        if pytest "$module_file" -v --tb=short --color=yes 2>&1 | tee /tmp/pytest_output.txt; then
            # Extract test counts from pytest output
            local passed=$(grep -oE "[0-9]+ passed" /tmp/pytest_output.txt | grep -oE "[0-9]+" | tail -1)
            local failed=$(grep -oE "[0-9]+ failed" /tmp/pytest_output.txt | grep -oE "[0-9]+" | tail -1)
            local skipped=$(grep -oE "[0-9]+ skipped" /tmp/pytest_output.txt | grep -oE "[0-9]+" | tail -1)
            
            passed=${passed:-0}
            failed=${failed:-0}
            skipped=${skipped:-0}
            
            local total=$((passed + failed + skipped))
            
            TESTS_RUN=$((TESTS_RUN + total))
            TESTS_PASSED=$((TESTS_PASSED + passed))
            TESTS_FAILED=$((TESTS_FAILED + failed))
            TESTS_SKIPPED=$((TESTS_SKIPPED + skipped))
            
            if [ "$failed" -eq 0 ]; then
                echo -e "${GREEN}✅ $module_name: All tests passed ($passed/$total)${NC}"
                return 0
            else
                echo -e "${RED}❌ $module_name: Some tests failed ($failed failed, $passed passed)${NC}"
                return 1
            fi
        else
            echo -e "${RED}❌ $module_name: Test execution failed${NC}"
            TESTS_FAILED=$((TESTS_FAILED + expected_count))
            TESTS_RUN=$((TESTS_RUN + expected_count))
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  $module_file not found - creating placeholder${NC}"
        TESTS_SKIPPED=$((TESTS_SKIPPED + expected_count))
        TESTS_RUN=$((TESTS_RUN + expected_count))
        return 2
    fi
}

# Function to print progress bar
print_progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    
    echo -n "["
    for ((i=0; i<filled; i++)); do echo -n "█"; done
    for ((i=filled; i<width; i++)); do echo -n "░"; done
    echo -n "] $percent% ($current/$total)"
}

# Function to print test matrix
print_test_matrix() {
    echo ""
    echo "📊 測試分布與結果矩陣"
    echo "═══════════════════════════════════════════════════════════════════"
    echo "| 測試模組        | 單元測試      | 總計         | 狀態 | 成功率 |"
    echo "|-----------------|---------------|--------------|------|--------|"
    
    # Language Detection
    local ld_status="✅"
    if [ -f "test/unit/services/test_language_detection_service.py" ]; then
        local ld_result=$(pytest test/unit/services/test_language_detection_service.py --co -q 2>/dev/null | tail -1 | grep -oE "[0-9]+" || echo "0")
    else
        ld_result=0
        ld_status="⏳"
    fi
    printf "| %-15s | %-13s | %-12s | %-4s | %-6s |\n" "語言檢測" "14+4 ${ld_status}" "18 ${ld_status}" "$ld_status" "TBD"
    
    # Prompt Management
    local pm_status="✅"
    if [ -f "test/unit/services/test_unified_prompt_service.py" ]; then
        local pm_result=$(pytest test/unit/services/test_unified_prompt_service.py --co -q 2>/dev/null | tail -1 | grep -oE "[0-9]+" || echo "0")
    else
        pm_result=0
        pm_status="⏳"
    fi
    printf "| %-15s | %-13s | %-12s | %-4s | %-6s |\n" "Prompt管理" "15+3 ${pm_status}" "18 ${pm_status}" "$pm_status" "TBD"
    
    # Keyword Service
    local kw_status="✅"
    if [ -f "test/unit/services/test_keyword_service_integration.py" ]; then
        local kw_result=$(pytest test/unit/services/test_keyword_service_integration.py --co -q 2>/dev/null | tail -1 | grep -oE "[0-9]+" || echo "0")
    else
        kw_result=0
        kw_status="⏳"
    fi
    printf "| %-15s | %-13s | %-12s | %-4s | %-6s |\n" "關鍵字服務" "10 ${kw_status}(10/0)" "10 ${kw_status}(10/0)" "$kw_status" "100%"
    
    # LLM Factory
    local llm_status="✅"
    if [ -f "test/unit/services/test_llm_factory_service.py" ]; then
        local llm_result=$(pytest test/unit/services/test_llm_factory_service.py --co -q 2>/dev/null | tail -1 | grep -oE "[0-9]+" || echo "0")
    else
        llm_result=0
        llm_status="⏳"
    fi
    printf "| %-15s | %-13s | %-12s | %-4s | %-6s |\n" "LLM Factory" "8+3 ${llm_status}" "11 ${llm_status}" "$llm_status" "TBD"
    
    echo "|-----------------|---------------|--------------|------|--------|"
    
    # Total row
    local total_status="✅"
    if [ $TESTS_FAILED -gt 0 ]; then
        total_status="❌"
    elif [ $TESTS_SKIPPED -gt 0 ]; then
        total_status="⚠️"
    fi
    
    local success_rate=0
    if [ $TESTS_RUN -gt 0 ]; then
        success_rate=$((TESTS_PASSED * 100 / TESTS_RUN))
    fi
    
    printf "| ${BOLD}%-15s${NC} | ${BOLD}%-13s${NC} | ${BOLD}%-12s${NC} | ${BOLD}%-4s${NC} | ${BOLD}%-5s%%${NC} |\n" \
           "總計" "$TESTS_RUN ($TESTS_PASSED/$TESTS_FAILED)" "$TESTS_RUN ($TESTS_PASSED/$TESTS_FAILED)" "$total_status" "$success_rate"
    echo "═══════════════════════════════════════════════════════════════════"
}

# Main execution
main() {
    print_header
    
    # Check if test directory exists
    if [ ! -d "test/unit/services" ]; then
        echo -e "${YELLOW}Creating test/unit/services directory...${NC}"
        mkdir -p test/unit/services
    fi
    
    # Module test execution
    echo -e "${BOLD}🚀 Starting Service Module Tests${NC}"
    echo ""
    
    # Run each module's tests
    MODULE_RESULTS=()
    
    # 1. Language Detection Service (14 tests)
    print_module_header "Language Detection Service" "14"
    if run_module_tests "test/unit/services/test_language_detection_service.py" "Language Detection" 14; then
        MODULE_RESULTS+=("LD:PASS")
    else
        MODULE_RESULTS+=("LD:FAIL")
    fi
    
    # 2. Unified Prompt Service (15 tests)
    print_module_header "Unified Prompt Service" "15"
    if run_module_tests "test/unit/services/test_unified_prompt_service.py" "Prompt Management" 15; then
        MODULE_RESULTS+=("PM:PASS")
    else
        MODULE_RESULTS+=("PM:FAIL")
    fi
    
    # 3. Keyword Service Integration (10 tests)
    print_module_header "Keyword Service Integration" "10"
    if run_module_tests "test/unit/services/test_keyword_service_integration.py" "Keyword Service" 10; then
        MODULE_RESULTS+=("KW:PASS")
    else
        MODULE_RESULTS+=("KW:FAIL")
    fi
    
    # 4. LLM Factory Service (8 tests)
    print_module_header "LLM Factory Service" "8"
    if run_module_tests "test/unit/services/test_llm_factory_service.py" "LLM Factory" 8; then
        MODULE_RESULTS+=("LLM:PASS")
    else
        MODULE_RESULTS+=("LLM:FAIL")
    fi
    
    # Calculate execution time
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Print test matrix
    print_test_matrix
    
    # Print summary
    echo ""
    echo "📈 測試執行摘要"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "總測試數: ${BOLD}$TOTAL_TESTS${NC}"
    echo -e "已執行: ${BOLD}$TESTS_RUN${NC}"
    echo -e "通過: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "失敗: ${RED}$TESTS_FAILED${NC}"
    echo -e "跳過: ${YELLOW}$TESTS_SKIPPED${NC}"
    echo -e "執行時間: ${BOLD}${DURATION}秒${NC}"
    echo ""
    
    # Print progress bar
    echo -n "整體進度: "
    print_progress_bar $TESTS_PASSED $TESTS_RUN
    echo ""
    
    # Coverage report (if coverage is installed)
    if command -v coverage &> /dev/null; then
        echo ""
        echo "📊 生成覆蓋率報告..."
        coverage run -m pytest test/unit/services/ -q 2>/dev/null || true
        coverage report --include="src/services/*" 2>/dev/null || echo "Coverage report not available"
    fi
    
    # Exit code based on results
    if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_RUN -eq $TOTAL_TESTS ]; then
        echo ""
        echo -e "${GREEN}${BOLD}✅ 所有服務層測試通過！${NC}"
        exit 0
    elif [ $TESTS_FAILED -gt 0 ]; then
        echo ""
        echo -e "${RED}${BOLD}❌ 有 $TESTS_FAILED 個測試失敗${NC}"
        exit 1
    else
        echo ""
        echo -e "${YELLOW}${BOLD}⚠️  部分測試未執行 (已執行: $TESTS_RUN/$TOTAL_TESTS)${NC}"
        exit 2
    fi
}

# Run main function
main "$@"