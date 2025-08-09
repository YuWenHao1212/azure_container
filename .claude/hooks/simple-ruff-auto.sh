#!/bin/bash
# Simple Ruff Auto-Fix Hook: 直接執行 ruff check + fix
# 設計目標: < 3秒完成，95%+ 自動修復成功

# Debug 日誌
log_debug() {
    echo "[$(date '+%H:%M:%S')] Simple Ruff: $1" >> /tmp/claude_simple_ruff.log
}

# 確保在正確的工作目錄
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# 檢查是否有 Python 檔案修改
check_python_changes() {
    # 檢查 git 修改的 Python 檔案（在 src/ 或 test/ 目錄）
    local modified_py=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep -E "^(src|test)/.*\.py$" || true)
    local staged_py=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep -E "^(src|test)/.*\.py$" || true)
    local untracked_py=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E "^(src|test)/.*\.py$" || true)
    
    echo -e "$modified_py\n$staged_py\n$untracked_py" | sort -u | grep -v "^$" || true
}

# 兩階段檢查和修復邏輯
main() {
    local changed_files=$(check_python_changes)
    
    if [ -z "$changed_files" ]; then
        log_debug "No Python files changed in src/ or test/ directories"
        echo "🔍 Ruff Hook: 📊 已檢查，無需修復的檔案變更"
        return 0
    fi
    
    local file_count=$(echo "$changed_files" | wc -l)
    log_debug "Detected $file_count Python file(s) changed: $(echo $changed_files | tr '
' ' ')"
    
    echo "🔍 Ruff Hook: 開始兩階段品質檢查 ($file_count 個檔案)"
    echo "📋 檢查檔案: $(echo $changed_files | tr '
' ' ' | head -c 60)..."
    
    # 階段 1: 初始檢查
    echo ""
    echo "📝 階段 1: 初始品質檢查"
    
    # 先執行檢查，正確捕捉 exit code
    ruff check src/ test/ --line-length=120 > /tmp/ruff_initial_check.txt 2>&1
    local initial_exit_code=$?
    local initial_check=$(cat /tmp/ruff_initial_check.txt)
    
    if [ $initial_exit_code -eq 0 ]; then
        log_debug "✅ Initial check passed - no issues found"
        echo "✅ 初始檢查: 程式碼完全符合品質標準"
        echo "🎉 結果: 無需修復，品質優良"
        echo ""
        return 0
    fi
    
    # 統計初始錯誤
    local initial_error_count=$(echo "$initial_check" | grep -c ":" || echo "0")
    echo "⚠️  初始檢查: 發現 $initial_error_count 個品質問題"
    echo "📊 錯誤類型:"
    echo "$initial_check" | head -3
    echo ""
    
    # 階段 2: 自動修復
    echo "🔧 階段 2: 執行自動修復"
    log_debug "Running ruff check src/ test/ --fix --line-length=120"
    
    # 執行自動修復並正確捕捉結果
    ruff check src/ test/ --fix --line-length=120 > /tmp/ruff_fix_output.txt 2>&1
    local fix_exit_code=$?
    local fix_output=$(cat /tmp/ruff_fix_output.txt)
    
    # 統計修復結果
    local fixed_count=$(echo "$fix_output" | grep -c "Fixed" || echo "0")
    if [ $fixed_count -gt 0 ]; then
        echo "✅ 自動修復: 成功修復 $fixed_count 個問題"
        log_debug "✅ Auto-fixed $fixed_count issues"
    else
        echo "⚠️  自動修復: 無法自動修復任何問題"
        log_debug "⚠️ No issues could be auto-fixed"
    fi
    
    # 階段 3: 修復後再檢查
    echo "🔍 階段 3: 修復後驗證"
    
    # 再次檢查並正確捕捉結果
    ruff check src/ test/ --line-length=120 > /tmp/ruff_final_check.txt 2>&1
    local final_exit_code=$?
    local final_check=$(cat /tmp/ruff_final_check.txt)
    
    if [ $final_exit_code -eq 0 ]; then
        echo "🎉 最終結果: ✅ 所有問題已解決，程式碼品質通過"
        echo "📈 修復統計: $initial_error_count 個問題 → $fixed_count 個自動修復 → 0 個剩餘"
        log_debug "✅ All issues resolved after auto-fix"
    else
        local remaining_count=$(echo "$final_check" | grep -c ":" || echo "0")
        echo "⚠️  最終結果: 仍有 $remaining_count 個問題需要手動處理"
        echo "📈 修復統計: $initial_error_count 個問題 → $fixed_count 個自動修復 → $remaining_count 個剩餘"
        echo ""
        echo "🔧 建議行動:"
        echo "   • 手動修復: ruff check src/ test/ --line-length=120"
        echo "   • 深度分析: @Ruff-checker"
        echo ""
        echo "❌ 剩餘問題預覽:"
        echo "$final_check" | head -3
        log_debug "⚠️ $remaining_count issues remain after auto-fix"
    fi
    
    echo "📍 詳細記錄: /tmp/claude_simple_ruff.log"
    echo ""
    log_debug "Completed 3-stage check in $(date '+%H:%M:%S')"
}

# 執行主程序
main "$@"
exit 0