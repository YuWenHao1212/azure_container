#!/bin/bash

# Memory Leak Detection Test Runner for Azure Container Apps
# This script runs comprehensive memory leak tests and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../memory" && pwd)"
LOG_DIR="test/logs/memory"
REPORT_DIR="test/reports/memory"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create directories
mkdir -p "$LOG_DIR" "$REPORT_DIR"

echo -e "${BLUE}=== Azure Container Apps Memory Leak Detection ===${NC}"
echo "Test Directory: $TEST_DIR"
echo "Log Directory: $LOG_DIR"
echo "Report Directory: $REPORT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to run memory tests with different configurations
run_memory_tests() {
    local test_name="$1"
    local additional_args="$2"
    local log_file="$LOG_DIR/memory_leak_${test_name}_${TIMESTAMP}.log"
    
    echo -e "${YELLOW}Running $test_name memory leak tests...${NC}"
    
    # Set memory-specific environment variables
    export MEMORY_WARNING_THRESHOLD=100  # Lower threshold for testing
    export MEMORY_CRITICAL_THRESHOLD=200
    export CONTAINER_MEMORY_LIMIT_MB=512  # Simulate smaller container
    
    # Run tests with memory profiling
    if pytest "$TEST_DIR/test_memory_leak_detection.py" \
        --tb=short \
        --capture=no \
        --verbose \
        --durations=10 \
        $additional_args \
        2>&1 | tee "$log_file"; then
        echo -e "${GREEN}✅ $test_name tests passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $test_name tests failed${NC}"
        return 1
    fi
}

# Function to run performance stress tests
run_stress_tests() {
    echo -e "${YELLOW}Running memory stress tests...${NC}"
    
    local stress_log="$LOG_DIR/memory_stress_${TIMESTAMP}.log"
    
    # Run stress tests in background and monitor memory
    python3 -c "
import asyncio
import psutil
import time
import json
from datetime import datetime

async def stress_test():
    '''Simulate heavy memory usage patterns'''
    results = []
    process = psutil.Process()
    
    for iteration in range(50):  # 50 iterations
        # Create memory pressure
        data = []
        for i in range(100):
            # Create objects that simulate API processing
            obj = {
                'resume': 'x' * 1000,  # 1KB per object
                'job_description': 'y' * 1000,
                'keywords': ['keyword'] * 20,
                'embedding': [0.1] * 1536,  # Simulate embedding vector
                'metadata': {'iteration': iteration, 'batch': i}
            }
            data.append(obj)
        
        # Measure memory
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        results.append({
            'iteration': iteration,
            'memory_mb': memory_mb,
            'objects_created': len(data) * iteration,
            'timestamp': datetime.now().isoformat()
        })
        
        # Clear some data (simulate partial cleanup)
        if iteration % 10 == 0:
            data = data[:len(data)//2]  # Keep half
        
        # Small delay
        await asyncio.sleep(0.1)
        
        if iteration % 10 == 0:
            print(f'Iteration {iteration}: {memory_mb:.1f}MB')
    
    return results

# Run the stress test
results = asyncio.run(stress_test())

# Save results
with open('$stress_log', 'w') as f:
    json.dump(results, f, indent=2)
    
print(f'Stress test completed. Results saved to $stress_log')
"
}

# Function to analyze memory test results
analyze_results() {
    echo -e "${YELLOW}Analyzing memory test results...${NC}"
    
    local analysis_report="$REPORT_DIR/memory_analysis_${TIMESTAMP}.md"
    
    python3 -c "
import json
import glob
import os
from datetime import datetime

def analyze_memory_logs():
    '''Analyze memory test logs and generate report'''
    log_files = glob.glob('$LOG_DIR/memory_*_${TIMESTAMP}.log')
    
    report_lines = [
        '# Memory Leak Detection Analysis Report',
        f'**Generated**: {datetime.now().isoformat()}',
        f'**Test Session**: ${TIMESTAMP}',
        '',
        '## Test Summary',
        ''
    ]
    
    total_tests = len(log_files)
    passed_tests = 0
    
    for log_file in log_files:
        test_name = os.path.basename(log_file).replace('.log', '')
        
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
            if 'PASSED' in content and 'FAILED' not in content:
                status = '✅ PASSED'
                passed_tests += 1
            else:
                status = '❌ FAILED'
                
            report_lines.extend([
                f'- **{test_name}**: {status}',
                ''
            ])
            
            # Extract memory growth information
            lines = content.split('\n')
            for line in lines:
                if 'Memory grew by' in line or 'Memory usage' in line:
                    report_lines.append(f'  - {line.strip()}')
                    
        except Exception as e:
            report_lines.append(f'- **{test_name}**: ⚠️  Error analyzing: {e}')
    
    report_lines.extend([
        '',
        '## Overall Results',
        f'- **Total Tests**: {total_tests}',
        f'- **Passed**: {passed_tests}',
        f'- **Failed**: {total_tests - passed_tests}',
        f'- **Success Rate**: {(passed_tests/total_tests)*100:.1f}%' if total_tests > 0 else '- **Success Rate**: N/A',
        '',
        '## Recommendations',
        ''
    ])
    
    if passed_tests == total_tests:
        report_lines.extend([
            '🎉 **All memory leak tests passed!**',
            '',
            '- No significant memory leaks detected',
            '- Resource cleanup appears to be working correctly',
            '- Application is ready for Azure Container Apps deployment',
        ])
    else:
        report_lines.extend([
            '⚠️  **Some memory tests failed**',
            '',
            '- Review failed test logs for specific issues',
            '- Consider implementing additional cleanup mechanisms',
            '- Monitor memory usage closely in production',
        ])
    
    return '\n'.join(report_lines)

# Generate and save report
report_content = analyze_memory_logs()
with open('$analysis_report', 'w') as f:
    f.write(report_content)

print(f'Analysis report generated: $analysis_report')
print()
print(report_content)
"
}

# Main execution
main() {
    local overall_result=0
    
    echo -e "${BLUE}Starting memory leak detection tests...${NC}"
    echo ""
    
    # 1. Basic memory leak tests
    if ! run_memory_tests "basic" ""; then
        overall_result=1
    fi
    
    echo ""
    
    # 2. Concurrent processing tests
    if ! run_memory_tests "concurrent" "-k test_concurrent"; then
        overall_result=1
    fi
    
    echo ""
    
    # 3. Resource cleanup tests
    if ! run_memory_tests "cleanup" "-k test_.*_cleanup"; then
        overall_result=1
    fi
    
    echo ""
    
    # 4. Container-specific tests
    if ! run_memory_tests "container" "-k test_container"; then
        overall_result=1
    fi
    
    echo ""
    
    # 5. Stress tests (optional)
    if [[ "${RUN_STRESS_TESTS:-false}" == "true" ]]; then
        run_stress_tests
        echo ""
    fi
    
    # 6. Analyze results
    analyze_results
    
    echo ""
    echo -e "${BLUE}=== Memory Leak Detection Complete ===${NC}"
    
    if [[ $overall_result -eq 0 ]]; then
        echo -e "${GREEN}🎉 All memory leak tests passed!${NC}"
        echo -e "${GREEN}✅ Application is ready for Azure Container Apps deployment${NC}"
    else
        echo -e "${RED}❌ Some memory tests failed${NC}"
        echo -e "${YELLOW}⚠️  Review test logs and fix memory issues before deployment${NC}"
    fi
    
    echo ""
    echo "📊 Test logs: $LOG_DIR"
    echo "📋 Reports: $REPORT_DIR"
    
    return $overall_result
}

# Handle script arguments
case "${1:-}" in
    "stress")
        echo "Running stress tests only..."
        export RUN_STRESS_TESTS=true
        run_stress_tests
        ;;
    "analyze")
        echo "Analyzing existing results..."
        analyze_results
        ;;
    *)
        main "$@"
        ;;
esac