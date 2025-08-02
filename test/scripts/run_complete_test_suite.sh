#!/bin/bash

# Complete Test Suite for Health Check and Keyword Extraction
# Optimized for minimal output and debugging with Claude Code

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
TIMESTAMP=$(date +%Y%m%d_%H%M)
REPORT_DIR="/Users/yuwenhao/Documents/GitHub/azure_container/test/logs"
ERROR_LOG="${REPORT_DIR}/error_${TIMESTAMP}.log"

# Create reports directory if not exists
mkdir -p "$REPORT_DIR"

# Function to clean old reports (keep only latest 6)
clean_old_reports() {
    local current_dir=$(pwd)
    cd "$REPORT_DIR"
    # Count total files
    local file_count=$(ls -1 | wc -l)
    
    if [ $file_count -gt 6 ]; then
        # Delete oldest files, keep newest 6
        ls -t | tail -n +7 | xargs rm -f
        echo -e "${YELLOW}Cleaned old reports, kept latest 6 files${NC}"
    fi
    cd "$current_dir"
}

# Function to log only to console (no file output unless error)
log() {
    echo -e "$1"
}

# Function to log errors with context for Claude Code
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

# Function to run tests and capture results
# Function to collect and display test statistics
collect_test_statistics() {
    log "
${BLUE}=== 詳細測試統計 ===${NC}"
    log ""
    log "| 模組              | 單元測試 (通過/失敗) | 整合測試 (通過/失敗) | 效能測試 (通過/失敗) | 總計 (通過/失敗) |"
    log "|-------------------|---------------------|---------------------|---------------------|------------------|"
    
    # Function to extract passed and failed counts
    extract_test_counts() {
        local log_file=$1
        local passed=$(grep -E "[0-9]+ passed" "$log_file" 2>/dev/null | tail -1 | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
        local failed=$(grep -E "[0-9]+ failed" "$log_file" 2>/dev/null | tail -1 | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo 0)
        echo "$passed/$failed"
    }
    
    # Health Check
    local health_unit_counts=$(extract_test_counts /tmp/unit_health_output.log)
    local health_int_counts=$(extract_test_counts /tmp/integration_health_output.log)
    local health_unit_passed=$(echo $health_unit_counts | cut -d'/' -f1)
    local health_unit_failed=$(echo $health_unit_counts | cut -d'/' -f2)
    local health_int_passed=$(echo $health_int_counts | cut -d'/' -f1)
    local health_int_failed=$(echo $health_int_counts | cut -d'/' -f2)
    local health_total_passed=$((health_unit_passed + health_int_passed))
    local health_total_failed=$((health_unit_failed + health_int_failed))
    log "| 健康檢查          | $health_unit_counts         | $health_int_counts          | 0/0                 | $health_total_passed/$health_total_failed            |"
    
    # Keyword Extraction
    local kw_unit1_counts=$(extract_test_counts /tmp/unit_keyword_extraction_output.log)
    local kw_unit2_counts=$(extract_test_counts /tmp/unit_keyword_extended_output.log)
    local kw_unit1_passed=$(echo $kw_unit1_counts | cut -d'/' -f1)
    local kw_unit1_failed=$(echo $kw_unit1_counts | cut -d'/' -f2)
    local kw_unit2_passed=$(echo $kw_unit2_counts | cut -d'/' -f1)
    local kw_unit2_failed=$(echo $kw_unit2_counts | cut -d'/' -f2)
    local kw_unit_passed=$((kw_unit1_passed + kw_unit2_passed))
    local kw_unit_failed=$((kw_unit1_failed + kw_unit2_failed))
    local kw_int_counts=$(extract_test_counts /tmp/integration_azure_openai_output.log)
    local kw_int_passed=$(echo $kw_int_counts | cut -d'/' -f1)
    local kw_int_failed=$(echo $kw_int_counts | cut -d'/' -f2)
    
    # Performance test (check if passed or failed based on exit code)
    local kw_perf_passed=0
    local kw_perf_failed=0
    if [ -f "/tmp/performance_keyword_output.log" ]; then
        # Check if all SLA tests passed (< 3000ms)
        if grep -q "Overall Performance Summary" /tmp/performance_keyword_output.log; then
            local overall_avg=$(grep "Overall Average Response Time:" /tmp/performance_keyword_output.log | grep -oE '[0-9]+\.[0-9]+' || echo "10000")
            if [ $(echo "$overall_avg < 3000" | bc -l) -eq 1 ]; then
                kw_perf_passed=1
            else
                kw_perf_failed=1
            fi
        fi
    fi
    
    local kw_total_passed=$((kw_unit_passed + kw_int_passed + kw_perf_passed))
    local kw_total_failed=$((kw_unit_failed + kw_int_failed + kw_perf_failed))
    log "| 關鍵字提取        | $kw_unit_passed/$kw_unit_failed        | $kw_int_passed/$kw_int_failed         | $kw_perf_passed/$kw_perf_failed                 | $kw_total_passed/$kw_total_failed            |"
    
    # Language Detection
    local lang_unit_counts=$(extract_test_counts /tmp/unit_language_detection_output.log)
    local lang_int_counts=$(extract_test_counts /tmp/integration_keyword_language_output.log)
    local lang_unit_passed=$(echo $lang_unit_counts | cut -d'/' -f1)
    local lang_unit_failed=$(echo $lang_unit_counts | cut -d'/' -f2)
    local lang_int_passed=$(echo $lang_int_counts | cut -d'/' -f1)
    local lang_int_failed=$(echo $lang_int_counts | cut -d'/' -f2)
    local lang_total_passed=$((lang_unit_passed + lang_int_passed))
    local lang_total_failed=$((lang_unit_failed + lang_int_failed))
    log "| 語言檢測          | $lang_unit_counts        | $lang_int_counts         | 0/0                 | $lang_total_passed/$lang_total_failed            |"
    
    # Prompt Manager
    local prompt_unit_counts=$(extract_test_counts /tmp/unit_prompt_manager_output.log)
    local prompt_unit_passed=$(echo $prompt_unit_counts | cut -d'/' -f1)
    local prompt_unit_failed=$(echo $prompt_unit_counts | cut -d'/' -f2)
    log "| Prompt管理        | $prompt_unit_counts        | 0/0                 | 0/0                 | $prompt_unit_passed/$prompt_unit_failed            |"
    
    # LLM Factory
    local llm_unit_counts=$(extract_test_counts /tmp/unit_llm_factory_output.log)
    local llm_unit_passed=$(echo $llm_unit_counts | cut -d'/' -f1)
    local llm_unit_failed=$(echo $llm_unit_counts | cut -d'/' -f2)
    log "| LLM Factory       | $llm_unit_counts         | 0/0                 | 0/0                 | $llm_unit_passed/$llm_unit_failed            |"
    
    # Totals
    local total_unit_passed=$((health_unit_passed + kw_unit_passed + lang_unit_passed + prompt_unit_passed + llm_unit_passed))
    local total_unit_failed=$((health_unit_failed + kw_unit_failed + lang_unit_failed + prompt_unit_failed + llm_unit_failed))
    local total_int_passed=$((health_int_passed + kw_int_passed + lang_int_passed))
    local total_int_failed=$((health_int_failed + kw_int_failed + lang_int_failed))
    local total_perf_passed=$kw_perf_passed
    local total_perf_failed=$kw_perf_failed
    local grand_total_passed=$((total_unit_passed + total_int_passed + total_perf_passed))
    local grand_total_failed=$((total_unit_failed + total_int_failed + total_perf_failed))
    
    log "|-------------------|---------------------|---------------------|---------------------|------------------|"
    log "| **總計**          | **$total_unit_passed/$total_unit_failed**    | **$total_int_passed/$total_int_failed**    | **$total_perf_passed/$total_perf_failed**    | **$grand_total_passed/$grand_total_failed**   |"
    
    # Performance test details if available
    if [ -f "/tmp/performance_keyword_output.log" ] && grep -q "Overall Performance Summary" /tmp/performance_keyword_output.log; then
        log "
${BLUE}效能測試詳情:${NC}"
        log "------------------------------------------------------------"
        
        # Extract performance metrics
        local small_avg=$(grep -A10 "Small JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local medium_avg=$(grep -A10 "Medium JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local large_avg=$(grep -A10 "Large JD" /tmp/performance_keyword_output.log | grep "Average:" | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "N/A")
        local overall_avg=$(grep "Overall Average Response Time:" /tmp/performance_keyword_output.log | grep -oE '[0-9]+\.[0-9]+' || echo "N/A")
        
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
}

run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local start_time=$(date +%s)
    
    log "${BLUE}Running $suite_name...${NC}"
    
    # Run test and capture output
    if $test_command > /tmp/${suite_name}_output.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Extract test statistics from pytest output
        local stats=$(grep -E "(passed|failed|skipped|warnings)" /tmp/${suite_name}_output.log | tail -1 || echo "")
        
        log "  ${GREEN}✓ PASSED${NC} (${duration}s) - $stats"
        
        # Don't clean up yet - needed for statistics
        
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "  ${RED}✗ FAILED${NC} (${duration}s)"
        
        # Save error context for Claude Code
        log_error "$suite_name" "Test command failed: $test_command"
        
        return 1
    fi
}

# Main test execution function
main() {
    log "
${BLUE}=== Complete Test Suite ===${NC}"
    log "Timestamp: $(date)"
    
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
    
    # Run test suites
    log "\n${BLUE}4. Test Execution${NC}"
    
    # Define test suites
    declare -a TEST_SUITES=(
        "unit_health:python -m pytest test/unit/test_health.py -v"
        "unit_keyword_extraction:python -m pytest test/unit/test_keyword_extraction.py -v"
        "unit_keyword_extended:python -m pytest test/unit/test_keyword_extraction_extended.py -v"
        "unit_language_detection:python -m pytest test/unit/test_language_detection.py -v"
        "unit_prompt_manager:python -m pytest test/unit/test_prompt_manager.py -v"
        "unit_llm_factory:python -m pytest test/unit/test_llm_factory_deployment_mapping.py -v"
        "integration_keyword_language:python -m pytest test/integration/test_keyword_extraction_language.py -v"
        "integration_health:python -m pytest test/integration/test_health_integration.py -v"
        "integration_azure_openai:python -m pytest test/integration/test_azure_openai_integration.py -v"
    )
    
    # Run each test suite
    for suite in "${TEST_SUITES[@]}"; do
        IFS=':' read -r suite_name test_command <<< "$suite"
        if run_test_suite "$suite_name" "$test_command"; then
            ((PASSED_TESTS++))
        else
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
    done
    
    # Performance Test
    log "\n${BLUE}5. Performance Test${NC}"
    if [ -f "test/performance/test_keyword_extraction_performance_simple.py" ]; then
        if run_test_suite "performance_keyword" "python test/performance/test_keyword_extraction_performance_simple.py"; then
            ((PASSED_TESTS++))
            
            # Extract and display performance summary
            if [ -f "/tmp/performance_keyword_output.log" ]; then
                log "
${BLUE}Performance Summary:${NC}"
                grep -E "Small JD.*Average:|Medium JD.*Average:|Large JD.*Average:|Overall Average" /tmp/performance_keyword_output.log | sed 's/^/  /'
                # Keep the log file for statistics function
            fi
        else
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
    fi
    
    # Stop API server
    kill $API_PID 2>/dev/null || true
    
    # Collect individual test statistics
    collect_test_statistics
    
    # Summary
    log "
${BLUE}=== Test Summary ===${NC}"
    log "Total: $TOTAL_TESTS | Passed: ${GREEN}$PASSED_TESTS${NC} | Failed: ${RED}$FAILED_TESTS${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log "\n${GREEN}✅ All tests passed!${NC}"
        
        # Clean up all temp files on success
        rm -f /tmp/*_output.log /tmp/api_server.log /tmp/performance_output.log
        
        exit 0
    else
        log "\n${RED}❌ Some tests failed. Error logs saved in: $REPORT_DIR${NC}"
        log "Latest error: $ERROR_LOG"
        exit 1
    fi
}

# Function to run only performance tests
run_performance_only() {
    log "\n${BLUE}=== Performance Test Only ===${NC}"
    log "Timestamp: $(date)"
    
    # Change to project root directory
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    
    # Clean old reports at start
    clean_old_reports
    
    # Check environment
    if [ ! -f ".env" ]; then
        log "${RED}✗ .env file missing${NC}"
        exit 1
    fi
    
    # Start API server
    log "\n${BLUE}Starting API Server${NC}"
    
    # Kill any existing process on port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Load environment variables and start server
    export $(grep -v '^#' .env | xargs)
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    export CONTAINER_APP_API_KEY=""
    uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
    API_PID=$!
    
    # Wait for server
    SERVER_STARTED=false
    for i in {1..20}; do
        if curl -s http://localhost:8000/health > /dev/null 2>/dev/null; then
            log "  ${GREEN}✓ Server started${NC}"
            SERVER_STARTED=true
            break
        fi
        sleep 1
    done
    
    if [ "$SERVER_STARTED" = false ]; then
        log "  ${RED}✗ Server failed to start${NC}"
        log_error "api_server" "Failed to start API server"
        exit 1
    fi
    
    # Run performance test
    log "\n${BLUE}Running Performance Test${NC}"
    
    if [ -f "test/performance/test_keyword_extraction_performance_simple.py" ]; then
        if python test/performance/test_keyword_extraction_performance_simple.py > /tmp/performance_output.log 2>&1; then
            log "  ${GREEN}✓ Performance test passed${NC}"
            
            # Show summary
            log "\n${BLUE}Results:${NC}"
            grep -E "Small JD.*Average:|Medium JD.*Average:|Large JD.*Average:|Overall Average|SLA" /tmp/performance_output.log | sed 's/^/  /'
            
            # Clean up
            rm -f /tmp/performance_output.log /tmp/api_server.log
            
            RESULT=0
        else
            log "  ${RED}✗ Performance test failed${NC}"
            log_error "performance_test" "Performance test execution failed"
            RESULT=1
        fi
    else
        log "  ${RED}✗ Performance test not found${NC}"
        RESULT=1
    fi
    
    # Stop API server
    kill $API_PID 2>/dev/null || true
    
    exit $RESULT
}

# Parse command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --performance, -p    Run only performance tests"
    echo "  --help, -h           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   Run all tests"
    echo "  $0 --performance     Run only performance tests"
    echo ""
    echo "Note: Reports are only saved when tests fail (for Claude Code debugging)"
    exit 0
fi

# Run tests
if [ "$1" = "--performance" ] || [ "$1" = "-p" ]; then
    run_performance_only
else
    main
fi