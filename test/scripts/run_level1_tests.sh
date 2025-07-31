#!/bin/bash

# Level 1 Test Runner for Azure Container API
# This script runs all Level 1 tests (code style checks)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "Running Level 1 Tests: Code Style Check"
echo "========================================="
echo ""

# Run the style check script
"$SCRIPT_DIR/scripts/run_style.sh"
exit_code=$?

echo ""
echo "========================================="
echo "Level 1 Test Summary"
echo "========================================="

if [ $exit_code -eq 0 ]; then
    echo "✅ All Level 1 tests passed!"
else
    echo "❌ Level 1 tests failed. See above for details."
fi

exit $exit_code