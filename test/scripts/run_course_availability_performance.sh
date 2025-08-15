#!/bin/bash

# Course Availability Performance Test Script
# Test ID: CA-001-PT (6-skill performance test with 20 iterations)

echo "=========================================="
echo "📊 Course Availability Performance Test"
echo "=========================================="
echo ""

# Create logs directory if not exists
mkdir -p test/logs

# Set timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="test/logs/performance_course_availability_${TIMESTAMP}.log"

echo "📝 Log file: $LOG_FILE"
echo ""

echo "🌐 Performance tests always use REAL API (requires Azure credentials)..."

# Check for iteration count parameter
ITERATIONS=${PERFORMANCE_ITERATIONS:-20}
if [ "$1" == "--iterations" ] && [ -n "$2" ]; then
    ITERATIONS=$2
    echo "📊 Custom iterations: $ITERATIONS (from parameter)"
elif [ -n "$PERFORMANCE_ITERATIONS" ]; then
    echo "📊 Custom iterations: $ITERATIONS (from environment variable)"  
else
    echo "📊 Default iterations: $ITERATIONS"
fi

echo "💡 Tip: Set PERFORMANCE_ITERATIONS=100 for detailed P50/P95 analysis"
echo ""

# Export the iterations count
export PERFORMANCE_ITERATIONS=$ITERATIONS

# Run the 6-skill performance test (CA-001-PT)
echo "🚀 Running 6-skill performance test (CA-001-PT)..."
echo "   Testing with 4 different skill sets, $ITERATIONS iterations total"
pytest test/performance/test_course_availability_performance.py::TestCourseAvailabilityPerformance::test_CA_001_PT_performance -xvs 2>&1 | tee -a "$LOG_FILE"

echo ""
echo "=========================================="
echo "✅ Performance tests completed"
echo "=========================================="

# Check if any JSON reports were generated
if ls test/logs/performance_CA-001-PT_*.json 1> /dev/null 2>&1; then
    echo ""
    echo "📊 Performance Report Generated:"
    ls -la test/logs/performance_CA-001-PT_*.json | tail -1
    
    # Show summary from latest report if jq is available
    if command -v jq &> /dev/null; then
        LATEST_REPORT=$(ls -t test/logs/performance_CA-001-PT_*.json 2>/dev/null | head -1)
        if [ -f "$LATEST_REPORT" ]; then
            echo ""
            echo "📈 Performance Summary (6 skills, 20 iterations):"
            jq '.statistics | {p50_ms, p95_ms, avg_ms, std_dev_ms}' "$LATEST_REPORT" 2>/dev/null
        fi
    fi
fi

echo ""
echo "📝 Full log saved to: $LOG_FILE"