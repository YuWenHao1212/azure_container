#!/bin/bash

# Level 3: Integration Tests Script
# Runs the 4 key integration tests

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/test"

# Source log manager
source "$SCRIPT_DIR/lib/log_manager.sh"

# Start timer
START_TIME=$(date +%s)

echo "======================================"
echo "Level 3: Integration Tests"
echo "======================================"
echo "Running 4 key integration tests"
echo ""

# Change to project root for pytest
cd "$PROJECT_ROOT"

# Define the specific integration tests to run
INTEGRATION_TESTS=(
    "test/integration/test_health_integration.py::TestHealthCheckIntegration::test_health_check_integration"
    "test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_english_job_description_uses_english_prompt"
    "test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_traditional_chinese_job_description_uses_chinese_prompt"
    "test/integration/test_keyword_extraction_language.py::TestKeywordExtractionLanguageIntegration::test_mixed_chinese_english_above_threshold"
)

# Build pytest command
echo "Selected integration tests:"
for test in "${INTEGRATION_TESTS[@]}"; do
    echo "  - $test"
done
echo ""

# Run pytest with specific tests
echo "Executing integration tests..."
echo ""

# Run tests and capture output
pytest_output=$(mktemp)
pytest -c test/pytest-precommit.ini "${INTEGRATION_TESTS[@]}" \
    -v --tb=short --no-cov --maxfail=1 --timeout=25 \
    --junit-xml="$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" \
    2>&1 | tee "$pytest_output"

pytest_exit_code=${PIPESTATUS[0]}

# Parse test results
if [ -f "$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" ]; then
    # Extract test counts from JUnit XML
    total_tests=$(grep -o 'tests="[0-9]*"' "$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    failed_tests=$(grep -o 'failures="[0-9]*"' "$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    error_tests=$(grep -o 'errors="[0-9]*"' "$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    skipped_tests=$(grep -o 'skipped="[0-9]*"' "$TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    
    # Calculate passed tests
    failed_total=$((failed_tests + error_tests))
    passed_tests=$((total_tests - failed_total - skipped_tests))
else
    # Fallback: parse from output
    total_tests=$(grep -E "^[0-9]+ passed|[0-9]+ failed|[0-9]+ skipped" "$pytest_output" | grep -oE "[0-9]+" | paste -sd+ | bc 2>/dev/null || echo "0")
    passed_tests=$(grep -oE "^[0-9]+ passed" "$pytest_output" | grep -oE "[0-9]+" || echo "0")
    failed_tests=$(grep -oE "^[0-9]+ failed" "$pytest_output" | grep -oE "[0-9]+" || echo "0")
    skipped_tests=$(grep -oE "^[0-9]+ skipped" "$pytest_output" | grep -oE "[0-9]+" || echo "0")
    failed_total=$failed_tests
fi

# Clean up temp file
rm -f "$pytest_output"

# End timer
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Summary
echo ""
echo "======================================"
echo "Summary"
echo "======================================"
echo "Total tests: $total_tests"
echo "Passed: $passed_tests"
echo "Failed: $failed_total"
echo "Skipped: $skipped_tests"
echo "Duration: ${DURATION}s"
echo ""

# Warn if duration is too long
if [ $DURATION -gt 25 ]; then
    echo "⚠️  WARNING: Integration tests took ${DURATION}s (target: <25s)"
fi

# Check if we ran the expected number of tests
if [ "$total_tests" -ne 4 ]; then
    echo "⚠️  WARNING: Expected 4 tests but ran $total_tests"
fi

# Exit code based on test results
if [ $pytest_exit_code -eq 0 ]; then
    echo "✅ All integration tests passed!"
    exit 0
else
    echo "❌ Integration tests failed!"
    echo ""
    echo "To see detailed failure information, check:"
    echo "  - $TEST_DIR/reports/precommit_integration_${LOG_TIMESTAMP}.xml"
    exit $pytest_exit_code
fi