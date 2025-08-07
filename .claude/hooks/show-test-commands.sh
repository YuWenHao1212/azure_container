#!/bin/bash
# UserPromptSubmit hook: 顯示測試指令
# 當使用者提到測試時觸發

echo ""
echo "💡 Test commands:"
echo "• Health & Keyword: ./test/scripts/run_health_keyword_unit_integration.sh"
echo "• Index Calc: ./test/scripts/run_index_calculation_unit_integration.sh"
echo "• Gap Analysis: ./test/scripts/run_index_cal_gap_analysis_unit_integration.sh"
echo "• Quick check: ruff check src/ test/ --line-length=120"