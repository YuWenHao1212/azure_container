#!/bin/bash

# Level 1 Style Check Script for Azure Container API
# This script performs code style checking using ruff
# Focus: health check and keyword extraction endpoints

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_DIR="$PROJECT_ROOT/test"
SRC_DIR="$PROJECT_ROOT/src"
LOG_DIR="$TEST_DIR/logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Generate timestamp for log file
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/level1_style_${TIMESTAMP}.log"

# Define target files for style checking
TARGET_FILES=(
    "$SRC_DIR/main.py"  # Contains health check endpoint
    "$SRC_DIR/api/v1/keyword_extraction.py"
    "$SRC_DIR/models/keyword_extraction.py"
    "$SRC_DIR/services/keyword_extraction.py"
    "$SRC_DIR/services/keyword_extraction_v2.py"
    "$SRC_DIR/services/keyword_standardizer.py"
)

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to print colored output
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Header
log "====================================="
log "Level 1: Code Style Check"
log "====================================="
log "Project Root: $PROJECT_ROOT"
log "Log File: $LOG_FILE"
log ""

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    log "ERROR: ruff is not installed. Please install it with: pip install ruff"
    exit 1
fi

log "Ruff version: $(ruff --version)"
log ""

# Initialize counters
TOTAL_FILES=0
PASSED_FILES=0
FAILED_FILES=0
MISSING_FILES=0

# Default ruff configuration if no config file exists
RUFF_CONFIG="
line-length = 88
target-version = 'py38'

select = [
    'E',    # pycodestyle errors
    'W',    # pycodestyle warnings
    'F',    # pyflakes
    'I',    # isort
    'N',    # pep8-naming
    'D',    # pydocstyle
    'UP',   # pyupgrade
    'B',    # flake8-bugbear
    'C4',   # flake8-comprehensions
    'SIM',  # flake8-simplify
]

ignore = [
    'D100', # Missing docstring in public module
    'D101', # Missing docstring in public class
    'D102', # Missing docstring in public method
    'D103', # Missing docstring in public function
    'D104', # Missing docstring in public package
    'D105', # Missing docstring in magic method
    'D107', # Missing docstring in __init__
]
"

# Create temporary ruff config if none exists
TEMP_RUFF_CONFIG=""
if [ ! -f "$PROJECT_ROOT/ruff.toml" ] && [ ! -f "$PROJECT_ROOT/.ruff.toml" ] && [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    TEMP_RUFF_CONFIG="$PROJECT_ROOT/.ruff.toml.tmp"
    echo "$RUFF_CONFIG" > "$TEMP_RUFF_CONFIG"
    log "Created temporary ruff configuration"
fi

# Function to check a single file
check_file() {
    local file=$1
    local relative_path="${file#$PROJECT_ROOT/}"
    
    TOTAL_FILES=$((TOTAL_FILES + 1))
    
    if [ ! -f "$file" ]; then
        log "MISSING: $relative_path"
        print_colored "$YELLOW" "⚠️  MISSING: $relative_path"
        MISSING_FILES=$((MISSING_FILES + 1))
        return
    fi
    
    log "Checking: $relative_path"
    
    # Run ruff check
    if [ -n "$TEMP_RUFF_CONFIG" ]; then
        ruff_output=$(ruff check "$file" --config "$TEMP_RUFF_CONFIG" 2>&1)
    else
        ruff_output=$(ruff check "$file" 2>&1)
    fi
    ruff_exit_code=$?
    
    if [ $ruff_exit_code -eq 0 ]; then
        log "PASSED: $relative_path"
        print_colored "$GREEN" "✅ PASSED: $relative_path"
        PASSED_FILES=$((PASSED_FILES + 1))
    else
        log "FAILED: $relative_path"
        log "Issues found:"
        echo "$ruff_output" | while IFS= read -r line; do
            log "  $line"
        done
        print_colored "$RED" "❌ FAILED: $relative_path"
        echo "$ruff_output"
        FAILED_FILES=$((FAILED_FILES + 1))
    fi
    
    echo "" | tee -a "$LOG_FILE"
}

# Check each target file
log "Starting style checks..."
log "Target files:"
for file in "${TARGET_FILES[@]}"; do
    log "  - ${file#$PROJECT_ROOT/}"
done
log ""

for file in "${TARGET_FILES[@]}"; do
    check_file "$file"
done

# Additional checks for import sorting
log "====================================="
log "Import Sorting Check"
log "====================================="

for file in "${TARGET_FILES[@]}"; do
    if [ -f "$file" ]; then
        relative_path="${file#$PROJECT_ROOT/}"
        log "Checking imports in: $relative_path"
        
        if [ -n "$TEMP_RUFF_CONFIG" ]; then
            import_output=$(ruff check "$file" --select I --config "$TEMP_RUFF_CONFIG" 2>&1)
        else
            import_output=$(ruff check "$file" --select I 2>&1)
        fi
        
        if [ $? -eq 0 ]; then
            log "  Imports are properly sorted"
        else
            log "  Import issues found:"
            echo "$import_output" | while IFS= read -r line; do
                log "    $line"
            done
        fi
    fi
done

# Check naming conventions
log ""
log "====================================="
log "Naming Convention Check"
log "====================================="

for file in "${TARGET_FILES[@]}"; do
    if [ -f "$file" ]; then
        relative_path="${file#$PROJECT_ROOT/}"
        log "Checking naming in: $relative_path"
        
        if [ -n "$TEMP_RUFF_CONFIG" ]; then
            naming_output=$(ruff check "$file" --select N --config "$TEMP_RUFF_CONFIG" 2>&1)
        else
            naming_output=$(ruff check "$file" --select N 2>&1)
        fi
        
        if [ $? -eq 0 ]; then
            log "  Naming conventions followed"
        else
            log "  Naming issues found:"
            echo "$naming_output" | while IFS= read -r line; do
                log "    $line"
            done
        fi
    fi
done

# Clean up temporary config
if [ -n "$TEMP_RUFF_CONFIG" ]; then
    rm -f "$TEMP_RUFF_CONFIG"
fi

# Summary
log ""
log "====================================="
log "Summary"
log "====================================="
log "Total files checked: $TOTAL_FILES"
log "Passed: $PASSED_FILES"
log "Failed: $FAILED_FILES"
log "Missing: $MISSING_FILES"

# Calculate success rate
if [ $TOTAL_FILES -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; ($PASSED_FILES * 100) / $TOTAL_FILES" | bc)
    log "Success rate: ${SUCCESS_RATE}%"
else
    log "No files were checked"
fi

log ""
log "Full log saved to: $LOG_FILE"

# Exit code based on results
if [ $FAILED_FILES -eq 0 ] && [ $MISSING_FILES -eq 0 ]; then
    log "✅ All style checks passed!"
    print_colored "$GREEN" "✅ All style checks passed!"
    exit 0
else
    log "❌ Style check failed. Please fix the issues above."
    print_colored "$RED" "❌ Style check failed. Please fix the issues above."
    exit 1
fi