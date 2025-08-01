#!/bin/bash

# Complete Test Suite for CI/CD Environment
# Adapted for GitHub Actions and other CI environments

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine project root (works in both local and CI environments)
PROJECT_ROOT="${GITHUB_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
REPORT_DIR="${PROJECT_ROOT}/test/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M)
ERROR_LOG="${REPORT_DIR}/error_${TIMESTAMP}.log"

# Create reports directory if not exists
mkdir -p "$REPORT_DIR"

# Function to clean old reports (keep only latest 6)
clean_old_reports() {
    if [ -d "$REPORT_DIR" ]; then
        cd "$REPORT_DIR" || return
        # Count total files (excluding directories)
        local file_count=$(find . -maxdepth 1 -type f | wc -l)
        
        if [ $file_count -gt 6 ]; then
            # Delete oldest files, keep newest 6
            find . -maxdepth 1 -type f -printf '%T@ %p\n' | sort -n | head -n -6 | cut -d' ' -f2- | xargs rm -f
            echo -e "${YELLOW}Cleaned old reports, kept latest 6 files${NC}"
        fi
        cd - > /dev/null || return
    fi
}

# Function to log only to console (no file output unless error)
log() {
    echo -e "$1"
}

# Function to log errors with context
log_error() {
    local suite_name=$1
    local error_context=$2
    
    # Create error log only when needed
    {
        echo "=== ERROR REPORT ==="
        echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "Test Suite: $suite_name"
        echo "Python Version: $(python --version 2>&1)"
        echo "Working Directory: $(pwd)"
        echo ""
        echo "=== ERROR CONTEXT ==="
        echo "$error_context"
        echo ""
        if [ -f "/tmp/${suite_name}_output.log" ]; then
            echo "=== LAST 50 LINES OF TEST OUTPUT ==="
            tail -50 "/tmp/${suite_name}_output.log"
        fi
    } > "$ERROR_LOG"
    
    log "  ${RED}✗ Error log saved: $ERROR_LOG${NC}"
}

# Function to run tests and capture results
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local start_time=$(date +%s)
    
    log "${BLUE}Running $suite_name...${NC}"
    
    # Run test and capture output
    if $test_command > "/tmp/${suite_name}_output.log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Extract test statistics from pytest output
        local stats=$(grep -E "(passed|failed|skipped|warnings)" "/tmp/${suite_name}_output.log" | tail -1 || echo "")
        
        log "  ${GREEN}✓ PASSED${NC} (${duration}s) - $stats"
        
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "  ${RED}✗ FAILED${NC} (${duration}s)"
        
        # Save error context
        log_error "$suite_name" "Test command failed: $test_command"
        
        return 1
    fi
}

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
    
    # Extract counts from each test suite
    local health_unit_counts=$(extract_test_counts /tmp/unit_health_output.log)
    local kw_unit1_counts=$(extract_test_counts /tmp/unit_keyword_extraction_output.log)
    local kw_unit2_counts=$(extract_test_counts /tmp/unit_keyword_extended_output.log)
    local lang_unit_counts=$(extract_test_counts /tmp/unit_language_detection_output.log)
    local prompt_unit_counts=$(extract_test_counts /tmp/unit_prompt_manager_output.log)
    local llm_unit_counts=$(extract_test_counts /tmp/unit_llm_factory_output.log)
    
    # Integration tests
    local health_int_counts=$(extract_test_counts /tmp/integration_health_output.log)
    local kw_int_counts=$(extract_test_counts /tmp/integration_azure_openai_output.log)
    local lang_int_counts=$(extract_test_counts /tmp/integration_keyword_language_output.log)
    
    # Performance test
    local perf_counts="0/0"
    if [ -f "/tmp/performance_keyword_output.log" ] && grep -q "Overall Performance Summary" /tmp/performance_keyword_output.log; then
        local overall_avg=$(grep "Overall Average Response Time:" /tmp/performance_keyword_output.log | grep -oE '[0-9]+\.[0-9]+' || echo "10000")
        if [ $(echo "$overall_avg < 3000" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
            perf_counts="1/0"
        else
            perf_counts="0/1"
        fi
    fi
    
    # Calculate totals for each module
    # Health module
    local health_total_passed=$(echo "$health_unit_counts $health_int_counts" | awk -F'/' '{sum=0; for(i=1;i<=NF;i+=2) sum+=$i; print sum}')
    local health_total_failed=$(echo "$health_unit_counts $health_int_counts" | awk -F'/' '{sum=0; for(i=2;i<=NF;i+=2) sum+=$i; print sum}')
    log "| Health Check      | $health_unit_counts             | $health_int_counts             | -                   | $health_total_passed/$health_total_failed             |"
    
    # Keyword Extraction module
    local kw_unit_passed=$(echo "$kw_unit1_counts $kw_unit2_counts" | awk -F'/' '{p1=$1; p2=$3} END {print p1+p2}')
    local kw_unit_failed=$(echo "$kw_unit1_counts $kw_unit2_counts" | awk -F'/' '{f1=$2; f2=$4} END {print f1+f2}')
    local kw_total_passed=$(echo "$kw_unit_passed $kw_int_counts" | awk -F'/' '{sum=$1+$2; print sum}')
    local kw_total_failed=$(echo "$kw_unit_failed $kw_int_counts" | awk -F'/' '{sum=$1+$3; print sum}')
    log "| Keyword Extract   | $kw_unit_passed/$kw_unit_failed             | $kw_int_counts             | $perf_counts             | $kw_total_passed/$kw_total_failed             |"
    
    # Language Detection module
    local lang_int_passed=$(echo "$lang_int_counts" | cut -d'/' -f1)
    local lang_int_failed=$(echo "$lang_int_counts" | cut -d'/' -f2)
    local lang_total_passed=$(echo "$lang_unit_counts $lang_int_counts" | awk -F'/' '{sum=$1+$3; print sum}')
    local lang_total_failed=$(echo "$lang_unit_counts $lang_int_counts" | awk -F'/' '{sum=$2+$4; print sum}')
    log "| Language Detect   | $lang_unit_counts             | $lang_int_counts             | -                   | $lang_total_passed/$lang_total_failed             |"
    
    # Prompt Manager module
    log "| Prompt Manager    | $prompt_unit_counts             | -                   | -                   | $prompt_unit_counts             |"
    
    # LLM Factory module
    log "| LLM Factory       | $llm_unit_counts              | -                   | -                   | $llm_unit_counts              |"
    
    log "|-------------------|---------------------|---------------------|---------------------|------------------|"
    
    # Calculate grand totals
    local grand_total_passed=$((health_total_passed + kw_total_passed + lang_total_passed + $(echo "$prompt_unit_counts" | cut -d'/' -f1) + $(echo "$llm_unit_counts" | cut -d'/' -f1)))
    local grand_total_failed=$((health_total_failed + kw_total_failed + lang_total_failed + $(echo "$prompt_unit_counts" | cut -d'/' -f2) + $(echo "$llm_unit_counts" | cut -d'/' -f2)))
    
    log "| **總計**          | -                   | -                   | -                   | **$grand_total_passed/$grand_total_failed**         |"
    
    log "\nTest statistics collection complete"
}

# Main test execution function
main() {
    log "
${BLUE}=== Complete Test Suite ===${NC}"
    log "Timestamp: $(date)"
    log "Project Root: $PROJECT_ROOT"
    
    # Change to project root directory
    cd "$PROJECT_ROOT" || {
        log "${RED}Failed to change to project root: $PROJECT_ROOT${NC}"
        exit 1
    }
    
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
    if command -v lsof &> /dev/null; then
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    else
        # For environments without lsof
        pkill -f "uvicorn.*8000" 2>/dev/null || true
    fi
    sleep 1
    
    # Load environment variables
    export $(grep -v '^#' .env | xargs)
    
    # Start server
    export CONTAINER_APP_API_KEY=""
    uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
    API_PID=$!
    
    # Wait for server to start
    SERVER_STARTED=false
    for i in {1..20}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log "  Server: ${GREEN}✓ Started (PID: $API_PID)${NC}"
            SERVER_STARTED=true
            break
        fi
        sleep 1
    done
    
    if [ "$SERVER_STARTED" = false ]; then
        log "  Server: ${RED}✗ Failed to start${NC}"
        log_error "api_server" "Failed to start API server after 20 seconds"
        if [ -f /tmp/api_server.log ]; then
            log "  Server logs:"
            cat /tmp/api_server.log
        fi
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
    
    # Performance test removed - now part of smoke test in deployment
    
    # Stop API server
    kill $API_PID 2>/dev/null || true
    
    # Collect test statistics
    collect_test_statistics
    
    # Summary
    log "
${BLUE}=== Test Summary ===${NC}"
    log "Total: $TOTAL_TESTS | Passed: ${GREEN}$PASSED_TESTS${NC} | Failed: ${RED}$FAILED_TESTS${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log "\n${GREEN}✅ All tests passed!${NC}"
        
        # Clean up all temp files on success
        rm -f /tmp/*_output.log /tmp/api_server.log
        
        exit 0
    else
        log "\n${RED}❌ Some tests failed. Error logs saved in: $REPORT_DIR${NC}"
        log "Latest error: $ERROR_LOG"
        exit 1
    fi
}

# Run tests
main