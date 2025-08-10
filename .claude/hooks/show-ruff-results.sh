#!/bin/bash
# Stop hook: 顯示累積的 Ruff 檢查結果
# 在對話結束時執行

# 確保在專案根目錄執行
cd "$(dirname "$0")/../.." 2>/dev/null || true

# 檢查是否有 Ruff 檢查結果
LAST_CHECK_FILE="/tmp/claude_last_ruff_check.txt"

if [ -f "$LAST_CHECK_FILE" ]; then
    echo ""
    echo "🔍 最近的 Ruff 程式碼品質檢查結果："
    echo ""
    cat "$LAST_CHECK_FILE"
    echo ""
else
    # 檢查是否有修改的 Python 檔案但沒有檢查結果
    MODIFIED_PY=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
    STAGED_PY=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
    UNTRACKED_PY=$(git ls-files --others --exclude-standard 2>/dev/null | grep "\.py$" || true)
    
    ALL_MODIFIED_PY=$(echo -e "$MODIFIED_PY\n$STAGED_PY\n$UNTRACKED_PY" | sort -u | grep -v "^$" || true)
    
    if [ -n "$ALL_MODIFIED_PY" ]; then
        FILE_COUNT=$(echo "$ALL_MODIFIED_PY" | wc -l | tr -d ' ')
        echo ""
        echo "💡 發現 $FILE_COUNT 個修改的 Python 檔案，但沒有品質檢查記錄"
        echo "   建議執行: ruff check $(echo $ALL_MODIFIED_PY | tr '\n' ' ')--line-length=120"
        echo ""
    fi
fi