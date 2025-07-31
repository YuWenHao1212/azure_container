#!/bin/bash

# Complete Test Suite for Health Check and Keyword Extraction
# Runs all tests in background and generates a comprehensive report

# set -e  # Temporarily disabled for debugging

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
REPORT_DIR="/Users/yuwenhao/Documents/GitHub/azure_container/test/reports"
REPORT_FILE="${REPORT_DIR}/test_report_${TIMESTAMP}.md"
JSON_REPORT="${REPORT_DIR}/test_report_${TIMESTAMP}.json"

# Create reports directory if not exists
mkdir -p "$REPORT_DIR"

# Function to log to both console and file
log() {
    echo -e "$1" | tee -a "$REPORT_FILE"
}

# Function to run tests and capture results
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    local start_time=$(date +%s)
    
    log "\n${BLUE}Running $suite_name...${NC}"
    
    # Run test and capture output
    if $test_command > /tmp/${suite_name}_output.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local status="${GREEN}PASSED${NC}"
        local exit_code=0
        
        # Extract test statistics from pytest output
        local stats=$(grep -E "(passed|failed|skipped|warnings)" /tmp/${suite_name}_output.log | tail -1 || echo "No statistics available")
        
        log "  Status: $status"
        log "  Duration: ${duration}s"
        log "  Results: $stats"
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local status="${RED}FAILED${NC}"
        local exit_code=1
        
        log "  Status: $status"
        log "  Duration: ${duration}s"
        log "  Error: Check /tmp/${suite_name}_output.log for details"
    fi
    
    return $exit_code
}

# Main test execution function
main() {
    # Header
    {
        echo "======================================"
        echo "Complete Test Suite Report"
        echo "======================================"
        echo "Generated: $(date)"
        echo "Project: Azure Container API"
        echo "Environment: Development"
        echo "======================================"
    } > "$REPORT_FILE"
    
    log "\n${BLUE}Starting Complete Test Suite...${NC}"
    
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
        exit 1
    fi
    
    # Check dependencies
    log "\n${BLUE}2. Dependency Check${NC}"
    if python -c "import fastapi, pytest" 2>/dev/null; then
        log "  Dependencies: ${GREEN}✓ All required packages installed${NC}"
    else
        log "  Dependencies: ${YELLOW}⚠ Installing dependencies...${NC}"
        pip install -r requirements.txt > /tmp/pip_install.log 2>&1
    fi
    
    # Start API server
    log "\n${BLUE}3. Starting API Server${NC}"
    
    # Kill any existing process on port 8000
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
    
    # Load environment variables
    export $(grep -v '^#' .env | xargs)
    
    # Start server with test API key disabled for testing
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    # Temporarily disable API key requirement for testing
    export CONTAINER_APP_API_KEY=""
    uvicorn src.main:app --port 8000 --log-level error > /tmp/api_server.log 2>&1 &
    API_PID=$!
    
    # Wait for server to start
    SERVER_STARTED=false
    for i in {1..20}; do
        if curl -s http://localhost:8000/health > /dev/null 2>/dev/null; then
            log "  API Server: ${GREEN}✓ Started (PID: $API_PID)${NC}"
            SERVER_STARTED=true
            break
        fi
        sleep 1
    done
    
    if [ "$SERVER_STARTED" = false ]; then
        log "  API Server: ${RED}✗ Failed to start${NC}"
        exit 1
    fi
    
    # Test execution counters
    TOTAL_TESTS=0
    PASSED_TESTS=0
    FAILED_TESTS=0
    
    # Run test suites
    log "\n${BLUE}4. Running Test Suites${NC}"
    
    # A. Unit Tests - Health Check
    if run_test_suite "unit_health" "python -m pytest test/unit/test_health.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # B. Unit Tests - Keyword Extraction
    if run_test_suite "unit_keyword_extraction" "python -m pytest test/unit/test_keyword_extraction.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # C. Unit Tests - Keyword Extraction Extended
    if run_test_suite "unit_keyword_extended" "python -m pytest test/unit/test_keyword_extraction_extended.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # D. Unit Tests - Language Detection
    if run_test_suite "unit_language_detection" "python -m pytest test/unit/test_language_detection.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # E. Unit Tests - Prompt Manager
    if run_test_suite "unit_prompt_manager" "python -m pytest test/unit/test_prompt_manager.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # F. Integration Tests - Keyword Extraction Language
    if run_test_suite "integration_keyword_language" "python -m pytest test/integration/test_keyword_extraction_language.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # G. Integration Tests - Health Check External Dependencies
    if run_test_suite "integration_health" "python -m pytest test/integration/test_health_integration.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # H. Integration Tests - Azure OpenAI Integration
    if run_test_suite "integration_azure_openai" "python -m pytest test/integration/test_azure_openai_integration.py -v"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
    
    # I. Performance Test - Keyword Extraction
    log "
${BLUE}5. Performance Testing${NC}"
    if [ -f "test/performance/test_keyword_extraction_performance_simple.py" ]; then
        if run_test_suite "performance_keyword" "python test/performance/test_keyword_extraction_performance_simple.py"; then
            ((PASSED_TESTS++))
        else
            ((FAILED_TESTS++))
        fi
        ((TOTAL_TESTS++))
    else
        log "  ${YELLOW}⚠ Performance test script not found${NC}"
    fi
    
    # Stop API server
    kill $API_PID 2>/dev/null || true
    log "\n  API Server: Stopped"
    
    # Generate summary
    log "\n${BLUE}======================================"
    log "Test Summary"
    log "======================================${NC}"
    log "Total Test Suites: $TOTAL_TESTS"
    log "Passed: ${GREEN}$PASSED_TESTS${NC}"
    log "Failed: ${RED}$FAILED_TESTS${NC}"
    log "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    
    # Collect detailed test results
    log "\n${BLUE}Detailed Test Results:${NC}"
    
    # Count individual tests from logs
    TOTAL_INDIVIDUAL_TESTS=0
    PASSED_INDIVIDUAL_TESTS=0
    FAILED_INDIVIDUAL_TESTS=0
    
    for log_file in /tmp/*_output.log; do
        if [ -f "$log_file" ]; then
            suite_name=$(basename "$log_file" | sed 's/_output.log//')
            
            # Extract pytest statistics
            if grep -q "passed" "$log_file"; then
                stats=$(grep -E "passed|failed" "$log_file" | tail -1)
                log "  $suite_name: $stats"
                
                # Extract numbers
                passed=$(echo "$stats" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
                failed=$(echo "$stats" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo 0)
                
                TOTAL_INDIVIDUAL_TESTS=$((TOTAL_INDIVIDUAL_TESTS + passed + failed))
                PASSED_INDIVIDUAL_TESTS=$((PASSED_INDIVIDUAL_TESTS + passed))
                FAILED_INDIVIDUAL_TESTS=$((FAILED_INDIVIDUAL_TESTS + failed))
            fi
        fi
    done
    
    log "\n${BLUE}Individual Test Statistics:${NC}"
    log "Total Tests Run: $TOTAL_INDIVIDUAL_TESTS"
    log "Tests Passed: ${GREEN}$PASSED_INDIVIDUAL_TESTS${NC}"
    log "Tests Failed: ${RED}$FAILED_INDIVIDUAL_TESTS${NC}"
    
    # Generate JSON report
    cat > "$JSON_REPORT" << EOF
{
  "report_metadata": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "project": "Azure Container API",
    "environment": "Development",
    "test_suites_total": $TOTAL_TESTS,
    "test_suites_passed": $PASSED_TESTS,
    "test_suites_failed": $FAILED_TESTS,
    "individual_tests_total": $TOTAL_INDIVIDUAL_TESTS,
    "individual_tests_passed": $PASSED_INDIVIDUAL_TESTS,
    "individual_tests_failed": $FAILED_INDIVIDUAL_TESTS,
    "success_rate": $(( PASSED_TESTS * 100 / TOTAL_TESTS ))
  },
  "test_suites": [
    {
      "name": "unit_health",
      "type": "unit",
      "module": "health_check",
      "status": "$([ -f /tmp/unit_health_output.log ] && grep -q "failed" /tmp/unit_health_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "unit_keyword_extraction",
      "type": "unit",
      "module": "keyword_extraction",
      "status": "$([ -f /tmp/unit_keyword_extraction_output.log ] && grep -q "failed" /tmp/unit_keyword_extraction_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "unit_keyword_extended",
      "type": "unit",
      "module": "keyword_extraction",
      "status": "$([ -f /tmp/unit_keyword_extended_output.log ] && grep -q "failed" /tmp/unit_keyword_extended_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "unit_language_detection",
      "type": "unit",
      "module": "language_detection",
      "status": "$([ -f /tmp/unit_language_detection_output.log ] && grep -q "failed" /tmp/unit_language_detection_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "unit_prompt_manager",
      "type": "unit",
      "module": "prompt_management",
      "status": "$([ -f /tmp/unit_prompt_manager_output.log ] && grep -q "failed" /tmp/unit_prompt_manager_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "integration_keyword_language",
      "type": "integration",
      "module": "keyword_extraction",
      "status": "$([ -f /tmp/integration_keyword_language_output.log ] && grep -q "failed" /tmp/integration_keyword_language_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "integration_health",
      "type": "integration",
      "module": "health_check",
      "status": "$([ -f /tmp/integration_health_output.log ] && grep -q "failed" /tmp/integration_health_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "integration_azure_openai",
      "type": "integration",
      "module": "keyword_extraction",
      "status": "$([ -f /tmp/integration_azure_openai_output.log ] && grep -q "failed" /tmp/integration_azure_openai_output.log && echo "failed" || echo "passed")"
    },
    {
      "name": "performance_keyword",
      "type": "performance",
      "module": "keyword_extraction",
      "status": "$([ -f /tmp/performance_keyword_output.log ] && grep -q "failed" /tmp/performance_keyword_output.log && echo "failed" || echo "passed")"
    }
  ],
  "report_files": {
    "text_report": "$REPORT_FILE",
    "json_report": "$JSON_REPORT",
    "test_logs": "/tmp/*_output.log"
  }
}
EOF
    
    # Final message
    log "\n${BLUE}======================================"
    log "Test Execution Completed"
    log "======================================${NC}"
    log "Reports saved to:"
    log "  Text Report: $REPORT_FILE"
    log "  JSON Report: $JSON_REPORT"
    log ""
    
    if [ $FAILED_TESTS -eq 0 ]; then
        log "${GREEN}✅ All test suites passed!${NC}"
        exit 0
    else
        log "${RED}❌ Some test suites failed. Check the logs for details.${NC}"
        exit 1
    fi
}

# Run in background if requested
if [ "$1" = "--background" ] || [ "$1" = "-b" ]; then
    echo "Starting test suite in background..."
    echo "Test report will be saved to: ${REPORT_DIR}/test_report_${TIMESTAMP}.txt"
    nohup bash -c "$(declare -f log run_test_suite main); main" > /tmp/test_suite_${TIMESTAMP}.log 2>&1 &
    TEST_PID=$!
    echo "Test suite running in background (PID: $TEST_PID)"
    echo "Monitor progress with: tail -f /tmp/test_suite_${TIMESTAMP}.log"
else
    # Run in foreground
    main
fi