#!/bin/bash

# Level 2: Unit Tests Script
# Runs the 50 selected unit tests marked with @pytest.mark.precommit

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/test"

# Source log manager
source "$SCRIPT_DIR/lib/log_manager.sh"

# Start timer
START_TIME=$(date +%s)

echo "======================================"
echo "Level 2: Unit Tests (Precommit)"
echo "======================================"
echo "Running 50 selected unit tests"
echo ""

# Change to project root for pytest
cd "$PROJECT_ROOT"

# Run pytest with precommit marker
echo "Executing: pytest -c test/pytest-precommit.ini -m precommit"
echo ""

# Run tests and capture output
pytest_output=$(mktemp)
pytest -c test/pytest-precommit.ini -m precommit \
    --junit-xml="$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" \
    2>&1 | tee "$pytest_output"

pytest_exit_code=${PIPESTATUS[0]}

# Parse test results
if [ -f "$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" ]; then
    # Extract test counts from JUnit XML
    total_tests=$(grep -o 'tests="[0-9]*"' "$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    failed_tests=$(grep -o 'failures="[0-9]*"' "$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    error_tests=$(grep -o 'errors="[0-9]*"' "$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    skipped_tests=$(grep -o 'skipped="[0-9]*"' "$TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml" | head -1 | grep -o '[0-9]*')
    
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

# Check if we ran the expected number of tests
if [ "$total_tests" -lt 45 ]; then
    echo "⚠️  WARNING: Expected ~50 tests but only ran $total_tests"
    echo "Some tests may not be properly marked with @pytest.mark.precommit"
elif [ "$total_tests" -gt 55 ]; then
    echo "⚠️  WARNING: Expected ~50 tests but ran $total_tests"
    echo "Too many tests marked with @pytest.mark.precommit"
fi

# Exit code based on test results
if [ $pytest_exit_code -eq 0 ]; then
    echo "✅ All unit tests passed!"
    exit 0
else
    echo "❌ Unit tests failed!"
    echo ""
    echo "To see detailed failure information, check:"
    echo "  - $TEST_DIR/reports/precommit_unit_${LOG_TIMESTAMP}.xml"
    exit $pytest_exit_code
fi