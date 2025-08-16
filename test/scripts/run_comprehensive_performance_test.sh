#!/bin/bash

# ============================================
# Comprehensive Performance Test Runner
# For /api/v1/index-cal-and-gap-analysis API
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 Index-Cal-Gap-Analysis Performance Test${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if API key is set
if [ -z "$CONTAINER_APP_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: CONTAINER_APP_API_KEY not set${NC}"
    echo "Please set your API key:"
    echo "export CONTAINER_APP_API_KEY=your-api-key"
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/../.."

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Using existing virtual environment${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
fi

# Install required dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install httpx matplotlib pandas numpy

# Create results directory if it doesn't exist
RESULTS_DIR="docs/issues/index-cal-gap-analysis-evolution/performance"
mkdir -p "$RESULTS_DIR"

# Run the performance test
echo -e "${GREEN}🔧 Running comprehensive performance test...${NC}"
echo "This will:"
echo "  • Run 20 unique test cases"
echo "  • Measure detailed timing for each API call"
echo "  • Calculate P50/P95/worst-case statistics"
echo "  • Generate Gantt chart visualization"
echo "  • Save results to $RESULTS_DIR"
echo ""

# Execute the test
python test/performance/test_index_cal_gap_analysis_comprehensive.py

echo -e "${GREEN}✅ Performance test completed!${NC}"
echo -e "Results saved in: ${RESULTS_DIR}"

# List generated files
echo -e "${GREEN}📁 Generated files:${NC}"
ls -la "$RESULTS_DIR" | tail -n +2

echo -e "${GREEN}========================================${NC}"