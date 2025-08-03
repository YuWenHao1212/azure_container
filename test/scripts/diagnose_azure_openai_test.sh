#!/bin/bash
# 診斷 Azure OpenAI 測試間歇性失敗的腳本

ITERATIONS=100
FAILURES=0
PASSES=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/test/logs/diagnostic_runs"

echo "=== Azure OpenAI Integration Test Diagnostic Tool ==="
echo "Starting diagnostic run of $ITERATIONS iterations..."
echo "Project root: $PROJECT_ROOT"
echo "Log directory: $LOG_DIR"

# 創建日誌目錄
mkdir -p "$LOG_DIR"

# 記錄開始時間
START_TIME=$(date +%s)
echo "Start time: $(date)"

# 主要診斷循環
for i in $(seq 1 $ITERATIONS); do
    echo -n "Run $i/$ITERATIONS: "
    
    # 記錄環境狀態
    {
        echo "=== Test Run $i ==="
        echo "Date: $(date)"
        echo "=== System State ==="
        echo "Process count: $(ps aux | wc -l)"
        
        # macOS 記憶體資訊
        if [[ "$(uname)" == "Darwin" ]]; then
            echo "Memory info:"
            vm_stat | grep -E "Pages (free|active|inactive|wired down):"
        else
            echo "Memory info:"
            free -h
        fi
        
        echo "Python processes: $(ps aux | grep -c python)"
        echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"
        
        echo -e "\n=== Test Execution ==="
    } > "$LOG_DIR/run_$i.log"
    
    # 執行測試
    cd "$PROJECT_ROOT"
    if python -m pytest test/integration/test_azure_openai_integration.py::TestAzureOpenAIIntegration::test_azure_openai_integration \
        -v --tb=short -s >> "$LOG_DIR/run_$i.log" 2>&1; then
        ((PASSES++))
        echo "✓ PASS"
    else
        ((FAILURES++))
        echo "✗ FAIL"
        
        # 保存失敗的詳細日誌
        cp "$LOG_DIR/run_$i.log" "$LOG_DIR/failure_${FAILURES}_run_${i}.log"
        
        # 提取錯誤類型
        ERROR_TYPE="Unknown"
        if grep -q "AttributeError.*max_retries" "$LOG_DIR/run_$i.log"; then
            ERROR_TYPE="AttributeError_max_retries"
        elif grep -q "AttributeError.*retry_delays" "$LOG_DIR/run_$i.log"; then
            ERROR_TYPE="AttributeError_retry_delays"
        elif grep -q "MagicMock.*await" "$LOG_DIR/run_$i.log"; then
            ERROR_TYPE="Mock_await_error"
        elif grep -q "TimeoutError" "$LOG_DIR/run_$i.log"; then
            ERROR_TYPE="Timeout"
        fi
        
        echo "  Error type: $ERROR_TYPE"
        echo "$i,$ERROR_TYPE" >> "$LOG_DIR/failure_summary.csv"
    fi
    
    # 短暫等待，避免資源競爭
    sleep 1
done

# 計算統計
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
FAILURE_RATE=$(echo "scale=2; $FAILURES * 100 / $ITERATIONS" | bc)

# 生成摘要報告
{
    echo "=== Diagnostic Summary Report ==="
    echo "Generated: $(date)"
    echo "Total runs: $ITERATIONS"
    echo "Passes: $PASSES"
    echo "Failures: $FAILURES"
    echo "Failure rate: ${FAILURE_RATE}%"
    echo "Total duration: ${DURATION} seconds"
    echo ""
    
    if [ $FAILURES -gt 0 ]; then
        echo "=== Failure Analysis ==="
        echo "Error type distribution:"
        if [ -f "$LOG_DIR/failure_summary.csv" ]; then
            cut -d',' -f2 "$LOG_DIR/failure_summary.csv" | sort | uniq -c | sort -nr
        fi
        echo ""
        echo "Failed runs: $(cut -d',' -f1 "$LOG_DIR/failure_summary.csv" | tr '\n' ' ')"
    fi
    
    echo ""
    echo "=== Recommendations ==="
    if [ $FAILURES -eq 0 ]; then
        echo "✅ All tests passed! The issue might be environment-specific."
    elif [ $FAILURE_RATE -gt 50 ]; then
        echo "⚠️  High failure rate detected. This indicates a systematic issue."
        echo "   Check the most common error type and focus on that fix."
    else
        echo "⚠️  Intermittent failures detected. This confirms the sporadic nature."
        echo "   Review failure patterns for timing or resource-related issues."
    fi
} | tee "$LOG_DIR/diagnostic_summary.txt"

echo ""
echo "Diagnostic complete. Results saved to: $LOG_DIR/"
echo "Summary: $PASSES passes, $FAILURES failures (${FAILURE_RATE}% failure rate)"

# 如果有失敗，顯示最常見的錯誤
if [ $FAILURES -gt 0 ] && [ -f "$LOG_DIR/failure_summary.csv" ]; then
    echo ""
    echo "Most common error:"
    cut -d',' -f2 "$LOG_DIR/failure_summary.csv" | sort | uniq -c | sort -nr | head -1
fi