#!/bin/bash
# PostToolUse hook: 檢查修改的 Python 檔案並回饋錯誤給 Claude
# 使用退出碼 2 來阻塞並顯示錯誤

# Debug: 記錄執行資訊
echo "[$(date)] PostToolUse hook executed" >> /tmp/claude_hook_debug.log

# 確保在正確的工作目錄
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

# Get all modified Python files
MODIFIED_PY=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
STAGED_PY=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
UNTRACKED_PY=$(git ls-files --others --exclude-standard 2>/dev/null | grep "\.py$" || true)

# Combine and deduplicate
ALL_MODIFIED_PY=$(echo -e "$MODIFIED_PY\n$STAGED_PY\n$UNTRACKED_PY" | sort -u | grep -v "^$" || true)

# 儲存上次檢查的結果
LAST_CHECK_FILE="/tmp/claude_last_ruff_check.txt"

if [ -n "$ALL_MODIFIED_PY" ]; then
    FILE_COUNT=$(echo "$ALL_MODIFIED_PY" | wc -l | tr -d ' ')
    echo "[$(date)] Found $FILE_COUNT modified Python files" >> /tmp/claude_hook_debug.log
    
    # 限制檢查頻率：只在少量檔案修改時執行
    if [ "$FILE_COUNT" -le 3 ] && command -v ruff &> /dev/null; then
        # 執行 ruff 檢查
        ERROR_OUTPUT=$(ruff check $ALL_MODIFIED_PY --line-length=120 2>&1 || true)
        
        if [ -n "$ERROR_OUTPUT" ] && ! echo "$ERROR_OUTPUT" | grep -q "All checks passed"; then
            # 有錯誤時，統計並儲存
            ERROR_COUNT=$(echo "$ERROR_OUTPUT" | grep -E "^Found [0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0")
            FIXABLE_COUNT=$(echo "$ERROR_OUTPUT" | grep -E "\[\*\] [0-9]+ fixable" | grep -oE "[0-9]+" | head -1 || echo "0")
            
            # 統計各種錯誤代碼
            ERROR_CODES=$(echo "$ERROR_OUTPUT" | grep -oE "[A-Z][0-9]{3,4}" | sort | uniq -c | sort -rn)
            
            # 儲存結果供 Stop hook 使用
            {
                echo "═══════════════════════════════════════════════════════════════"
                echo "⚠️  Ruff Check Results - $(date '+%H:%M:%S')"
                echo "═══════════════════════════════════════════════════════════════"
                echo "📊 Statistics:"
                echo "   • Files checked: $FILE_COUNT"
                echo "   • Total errors: $ERROR_COUNT"
                echo "   • Auto-fixable: $FIXABLE_COUNT"
                echo ""
                echo "📋 Error breakdown:"
                while IFS= read -r line; do
                    if [ -n "$line" ]; then
                        COUNT=$(echo "$line" | awk '{print $1}')
                        CODE=$(echo "$line" | awk '{print $2}')
                        echo "   • $CODE: $COUNT"
                    fi
                done <<< "$ERROR_CODES"
                echo "───────────────────────────────────────────────────────────────"
                echo "💡 Quick fix: ruff check --fix $ALL_MODIFIED_PY --line-length=120"
                echo "📝 View details: ruff check $ALL_MODIFIED_PY --line-length=120"
                echo "═══════════════════════════════════════════════════════════════"
            } > "$LAST_CHECK_FILE"
            
            # 記錄到 debug
            echo "[$(date)] Ruff found $ERROR_COUNT errors" >> /tmp/claude_hook_debug.log
        else
            # 成功時儲存結果
            {
                echo "═══════════════════════════════════════════════════════════════"
                echo "✅ Ruff Check Passed! - $(date '+%H:%M:%S')"
                echo "───────────────────────────────────────────────────────────────"
                echo "📊 Statistics:"
                echo "   • Files checked: $FILE_COUNT"
                echo "   • Total errors: 0"
                echo "   • All Python files meet quality standards"
                echo "═══════════════════════════════════════════════════════════════"
            } > "$LAST_CHECK_FILE"
            
            echo "[$(date)] All checks passed" >> /tmp/claude_hook_debug.log
        fi
    else
        echo "[$(date)] Skipped: too many files or ruff not available" >> /tmp/claude_hook_debug.log
    fi
fi

# PostToolUse: 不阻塞，只記錄結果
# Stop hook 或手動執行時會顯示結果
exit 0