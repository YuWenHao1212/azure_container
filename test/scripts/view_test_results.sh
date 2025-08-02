#!/bin/bash

# View Test Results Script
# Displays the latest test results and current status

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REPORT_DIR="/Users/yuwenhao/Documents/GitHub/azure_container/test/logs"

# Function to show latest results
show_latest_results() {
    local latest_log=$(ls -t "$REPORT_DIR"/complete_test_*.log 2>/dev/null | head -1)
    
    if [ -z "$latest_log" ]; then
        echo -e "${RED}找不到測試結果${NC}"
        echo "請先執行測試: ./test/scripts/run_complete_test_suite.sh"
        exit 1
    fi
    
    echo -e "${BLUE}=== 最新測試結果 ===${NC}"
    echo "檔案: $latest_log"
    echo "修改時間: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$latest_log")"
    echo ""
    
    # Extract summary section
    echo -e "${BLUE}測試摘要:${NC}"
    sed -n '/=== Test Summary ===/,/^$/p' "$latest_log" | tail -n +2
    
    # Extract test statistics
    echo -e "\n${BLUE}詳細統計:${NC}"
    sed -n '/=== 詳細測試統計 ===/,/\*.*表示視選項執行/p' "$latest_log"
    
    # Extract performance details if available
    if grep -q "效能測試詳情:" "$latest_log"; then
        echo -e "\n${BLUE}效能測試結果:${NC}"
        
        # Keyword extraction performance
        if grep -q "關鍵字提取效能測試詳情:" "$latest_log"; then
            echo -e "\n${YELLOW}關鍵字提取:${NC}"
            sed -n '/關鍵字提取效能測試詳情:/,/SLA 目標:/p' "$latest_log" | tail -n +2
        fi
        
        # Index Calculation V2 performance
        if grep -q "Index Calculation V2 效能測試詳情:" "$latest_log"; then
            echo -e "\n${YELLOW}Index Calculation V2:${NC}"
            sed -n '/Index Calculation V2 效能測試詳情:/,/SLA 目標:/p' "$latest_log" | tail -n +2
        fi
    fi
    
    # Check for errors
    local error_count=$(grep -c "✗ FAILED" "$latest_log" 2>/dev/null || echo 0)
    if [ $error_count -gt 0 ]; then
        echo -e "\n${RED}錯誤摘要:${NC}"
        grep -B2 -A2 "✗ FAILED" "$latest_log" | head -20
        echo -e "\n查看完整錯誤: grep -B5 -A5 'FAILED' $latest_log"
    fi
    
    # Show JSON summary if available
    local summary_file="${latest_log%.log}_summary.json"
    summary_file=$(echo "$summary_file" | sed 's/complete_test_/summary_/')
    if [ -f "$summary_file" ]; then
        echo -e "\n${BLUE}JSON 摘要:${NC}"
        if command -v jq &> /dev/null; then
            jq . "$summary_file"
        else
            cat "$summary_file"
        fi
    fi
}

# Function to check if tests are running
check_running() {
    local progress_file="$REPORT_DIR/.test_progress"
    
    if [ -f "$progress_file" ]; then
        echo -e "${YELLOW}⏳ 測試執行中...${NC}"
        echo ""
        cat "$progress_file"
        echo ""
        
        # Find the running log file
        local running_log=$(ls -t "$REPORT_DIR"/complete_test_*.log 2>/dev/null | head -1)
        if [ -n "$running_log" ]; then
            echo "查看即時進度: tail -f $running_log"
        fi
        return 0
    else
        # Check if process is running
        if pgrep -f "run_complete_test_suite" > /dev/null; then
            echo -e "${YELLOW}⏳ 測試正在執行但無進度資訊${NC}"
            return 0
        else
            return 1
        fi
    fi
}

# Function to list recent test results
list_recent() {
    echo -e "${BLUE}=== 最近的測試結果 ===${NC}"
    echo ""
    
    local count=0
    for log in $(ls -t "$REPORT_DIR"/complete_test_*.log 2>/dev/null | head -6); do
        ((count++))
        local timestamp=$(basename "$log" | sed 's/complete_test_//; s/.log//')
        local mod_time=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$log")
        local size=$(stat -f "%z" "$log")
        local size_kb=$((size / 1024))
        
        # Check if passed or failed
        if grep -q "✅ All tests passed!" "$log"; then
            local status="${GREEN}PASSED${NC}"
        else
            local status="${RED}FAILED${NC}"
        fi
        
        echo "$count. $timestamp - $status - ${size_kb}KB - $mod_time"
    done
    
    if [ $count -eq 0 ]; then
        echo "沒有找到測試結果"
    fi
}

# Function to show specific result
show_specific() {
    local index=$1
    local log=$(ls -t "$REPORT_DIR"/complete_test_*.log 2>/dev/null | sed -n "${index}p")
    
    if [ -z "$log" ]; then
        echo -e "${RED}找不到第 $index 個測試結果${NC}"
        exit 1
    fi
    
    # Temporarily set latest_log and call show_latest_results
    local latest_log=$log
    show_latest_results
}

# Parse command line arguments
case "$1" in
    --list|-l)
        list_recent
        ;;
    --running|-r)
        if check_running; then
            exit 0
        else
            echo -e "${GREEN}✓ 沒有正在執行的測試${NC}"
            echo ""
            show_latest_results
        fi
        ;;
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  (no option)     Show latest test results"
        echo "  --list, -l      List recent test results"
        echo "  --running, -r   Check if tests are running"
        echo "  --help, -h      Show this help message"
        echo "  <number>        Show specific test result (1-6)"
        echo ""
        echo "Examples:"
        echo "  $0              Show latest results"
        echo "  $0 --list       List recent results"
        echo "  $0 2            Show 2nd most recent result"
        ;;
    [1-6])
        show_specific $1
        ;;
    "")
        # Check if running first
        if check_running; then
            echo ""
            echo -e "${YELLOW}提示: 使用 Ctrl+C 結束查看，測試會繼續在背景執行${NC}"
        else
            show_latest_results
        fi
        ;;
    *)
        echo -e "${RED}未知選項: $1${NC}"
        echo "使用 --help 查看幫助"
        exit 1
        ;;
esac