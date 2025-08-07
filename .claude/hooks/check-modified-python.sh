#!/bin/bash
# Stop hook: 檢查修改過的 Python 檔案
# 在每次 Claude 回應後執行

# Get modified Python files (both staged and unstaged)
MODIFIED_PY=$(git diff --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)
STAGED_PY=$(git diff --cached --name-only --diff-filter=AM 2>/dev/null | grep "\.py$" || true)

# Combine and deduplicate
ALL_MODIFIED_PY=$(echo -e "$MODIFIED_PY\n$STAGED_PY" | sort -u | grep -v "^$" || true)

if [ -n "$ALL_MODIFIED_PY" ]; then
    echo ""
    echo "🔍 Checking modified Python files with ruff..."
    
    # Count files
    FILE_COUNT=$(echo "$ALL_MODIFIED_PY" | wc -l | tr -d ' ')
    echo "   Found $FILE_COUNT modified Python file(s)"
    
    # Run ruff check
    if command -v ruff &> /dev/null; then
        # Run ruff and capture result
        if ruff check $ALL_MODIFIED_PY --line-length=120 2>/dev/null; then
            echo "   ✅ All files pass ruff checks!"
        else
            echo "   ⚠️  Some ruff checks failed (non-blocking)"
        fi
    else
        echo "   ⚠️  Ruff not installed, skipping checks"
    fi
fi