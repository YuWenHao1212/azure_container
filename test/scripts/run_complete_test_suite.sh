#!/bin/bash

# Complete Test Suite for All Modules Including Index Calculation V2
# Supports background execution, stage execution, and performance/E2E options

# Initialize pyenv and use Python 3.11.8
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
pyenv shell 3.11.8

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get timestamp for report
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="/Users/yuwenhao/Documents/GitHub/azure_container/test/logs"
ERROR_LOG="${REPORT_DIR}/error_${TIMESTAMP}.log"
LOG_FILE="${REPORT_DIR}/complete_test_${TIMESTAMP}.log"
SUMMARY_FILE="${REPORT_DIR}/summary_${TIMESTAMP}.json"
PROGRESS_FILE="${REPORT_DIR}/.test_progress"

# Create reports directory if not exists
mkdir -p "$REPORT_DIR"

# Command line options
INCLUDE_PERFORMANCE=false
INCLUDE_E2E=false
INDEX_CALC_ONLY=false
BACKGROUND_EXEC=false
STAGE_EXEC=""
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --include-performance)
            INCLUDE_PERFORMANCE=true
            shift
            ;;
        --include-e2e)
            INCLUDE_E2E=true
            shift
            ;;
        --index-calc-only)
            INDEX_CALC_ONLY=true
            shift
            ;;
        --background|-b)
            BACKGROUND_EXEC=true
            shift
            ;;
        --stage)
            STAGE_EXEC="$2"
            shift 2
            ;;
        --performance|-p)
            # Legacy option - run only performance tests
            STAGE_EXEC="performance"
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            SHOW_HELP=true
            shift
            ;;
    esac
done

# Show help message
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --performance, -p          Run only performance tests"
    echo "  --include-performance      Include ALL performance tests (existing + Index Calc V2)"
    echo "  --include-e2e             Include E2E tests (Index Calculation V2)"
    echo "  --index-calc-only         Run only Index Calculation V2 tests"
    echo "  --background, -b          Run tests in background"
    echo "  --stage <stage>           Run specific stage: unit, integration, performance, e2e"
    echo "  --help, -h                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                        Run core tests (Unit + Integration only)"
    echo "  $0 --include-performance  Run all tests including performance"
    echo "  $0 --include-e2e          Run all tests including E2E"
    echo "  $0 --index-calc-only      Run only Index Calculation V2 tests (18-26 tests)"
    echo "  $0 --background           Run tests in background and save to log"
    echo "  $0 --stage unit           Run only unit tests"
    echo ""
    echo "To stop background tests:"
    echo "  ./test/scripts/stop_test.sh"
    echo ""
    echo "Estimated execution times:"
    echo "  Unit Tests (106): ~40 seconds"
    echo "  Integration Tests (24): ~30 seconds"
    echo "  Performance Tests (6): ~90 seconds"
    echo "  E2E Tests (3): ~30 seconds"
    echo "  Total (all): ~190 seconds"
    exit 0
}

if [ "$SHOW_HELP" = true ]; then
    show_help
fi

# Auto-enable background execution for performance tests
if [ "$INCLUDE_PERFORMANCE" = true ] || [ "$STAGE_EXEC" = "performance" ]; then
    if [ "$BACKGROUND_EXEC" = false ]; then
        echo "Note: Performance tests take ~90 seconds. Auto-enabling background execution."
        echo "Use 'tail -f' on the log file to monitor progress."
        BACKGROUND_EXEC=true
    fi
fi

# Function to clean old reports (keep only latest 6)
clean_old_reports() {
    local current_dir=$(pwd)
    cd "$REPORT_DIR"
    
    # Define log file patterns to clean
    local patterns=(
        "complete_test_*.log"
        "error_*.log"
        "index_calculation_v2_*.log"
        "performance_test_*.json"
        "summary_*.json"
    )
    
    # Clean each type of log file
    for pattern in "${patterns[@]}"; do
        local file_count=$(ls -1 $pattern 2>/dev/null | wc -l)
        
        if [ $file_count -gt 6 ]; then
            # Delete oldest files, keep newest 6
            ls -t $pattern | tail -n +7 | xargs rm -f
            echo -e "${YELLOW}Cleaned old ${pattern} files, kept latest 6${NC}"
        fi
    done
    
    # Also remove any .test_progress file older than 1 day
    find . -name ".test_progress" -mtime +1 -delete 2>/dev/null
    
    cd "$current_dir"
}

# Function to log to both console and file
log() {
    echo -e "$1"
    echo -e "$1" >> "$LOG_FILE"
}

# Function to log errors with context
log_error() {
    local suite_name=$1
    local error_context=$2
    
    # Create error log only when needed
    {
        echo "=== ERROR REPORT FOR CLAUDE CODE ==="
        echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "Test Suite: $suite_name"
        echo "Python Version: $(python --version)"
        echo "Working Directory: $(pwd)"
        echo ""
        echo "=== ENVIRONMENT ==="
        echo "Key environment variables:"
        env | grep -E "(AZURE|OPENAI|CONTAINER|ENVIRONMENT)" | sed 's/=.*/=<hidden>/'
        echo ""
        echo "=== ERROR CONTEXT ==="
        echo "$error_context"
        echo ""
        echo "=== LAST 50 LINES OF TEST OUTPUT ==="
        tail -50 /tmp/${suite_name}_output.log
        echo ""
        echo "=== PYTEST FAILURE DETAILS ==="
        grep -A 20 -B 5 "FAILED\|ERROR\|AssertionError\|Exception" /tmp/${suite_name}_output.log || echo "No failure details found"
        echo ""
        echo "=== API SERVER LOGS (if available) ==="
        if [ -f /tmp/api_server.log ]; then
            tail -30 /tmp/api_server.log
        else
            echo "No API server logs found"
        fi
        echo ""
        echo "=== SUGGESTIONS FOR CLAUDE CODE ==="
        echo "1. Check the error message and stack trace above"
        echo "2. Look for assertion failures or connection errors"
        echo "3. Verify environment variables are set correctly"
        echo "4. Check if API server started successfully"
        echo "5. Review the test that failed: $suite_name"
    } > "$ERROR_LOG"
    
    log "  ${RED}✗ Error log saved: $ERROR_LOG${NC}"
}

# Progress tracking
update_progress() {
    local current=$1
    local total=$2
    local test_name=$3
    local percent=$((current * 100 / total))
    
    {
        echo "進度: $current/$total ($percent%)"
        echo "目前測試: $test_name"
        echo "開始時間: $(date -r $START_TIME '+%Y-%m-%d %H:%M:%S')"
        echo "已執行: $(($(date +%s) - START_TIME)) 秒"
    } > "$PROGRESS_FILE"
}

# Function to extract test counts
extract_test_counts() {
    local log_file=$1
    local passed=$(grep -E "[0-9]+ passed" "$log_file" 2>/dev/null | tail -1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
    local xpassed=$(grep -E "[0-9]+ xpassed" "$log_file" 2>/dev/null | tail -1 | grep -oE '[0-9]+ xpassed' | grep -oE '[0-9]+' || echo 0)
    local failed=$(grep -E "[0-9]+ failed" "$log_file" 2>/dev/null | tail -1 | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo 0)
    # Include xpassed in the passed count (tests that were expected to fail but passed)
    local total_passed=$((passed + xpassed))
    echo "$total_passed/$failed"
}

# Function to collect and display test statistics
collect_test_statistics() {
    log "
${BLUE}=== 詳細測試統計 ===${NC}"
    log ""
    log "| 模組                | 單元測試 | 整合測試 | 效能測試 | E2E測試 | 總計 |"
    log "|-------------------|----------|----------|----------|---------|------|"
    
    # Health Check
    local health_unit_counts=$(extract_test_counts /tmp/unit_health_output.log)
    local health_int_counts=$(extract_test_counts /tmp/integration_health_output.log)
    local health_unit_passed=$(echo $health_unit_counts | cut -d'/' -f1)
    local health_unit_failed=$(echo $health_unit_counts | cut -d'/' -f2)
    local health_int_passed=$(echo $health_int_counts | cut -d'/' -f1)
    local health_int_failed=$(echo $health_int_counts | cut -d'/' -f2)
    local health_total_passed=$((health_unit_passed + health_int_passed))
    local health_total_failed=$((health_unit_failed + health_int_failed))
    log "| 健康檢查          | $health_unit_counts | $health_int_counts | 0/0 | 0/0 | $health_total_passed/$health_total_failed |"
    
    # Keyword Extraction
    local kw_unit1_counts=$(extract_test_counts /tmp/unit_keyword_extraction_output.log)
    local kw_unit2_counts=$(extract_test_counts /tmp/unit_keyword_extended_output.log)
    local kw_unit1_passed=$(echo $kw_unit1_counts | cut -d'/' -f1)
    local kw_unit1_failed=$(echo $kw_unit1_counts | cut -d'/' -f2)
    local kw_unit2_passed=$(echo $kw_unit2_counts | cut -d'/' -f1)
    local kw_unit2_failed=$(echo $kw_unit2_counts | cut -d'/' -f2)
    local kw_unit_passed=$((kw_unit1_passed + kw_unit2_passed))
    local kw_unit_failed=$((kw_unit1_failed + kw_unit2_failed))
    # Fix: keyword extraction language integration tests should be counted here
    local kw_int_counts=$(extract_test_counts /tmp/integration_keyword_language_output.log)
    local kw_int_passed=$(echo $kw_int_counts | cut -d'/' -f1)
    local kw_int_failed=$(echo $kw_int_counts | cut -d'/' -f2)
    
    # Performance test counts for keyword extraction
    local kw_perf_counts="0/0"
    if [ "$INCLUDE_PERFORMANCE" = true ] || [ "$STAGE_EXEC" = "performance" ]; then
        kw_perf_counts=$(extract_test_counts /tmp/performance_keyword_output.log)
    fi
    local kw_perf_passed=$(echo $kw_perf_counts | cut -d'/' -f1)
    local kw_perf_failed=$(echo $kw_perf_counts | cut -d'/' -f2)
    
    local kw_total_passed=$((kw_unit_passed + kw_int_passed + kw_perf_passed))
    local kw_total_failed=$((kw_unit_failed + kw_int_failed + kw_perf_failed))
    log "| 關鍵字提取        | $kw_unit_passed/$kw_unit_failed | $kw_int_passed/$kw_int_failed | $kw_perf_counts$([ "$INCLUDE_PERFORMANCE" = false ] && [ "$STAGE_EXEC" != "performance" ] && echo '*') | 0/0 | $kw_total_passed/$kw_total_failed |"
    
    # Language Detection
    local lang_unit_counts=$(extract_test_counts /tmp/unit_language_detection_output.log)
    # Fix: language detection doesn't have integration tests currently
    local lang_int_counts="0/0"
    local lang_unit_passed=$(echo $lang_unit_counts | cut -d'/' -f1)
    local lang_unit_failed=$(echo $lang_unit_counts | cut -d'/' -f2)
    local lang_int_passed=0
    local lang_int_failed=0
    local lang_total_passed=$((lang_unit_passed + lang_int_passed))
    local lang_total_failed=$((lang_unit_failed + lang_int_failed))
    log "| 語言檢測          | $lang_unit_counts | $lang_int_counts | 0/0 | 0/0 | $lang_total_passed/$lang_total_failed |"
    
    # Prompt Manager
    local prompt_unit_counts=$(extract_test_counts /tmp/unit_prompt_manager_output.log)
    local prompt_unit_passed=$(echo $prompt_unit_counts | cut -d'/' -f1)
    local prompt_unit_failed=$(echo $prompt_unit_counts | cut -d'/' -f2)
    log "| Prompt管理        | $prompt_unit_counts | 0/0 | 0/0 | 0/0 | $prompt_unit_passed/$prompt_unit_failed |"
    
    # LLM Factory
    local llm_unit_counts=$(extract_test_counts /tmp/unit_llm_factory_output.log)
    local llm_unit_passed=$(echo $llm_unit_counts | cut -d'/' -f1)
    local llm_unit_failed=$(echo $llm_unit_counts | cut -d'/' -f2)
    log "| LLM Factory       | $llm_unit_counts | 0/0 | 0/0 | 0/0 | $llm_unit_passed/$llm_unit_failed |"
    
    # Index Calculation V2
    local ic_unit_counts=$(extract_test_counts /tmp/unit_index_calc_v2_output.log)
    local ic_int_counts=$(extract_test_counts /tmp/integration_index_calc_v2_output.log)
    local ic_unit_passed=$(echo $ic_unit_counts | cut -d'/' -f1)
    local ic_unit_failed=$(echo $ic_unit_counts | cut -d'/' -f2)
    local ic_int_passed=$(echo $ic_int_counts | cut -d'/' -f1)
    local ic_int_failed=$(echo $ic_int_counts | cut -d'/' -f2)
    
    # Performance and E2E tests for Index Calc V2
    local ic_perf_counts="0/0"
    local ic_e2e_counts="0/0"
    if [ "$INCLUDE_PERFORMANCE" = true ] || [ "$STAGE_EXEC" = "performance" ]; then
        ic_perf_counts=$(extract_test_counts /tmp/performance_index_calc_v2_output.log)
    fi
    if [ "$INCLUDE_E2E" = true ] || [ "$STAGE_EXEC" = "e2e" ]; then
        ic_e2e_counts=$(extract_test_counts /tmp/e2e_index_calc_v2_output.log)
    fi
    local ic_perf_passed=$(echo $ic_perf_counts | cut -d'/' -f1)
    local ic_perf_failed=$(echo $ic_perf_counts | cut -d'/' -f2)
    local ic_e2e_passed=$(echo $ic_e2e_counts | cut -d'/' -f1)
    local ic_e2e_failed=$(echo $ic_e2e_counts | cut -d'/' -f2)
    
    local ic_total_passed=$((ic_unit_passed + ic_int_passed + ic_perf_passed + ic_e2e_passed))
    local ic_total_failed=$((ic_unit_failed + ic_int_failed + ic_perf_failed + ic_e2e_failed))
    log "| Index Calculation V2 | $ic_unit_counts | $ic_int_counts | $ic_perf_counts$([ "$INCLUDE_PERFORMANCE" = false ] && [ "$STAGE_EXEC" != "performance" ] && echo '*') | $ic_e2e_counts$([ "$INCLUDE_E2E" = false ] && [ "$STAGE_EXEC" != "e2e" ] && echo '*') | $ic_total_passed/$ic_total_failed |"
    
    # Totals
    local total_unit_passed=$((health_unit_passed + kw_unit_passed + lang_unit_passed + prompt_unit_passed + llm_unit_passed + ic_unit_passed))
    local total_unit_failed=$((health_unit_failed + kw_unit_failed + lang_unit_failed + prompt_unit_failed + llm_unit_failed + ic_unit_failed))
    local total_int_passed=$((health_int_passed + kw_int_passed + lang_int_passed + ic_int_passed))
    local total_int_failed=$((health_int_failed + kw_int_failed + lang_int_failed + ic_int_failed))
    local total_perf_passed=$((kw_perf_passed + ic_perf_passed))
    local total_perf_failed=$((kw_perf_failed + ic_perf_failed))
    local total_e2e_passed=$ic_e2e_passed
    local total_e2e_failed=$ic_e2e_failed
    local grand_total_passed=$((total_unit_passed + total_int_passed + total_perf_passed + total_e2e_passed))
    local grand_total_failed=$((total_unit_failed + total_int_failed + total_perf_failed + total_e2e_failed))
    
    log "|-------------------|----------|----------|----------|---------|------|"
    log "| **總計**          | **$total_unit_passed/$total_unit_failed** | **$total_int_passed/$total_int_failed** | **$total_perf_passed/$total_perf_failed** | **$total_e2e_passed/$total_e2e_failed** | **$grand_total_passed/$grand_total_failed** |"
    log ""
    log "* 表示視選項執行"
    
    # Performance test details if available
    if [ -f "/tmp/performance_keyword_output.log" ] && grep -q "Overall Performance:" /tmp/performance_keyword_output.log; then
        log "
${BLUE}關鍵字提取效能測試詳情:${NC}"
        log "------------------------------------------------------------"
        
        # Extract performance metrics
        local small_avg=$(grep -A10 "Small JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local medium_avg=$(grep -A10 "Medium JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local large_avg=$(grep -A10 "Large JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local overall_avg=$(grep "Overall Performance:" -A2 /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' || echo "N/A")
        
        log "測試案例             | 平均回應時間 | SLA 狀態"
        log "---------------------|--------------|----------"
        log "Small JD (200 chars) | ${small_avg} ms    | $([ "$small_avg" != "N/A" ] && [ $(echo "$small_avg < 3000" | bc -l) -eq 1 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "Medium JD (500 chars)| ${medium_avg} ms    | $([ "$medium_avg" != "N/A" ] && [ $(echo "$medium_avg < 3000" | bc -l) -eq 1 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "Large JD (1000+ chars)| ${large_avg} ms    | $([ "$large_avg" != "N/A" ] && [ $(echo "$large_avg < 3000" | bc -l) -eq 1 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "---------------------|--------------|----------"
        log "整體平均             | ${overall_avg} ms    | $([ "$overall_avg" != "N/A" ] && [ $(echo "$overall_avg < 3000" | bc -l) -eq 1 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log ""
        log "SLA 目標: < 3000ms"
    fi
    
    # Index Calculation V2 Performance test details
    if [ -f "/tmp/performance_index_calc_v2_output.log" ] && grep -q "Overall Performance:" /tmp/performance_index_calc_v2_output.log; then
        log "
${BLUE}Index Calculation V2 效能測試詳情:${NC}"
        log "------------------------------------------------------------"
        
        # Extract performance metrics
        local small_p50=$(grep "Small.*P50:" /tmp/performance_index_calc_v2_output.log | sed -E 's/^.*P50: ([0-9]+)ms.*$/\1/' | head -1 || echo "N/A")
        local medium_p50=$(grep "Medium.*P50:" /tmp/performance_index_calc_v2_output.log | sed -E 's/^.*P50: ([0-9]+)ms.*$/\1/' | head -1 || echo "N/A")
        local large_p50=$(grep "Large.*P50:" /tmp/performance_index_calc_v2_output.log | sed -E 's/^.*P50: ([0-9]+)ms.*$/\1/' | head -1 || echo "N/A")
        local overall_p50=$(grep "Overall Performance:" -A5 /tmp/performance_index_calc_v2_output.log | grep "P50:" | sed -E 's/^.*P50: ([0-9]+)ms.*$/\1/' || echo "N/A")
        local overall_p95=$(grep "Overall Performance:" -A5 /tmp/performance_index_calc_v2_output.log | grep "P95:" | sed -E 's/^.*P95: ([0-9]+)ms.*$/\1/' || echo "N/A")
        local overall_p99=$(grep "Overall Performance:" -A5 /tmp/performance_index_calc_v2_output.log | grep "P99:" | sed -E 's/^.*P99: ([0-9]+)ms.*$/\1/' || echo "N/A")
        
        log "測試案例             | P50 回應時間 | SLA 狀態"
        log "---------------------|--------------|----------"
        log "Small (< 1KB)       | ${small_p50} ms      | $([ "$small_p50" != "N/A" ] && [ $small_p50 -lt 1000 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "Medium (1-10KB)     | ${medium_p50} ms      | $([ "$medium_p50" != "N/A" ] && [ $medium_p50 -lt 1000 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "Large (10-30KB)     | ${large_p50} ms      | $([ "$large_p50" != "N/A" ] && [ $large_p50 -lt 1000 ] && echo '✅ PASS' || echo '❌ FAIL')"
        log "---------------------|--------------|----------"
        log "整體統計:"
        log "  P50: ${overall_p50} ms $([ "$overall_p50" != "N/A" ] && [ $overall_p50 -lt 1000 ] && echo '✅' || echo '❌')"
        log "  P95: ${overall_p95} ms $([ "$overall_p95" != "N/A" ] && [ $overall_p95 -lt 2000 ] && echo '✅' || echo '❌')"
        log "  P99: ${overall_p99} ms $([ "$overall_p99" != "N/A" ] && [ $overall_p99 -lt 3000 ] && echo '✅' || echo '❌')"
        log ""
        log "SLA 目標: P50 < 1000ms, P95 < 2000ms, P99 < 3000ms"
    fi
    
    # Generate JSON summary
    generate_summary_json
}

# Generate JSON summary
generate_summary_json() {
    cat > "$SUMMARY_FILE" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "total_tests": $((TOTAL_TESTS)),
    "passed": $((PASSED_TESTS)),
    "failed": $((FAILED_TESTS)),
    "duration_seconds": $(($(date +%s) - START_TIME)),
    "options": {
        "include_performance": $INCLUDE_PERFORMANCE,
        "include_e2e": $INCLUDE_E2E,
        "stage": "$STAGE_EXEC"
    }
}
EOF
}

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local start_time=$(date +%s)
    
    log "${BLUE}Running $suite_name...${NC}"
    
    # Update progress
    update_progress $((CURRENT_TEST)) $((TOTAL_PLANNED_TESTS)) "$suite_name"
    
    # Run test and capture output
    if $test_command > /tmp/${suite_name}_output.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Extract test statistics from pytest output
        local stats=$(grep -E "(passed|failed|skipped|warnings)" /tmp/${suite_name}_output.log | tail -1 || echo "")
        
        log "  ${GREEN}✓ PASSED${NC} (${duration}s) - $stats"
        
        ((PASSED_TESTS++))
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "  ${RED}✗ FAILED${NC} (${duration}s)"
        
        # Save error context for Claude Code
        log_error "$suite_name" "Test command failed: $test_command"
        
        ((FAILED_TESTS++))
        FAILED_SUITES+=("$suite_name")
        return 1
    fi
}

# Main test execution function
run_all_tests() {
    log "
${BLUE}=== Complete Test Suite ===${NC}"
    log "Timestamp: $(date)"
    log "Options: include_performance=$INCLUDE_PERFORMANCE, include_e2e=$INCLUDE_E2E, stage=$STAGE_EXEC"
    
    # Change to project root directory
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    
    # Clean old reports at start
    clean_old_reports
    
    # Check environment
    log "\n${BLUE}1. Environment Check${NC}"
    
    # Check Python
    PYTHON_VERSION=$(python --version 2>&1)
    log "  Python: $PYTHON_VERSION"
    
    # Check if .env exists
    if [ -f ".env" ]; then
        log "  Environment: ${GREEN}✓ .env file found${NC}"
    else
        log "  Environment: ${RED}✗ .env file missing${NC}"
        echo "ERROR: .env file not found" > "$ERROR_LOG"
        exit 1
    fi
    
    # Check dependencies
    log "\n${BLUE}2. Dependency Check${NC}"
    if python -c "import fastapi, pytest" 2>/dev/null; then
        log "  Dependencies: ${GREEN}✓ OK${NC}"
    else
        log "  Dependencies: ${YELLOW}⚠ Installing...${NC}"
        pip install -r requirements.txt > /tmp/pip_install.log 2>&1
    fi
    
    # Start API server
    log "\n${BLUE}3. API Server${NC}"
    
    # Kill any existing process on port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Load environment variables
    export $(grep -v '^#' .env | xargs)
    
    # Start server
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    export CONTAINER_APP_API_KEY=""
    uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
    API_PID=$!
    
    # Wait for server to start
    SERVER_STARTED=false
    for i in {1..20}; do
        if curl -s http://localhost:8000/health > /dev/null 2>/dev/null; then
            log "  Server: ${GREEN}✓ Started (PID: $API_PID)${NC}"
            SERVER_STARTED=true
            break
        fi
        sleep 1
    done
    
    if [ "$SERVER_STARTED" = false ]; then
        log "  Server: ${RED}✗ Failed to start${NC}"
        log_error "api_server" "Failed to start API server after 20 seconds"
        exit 1
    fi
    
    # Test execution counters
    TOTAL_TESTS=0
    PASSED_TESTS=0
    FAILED_TESTS=0
    CURRENT_TEST=0
    FAILED_SUITES=()
    
    # Define test suites based on options
    declare -a TEST_SUITES=()
    
    # Add tests based on stage or default behavior
    if [ "$INDEX_CALC_ONLY" = true ]; then
        # Only Index Calculation V2 tests
        if [ -z "$STAGE_EXEC" ] || [ "$STAGE_EXEC" = "unit" ]; then
            TEST_SUITES+=("unit_index_calc_v2:python -m pytest test/unit/test_index_calculation_v2.py -v")
        fi
        if [ -z "$STAGE_EXEC" ] || [ "$STAGE_EXEC" = "integration" ]; then
            TEST_SUITES+=("integration_index_calc_v2:python -m pytest test/integration/test_index_calculation_v2_api.py -v")
        fi
        if ([ -z "$STAGE_EXEC" ] && [ "$INCLUDE_PERFORMANCE" = true ]) || [ "$STAGE_EXEC" = "performance" ]; then
            TEST_SUITES+=("performance_index_calc_v2:python -m pytest test/performance/test_index_calculation_v2_performance.py -v -s")
        fi
        if ([ -z "$STAGE_EXEC" ] && [ "$INCLUDE_E2E" = true ]) || [ "$STAGE_EXEC" = "e2e" ]; then
            TEST_SUITES+=("e2e_index_calc_v2:python -m pytest test/e2e/test_index_calculation_v2_e2e.py -v")
        fi
    else
        # Normal test suite selection
        if [ -z "$STAGE_EXEC" ] || [ "$STAGE_EXEC" = "unit" ]; then
            TEST_SUITES+=(
                "unit_health:python -m pytest test/unit/test_health.py -v"
                "unit_keyword_extraction:python -m pytest test/unit/test_keyword_extraction.py -v"
                "unit_keyword_extended:python -m pytest test/unit/test_keyword_extraction_extended.py -v"
                "unit_language_detection:python -m pytest test/unit/test_language_detection.py -v"
                "unit_prompt_manager:python -m pytest test/unit/test_prompt_manager.py -v"
                "unit_llm_factory:python -m pytest test/unit/test_llm_factory_deployment_mapping.py -v"
                "unit_index_calc_v2:python -m pytest test/unit/test_index_calculation_v2.py -v"
            )
        fi
        
        if [ -z "$STAGE_EXEC" ] || [ "$STAGE_EXEC" = "integration" ]; then
            TEST_SUITES+=(
                "integration_keyword_language:python -m pytest test/integration/test_keyword_extraction_language.py -v"
                "integration_health:python -m pytest test/integration/test_health_integration.py -v"
                "integration_azure_openai:python -m pytest test/integration/test_azure_openai_integration.py -v"
                "integration_index_calc_v2:python -m pytest test/integration/test_index_calculation_v2_api.py -v"
            )
        fi
        
        if [ "$STAGE_EXEC" = "performance" ] || ([ -z "$STAGE_EXEC" ] && [ "$INCLUDE_PERFORMANCE" = true ]); then
            TEST_SUITES+=(
                "performance_keyword:python -m pytest test/performance/test_keyword_extraction_performance.py -v -s"
                "performance_index_calc_v2:python -m pytest test/performance/test_index_calculation_v2_performance.py -v -s"
            )
        fi
        
        if [ "$STAGE_EXEC" = "e2e" ] || ([ -z "$STAGE_EXEC" ] && [ "$INCLUDE_E2E" = true ]); then
            TEST_SUITES+=(
                "e2e_index_calc_v2:python -m pytest test/e2e/test_index_calculation_v2_e2e.py -v"
            )
        fi
    fi
    
    # Calculate total planned tests
    TOTAL_PLANNED_TESTS=${#TEST_SUITES[@]}
    
    log "\n${BLUE}4. Test Execution${NC}"
    log "Planning to run $TOTAL_PLANNED_TESTS test suites"
    
    # Run each test suite
    for suite in "${TEST_SUITES[@]}"; do
        IFS=':' read -r suite_name test_command <<< "$suite"
        ((CURRENT_TEST++))
        run_test_suite "$suite_name" "$test_command"
        ((TOTAL_TESTS++))
    done
    
    # Stop API server
    kill $API_PID 2>/dev/null || true
    
    # Collect individual test statistics
    collect_test_statistics
    
    # Summary
    log "
${BLUE}=== Test Suite Summary ===${NC}"
    log "Total Test Suites: $TOTAL_TESTS | Passed: ${GREEN}$PASSED_TESTS${NC} | Failed: ${RED}$FAILED_TESTS${NC}"
    
    # Show failed test suites if any
    if [ $FAILED_TESTS -gt 0 ]; then
        log "
${RED}Failed Test Suites:${NC}"
        for suite in "${FAILED_SUITES[@]}"; do
            log "  - ${RED}$suite${NC}"
        done
    fi
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log "\n${GREEN}✅ All tests passed!${NC}"
        
        # Clean up all temp files on success
        rm -f /tmp/*_output.log /tmp/api_server.log /tmp/performance_output.log
        
        return 0
    else
        log "\n${RED}❌ Some tests failed. Error logs saved in: $REPORT_DIR${NC}"
        log "Latest error: $ERROR_LOG"
        return 1
    fi
}

# Background execution wrapper
run_in_background() {
    {
        START_TIME=$(date +%s)
        run_all_tests
        exit_code=$?
        
        # Final message
        echo ""
        echo "=== Test execution completed at $(date) ==="
        echo "Exit code: $exit_code"
        echo "Log file: $LOG_FILE"
        echo "Summary: $SUMMARY_FILE"
        
        # Remove progress file
        rm -f "$PROGRESS_FILE"
        
        exit $exit_code
    } > "$LOG_FILE" 2>&1 &
    
    BG_PID=$!
    
    echo "測試已在背景執行中..."
    echo "PID: $BG_PID"
    echo "日誌檔案: $LOG_FILE"
    echo "查看進度: tail -f $LOG_FILE"
    echo "查看結果: ./test/scripts/view_test_results.sh"
}

# Main execution
START_TIME=$(date +%s)

if [ "$BACKGROUND_EXEC" = true ]; then
    run_in_background
else
    run_all_tests
    exit $?
fi