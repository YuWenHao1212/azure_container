#!/bin/bash

# Azure Container API - 統一測試執行腳本
# 執行所有層級的測試並產生完整報告

set -e  # 遇到錯誤立即停止

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source log utilities
source "$SCRIPT_DIR/log_utils.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to script directory
cd "$SCRIPT_DIR"

# Setup log directory with cleanup
LOG_DIR="$(get_log_dir)"
prepare_log_dir "$LOG_DIR" "level*_all_*.log"
prepare_log_dir "$LOG_DIR" "test_summary_*.txt"

# Test summary variables
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=""

# Function to print section header
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

# Function to run test and capture result
run_test() {
    local test_name=$1
    local test_command=$2
    local log_file=$3
    
    echo -e "${YELLOW}執行 $test_name...${NC}"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if eval "$test_command" > "$log_file" 2>&1; then
        echo -e "${GREEN}✓ $test_name 通過${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS="${TEST_RESULTS}\n${GREEN}✓ $test_name${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name 失敗${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS="${TEST_RESULTS}\n${RED}✗ $test_name${NC}"
        echo -e "${RED}詳細錯誤請查看: $log_file${NC}"
        return 1
    fi
}

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="reports/test_report_${TIMESTAMP}.txt"

# Start test report
{
    echo "Azure Container API 測試報告"
    echo "=========================="
    echo "執行時間: $(date)"
    echo ""
} > "$REPORT_FILE"

# Main test execution
print_header "Azure Container API 完整測試套件"

echo "開始執行所有測試層級..."
echo ""

# Level 0: Prompt Validation Tests
print_header "Level 0: Prompt 驗證測試"
run_test "Level 0 - YAML Prompt 驗證" \
    "bash scripts/run_level0_tests.sh" \
    "$LOG_DIR/level0_all_${TIMESTAMP}.log" || true

# Level 1: Code Style Tests  
print_header "Level 1: 程式碼風格測試"
run_test "Level 1 - Ruff 程式碼風格檢查" \
    "bash run_level1_tests.sh" \
    "$LOG_DIR/level1_all_${TIMESTAMP}.log" || true

# Level 2: Unit Tests
print_header "Level 2: 單元測試"
run_test "Level 2 - 單元測試套件" \
    "python run_level2_tests.py" \
    "$LOG_DIR/level2_all_${TIMESTAMP}.log" || true

# Level 3: Integration Tests (if exists)
if [ -f "scripts/run_level3_tests.sh" ]; then
    print_header "Level 3: 整合測試"
    run_test "Level 3 - 整合測試套件" \
        "bash scripts/run_level3_tests.sh" \
        "$LOG_DIR/level3_all_${TIMESTAMP}.log" || true
else
    echo -e "${YELLOW}Level 3 整合測試尚未實作${NC}"
fi

# Test Summary
print_header "測試摘要"

{
    echo ""
    echo "測試摘要"
    echo "========="
    echo "總測試數: $TOTAL_TESTS"
    echo "通過: $PASSED_TESTS"
    echo "失敗: $FAILED_TESTS"
    echo ""
    echo "詳細結果:"
    echo -e "$TEST_RESULTS"
} | tee -a "$REPORT_FILE"

echo ""
echo -e "${BLUE}完整測試報告已儲存至: $REPORT_FILE${NC}"

# Generate simple summary for CI/CD
SUMMARY_FILE="$LOG_DIR/test_summary_${TIMESTAMP}.json"
cat > "$SUMMARY_FILE" <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "total": $TOTAL_TESTS,
  "passed": $PASSED_TESTS,
  "failed": $FAILED_TESTS,
  "success_rate": $(awk "BEGIN {printf \"%.2f\", ($TOTAL_TESTS > 0 ? $PASSED_TESTS/$TOTAL_TESTS*100 : 0)}")
}
EOF

echo -e "${BLUE}測試摘要 JSON 已儲存至: $SUMMARY_FILE${NC}"

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}所有測試通過！${NC}"
    exit 0
else
    echo -e "\n${RED}有 $FAILED_TESTS 個測試失敗${NC}"
    exit 1
fi