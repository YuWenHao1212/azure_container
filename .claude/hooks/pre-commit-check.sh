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

# 2. Service Modules 測試
echo "📝 Step 2/5: Running Service Modules tests..."
if ./test/scripts/run_service_modules_tests_final.sh > /tmp/test_service_modules.log 2>&1; then
    echo "✅ Service Modules tests passed"
else
    echo "❌ Service Modules tests FAILED"
    echo "Check log: /tmp/test_service_modules.log"
    echo ""
    echo "⛔ BLOCKING COMMIT - Fix test failures first"
    exit 1
fi

echo ""

# 3. Health & Keyword 測試
echo "📝 Step 3/5: Running Health & Keyword tests..."
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

# 4. Index Calculation 測試
echo "📝 Step 4/5: Running Index Calculation tests..."
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

# 5. Gap Analysis 測試
echo "📝 Step 5/5: Running Gap Analysis tests..."
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
echo "✅ Service Modules tests: PASSED"
echo "✅ Health & Keyword tests: PASSED"
echo "✅ Index Calculation tests: PASSED"
echo "✅ Gap Analysis tests: PASSED"
echo ""
echo "👍 Ready to commit!"