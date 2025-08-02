#!/bin/bash

# Index Calculation V2 測試執行腳本
# 產生測試摘要表和詳細報告

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
declare -A test_results
declare -A test_times
declare -A test_priorities

# 測試 ID 和優先級定義
declare -A test_registry=(
    ["test_calculate_index_with_cache_hit"]="IC-UNIT-002,IC-UNIT-003|P0"
    ["test_calculate_index_with_cache_miss"]="IC-UNIT-005|P0"
    ["test_cache_key_generation"]="IC-UNIT-002|P0"
    ["test_cache_expiration"]="IC-UNIT-003|P1"
    ["test_lru_eviction"]="IC-UNIT-004|P1"
    ["test_cache_statistics"]="IC-UNIT-001|P0"
    ["test_parallel_execution"]="IC-UNIT-009|P0"
    ["test_parallel_error_handling"]="IC-UNIT-010|P1"
    ["test_python311_taskgroup"]="IC-UNIT-010|P1"
    ["test_successful_calculation"]="IC-INT-001|P0"
    ["test_cache_header_behavior"]="IC-INT-002|P0"
    ["test_validation_errors"]="IC-INT-003|P0"
    ["test_external_service_failure"]="IC-INT-004|P0"
    ["test_response_time_baseline"]="IC-PERF-001|P0"
    ["test_concurrent_load"]="IC-PERF-003|P0"
)

# Logging function
log() {
    echo -e "$1" | tee -a test_report.log
}

# Execute single test and track results
run_test() {
    local test_name=$1
    local test_path=$2
    local start_time=$(date +%s)
    
    # Get test ID and priority
    local test_info=${test_registry[$test_name]:-"UNKNOWN|P2"}
    local test_id=${test_info%|*}
    local priority=${test_info#*|}
    
    if pytest "$test_path::$test_name" -v > /tmp/${test_name}.log 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        test_results[$test_name]="PASSED"
        test_times[$test_name]=$duration
        test_priorities[$test_name]=$priority
        log "  ${GREEN}✓${NC} $test_name [$test_id] ($priority) - ${duration}s"
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        test_results[$test_name]="FAILED"
        test_times[$test_name]=$duration
        test_priorities[$test_name]=$priority
        log "  ${RED}✗${NC} $test_name [$test_id] ($priority) - ${duration}s"
        
        # Show error details
        tail -n 20 /tmp/${test_name}.log | sed 's/^/    /' >> test_report.log
    fi
}

# Generate test summary table
generate_summary() {
    log "
${BLUE}=== 測試摘要表 ===${NC}
"
    log "| 測試類型 | P0 通過/失敗 | P1 通過/失敗 | P2 通過/失敗 | 總計 |"
    log "|----------|-------------|-------------|-------------|------|"
    
    # Count by type and priority
    local unit_p0_pass=0 unit_p0_fail=0
    local unit_p1_pass=0 unit_p1_fail=0
    local unit_p2_pass=0 unit_p2_fail=0
    local int_p0_pass=0 int_p0_fail=0
    local int_p1_pass=0 int_p1_fail=0
    local int_p2_pass=0 int_p2_fail=0
    local perf_p0_pass=0 perf_p0_fail=0
    local perf_p1_pass=0 perf_p1_fail=0
    
    for test_name in "${!test_results[@]}"; do
        local result=${test_results[$test_name]}
        local priority=${test_priorities[$test_name]}
        local test_info=${test_registry[$test_name]:-"UNKNOWN|P2"}
        local test_id=${test_info%|*}
        
        # Determine test type from ID
        if [[ $test_id == IC-UNIT-* ]]; then
            if [[ $priority == "P0" ]]; then
                [[ $result == "PASSED" ]] && ((unit_p0_pass++)) || ((unit_p0_fail++))
            elif [[ $priority == "P1" ]]; then
                [[ $result == "PASSED" ]] && ((unit_p1_pass++)) || ((unit_p1_fail++))
            else
                [[ $result == "PASSED" ]] && ((unit_p2_pass++)) || ((unit_p2_fail++))
            fi
        elif [[ $test_id == IC-INT-* ]]; then
            if [[ $priority == "P0" ]]; then
                [[ $result == "PASSED" ]] && ((int_p0_pass++)) || ((int_p0_fail++))
            elif [[ $priority == "P1" ]]; then
                [[ $result == "PASSED" ]] && ((int_p1_pass++)) || ((int_p1_fail++))
            else
                [[ $result == "PASSED" ]] && ((int_p2_pass++)) || ((int_p2_fail++))
            fi
        elif [[ $test_id == IC-PERF-* ]]; then
            if [[ $priority == "P0" ]]; then
                [[ $result == "PASSED" ]] && ((perf_p0_pass++)) || ((perf_p0_fail++))
            elif [[ $priority == "P1" ]]; then
                [[ $result == "PASSED" ]] && ((perf_p1_pass++)) || ((perf_p1_fail++))
            fi
        fi
    done
    
    # Calculate totals
    local unit_total=$((unit_p0_pass + unit_p0_fail + unit_p1_pass + unit_p1_fail + unit_p2_pass + unit_p2_fail))
    local int_total=$((int_p0_pass + int_p0_fail + int_p1_pass + int_p1_fail + int_p2_pass + int_p2_fail))
    local perf_total=$((perf_p0_pass + perf_p0_fail + perf_p1_pass + perf_p1_fail))
    
    log "| 單元測試 | $unit_p0_pass/$unit_p0_fail | $unit_p1_pass/$unit_p1_fail | $unit_p2_pass/$unit_p2_fail | $unit_total |"
    log "| 整合測試 | $int_p0_pass/$int_p0_fail | $int_p1_pass/$int_p1_fail | $int_p2_pass/$int_p2_fail | $int_total |"
    log "| 效能測試 | $perf_p0_pass/$perf_p0_fail | $perf_p1_pass/$perf_p1_fail | 0/0 | $perf_total |"
    
    local total_pass=$((unit_p0_pass + unit_p1_pass + unit_p2_pass + int_p0_pass + int_p1_pass + int_p2_pass + perf_p0_pass + perf_p1_pass))
    local total_fail=$((unit_p0_fail + unit_p1_fail + unit_p2_fail + int_p0_fail + int_p1_fail + int_p2_fail + perf_p0_fail + perf_p1_fail))
    local grand_total=$((total_pass + total_fail))
    
    log "|----------|-------------|-------------|-------------|------|"
    log "| **總計** | **通過: $total_pass** | **失敗: $total_fail** | **總數: $grand_total** | 100% |"
    
    # Priority summary
    log "
${BLUE}=== 優先級統計 ===${NC}
"
    local p0_total_pass=$((unit_p0_pass + int_p0_pass + perf_p0_pass))
    local p0_total_fail=$((unit_p0_fail + int_p0_fail + perf_p0_fail))
    local p0_total=$((p0_total_pass + p0_total_fail))
    local p0_rate=0
    [[ $p0_total -gt 0 ]] && p0_rate=$((p0_total_pass * 100 / p0_total))
    
    local p1_total_pass=$((unit_p1_pass + int_p1_pass + perf_p1_pass))
    local p1_total_fail=$((unit_p1_fail + int_p1_fail + perf_p1_fail))
    local p1_total=$((p1_total_pass + p1_total_fail))
    local p1_rate=0
    [[ $p1_total -gt 0 ]] && p1_rate=$((p1_total_pass * 100 / p1_total))
    
    log "P0 (關鍵): $p0_total_pass/$p0_total (${p0_rate}%) - $([ $p0_rate -eq 100 ] && echo '✅ 符合發布標準' || echo '❌ 必須修復')"
    log "P1 (重要): $p1_total_pass/$p1_total (${p1_rate}%) - $([ $p1_rate -ge 95 ] && echo '✅ 符合發布標準' || echo '⚠️ 應該修復')"
    
    # Performance metrics if available
    if [ -f "/tmp/performance_metrics.log" ]; then
        log "
${BLUE}=== 效能指標 ===${NC}
"
        log "| 指標 | 實測值 | 目標值 | 狀態 |"
        log "|------|--------|--------|------|"
        
        # Extract performance data (placeholder - adjust based on actual output)
        local p50_time=$(grep "P50:" /tmp/performance_metrics.log | grep -oE '[0-9]+' || echo "N/A")
        local p95_time=$(grep "P95:" /tmp/performance_metrics.log | grep -oE '[0-9]+' || echo "N/A")
        local cache_hit_rate=$(grep "Cache Hit Rate:" /tmp/performance_metrics.log | grep -oE '[0-9]+' || echo "0")
        
        log "| P50 響應時間 | ${p50_time}ms | < 1000ms | $([ "$p50_time" != "N/A" ] && [ $p50_time -lt 1000 ] && echo '✅' || echo '❌') |"
        log "| P95 響應時間 | ${p95_time}ms | < 2000ms | $([ "$p95_time" != "N/A" ] && [ $p95_time -lt 2000 ] && echo '✅' || echo '❌') |"
        log "| 快取命中率 | ${cache_hit_rate}% | > 60% | $([ $cache_hit_rate -gt 60 ] && echo '✅' || echo '❌') |"
    fi
    
    # Test execution summary
    log "
${BLUE}=== 執行統計 ===${NC}
"
    local total_time=0
    for test_name in "${!test_times[@]}"; do
        total_time=$((total_time + ${test_times[$test_name]}))
    done
    
    log "總執行時間: ${total_time}秒"
    log "執行日期: $(date)"
    log "Python版本: $(python --version 2>&1)"
    log "測試框架: pytest $(pytest --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
}

# Main execution
main() {
    log "${BLUE}=== Index Calculation V2 測試執行 ===${NC}"
    log "開始時間: $(date)"
    
    # Clear previous report
    > test_report.log
    
    # Change to project root
    cd /Users/yuwenhao/Documents/GitHub/azure_container
    
    # Run unit tests
    log "
${YELLOW}執行單元測試...${NC}"
    for test in test_calculate_index_with_cache_hit test_calculate_index_with_cache_miss \
                test_cache_key_generation test_cache_expiration test_lru_eviction \
                test_cache_statistics test_parallel_execution test_parallel_error_handling \
                test_python311_taskgroup; do
        run_test "$test" "tests/unit/test_index_calculation_v2.py"
    done
    
    # Run integration tests
    log "
${YELLOW}執行整合測試...${NC}"
    for test in test_successful_calculation test_cache_header_behavior \
                test_validation_errors test_external_service_failure; do
        run_test "$test" "tests/integration/test_index_calculation_api.py"
    done
    
    # Run performance tests
    log "
${YELLOW}執行效能測試...${NC}"
    for test in test_response_time_baseline test_concurrent_load; do
        run_test "$test" "tests/performance/test_index_calculation_performance.py"
    done
    
    # Generate summary
    generate_summary
    
    # Determine exit code
    local failed_count=0
    for result in "${test_results[@]}"; do
        [[ $result == "FAILED" ]] && ((failed_count++))
    done
    
    if [ $failed_count -eq 0 ]; then
        log "
${GREEN}✅ 所有測試通過！${NC}"
        exit 0
    else
        log "
${RED}❌ $failed_count 個測試失敗${NC}"
        exit 1
    fi
}

# Run main function
main "$@"