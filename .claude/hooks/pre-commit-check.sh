#!/bin/bash
# UserPromptSubmit hook: Commit 前的完整檢查
# 當使用者提到 commit 時觸發

# 確保在正確的工作目錄
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# Global variables for collecting test results
SCRIPT_START_TIME=$(date +%s.%N)

# Variables to store test results (using regular variables instead of associative arrays for compatibility)
SERVICE_LANGUAGE_DETECTION=""
SERVICE_PROMPT_MGMT=""
SERVICE_KEYWORD_SERVICE=""
SERVICE_LLM_FACTORY=""
HEALTH_UT=""
HEALTH_IT=""
INDEX_UT=""
INDEX_IT=""
GAP_UT=""
GAP_IT=""

# Variables to store failed test IDs for error reporting
FAILED_SERVICE_TESTS=""
FAILED_HEALTH_UT_TESTS=""
FAILED_HEALTH_IT_TESTS=""
FAILED_INDEX_UT_TESTS=""
FAILED_INDEX_IT_TESTS=""
FAILED_GAP_UT_TESTS=""
FAILED_GAP_IT_TESTS=""

# Variables to track overall test results
OVERALL_TEST_FAILED=false
RUFF_FAILED=false
SERVICE_TESTS_FAILED=false
HEALTH_TESTS_FAILED=false
INDEX_TESTS_FAILED=false
GAP_TESTS_FAILED=false

# Variables to track execution time for each step
RUFF_START_TIME=""
RUFF_END_TIME=""
RUFF_DURATION=""
SERVICE_START_TIME=""
SERVICE_END_TIME=""
SERVICE_DURATION=""
HEALTH_START_TIME=""
HEALTH_END_TIME=""
HEALTH_DURATION=""
INDEX_START_TIME=""
INDEX_END_TIME=""
INDEX_DURATION=""
GAP_START_TIME=""
GAP_END_TIME=""
GAP_DURATION=""

# Function to calculate test execution time
calculate_test_time() {
    local start_time="$1"
    local end_time="$2"
    echo "$end_time - $start_time" | bc -l | xargs printf "%.1f"
}

# Function to parse service module test results
parse_service_module_results() {
    local log_file="/tmp/test_service_modules.log"
    
    if [ -f "$log_file" ]; then
        # Parse each line from the log file after the summary section
        while read -r line; do
            # Skip empty lines and table separators
            if [[ -z "$line" ]] || [[ "$line" =~ ^[\|+\-=[:space:]]*$ ]]; then
                continue
            fi
            
            # Clean ANSI color codes
            clean_line=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g')
            
            # Check for module lines with pattern: | 語言檢測 | 14 | 0 | 14 | ✅ |
            if [[ "$clean_line" =~ ^\|[[:space:]]*([^|]+)[[:space:]]*\|[[:space:]]*([0-9]+)[[:space:]]*\|[[:space:]]*([0-9]+)[[:space:]]*\|[[:space:]]*([0-9]+)[[:space:]]*\| ]]; then
                local module="${BASH_REMATCH[1]}"
                local passed="${BASH_REMATCH[2]}"
                local failed="${BASH_REMATCH[3]}"
                
                # Trim whitespace
                module=$(echo "$module" | xargs)
                
                # Check if it's one of our target modules and store results
                case "$module" in
                    "語言檢測")
                        SERVICE_LANGUAGE_DETECTION="${passed}:${failed}"
                        ;;
                    "Prompt管理")
                        SERVICE_PROMPT_MGMT="${passed}:${failed}"
                        ;;
                    "關鍵字服務")
                        SERVICE_KEYWORD_SERVICE="${passed}:${failed}"
                        ;;
                    "LLM Factory")
                        SERVICE_LLM_FACTORY="${passed}:${failed}"
                        ;;
                esac
            fi
        done < <(grep -A 20 "測試結果摘要" "$log_file" 2>/dev/null)
    fi
}

# Function to parse pytest output for UT/IT breakdown
parse_pytest_results() {
    local log_file="$1"
    local prefix="$2"
    
    if [ -f "$log_file" ]; then
        local ut_passed=0
        local ut_failed=0 
        local it_passed=0
        local it_failed=0
        local failed_ut_ids=""
        local failed_it_ids=""
        local ut_total_time=0
        local it_total_time=0
        
        # First pass: Parse individual test execution times and calculate real UT/IT times
        local current_section=""
        while read -r line; do
            # Clean ANSI color codes
            clean_line=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g')
            
            # Track which section we're in - handle different log formats
            if [[ "$clean_line" =~ "Unit Tests" ]]; then
                current_section="UT"
            elif [[ "$clean_line" =~ "Integration Tests" ]]; then
                current_section="IT"
            fi
            
            # Extract individual test times: "✓ PASSED (2s)" or "✗ FAILED (1s)"
            if [[ "$clean_line" =~ (✓|✗)[[:space:]]*(PASSED|FAILED)[[:space:]]*\(([0-9]+)s\) ]]; then
                local test_time="${BASH_REMATCH[3]}"
                if [[ "$current_section" == "UT" ]]; then
                    ut_total_time=$((ut_total_time + test_time))
                    if [[ "$clean_line" =~ PASSED ]]; then
                        ut_passed=$((ut_passed + 1))
                    else
                        ut_failed=$((ut_failed + 1))
                    fi
                elif [[ "$current_section" == "IT" ]]; then
                    it_total_time=$((it_total_time + test_time))
                    if [[ "$clean_line" =~ PASSED ]]; then
                        it_passed=$((it_passed + 1))
                    else
                        it_failed=$((it_failed + 1))
                    fi
                fi
            fi
            
            # Handle batch test results: "✓ Batch test completed (3s)" + "Results: 14 passed, 0 failed"
            if [[ "$clean_line" =~ "Batch test completed".*\(([0-9]+)s\) ]] && [[ "$current_section" == "IT" ]]; then
                local batch_time="${BASH_REMATCH[1]}"
                it_total_time=$((it_total_time + batch_time))
            fi
            
            # Handle Gap Analysis format: "Test Results: (17s)"
            if [[ "$clean_line" =~ "Test Results:".*\(([0-9]+)s\) ]] && [[ "$current_section" == "IT" ]]; then
                local gap_batch_time="${BASH_REMATCH[1]}"
                it_total_time=$((it_total_time + gap_batch_time))
            fi
            
            # Parse batch results: "Results: 14 passed, 0 failed" or "Total: 27 passed, 0 failed"
            if [[ "$clean_line" =~ (Results:|Total:)[[:space:]]*([0-9]+)[[:space:]]*passed,[[:space:]]*([0-9]+)[[:space:]]*failed ]] && [[ "$current_section" == "IT" ]]; then
                it_passed=$((it_passed + ${BASH_REMATCH[2]}))
                it_failed=$((it_failed + ${BASH_REMATCH[3]}))
            fi
        done < "$log_file"
        
        # Second pass: If there are failures, collect failed test IDs
        if [ "$ut_failed" -gt 0 ] || [ "$it_failed" -gt 0 ]; then
            while read -r line; do
                # Clean ANSI color codes
                clean_line=$(echo "$line" | sed 's/\x1b\[[0-9;]*m//g')
                
                # Look for failed test patterns from the test summary section
                if [[ "$clean_line" =~ ^[[:space:]]*-[[:space:]]+(API-[A-Z]+-[0-9]+-[UT|IT]+) ]]; then
                    local test_id="${BASH_REMATCH[1]}"
                    if [[ "$test_id" =~ -UT ]]; then
                        failed_ut_ids="${failed_ut_ids}${test_id} "
                    elif [[ "$test_id" =~ -IT ]]; then
                        failed_it_ids="${failed_it_ids}${test_id} "
                    fi
                fi
            done < "$log_file"
        fi
        
        # Store results based on prefix
        case "$prefix" in
            "health")
                HEALTH_UT="${ut_passed}:${ut_failed}:${ut_total_time}"
                HEALTH_IT="${it_passed}:${it_failed}:${it_total_time}"
                FAILED_HEALTH_UT_TESTS="$failed_ut_ids"
                FAILED_HEALTH_IT_TESTS="$failed_it_ids"
                ;;
            "index")
                INDEX_UT="${ut_passed}:${ut_failed}:${ut_total_time}"
                INDEX_IT="${it_passed}:${it_failed}:${it_total_time}"
                FAILED_INDEX_UT_TESTS="$failed_ut_ids"
                FAILED_INDEX_IT_TESTS="$failed_it_ids"
                ;;
            "gap")
                GAP_UT="${ut_passed}:${ut_failed}:${ut_total_time}"
                GAP_IT="${it_passed}:${it_failed}:${it_total_time}"
                FAILED_GAP_UT_TESTS="$failed_ut_ids"
                FAILED_GAP_IT_TESTS="$failed_it_ids"
                ;;
        esac
    fi
}

# Function to calculate test execution time
calculate_test_time() {
    local start_time="$1"
    local end_time="$2"
    echo "$end_time - $start_time" | bc -l | xargs printf "%.1f"
}

# Function to generate comprehensive summary table
generate_summary_table() {
    # Parse all test results
    parse_service_module_results
    parse_pytest_results "/tmp/test_health_keyword.log" "health"
    parse_pytest_results "/tmp/test_index_calc.log" "index"
    parse_pytest_results "/tmp/test_gap_analysis.log" "gap"
    
    # Calculate totals
    local total_passed=0
    local total_failed=0
    local total_time=$(calculate_test_time "$SCRIPT_START_TIME" "$(date +%s.%N)")
    
    # Header
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                    Pre-commit 完整測試報告                         ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 測試統計總覽"
    echo "═══════════════════════════════════════════════════════════════════"
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "測試分類" "通過" "失敗" "總計" "耗時" "狀態"
    echo "|----------------------------|-------|-------|-------|--------|------|"
    
    # Ruff check
    local ruff_status="✅"
    [ "$RUFF_FAILED" = true ] && ruff_status="❌"
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |
" "🔍 Ruff 檢查" "$ruff_status" "-" "-" "${RUFF_DURATION}s" "$ruff_status"
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "" "" "" "" "" ""
    
    # Service modules
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "🏗️ 服務模組測試" "" "" "" "" ""
    
    # Service module details
    for module_info in "語言檢測:$SERVICE_LANGUAGE_DETECTION" "Prompt管理:$SERVICE_PROMPT_MGMT" "關鍵字服務:$SERVICE_KEYWORD_SERVICE" "LLM Factory:$SERVICE_LLM_FACTORY"; do
        IFS=':' read -r module_name result rest <<< "$module_info"
        if [[ -n "$result" && -n "$rest" ]]; then
            local passed="$result"
            local failed="$rest"
            
            # Ensure numeric values with defaults
            passed=${passed:-0}
            failed=${failed:-0}
            
            if [[ "$passed" =~ ^[0-9]+$ ]] && [[ "$failed" =~ ^[0-9]+$ ]]; then
                local total=$((passed + failed))
                local status="✅"
                [ "$failed" -gt 0 ] && status="❌"
                
                printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "  ├─ $module_name" "$passed" "$failed" "$total" "0.4s" "$status"
                
                total_passed=$((total_passed + passed))
                total_failed=$((total_failed + failed))
            fi
        fi
    done
    
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "" "" "" "" "" ""
    
    # API tests
    for category in "🩺 Health & Keyword" "🧮 Index Calculation" "📈 Gap Analysis"; do
        local prefix=""
        case "$category" in
            *"Health"*) prefix="health" ;;
            *"Index"*) prefix="index" ;;
            *"Gap"*) prefix="gap" ;;
        esac
        
        printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "$category" "" "" "" "" ""
        
        # UT and IT breakdown
        for type in "UT" "IT"; do
            local result=""
            case "${prefix}_${type}" in
                "health_UT") result="$HEALTH_UT" ;;
                "health_IT") result="$HEALTH_IT" ;;
                "index_UT") result="$INDEX_UT" ;;
                "index_IT") result="$INDEX_IT" ;;
                "gap_UT") result="$GAP_UT" ;;
                "gap_IT") result="$GAP_IT" ;;
            esac
            
            if [[ -n "$result" ]]; then
                IFS=':' read -r passed failed actual_time <<< "$result"
                
                # Ensure numeric values with defaults
                passed=${passed:-0}
                failed=${failed:-0}
                actual_time=${actual_time:-0}
                
                # Only process if not zero values
                if [[ "$passed" =~ ^[0-9]+$ ]] && [[ "$failed" =~ ^[0-9]+$ ]]; then
                    local total=$((passed + failed))
                    local status="✅"
                    [ "$failed" -gt 0 ] && status="❌"
                    
                    local type_label=""
                    [ "$type" = "UT" ] && type_label="單元測試 (UT)" || type_label="整合測試 (IT)"
                    
                    # Use the real execution time from test logs
                    local type_time="${actual_time}s"
                    
                    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |
" "  ├─ $type_label" "$passed" "$failed" "$total" "$type_time" "$status"
                    
                    total_passed=$((total_passed + passed))
                    total_failed=$((total_failed + failed))
                fi
            fi
        done
        
        printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "" "" "" "" "" ""
    done
    
    # Total row
    local total_tests=$((total_passed + total_failed))
    local overall_status="✅"
    [ "$total_failed" -gt 0 ] && overall_status="❌"
    
    echo "|----------------------------|-------|-------|-------|--------|------|"
    printf "| %-26s | %-5s | %-5s | %-5s | %-6s | %-4s |\n" "🎯 總計" "$total_passed" "$total_failed" "$total_tests" "${total_time}s" "$overall_status"
    echo "═══════════════════════════════════════════════════════════════════"
    
    # Final message
    if [ "$total_failed" -eq 0 ]; then
        echo ""
        echo "🏆 所有檢查通過！代碼品質優良，準備提交。"
    else
        echo ""
        echo "❌ 發現 $total_failed 個測試失敗，無法提交"
        echo ""
        
        # Show detailed failed test information
        echo "🔍 失敗測試詳細資訊"
        echo "═══════════════════════════════════════════════════════════════════"
        
        local has_failed_tests=false
        
        # Health & Keyword failures
        if [[ -n "$FAILED_HEALTH_UT_TESTS" || -n "$FAILED_HEALTH_IT_TESTS" ]]; then
            echo "🩺 Health & Keyword 失敗測試:"
            [[ -n "$FAILED_HEALTH_UT_TESTS" ]] && echo "   ├─ 單元測試: $FAILED_HEALTH_UT_TESTS"
            [[ -n "$FAILED_HEALTH_IT_TESTS" ]] && echo "   ├─ 整合測試: $FAILED_HEALTH_IT_TESTS"
            has_failed_tests=true
        fi
        
        # Index Calculation failures
        if [[ -n "$FAILED_INDEX_UT_TESTS" || -n "$FAILED_INDEX_IT_TESTS" ]]; then
            echo "🧮 Index Calculation 失敗測試:"
            [[ -n "$FAILED_INDEX_UT_TESTS" ]] && echo "   ├─ 單元測試: $FAILED_INDEX_UT_TESTS"
            [[ -n "$FAILED_INDEX_IT_TESTS" ]] && echo "   ├─ 整合測試: $FAILED_INDEX_IT_TESTS"
            has_failed_tests=true
        fi
        
        # Gap Analysis failures
        if [[ -n "$FAILED_GAP_UT_TESTS" || -n "$FAILED_GAP_IT_TESTS" ]]; then
            echo "📈 Gap Analysis 失敗測試:"
            [[ -n "$FAILED_GAP_UT_TESTS" ]] && echo "   ├─ 單元測試: $FAILED_GAP_UT_TESTS"
            [[ -n "$FAILED_GAP_IT_TESTS" ]] && echo "   ├─ 整合測試: $FAILED_GAP_IT_TESTS"
            has_failed_tests=true
        fi
        
        # Service modules - simplified failure reporting
        local service_failures=""
        [[ "$SERVICE_LANGUAGE_DETECTION" =~ :([1-9][0-9]*) ]] && service_failures="${service_failures}語言檢測 "
        [[ "$SERVICE_PROMPT_MGMT" =~ :([1-9][0-9]*) ]] && service_failures="${service_failures}Prompt管理 "
        [[ "$SERVICE_KEYWORD_SERVICE" =~ :([1-9][0-9]*) ]] && service_failures="${service_failures}關鍵字服務 "
        [[ "$SERVICE_LLM_FACTORY" =~ :([1-9][0-9]*) ]] && service_failures="${service_failures}LLM_Factory "
        
        if [[ -n "$service_failures" ]]; then
            echo "🏗️ 服務模組失敗: $service_failures"
            has_failed_tests=true
        fi
        
        if [ "$has_failed_tests" = false ]; then
            echo "⚠️  無法獲取詳細失敗資訊，請檢查測試日誌。"
        fi
        
        echo ""
        echo "📋 建議修復步驟:"
        echo "1. 查看詳細日誌檔案"
        echo "2. 修復失敗的測試"
        echo "3. 重新執行測試確認修復"
        echo "4. 再次嘗試提交"
    fi
}

echo ""
echo "🚨 Pre-commit validation starting..."
echo "=" 
echo ""

# 1. Ruff 檢查
echo "📝 Step 1/5: Running Ruff check..."
echo "Checking src/ and test/ directories"

RUFF_START_TIME=$(date +%s.%N)
RUFF_ERRORS=$(ruff check src/ test/ --line-length=120 2>&1)
RUFF_EXIT_CODE=$?
RUFF_END_TIME=$(date +%s.%N)
RUFF_DURATION=$(calculate_test_time "$RUFF_START_TIME" "$RUFF_END_TIME")

if [ $RUFF_EXIT_CODE -ne 0 ]; then
    echo "❌ Ruff check FAILED"
    RUFF_FAILED=true
    OVERALL_TEST_FAILED=true
else
    echo "✅ Ruff check passed"
fi

echo ""

# 2. Service Modules 測試
echo "📝 Step 2/5: Running Service Modules tests..."
SERVICE_START_TIME=$(date +%s.%N)
if ./test/scripts/run_service_modules_tests_final.sh > /tmp/test_service_modules.log 2>&1; then
    echo "✅ Service Modules tests passed"
else
    echo "❌ Service Modules tests FAILED"
    SERVICE_TESTS_FAILED=true
    OVERALL_TEST_FAILED=true
fi
SERVICE_END_TIME=$(date +%s.%N)
SERVICE_DURATION=$(calculate_test_time "$SERVICE_START_TIME" "$SERVICE_END_TIME")

echo ""

# 3. Health & Keyword 測試
echo "📝 Step 3/5: Running Health & Keyword tests..."
HEALTH_START_TIME=$(date +%s.%N)
if ./test/scripts/run_health_keyword_unit_integration.sh > /tmp/test_health_keyword.log 2>&1; then
    echo "✅ Health & Keyword tests passed"
else
    echo "❌ Health & Keyword tests FAILED"
    HEALTH_TESTS_FAILED=true
    OVERALL_TEST_FAILED=true
fi
HEALTH_END_TIME=$(date +%s.%N)
HEALTH_DURATION=$(calculate_test_time "$HEALTH_START_TIME" "$HEALTH_END_TIME")

echo ""

# 4. Index Calculation 測試
echo "📝 Step 4/5: Running Index Calculation tests..."
INDEX_START_TIME=$(date +%s.%N)
if ./test/scripts/run_index_calculation_unit_integration.sh > /tmp/test_index_calc.log 2>&1; then
    echo "✅ Index Calculation tests passed"
else
    echo "❌ Index Calculation tests FAILED"
    INDEX_TESTS_FAILED=true
    OVERALL_TEST_FAILED=true
fi
INDEX_END_TIME=$(date +%s.%N)
INDEX_DURATION=$(calculate_test_time "$INDEX_START_TIME" "$INDEX_END_TIME")

echo ""

# 5. Gap Analysis 測試
echo "📝 Step 5/5: Running Gap Analysis tests..."
GAP_START_TIME=$(date +%s.%N)
if ./test/scripts/run_index_cal_gap_analysis_unit_integration.sh > /tmp/test_gap_analysis.log 2>&1; then
    echo "✅ Gap Analysis tests passed"
else
    echo "❌ Gap Analysis tests FAILED"
    GAP_TESTS_FAILED=true
    OVERALL_TEST_FAILED=true
fi
GAP_END_TIME=$(date +%s.%N)
GAP_DURATION=$(calculate_test_time "$GAP_START_TIME" "$GAP_END_TIME")

echo ""
echo "="

# Generate comprehensive summary table
generate_summary_table

echo ""

# Final decision based on overall test results
if [ "$OVERALL_TEST_FAILED" = true ]; then
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix test failures first"
    
    # Show specific failure details for quick reference
    if [ "$RUFF_FAILED" = true ]; then
        echo ""
        echo "📌 Ruff errors need to be fixed:"
        echo "$RUFF_ERRORS"
        echo ""
        echo "To fix: ruff check src/ test/ --fix --line-length=120"
    fi
    
    echo ""
    echo "🔧 Next steps:"
    echo "1. Fix the failed tests shown in the summary above"
    echo "2. Run individual test suites to verify fixes"
    echo "3. Re-run this pre-commit check"
    echo "4. Once all tests pass, try committing again"
    
    exit 1
else
    echo "🏆 All checks passed! Ready to commit."
fi