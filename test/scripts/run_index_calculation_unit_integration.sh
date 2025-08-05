#!/bin/bash

# Unit and Integration Test Runner for Index Calculation V2
# Tests with mocked services (no real API calls)
# Based on Index Calculation test specifications

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup logging
LOG_DIR="test/logs"
mkdir -p "$LOG_DIR"
# Generate timestamp once for consistent naming
TIMESTAMP=$(date +%Y%m%d_%H%M)
LOG_FILE="$LOG_DIR/test_suite_index_calculation_unit_integration_${TIMESTAMP}.log"

# Command line options
STAGE_EXEC=""
VERBOSE=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            STAGE_EXEC="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "Index Calculation Unit and Integration Test Runner (Mock Tests)"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <unit|integration>  Run specific test stage"
    echo "  --verbose                   Show verbose output"
    echo "  --help, -h                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  \$0                         # Run all available tests (10 unit + 14 integration = 24 total)"
    echo "  $0 --stage unit           # Run only unit tests (10 tests)"
    echo "  \$0 --stage integration    # Run only integration tests (14 tests)"
    echo ""
    echo "Note: These tests use mocks and do not require Azure OpenAI API access."
    exit 0
fi

# Function to manage log files (keep only latest 6)
manage_log_files() {
    # Clean up old main logs
    local log_files=($(ls -t "$LOG_DIR"/test_suite_index_calculation_unit_integration_*.log 2>/dev/null | grep -v "_batch" || true))
    if [ ${#log_files[@]} -gt 6 ]; then
        for ((i=6; i<${#log_files[@]}; i++)); do
            rm -f "${log_files[i]}"
            # Also remove corresponding batch log if exists
            local batch_log="${log_files[i]%.log}_batch.log"
            [ -f "$batch_log" ] && rm -f "$batch_log"
            echo "Removed old logs: ${log_files[i]}" >> "$LOG_FILE"
        done
    fi
}

# Function to log with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to log environment info
log_environment_info() {
    log_message "=== ENVIRONMENT INFORMATION ==="
    log_message "Python Version: $(python --version 2>&1)"
    log_message "Working Directory: $(pwd)"
    log_message "Script Version: Index Calculation Unit & Integration Test Runner v1.0"
    log_message "Test Specification: Index Calculation test specifications"
    log_message "Virtual Environment: ${VIRTUAL_ENV:-Not Active}"
    
    # LLM Configuration (from environment)
    log_message "LLM Configuration (Mocked):"
    log_message "  - Index Calculation: ${LLM_MODEL_INDEX_CAL:-gpt4o-2} @ ${AZURE_OPENAI_ENDPOINT:-Mocked}"
    log_message "  - Embedding Service: ${EMBEDDING_ENDPOINT:-Mocked}"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Mocked}"
    
    log_message "Test Files:"
    log_message "  - Unit Tests: test/unit/test_index_calculation_v2.py"
    log_message "  - Integration Tests: test/integration/test_index_calculation_v2_api.py"
    log_message "Total Tests: 22 (10 Unit + 12 Integration)"
    log_message "Mock Services: Enabled (No real API calls)"
    log_message "================================"
}

# Function to log and print
log_and_print() {
    local message="$1"
    echo -e "$message"
    log_message "$message"
}

# Test tracking arrays
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()

# Test categorization
UNIT_PASSED=()
UNIT_FAILED=()
INTEGRATION_PASSED=()
INTEGRATION_FAILED=()

# Priority tracking
P0_PASSED=()
P0_FAILED=()
P1_PASSED=()
P1_FAILED=()
P2_PASSED=()
P2_FAILED=()

# Test execution times
TEST_TIMES=()
START_TIME=$(date +%s)

# Function to check test priority
get_test_priority() {
    local test_id="$1"
    case $test_id in
        # P0 Priority tests (critical functionality)
        "API-IC-001-UT"|"API-IC-002-UT"|"API-IC-005-UT"|"API-IC-006-UT"|"API-IC-007-UT"|"API-IC-009-UT"|"API-IC-010-UT")
            echo "P0" ;;
        "API-IC-101-IT"|"API-IC-102-IT"|"API-IC-103-IT"|"API-IC-104-IT"|"API-IC-105-IT"|"API-IC-109-IT"|"API-IC-112-IT"|"API-IC-114-IT")
            echo "P0" ;;
        # P1 Priority tests (important functionality)
        "API-IC-003-UT"|"API-IC-004-UT"|"API-IC-008-UT")
            echo "P1" ;;
        "API-IC-106-IT"|"API-IC-108-IT"|"API-IC-110-IT"|"API-IC-111-IT"|"API-IC-113-IT")
            echo "P1" ;;
        # P2 Priority tests (nice to have)
        "API-IC-107-IT")
            echo "P2" ;;
        *)
            echo "Unknown" ;;
    esac
}

# Function to get test name
get_test_name() {
    local test_id="$1"
    case $test_id in
        # Unit Tests
        "API-IC-001-UT") echo "服務初始化測試" ;;
        "API-IC-002-UT") echo "快取鍵生成測試" ;;
        "API-IC-003-UT") echo "快取TTL過期測試" ;;
        "API-IC-004-UT") echo "快取LRU淘汰測試" ;;
        "API-IC-005-UT") echo "相似度計算整合測試" ;;
        "API-IC-006-UT") echo "Sigmoid轉換參數測試" ;;
        "API-IC-007-UT") echo "關鍵字覆蓋分析測試" ;;
        "API-IC-008-UT") echo "TinyMCE HTML清理測試" ;;
        "API-IC-009-UT") echo "TaskGroup並行執行測試" ;;
        "API-IC-010-UT") echo "TaskGroup錯誤處理測試" ;;
        # Integration Tests
        "API-IC-101-IT") echo "API端點基本功能測試" ;;
        "API-IC-102-IT") echo "快取行為整合測試" ;;
        "API-IC-103-IT") echo "輸入驗證測試" ;;
        "API-IC-104-IT") echo "Azure OpenAI速率限制錯誤測試" ;;
        "API-IC-105-IT") echo "Azure OpenAI認證錯誤測試" ;;
        "API-IC-106-IT") echo "Azure OpenAI伺服器錯誤測試" ;;
        "API-IC-107-IT") echo "並發請求處理測試" ;;
        "API-IC-108-IT") echo "大文檔處理測試" ;;
        "API-IC-109-IT") echo "服務統計端點測試" ;;
        "API-IC-110-IT") echo "跨語言內容測試" ;;
        "API-IC-111-IT") echo "高並發功能測試" ;;
        "API-IC-112-IT") echo "記憶體管理測試" ;;
        "API-IC-113-IT") echo "快取LRU功能測試" ;;
        "API-IC-114-IT") echo "錯誤恢復機制測試" ;;
        *)
            echo "Unknown Test" ;;
    esac
}

# Function to run a test and track detailed results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-120}"
    local category="$4"
    local priority=$(get_test_priority "$test_id")
    
    log_and_print "${BLUE}Running ${test_id} (${priority})...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s - Category: $category"
    
    local test_start=$(date +%s)
    local test_output_file="$LOG_DIR/test_${test_id}_$(date +%Y%m%d_%H%M%S).log"
    
    # Determine timeout command
    local timeout_cmd=""
    if command -v gtimeout >/dev/null 2>&1; then
        timeout_cmd="gtimeout ${timeout}s"
    elif command -v timeout >/dev/null 2>&1; then
        timeout_cmd="timeout ${timeout}s"
    else
        timeout_cmd=""
    fi
    
    if [ -n "$timeout_cmd" ]; then
        timeout_exec_cmd="$timeout_cmd python -m pytest"
    else
        timeout_exec_cmd="python -m pytest"
    fi
    
    # Execute test with mocks enabled (default behavior)
    if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${duration}s"
        PASSED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "unit") UNIT_PASSED+=("${test_id}") ;;
            "integration") INTEGRATION_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
            "P2") P2_PASSED+=("${test_id}") ;;
        esac
        
        # Log key test info to main log
        log_message "TEST DETAILS: $test_id completed successfully"
        
        # Clean up successful test log if not verbose
        if [ "$VERBOSE" = false ]; then
            rm -f "$test_output_file"
        fi
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${RED}✗ FAILED${NC} (${duration}s)"
        log_message "TEST FAILED: $test_id - Duration: ${duration}s"
        log_message "ERROR LOG saved to: $test_output_file"
        FAILED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "unit") UNIT_FAILED+=("${test_id}") ;;
            "integration") INTEGRATION_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
            "P2") P2_FAILED+=("${test_id}") ;;
        esac
        
        # Log error info to main log
        log_message "TEST ERROR: $test_id failed - see $test_output_file for details"
        # Extract and log the actual error message
        local error_msg=$(grep -E "(FAILED|ERROR|AssertionError)" "$test_output_file" | head -3)
        if [ -n "$error_msg" ]; then
            log_message "Error summary: $error_msg"
        fi
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
    fi
    echo
}

# Function to run unit tests (10 tests)
run_unit_tests() {
    echo -e "${BLUE}Running Index Calculation Unit Tests (10 tests)${NC}"
    echo "Testing file: test/unit/test_index_calculation_v2.py"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # All 10 unit tests from API-IC-001-UT to API-IC-010-UT
    local unit_tests=(
        "API-IC-001-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_service_initialization"
        "API-IC-002-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_key_generation"
        "API-IC-003-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_ttl_expiration"
        "API-IC-004-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_cache_lru_eviction"
        "API-IC-005-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_similarity_calculation_integration"
        "API-IC-006-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_sigmoid_transform_parameters"
        "API-IC-007-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_keyword_coverage_analysis"
        "API-IC-008-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_tinymce_html_cleaning"
        "API-IC-009-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_taskgroup_parallel_execution"
        "API-IC-010-UT:test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_taskgroup_error_handling"
    )
    
    for test_entry in "${unit_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        run_test "$test_id" "$test_path" 60 "unit"
    done
}

# Function to run integration tests (14 tests)
run_integration_tests() {
    echo -e "\${BLUE}Running Index Calculation Integration Tests (14 tests)\${NC}"
    echo "Testing file: test/integration/test_index_calculation_v2_api.py"
    echo "Note: Using mocked services (no real API calls)"
    echo
    
    # Run integration tests as a batch for efficiency
    local test_start=$(date +%s)
    local test_output_file="${LOG_DIR}/test_suite_index_calculation_unit_integration_${TIMESTAMP}_batch.log"
    
    echo -e "${BLUE}Running all integration tests in batch...${NC}"
    
    # Use virtual environment Python if available
    local python_cmd="python"
    if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
        python_cmd="venv/bin/python"
    fi
    
    # Run integration test file and post-process to add test IDs
    if $python_cmd -m pytest test/integration/test_index_calculation_v2_api.py -v --tb=short --durations=0 > "${test_output_file}.tmp" 2>&1; then
        # Post-process output to add test IDs
        add_test_ids_to_output "${test_output_file}.tmp" "$test_output_file"
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        
        # Parse results from pytest output
        local passed_count=$(grep -E "passed" "$test_output_file" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo "0")
        local failed_count=$(grep -E "failed" "$test_output_file" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo "0")
        
        echo -e "  ${GREEN}✓ Batch test completed${NC} (${duration}s)"
        echo -e "  Results: ${GREEN}${passed_count} passed${NC}, ${RED}${failed_count} failed${NC}"
        
        # Log batch results to main log
        log_message "BATCH TEST COMPLETED: ${passed_count} passed, ${failed_count} failed in ${duration}s"
        log_message "Batch output file: $test_output_file"
        
        # Parse individual test results for reporting
        parse_batch_test_results "$test_output_file"
        
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        
        echo -e "  ${RED}✗ Batch test failed${NC} (${duration}s)"
        echo "  Error details saved to: $(basename "$test_output_file")"
        
        # Run integration test and post-process to add test IDs  
        $python_cmd -m pytest test/integration/test_index_calculation_v2_api.py -v --tb=short --durations=0 > "${test_output_file}.tmp" 2>&1 || true
        # Post-process output to add test IDs
        add_test_ids_to_output "${test_output_file}.tmp" "$test_output_file"
        
        # Log batch failure to main log
        log_message "BATCH TEST FAILED: Integration tests failed in ${duration}s"
        log_message "Batch error file: $test_output_file"
        
        # Check if it's a collection error (syntax error, import error, etc.)
        if grep -q "ERROR collecting\|SyntaxError\|ImportError" "$test_output_file"; then
            echo -e "  ${RED}Collection Error: All integration tests marked as failed${NC}"
            log_message "COLLECTION ERROR: Marking all 14 integration tests as failed"
            
            # Log collection error details
            local error_details=$(grep -A 5 "ERROR collecting\|SyntaxError\|ImportError" "$test_output_file" | head -10)
            log_message "Collection error details:"
            echo "$error_details" | while IFS= read -r line; do
                log_message "  $line"
            done
            # Mark all 14 integration tests as failed (including new tests)
            for i in $(seq 101 114); do
                local test_id="API-IC-${i}-IT"
                FAILED_TESTS+=("$test_id")
                INTEGRATION_FAILED+=("$test_id")
                
                # Determine priority
                case "$test_id" in
                    API-IC-10[1-5]-IT|API-IC-109-IT|API-IC-112-IT) P0_FAILED+=("$test_id") ;;
                    API-IC-10[68]-IT|API-IC-11[01]-IT) P1_FAILED+=("$test_id") ;;
                    API-IC-107-IT) P2_FAILED+=("$test_id") ;;
                esac
            done
        else
            # Parse individual test results even on failure
            parse_batch_test_results "$test_output_file"
        fi
        
        if [ "$VERBOSE" = true ]; then
            echo "  Test summary:"
            grep -E "(PASSED|FAILED|ERROR)" "$test_output_file" | tail -20 | sed 's/^/    /'
        fi
    fi
}

# Function to add test IDs to pytest output
add_test_ids_to_output() {
    local input_file="$1"
    local output_file="$2"
    
    # Create a temporary file for processing
    local temp_file="${output_file}.processing"
    
    # Process the input file line by line
    while IFS= read -r line; do
        # Check if this is a test result line
        if [[ "$line" =~ test_api_endpoint_basic_functionality.*PASSED|test_api_endpoint_basic_functionality.*FAILED ]]; then
            echo "$line [API-IC-101-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_cache_behavior_integration.*PASSED|test_cache_behavior_integration.*FAILED ]]; then
            echo "$line [API-IC-102-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_input_validation.*PASSED|test_input_validation.*FAILED ]]; then
            echo "$line [API-IC-103-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_azure_openai_rate_limit_error.*PASSED|test_azure_openai_rate_limit_error.*FAILED ]]; then
            echo "$line [API-IC-104-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_azure_openai_auth_error.*PASSED|test_azure_openai_auth_error.*FAILED ]]; then
            echo "$line [API-IC-105-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_azure_openai_server_error.*PASSED|test_azure_openai_server_error.*FAILED ]]; then
            echo "$line [API-IC-106-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_concurrent_request_handling.*PASSED|test_concurrent_request_handling.*FAILED ]]; then
            echo "$line [API-IC-107-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_large_document_handling.*PASSED|test_large_document_handling.*FAILED ]]; then
            echo "$line [API-IC-108-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_service_stats_endpoint.*PASSED|test_service_stats_endpoint.*FAILED ]]; then
            echo "$line [API-IC-109-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_cross_language_content.*PASSED|test_cross_language_content.*FAILED ]]; then
            echo "$line [API-IC-110-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_high_concurrency_functionality.*PASSED|test_high_concurrency_functionality.*FAILED ]]; then
            echo "$line [API-IC-111-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_memory_management.*PASSED|test_memory_management.*FAILED ]]; then
            echo "$line [API-IC-112-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_cache_lru_functionality.*PASSED|test_cache_lru_functionality.*FAILED ]]; then
            echo "$line [API-IC-113-IT]" >> "$temp_file"
        elif [[ "$line" =~ test_error_recovery_mechanism.*PASSED|test_error_recovery_mechanism.*FAILED ]]; then
            echo "$line [API-IC-114-IT]" >> "$temp_file"
        else
            # For non-test result lines, keep them as-is
            echo "$line" >> "$temp_file"
        fi
    done < "$input_file"
    
    # Move the processed file to the final output
    mv "$temp_file" "$output_file"
    
    # Clean up temporary files
    rm -f "$input_file" "${output_file}.processing" 2>/dev/null || true
}

# Function to parse batch test results
parse_batch_test_results() {
    local output_file="$1"
    
    log_message "=== PARSING BATCH TEST RESULTS ==="
    log_message "Batch test output file: $output_file"
    
    # Map test method names to test IDs (using case statements for compatibility)
    map_test_method_to_id() {
        local method="$1"
        case "$method" in
            "test_api_endpoint_basic_functionality") echo "API-IC-101-IT" ;;
            "test_cache_behavior_integration") echo "API-IC-102-IT" ;;
            "test_input_validation") echo "API-IC-103-IT" ;;
            "test_azure_openai_rate_limit_error") echo "API-IC-104-IT" ;;
            "test_azure_openai_auth_error") echo "API-IC-105-IT" ;;
            "test_azure_openai_server_error") echo "API-IC-106-IT" ;;
            "test_concurrent_request_handling") echo "API-IC-107-IT" ;;
            "test_large_document_handling") echo "API-IC-108-IT" ;;
            "test_service_stats_endpoint") echo "API-IC-109-IT" ;;
            "test_cross_language_content") echo "API-IC-110-IT" ;;
            "test_high_concurrency_functionality") echo "API-IC-111-IT" ;;
            "test_memory_management") echo "API-IC-112-IT" ;;
            "test_cache_lru_functionality") echo "API-IC-113-IT" ;;
            "test_error_recovery_mechanism") echo "API-IC-114-IT" ;;
            *) echo "" ;;
        esac
    }
    
    # Parse PASSED tests
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            # Extract method name from line
            local method=$(echo "$line" | sed -E 's/.*::(test_[a-zA-Z_]+).*/\1/')
            if [ -n "$method" ]; then
                local test_id=$(map_test_method_to_id "$method")
                if [ -n "$test_id" ]; then
                    # Check if test_id is already in arrays to avoid duplicates
                    if [[ ! " ${PASSED_TESTS[*]} " =~ " $test_id " ]]; then
                        PASSED_TESTS+=("$test_id")
                        INTEGRATION_PASSED+=("$test_id")
                    
                        # Log successful test with clear ID mapping
                        log_message "BATCH TEST PASSED: $test_id → $method"
                        
                        # Categorize by priority
                        case "$test_id" in
                            API-IC-10[1-5]-IT|API-IC-109-IT|API-IC-112-IT) P0_PASSED+=("$test_id") ;;
                            API-IC-10[6-8]-IT|API-IC-11[0-1]-IT|API-IC-113-IT|API-IC-114-IT) P1_PASSED+=("$test_id") ;;
                            API-IC-107-IT) P2_PASSED+=("$test_id") ;;
                        esac
                    fi
                fi
            fi
        fi
    done < <(grep -E "PASSED" "$output_file" || true)
    
    # Parse FAILED tests with detailed error information
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            # Extract method name from line
            local method=$(echo "$line" | sed -E 's/.*::(test_[a-zA-Z_]+).*/\1/')
            if [ -n "$method" ]; then
                local test_id=$(map_test_method_to_id "$method")
                if [ -n "$test_id" ]; then
                    # Check if test_id is already in arrays to avoid duplicates
                    if [[ ! " ${FAILED_TESTS[*]} " =~ " $test_id " ]]; then
                        FAILED_TESTS+=("$test_id")
                        INTEGRATION_FAILED+=("$test_id")
                    
                        # Log failed test with clear ID mapping
                        log_message "BATCH TEST FAILED: $test_id → $method"
                        
                        # Extract error details from the batch log
                        local error_section=$(grep -A 20 "FAILURES" "$output_file" | grep -A 15 "$method" || true)
                        if [ -n "$error_section" ]; then
                            log_message "Error details for $test_id:"
                            echo "$error_section" | head -10 | while IFS= read -r error_line; do
                                log_message "  $error_line"
                            done
                        fi
                        
                        # Categorize by priority
                        case "$test_id" in
                            API-IC-10[1-5]-IT|API-IC-109-IT|API-IC-112-IT) P0_FAILED+=("$test_id") ;;
                            API-IC-10[6-8]-IT|API-IC-11[0-1]-IT|API-IC-113-IT|API-IC-114-IT) P1_FAILED+=("$test_id") ;;
                            API-IC-107-IT) P2_FAILED+=("$test_id") ;;
                        esac
                    fi
                fi
            fi
        fi
    done < <(grep -E "FAILED" "$output_file" || true)
    
    # Log summary of parsed results
    log_message "Parsed results - Passed: ${#INTEGRATION_PASSED[@]}, Failed: ${#INTEGRATION_FAILED[@]}"
    
    # If we have failures, extract the complete failure summary to the main log
    if [ ${#INTEGRATION_FAILED[@]} -gt 0 ]; then
        log_message "=== INTEGRATION TEST FAILURES SUMMARY ==="
        
        # Extract the FAILURES section from the batch log
        local failures_section=$(sed -n '/=== FAILURES ===/,/===.*warnings summary.*===/p' "$output_file" || true)
        if [ -n "$failures_section" ]; then
            log_message "Complete failure details:"
            echo "$failures_section" | head -50 | while IFS= read -r line; do
                log_message "  $line"
            done
        fi
        
        # Also extract the test result summary line
        local result_summary=$(grep -E "[0-9]+ failed.*[0-9]+ passed" "$output_file" | tail -1 || true)
        if [ -n "$result_summary" ]; then
            log_message "Test result summary: $result_summary"
        fi
    fi
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Index Calculation Unit & Integration 測試報告"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: Index Calculation test specifications"
    # Calculate total tests for display
    local display_total_tests=$(( ${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]} ))
    echo "測試總數: $display_total_tests 個測試案例 (已執行)"
    echo "執行環境: $(python --version 2>&1 | cut -d' ' -f2)"
    echo "總執行時間: ${total_duration}s"
    echo "日誌檔案: $(basename "$LOG_FILE")"
    echo
    
    # Log the full report
    log_message "=== FINAL REPORT ==="
    log_message "Total Duration: ${total_duration}s"
    log_message "Total Tests: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))"
    log_message "Passed: ${#PASSED_TESTS[@]}"
    log_message "Failed: ${#FAILED_TESTS[@]}"
    log_message "Skipped: ${#SKIPPED_TESTS[@]}"
    
    # Test summary (use the same calculation as above)
    local total_tests=$display_total_tests
    local pass_rate=0
    if [ $total_tests -gt 0 ]; then
        pass_rate=$(( ${#PASSED_TESTS[@]} * 100 / total_tests ))
    fi
    
    echo "測試檔案清單"
    echo "------------"
    echo "單元測試 (10個測試):"
    echo "  - test/unit/test_index_calculation_v2.py"
    echo ""
    echo "整合測試 (14個測試):"
    echo "  - test/integration/test_index_calculation_v2_api.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests (規格期望: 24)"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed test type statistics
    echo "測試類型統計"
    echo "------------"
    local unit_total=$((${#UNIT_PASSED[@]} + ${#UNIT_FAILED[@]}))
    local integration_total=$((${#INTEGRATION_PASSED[@]} + ${#INTEGRATION_FAILED[@]}))
    
    local unit_rate=0
    local integration_rate=0
    
    if [ $unit_total -gt 0 ]; then
        unit_rate=$(( ${#UNIT_PASSED[@]} * 100 / unit_total ))
    fi
    if [ $integration_total -gt 0 ]; then
        integration_rate=$(( ${#INTEGRATION_PASSED[@]} * 100 / integration_total ))
    fi
    
    echo "單元測試 (Unit): ${#UNIT_PASSED[@]}/${unit_total} (${unit_rate}%) - 規格要求: 10"
    echo "整合測試 (Integration): ${#INTEGRATION_PASSED[@]}/${integration_total} (${integration_rate}%) - 規格期望: 14"
    echo
    
    # Priority statistics
    echo "優先級統計"
    echo "----------"
    
    local p0_total=$((${#P0_PASSED[@]} + ${#P0_FAILED[@]}))
    local p1_total=$((${#P1_PASSED[@]} + ${#P1_FAILED[@]}))
    local p2_total=$((${#P2_PASSED[@]} + ${#P2_FAILED[@]}))
    
    local p0_rate=0
    local p1_rate=0
    local p2_rate=0
    
    if [ $p0_total -gt 0 ]; then
        p0_rate=$(( ${#P0_PASSED[@]} * 100 / p0_total ))
    fi
    if [ $p1_total -gt 0 ]; then
        p1_rate=$(( ${#P1_PASSED[@]} * 100 / p1_total ))
    fi
    if [ $p2_total -gt 0 ]; then
        p2_rate=$(( ${#P2_PASSED[@]} * 100 / p2_total ))
    fi
    
    echo "P0 (Critical): ${#P0_PASSED[@]}/${p0_total} (${p0_rate}%)"
    echo "P1 (Important): ${#P1_PASSED[@]}/${p1_total} (${p1_rate}%)"
    echo "P2 (Nice to have): ${#P2_PASSED[@]}/${p2_total} (${p2_rate}%)"
    echo
    
    # Detailed table
    echo "=== 詳細測試統計表 ==="
    echo
    echo "| 測試類型     | 通過/總數 | 成功率 | 失敗測試案例 |"
    echo "|--------------|-----------|--------|--------------|"
    # Format failed tests for better readability
    local unit_failed_display=""
    local integration_failed_display=""
    
    if [ ${#UNIT_FAILED[@]} -gt 0 ]; then
        unit_failed_display=$(printf "%s, " "${UNIT_FAILED[@]}")
        unit_failed_display=${unit_failed_display%, }  # Remove trailing comma
    else
        unit_failed_display="無"
    fi
    
    if [ ${#INTEGRATION_FAILED[@]} -gt 0 ]; then
        integration_failed_display=$(printf "%s, " "${INTEGRATION_FAILED[@]}")
        integration_failed_display=${integration_failed_display%, }  # Remove trailing comma
    else
        integration_failed_display="無"
    fi
    
    echo "| 單元測試     | ${#UNIT_PASSED[@]}/${unit_total} | ${unit_rate}% | ${unit_failed_display} |"
    echo "| 整合測試     | ${#INTEGRATION_PASSED[@]}/${integration_total} | ${integration_rate}% | ${integration_failed_display} |"
    echo "| **總計**     | **${#PASSED_TESTS[@]}/${total_tests}** | **${pass_rate}%** | $([ ${#FAILED_TESTS[@]} -gt 0 ] && printf "%s, " "${FAILED_TESTS[@]}" | sed 's/, $//' || echo "無") |"
    echo
    
    # Add integration test batch log reference if there are failures
    if [ ${#INTEGRATION_FAILED[@]} -gt 0 ]; then
        echo "🔍 **Integration 測試詳細錯誤資訊**:"
        echo "   - 批次日誌檔案: $(basename "${LOG_DIR}/test_suite_index_calculation_unit_integration_${TIMESTAMP}_batch.log")"
        echo "   - 失敗測試數: ${#INTEGRATION_FAILED[@]} / ${integration_total}"
        echo
    fi
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例詳情:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            local priority=$(get_test_priority "$test_id")
            if [[ "$test_id" == *"-IT" ]]; then
                # Integration test - refer to batch log
                echo "❌ $test_id ($priority) - 詳見批次日誌: test_suite_index_calculation_unit_integration_${TIMESTAMP}_batch.log"
            else
                # Unit test - has individual log
                echo "❌ $test_id ($priority) - 日誌: $LOG_DIR/test_${test_id}_*.log"
            fi
        done
        echo
        echo "修復建議:"
        echo "1. 檢查測試驗證報告中的已知問題"
        echo "2. 運行單一失敗測試進行詳細調試:"
        echo "   - Unit Test: pytest test/unit/test_index_calculation_v2.py::TestIndexCalculationV2Unit::test_method -v"
        echo "   - Integration Test: pytest test/integration/test_index_calculation_v2_api.py::TestIndexCalculationV2Integration::test_method -v"
        echo "3. 檢查 mock 設定是否正確"
        echo "4. 參考 CLAUDE.md 中的依賴配置指南"
        if [ ${#INTEGRATION_FAILED[@]} -gt 0 ]; then
            echo "5. Integration Test 錯誤詳情請查看批次日誌檔案"
        fi
        echo
    fi
    
    # Individual Test Results Summary Table
    echo "=== 個別測試結果摘要 ==="
    echo
    echo "| Test ID | 狀態 | 類型 | 優先級 | 測試名稱 |"
    echo "|---------|------|------|--------|----------|"
    
    # Show unit tests
    for test_id in API-IC-001-UT API-IC-002-UT API-IC-003-UT API-IC-004-UT API-IC-005-UT API-IC-006-UT API-IC-007-UT API-IC-008-UT API-IC-009-UT API-IC-010-UT; do
        local status="❌ FAIL"
        local found=false
        for passed_test in "${UNIT_PASSED[@]}"; do
            if [ "$passed_test" = "$test_id" ]; then
                status="✅ PASS"
                found=true
                break
            fi
        done
        if [ "$found" = false ]; then
            for failed_test in "${UNIT_FAILED[@]}"; do
                if [ "$failed_test" = "$test_id" ]; then
                    found=true
                    break
                fi
            done
        fi
        if [ "$found" = false ]; then
            status="⏭️  SKIP"
        fi
        
        local priority=$(get_test_priority "$test_id")
        local test_name=$(get_test_name "$test_id")
        echo "| $test_id | $status | Unit | $priority | $test_name |"
    done
    
    # Show integration tests (all 14 expected tests)
    for test_id in API-IC-101-IT API-IC-102-IT API-IC-103-IT API-IC-104-IT API-IC-105-IT API-IC-106-IT API-IC-107-IT API-IC-108-IT API-IC-109-IT API-IC-110-IT API-IC-111-IT API-IC-112-IT API-IC-113-IT API-IC-114-IT; do
        local status="❌ FAIL"
        local found=false
        for passed_test in "${INTEGRATION_PASSED[@]}"; do
            if [ "$passed_test" = "$test_id" ]; then
                status="✅ PASS"
                found=true
                break
            fi
        done
        if [ "$found" = false ]; then
            for failed_test in "${INTEGRATION_FAILED[@]}"; do
                if [ "$failed_test" = "$test_id" ]; then
                    found=true
                    break
                fi
            done
        fi
        if [ "$found" = false ]; then
            status="⏭️  SKIP"
        fi
        
        local priority=$(get_test_priority "$test_id")
        local test_name=$(get_test_name "$test_id")
        echo "| $test_id | $status | Integration | $priority | $test_name |"
    done
    
    echo
    echo "**說明**: 整合測試檔案包含完整的 14 個測試函數 (API-IC-101-IT 到 API-IC-114-IT)"
    echo
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        echo -e "🎉 ${GREEN}所有 $total_tests 個 Index Calculation Unit & Integration 測試全部通過！${NC}"
        echo "   所有測試都使用 mock services，無需 Azure OpenAI API"
    else
        echo -e "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
        if [ ${#P0_FAILED[@]} -gt 0 ]; then
            echo "   ⚠️  有 ${#P0_FAILED[@]} 個 P0 (Critical) 測試失敗，需要優先修復"
        fi
    fi
}

# Main execution
main() {
    # Change to project root
    cd "$(dirname "$0")/../.."
    
    # Use virtual environment Python if available
    local python_cmd="python"
    if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
        python_cmd="venv/bin/python"
    fi
    
    # Initialize logging
    manage_log_files
    log_message "=== Index Calculation Unit & Integration Test Suite Started ==="
    log_message "Based on Index Calculation test specifications"
    log_message "Python version: $(python --version 2>&1)"
    log_message "Stage execution: ${STAGE_EXEC:-all}"
    log_environment_info
    
    echo -e "\${BLUE}=== Index Calculation Unit & Integration Test Suite (24 tests available) ===\${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "Based on: Index Calculation test specifications"
    echo "Note: These tests use mocked services (no real API calls)"
    echo
    
    echo -e "${BLUE}Environment Check${NC}"
    if [ -f ".env" ]; then
        echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
        log_message "Environment: .env file found"
    else
        echo -e "  Environment: ${YELLOW}⚠ .env file not found (not required for mock tests)${NC}"
        log_message "WARNING: .env file not found, but not required for mock tests"
    fi
    echo -e "  Python: $(python --version 2>&1)"
    echo -e "  Working Directory: $(pwd)"
    echo
    
    # Execute based on stage or run all tests
    case "$STAGE_EXEC" in
        "unit")
            run_unit_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "")
            # Run all tests in order
            run_unit_tests
            run_integration_tests
            ;;
        *)
            echo -e "${RED}Unknown stage: $STAGE_EXEC${NC}"
            echo "Valid stages: unit, integration"
            exit 1
            ;;
    esac
    
    # Generate detailed report
    generate_report
    
    # Log detailed test summary
    log_message "=== DETAILED TEST SUMMARY ==="
    log_message "Total Tests Executed: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
    log_message "Unit Tests - Passed: ${#UNIT_PASSED[@]}, Failed: ${#UNIT_FAILED[@]}"
    log_message "Integration Tests - Passed: ${#INTEGRATION_PASSED[@]}, Failed: ${#INTEGRATION_FAILED[@]}"
    log_message "P0 Priority - Passed: ${#P0_PASSED[@]}, Failed: ${#P0_FAILED[@]}"
    log_message "P1 Priority - Passed: ${#P1_PASSED[@]}, Failed: ${#P1_FAILED[@]}"
    log_message "P2 Priority - Passed: ${#P2_PASSED[@]}, Failed: ${#P2_FAILED[@]}"
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        log_message "=== FAILED TESTS DETAILS ==="
        for test_id in "${FAILED_TESTS[@]}"; do
            log_message "FAILED: $test_id"
            # Log last few lines of error from individual test logs
            local error_log=$(ls -t "$LOG_DIR"/test_${test_id}_*.log 2>/dev/null | head -1)
            if [ -f "$error_log" ]; then
                log_message "Error snippet from $test_id:"
                tail -5 "$error_log" | while IFS= read -r line; do
                    log_message "  $line"
                done
            fi
        done
    fi
    
    log_message "=== Test Suite Completed ==="
    
    # Final result determination
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All Index Calculation Unit & Integration tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Execute main function
main