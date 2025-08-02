#!/bin/bash

# Index Calculation V2 Performance Test Runner
# This script runs the performance tests for Index Calculation V2 with proper configuration
# Total execution time: ~2 minutes

echo "==================================================================="
echo "Index Calculation V2 Performance Test Runner"
echo "==================================================================="
echo ""
echo "This script will run all 5 performance tests:"
echo "- API-IC-201-PT: Response Time Benchmark (30s)"
echo "- API-IC-202-PT: Cache Performance Test (30s)"
echo "- API-IC-203-PT: High Concurrency Load Test (60s)"
echo "- API-IC-204-PT: Memory Efficiency Test (30s)"
echo "- API-IC-205-PT: Cache Size Limits Test (30s)"
echo ""
echo "Total estimated time: ~2 minutes"
echo ""
echo "==================================================================="
echo ""

# Check if we're in the project root or test directory
if [ -f "pyproject.toml" ]; then
    PROJECT_ROOT="."
elif [ -f "../pyproject.toml" ]; then
    PROJECT_ROOT=".."
elif [ -f "../../pyproject.toml" ]; then
    PROJECT_ROOT="../.."
else
    echo "Error: Cannot find project root (pyproject.toml)"
    exit 1
fi

cd "$PROJECT_ROOT"

# Set environment variables for performance testing
export TESTING=true
export MONITORING_ENABLED=false
export LIGHTWEIGHT_MONITORING=false
export ERROR_CAPTURE_ENABLED=false
export INDEX_CALC_CACHE_ENABLED=true
export INDEX_CALC_CACHE_TTL_MINUTES=60
export INDEX_CALC_CACHE_MAX_SIZE=1000

# Create timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="test/logs"
LOG_FILE="$LOG_DIR/performance_test_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Starting performance tests..."
echo "Log file: $LOG_FILE"
echo ""

# Function to run a single test and capture output
run_test() {
    local test_name=$1
    local test_path=$2
    local timeout=$3
    
    echo "Running $test_name (timeout: ${timeout}s)..."
    echo "----------------------------------------"
    
    # Run the test with pytest's built-in timeout and capture output
    if python -m pytest "$test_path" -v -s --tb=short --timeout=$timeout > temp_output.txt 2>&1; then
        echo "✅ PASSED"
        # Extract performance metrics if available
        grep -E "(P50:|P95:|P99:|Median:|Hit Rate:|Success Rate:)" temp_output.txt | sed 's/^/   /'
    else
        echo "❌ FAILED"
        # Show last few lines of error
        tail -n 5 temp_output.txt | sed 's/^/   /'
    fi
    
    # Append to log file
    echo "=== $test_name ===" >> "$LOG_FILE"
    cat temp_output.txt >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    # Clean up temp file
    rm -f temp_output.txt
    
    echo ""
}

# Run each performance test individually with appropriate timeouts
run_test "API-IC-201-PT Response Time Benchmark" \
    "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_response_time_benchmark" \
    40

run_test "API-IC-202-PT Cache Performance" \
    "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_cache_performance" \
    40

run_test "API-IC-203-PT High Concurrency Load" \
    "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_high_concurrency_load" \
    70

run_test "API-IC-204-PT Memory Efficiency" \
    "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_memory_efficiency" \
    40

run_test "API-IC-205-PT Cache Size Limits" \
    "test/performance/test_index_calculation_v2_performance.py::TestIndexCalculationV2Performance::test_cache_size_limits" \
    40

echo "==================================================================="
echo "Performance Test Summary"
echo "==================================================================="
echo ""

# Generate summary from log file
echo "Test Results:"
grep -E "(PASSED|FAILED)" "$LOG_FILE" | grep "::test_" | awk -F'::' '{print "- " $NF}' | sort | uniq

echo ""
echo "Performance Metrics:"
grep -E "(P50:|P95:|P99:|Median:|Hit Rate:|Success Rate:)" "$LOG_FILE" | sort | uniq

echo ""
echo "Full results saved to: $LOG_FILE"
echo ""

# Check if all tests passed
if grep -q "FAILED" "$LOG_FILE"; then
    echo "⚠️  Some tests failed. Please review the log file for details."
    exit 1
else
    echo "✅ All performance tests passed!"
    exit 0
fi