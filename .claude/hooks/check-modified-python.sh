#!/bin/bash
# Stop hook: 檢查修改過的 Python 檔案
# 在每次 Claude 回應後執行

MODIFIED_PY=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep "\.py$")

if [ -n "$MODIFIED_PY" ]; then
    echo ""
    echo "🔍 Checking modified Python files..."
    ruff check $MODIFIED_PY --line-length=120 2>/dev/null || true
fi