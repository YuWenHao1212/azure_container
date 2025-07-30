#!/bin/bash
# Level 0 Tests - No AI credentials required
# These tests validate configuration and syntax

set -e  # Exit on error

echo "========================================"
echo "Running Level 0 Tests - Prompt Validation"
echo "========================================"
echo ""

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Create logs directory if it doesn't exist
mkdir -p test/logs

# Run prompt validation
echo "1. Validating YAML prompt files..."
python test/scripts/check_prompts.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All Level 0 tests passed!"
    exit 0
else
    echo ""
    echo "❌ Level 0 tests failed!"
    exit 1
fi