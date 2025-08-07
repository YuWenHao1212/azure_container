#!/bin/bash
# UserPromptSubmit hook: Commit 前的完整檢查
# 當使用者提到 commit 時觸發

echo ""
echo "🚨 Pre-commit validation starting..."
echo "=" 
echo ""

# 1. Ruff 檢查
echo "📝 Step 1/4: Running Ruff check..."
echo "Checking src/ and test/ directories"

RUFF_ERRORS=$(ruff check src/ test/ --line-length=120 2>&1)
RUFF_EXIT_CODE=$?

if [ $RUFF_EXIT_CODE -ne 0 ]; then
    echo "❌ Ruff check FAILED:"
    echo "$RUFF_ERRORS"
    echo ""
    echo "📌 To fix: ruff check src/ test/ --fix --line-length=120"
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix Ruff errors first"
    exit 1
else
    echo "✅ Ruff check passed"
fi

echo ""

# 2. Health & Keyword 測試
echo "📝 Step 2/4: Running Health & Keyword tests..."
if ./test/scripts/run_health_keyword_unit_integration.sh > /tmp/test_health_keyword.log 2>&1; then
    echo "✅ Health & Keyword tests passed"
else
    echo "❌ Health & Keyword tests FAILED"
    echo "Check log: /tmp/test_health_keyword.log"
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix test failures first"
    exit 1
fi

echo ""

# 3. Index Calculation 測試
echo "📝 Step 3/4: Running Index Calculation tests..."
if ./test/scripts/run_index_calculation_unit_integration.sh > /tmp/test_index_calc.log 2>&1; then
    echo "✅ Index Calculation tests passed"
else
    echo "❌ Index Calculation tests FAILED"
    echo "Check log: /tmp/test_index_calc.log"
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix test failures first"
    exit 1
fi

echo ""

# 4. Gap Analysis 測試
echo "📝 Step 4/4: Running Gap Analysis tests..."
if ./test/scripts/run_index_cal_gap_analysis_unit_integration.sh > /tmp/test_gap_analysis.log 2>&1; then
    echo "✅ Gap Analysis tests passed"
else
    echo "❌ Gap Analysis tests FAILED"
    echo "Check log: /tmp/test_gap_analysis.log"
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix test failures first"
    exit 1
fi

echo ""
echo "=" 
echo "🎉 All pre-commit checks passed!"
echo "✅ Ruff check: PASSED"
echo "✅ Health & Keyword tests: PASSED"
echo "✅ Index Calculation tests: PASSED"
echo "✅ Gap Analysis tests: PASSED"
echo ""
echo "👍 Ready to commit!"