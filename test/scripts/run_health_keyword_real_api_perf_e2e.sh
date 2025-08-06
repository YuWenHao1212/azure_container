#!/bin/bash

# Real API Test Runner for Health Check and Keyword Extraction
# Tests Performance and E2E functionality with real Azure OpenAI API
# Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup logging - will be set with absolute path in main()
LOG_DIR=""
LOG_FILE=""
TIMESTAMP=""

# Test tracking arrays
PASSED_TESTS=()
FAILED_TESTS=()
SKIPPED_TESTS=()
TEST_TIMES=()
START_TIME=$(date +%s)

# Test categorization
PERFORMANCE_PASSED=()
PERFORMANCE_FAILED=()
E2E_PASSED=()
E2E_FAILED=()

# Module tracking
HEALTH_PASSED=()
HEALTH_FAILED=()
KEYWORD_PASSED=()
KEYWORD_FAILED=()

# Priority tracking
P0_PASSED=()
P0_FAILED=()
P1_PASSED=()
P1_FAILED=()

# Command line options
STAGE_EXEC=""
VERBOSE=false
SHOW_HELP=false
SPECIFIC_PERF_TESTS=""
BACKGROUND_EXEC=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage)
            STAGE_EXEC="$2"
            shift 2
            ;;
        --perf-test)
            SPECIFIC_PERF_TESTS="$2"
            STAGE_EXEC="performance"
            shift 2
            ;;
        --background)
            BACKGROUND_EXEC=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Show help
if [ "$SHOW_HELP" = true ]; then
    echo "Real API Test Runner for Health & Keyword (Performance + E2E)"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --stage <performance|e2e>          Run specific test stage"
    echo "  --perf-test <test-id>              Run specific performance test(s)"
    echo "  --background                       Run tests in background"
    echo "  --verbose                          Show verbose output"
    echo "  --help, -h                         Show this help message"
    echo ""
    echo "Examples:"
    echo "  \$0                                 # Run all 2 tests (1 perf + 1 e2e)"
    echo "  \$0 --stage performance             # Run only performance tests (1 test)"
    echo "  \$0 --stage e2e                     # Run only E2E tests (1 test)"
    echo "  \$0 --perf-test keyword             # Run keyword performance test"
    echo "  \$0 --background                    # Run in background"
    echo ""
    echo "Available Tests:"
    echo "  Performance:"
    echo "    - API-KW-201-PT: Keyword extraction response time (< 15s target)"
    echo "  E2E:"
    echo "    - API-KW-301-E2E: Complete health + keyword workflow"
    echo ""
    echo "⚠️  This script uses REAL Azure OpenAI APIs and will incur costs!"
    exit 0
fi

# Function to log with timestamp
log_message() {
    # Strip ANSI color codes from log messages for clean file output
    local clean_message
    clean_message=$(echo "$1" | sed $'s/\033\[[0-9;]*m//g')
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $clean_message" >> "$LOG_FILE"
}

# Function to log environment info
log_environment_info() {
    log_message "=== ENVIRONMENT INFORMATION ==="
    log_message "Python Version: $(python --version 2>&1)"
    log_message "Working Directory: $(pwd)"
    log_message "Script Version: Health & Keyword Real API Test Runner v1.0"
    log_message "Test Specification: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    log_message "API Endpoint: ${AZURE_OPENAI_ENDPOINT:-Not Set}"
    
    # LLM Configuration
    log_message "LLM Configuration:"
    log_message "  - Keywords Extraction: ${LLM_MODEL_KEYWORDS:-gpt41-mini} @ ${GPT41_MINI_JAPANEAST_ENDPOINT:-Not Set}"
    log_message "  - GPT-4.1 Deployment: ${AZURE_OPENAI_GPT4_DEPLOYMENT:-Not Set}"
    log_message "  - GPT-4.1 Mini Deployment: ${GPT41_MINI_JAPANEAST_DEPLOYMENT:-Not Set}"
    
    log_message "Test Files:"
    log_message "  - Performance: test/performance/test_keyword_extraction_performance.py"
    log_message "  - E2E: test/e2e_standalone/test_health_keyword_e2e.py"
    log_message "Total Tests: 2 (1 Performance + 1 E2E)"
    log_message "================================"
}

# Function to log and print
log_and_print() {
    local message="$1"
    echo -e "$message"
    log_message "$message"
}

# Function to check test priority
get_test_priority() {
    local test_id="$1"
    case $test_id in
        # P0 Priority tests
        "API-KW-201-PT"|"API-KW-301-E2E")
            echo "P0" ;;
        *)
            echo "Unknown" ;;
    esac
}

# Function to clean up old logs
cleanup_old_logs() {
    local test_id="$1"
    local log_pattern="$LOG_DIR/test_health_keyword_real_api_*_${test_id}.log"
    local performance_pattern="$LOG_DIR/performance_${test_id}_*.json"
    
    # Clean test logs
    local logs=($(ls -t $log_pattern 2>/dev/null))
    if [ ${#logs[@]} -gt 5 ]; then
        for i in $(seq 5 $((${#logs[@]} - 1))); do
            rm -f "${logs[$i]}"
            log_message "Removed old log: ${logs[$i]}"
        done
    fi
    
    # Clean performance logs
    local perf_logs=($(ls -t $performance_pattern 2>/dev/null))
    if [ ${#perf_logs[@]} -gt 5 ]; then
        for i in $(seq 5 $((${#perf_logs[@]} - 1))); do
            rm -f "${perf_logs[$i]}"
            log_message "Removed old performance log: ${perf_logs[$i]}"
        done
    fi
}

# Function to run a test and track results
run_test() {
    local test_id="$1"
    local test_path="$2"
    local timeout="${3:-120}"
    local category="$4"
    local module="$5"
    local priority=$(get_test_priority "$test_id")
    
    log_and_print "${BLUE}Running ${test_id} (${priority})...${NC}"
    log_message "TEST START: $test_id - Path: $test_path - Timeout: ${timeout}s - Category: $category - Module: $module"
    
    local test_start=$(date +%s)
    local test_output_file="$LOG_DIR/test_health_keyword_real_api_${TIMESTAMP}_${test_id}.log"
    
    # Determine timeout command
    local timeout_cmd=""
    if command -v gtimeout >/dev/null 2>&1; then
        timeout_cmd="gtimeout ${timeout}s"
    elif command -v timeout >/dev/null 2>&1; then
        timeout_cmd="timeout ${timeout}s"
    else
        timeout_cmd=""
    fi
    
    if [ -n "$timeout_cmd" ]; then
        timeout_exec_cmd="$timeout_cmd python -m pytest"
    else
        timeout_exec_cmd="python -m pytest"
    fi
    
    # Execute test
    if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 > "$test_output_file" 2>&1; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
        log_message "TEST PASSED: $test_id - Duration: ${duration}s"
        PASSED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "performance") PERFORMANCE_PASSED+=("${test_id}") ;;
            "e2e") E2E_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by module
        case $module in
            "health") HEALTH_PASSED+=("${test_id}") ;;
            "keyword") KEYWORD_PASSED+=("${test_id}") ;;
            "combined") KEYWORD_PASSED+=("${test_id}"); HEALTH_PASSED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_PASSED+=("${test_id}") ;;
            "P1") P1_PASSED+=("${test_id}") ;;
        esac
        
        # Clean up successful test log if not verbose
        if [ "$VERBOSE" = false ]; then
            rm -f "$test_output_file"
        fi
        
        # Clean up old logs
        cleanup_old_logs "$test_id"
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TEST_TIMES+=("${test_id}:${duration}s")
        
        echo -e "  ${RED}✗ FAILED${NC} (${duration}s)"
        log_message "TEST FAILED: $test_id - Duration: ${duration}s"
        log_message "ERROR LOG saved to: $test_output_file"
        FAILED_TESTS+=("${test_id}")
        
        # Categorize by type
        case $category in
            "performance") PERFORMANCE_FAILED+=("${test_id}") ;;
            "e2e") E2E_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by module
        case $module in
            "health") HEALTH_FAILED+=("${test_id}") ;;
            "keyword") KEYWORD_FAILED+=("${test_id}") ;;
            "combined") KEYWORD_FAILED+=("${test_id}"); HEALTH_FAILED+=("${test_id}") ;;
        esac
        
        # Categorize by priority
        case $priority in
            "P0") P0_FAILED+=("${test_id}") ;;
            "P1") P1_FAILED+=("${test_id}") ;;
        esac
        
        # Show brief error info
        echo "  Error details saved to: $(basename "$test_output_file")"
        if [ "$VERBOSE" = true ]; then
            echo "  Last few lines of error:"
            tail -10 "$test_output_file" | sed 's/^/    /'
        fi
        
        # Clean up old logs
        cleanup_old_logs "$test_id"
    fi
    echo
}

# Function to setup performance test file if it doesn't exist
setup_performance_test_file() {
    local perf_dir="test/performance"
    local perf_file="$perf_dir/test_keyword_extraction_performance.py"
    
    if [ ! -f "$perf_file" ]; then
        echo "Setting up keyword extraction performance test..."
        mkdir -p "$perf_dir"
        
        cat > "$perf_file" << 'EOF'
"""
Performance tests for keyword extraction - Real Azure OpenAI API.

Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0
Implements API-KW-201-PT: Keyword extraction response time performance test.
"""

import json
import os
import sys
import time
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.main import create_app


class TestKeywordExtractionPerformance:
    """Performance tests for keyword extraction endpoint."""

    @pytest.fixture
    def test_client(self):
        """Create test client without mocking services for real API tests."""
        # Ensure we don't use mocks for performance tests
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def valid_english_jd_request(self):
        """Valid English job description request for performance testing."""
        return {
            "job_description": "We are seeking a Senior Python Developer with extensive experience in building "
                             "scalable web applications using FastAPI and Django frameworks. The ideal candidate "
                             "should have strong knowledge of Docker, Kubernetes, and AWS cloud services. "
                             "Experience with microservices architecture, RESTful APIs, GraphQL, PostgreSQL, "
                             "MongoDB, Redis, and distributed systems is highly valued. Must be proficient in "
                             "CI/CD pipelines, automated testing, and test-driven development methodologies. "
                             "Knowledge of monitoring tools, logging frameworks, and performance optimization "
                             "techniques is essential for this role. The candidate should be comfortable working "
                             "in agile environments and have excellent problem-solving skills.",
            "max_keywords": 15
        }

    def test_API_KW_201_PT_keyword_extraction_response_time(self, test_client, valid_english_jd_request):
        """
        TEST ID: API-KW-201-PT
        測試名稱: 關鍵字提取響應時間效能測試
        優先級: P0
        類型: 效能測試
        測試目標: 驗證關鍵字提取在真實 Azure OpenAI API 下的響應時間
        
        判斷標準:
        - ✅ 響應時間 < 15 秒 (95% 的請求)
        - ✅ HTTP 200 狀態碼
        - ✅ 成功率 ≥ 95%
        - ✅ 返回有效的關鍵字結果
        """
        start_time = datetime.now(timezone.utc)
        
        # Performance test configuration
        test_runs = 5  # Small sample for performance validation
        successful_runs = 0
        response_times = []
        
        # Store results for later analysis
        performance_data = {
            "test_id": "API-KW-201-PT",
            "test_name": "Keyword Extraction Response Time Performance",
            "start_time": start_time.isoformat(),
            "target_response_time_s": 15.0,
            "target_success_rate": 0.95,
            "runs": []
        }
        
        print(f"\n🎯 Running {test_runs} performance test iterations...")
        
        for i in range(test_runs):
            run_start = time.time()
            
            try:
                response = test_client.post(
                    "/api/v1/extract-jd-keywords",
                    json=valid_english_jd_request,
                    headers={"Content-Type": "application/json"}
                )
                
                run_end = time.time()
                response_time = run_end - run_start
                response_times.append(response_time)
                
                # Track run details
                run_data = {
                    "run": i + 1,
                    "response_time_s": response_time,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    successful_runs += 1
                    data = response.json()
                    
                    # Validate response structure
                    assert data["success"] is True
                    assert "data" in data
                    assert "keywords" in data["data"]
                    assert len(data["data"]["keywords"]) > 0
                    
                    # Add response validation info
                    run_data.update({
                        "keywords_count": len(data["data"]["keywords"]),
                        "has_detected_language": "detected_language" in data["data"],
                        "processing_time_ms": data["data"].get("processing_time_ms", 0)
                    })
                    
                    print(f"  Run {i+1}: ✅ {response_time:.3f}s ({len(data['data']['keywords'])} keywords)")
                else:
                    print(f"  Run {i+1}: ❌ {response_time:.3f}s (HTTP {response.status_code})")
                    run_data["error"] = response.text
                
                performance_data["runs"].append(run_data)
                
            except Exception as e:
                run_end = time.time()
                response_time = run_end - run_start
                response_times.append(response_time)
                
                print(f"  Run {i+1}: 💥 {response_time:.3f}s (Exception: {str(e)})")
                
                performance_data["runs"].append({
                    "run": i + 1,
                    "response_time_s": response_time,
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })
            
            # Small delay between requests to avoid rate limiting
            if i < test_runs - 1:
                time.sleep(1)
        
        # Calculate performance metrics
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            p50_time = sorted(response_times)[len(response_times) // 2]
            p95_index = int(len(response_times) * 0.95) - 1
            p95_time = sorted(response_times)[max(0, p95_index)]
            max_time = max(response_times)
            min_time = min(response_times)
        else:
            avg_time = p50_time = p95_time = max_time = min_time = 0
        
        success_rate = successful_runs / test_runs
        
        # Update performance data with metrics
        performance_data.update({
            "end_time": datetime.now(timezone.utc).isoformat(),
            "total_runs": test_runs,
            "successful_runs": successful_runs,
            "success_rate": success_rate,
            "response_times": {
                "min_time_s": min_time,
                "max_time_s": max_time,
                "avg_time_s": avg_time,
                "p50_time_s": p50_time,
                "p95_time_s": p95_time
            }
        })
        
        # Save performance results to JSON
        log_dir = "test/logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        perf_file = f"{log_dir}/performance_API-KW-201-PT_{timestamp}.json"
        
        with open(perf_file, 'w') as f:
            json.dump(performance_data, f, indent=2)
        
        print(f"\n📊 Performance Results:")
        print(f"   Success Rate: {success_rate:.1%} (target: ≥95%)")
        print(f"   Average Time: {avg_time:.3f}s")
        print(f"   P50 Time: {p50_time:.3f}s")
        print(f"   P95 Time: {p95_time:.3f}s (target: <15s)")
        print(f"   Min Time: {min_time:.3f}s")
        print(f"   Max Time: {max_time:.3f}s")
        print(f"   Results saved: {perf_file}")
        
        # Performance assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} below target 95%"
        assert p95_time < 15.0, f"P95 response time {p95_time:.3f}s exceeds target 15s"
        assert successful_runs > 0, "No successful runs completed"
        
        print(f"\n✅ Performance test passed!")
EOF
    fi
}

# Function to setup E2E test file if it doesn't exist
setup_e2e_test_file() {
    local e2e_dir="test/e2e_standalone"
    local e2e_file="$e2e_dir/test_health_keyword_e2e.py"
    
    if [ ! -f "$e2e_file" ]; then
        echo "Setting up health + keyword E2E test..."
        mkdir -p "$e2e_dir"
        touch "$e2e_dir/__init__.py"
        
        cat > "$e2e_file" << 'EOF'
"""
E2E tests for Health Check + Keyword Extraction - Real Azure OpenAI API.

Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0
Implements API-KW-301-E2E: Complete health + keyword workflow test.
"""

import os
import sys
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.main import create_app


class TestHealthKeywordE2E:
    """E2E tests for complete health + keyword workflow."""

    @pytest.fixture
    def test_client(self):
        """Create test client without mocking services for real API tests."""
        # Ensure we don't use mocks for E2E tests
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def valid_traditional_chinese_jd_request(self):
        """Valid Traditional Chinese job description request for E2E testing."""
        return {
            "job_description": "我們正在尋找一位資深的全端工程師，需要具備React前端開發和Python後端開發的豐富經驗。"
                             "理想的候選人應該熟悉FastAPI框架、Docker容器技術和Azure雲端服務的部署。"
                             "必須對微服務架構有深入理解，並且有RESTful API和GraphQL的開發經驗。"
                             "具備CI/CD流程和測試驅動開發經驗者優先考慮。同時需要熟悉分散式系統設計，"
                             "具備系統架構規劃能力和優秀的團隊合作精神。需要至少五年以上的軟體開發經驗，"
                             "能夠在快節奏的敏捷開發環境中獨立工作。必須具備良好的溝通能力和問題解決技能，"
                             "並能夠指導初級工程師的技術成長。對於新技術學習有熱忱，能夠持續提升個人技能。",
            "max_keywords": 12
        }

    def test_API_KW_301_E2E_complete_health_keyword_workflow(self, test_client, valid_traditional_chinese_jd_request):
        """
        TEST ID: API-KW-301-E2E
        測試名稱: 完整健康檢查 + 關鍵字提取工作流程
        優先級: P0
        類型: E2E 測試
        測試目標: 驗證系統健康檢查和關鍵字提取的完整端對端流程
        
        判斷標準:
        1. 健康檢查端點正常運作
        2. 關鍵字提取能夠處理繁體中文 JD
        3. 系統在真實 API 環境下穩定運作
        4. 所有回應格式正確且完整
        """
        print("\n🔍 Starting complete Health + Keyword E2E workflow test...")
        
        # Step 1: Health Check Validation
        print("  Step 1: Testing health check endpoint...")
        health_start = time.time()
        health_response = test_client.get("/health")
        health_duration = time.time() - health_start
        
        # Validate health check response
        assert health_response.status_code == 200, f"Health check failed with status {health_response.status_code}"
        health_data = health_response.json()
        assert health_data["success"] is True, "Health check success field is not True"
        assert "data" in health_data, "Health check missing data field"
        assert health_data["data"]["status"] == "healthy", "Health status is not healthy"
        
        print(f"    ✅ Health check passed in {health_duration:.3f}s")
        
        # Step 2: Keyword Extraction with Traditional Chinese
        print("  Step 2: Testing keyword extraction with Traditional Chinese JD...")
        keyword_start = time.time()
        
        keyword_response = test_client.post(
            "/api/v1/extract-jd-keywords",
            json=valid_traditional_chinese_jd_request,
            headers={"Content-Type": "application/json"}
        )
        keyword_duration = time.time() - keyword_start
        
        # Validate keyword extraction response
        assert keyword_response.status_code == 200, f"Keyword extraction failed with status {keyword_response.status_code}"
        keyword_data = keyword_response.json()
        assert keyword_data["success"] is True, "Keyword extraction success field is not True"
        assert "data" in keyword_data, "Keyword extraction missing data field"
        
        # Validate keyword data structure
        kw_data = keyword_data["data"]
        required_fields = ["keywords", "keyword_count", "detected_language", "processing_time_ms"]
        for field in required_fields:
            assert field in kw_data, f"Missing required field: {field}"
        
        # Validate Traditional Chinese language detection
        assert kw_data["detected_language"] == "zh-TW", f"Expected zh-TW, got {kw_data['detected_language']}"
        
        # Validate keywords content
        keywords = kw_data["keywords"]
        assert isinstance(keywords, list), "Keywords should be a list"
        assert len(keywords) > 0, "Keywords list should not be empty"
        assert kw_data["keyword_count"] == len(keywords), "Keyword count mismatch"
        
        # Validate Traditional Chinese keywords are present
        chinese_keywords_found = 0
        for keyword in keywords:
            if any('\u4e00' <= char <= '\u9fff' for char in keyword):  # Chinese character range
                chinese_keywords_found += 1
        
        assert chinese_keywords_found > 0, "No Traditional Chinese keywords found in results"
        
        print(f"    ✅ Keyword extraction passed in {keyword_duration:.3f}s")
        print(f"    📋 Extracted {len(keywords)} keywords ({chinese_keywords_found} Chinese)")
        
        # Step 3: System Integration Validation
        print("  Step 3: Validating system integration...")
        
        # Check that the system handles both endpoints consistently
        total_time = health_duration + keyword_duration
        assert total_time < 30.0, f"Total workflow time {total_time:.3f}s exceeds 30s limit"
        
        # Validate response consistency
        assert health_data["timestamp"], "Health check missing timestamp"
        assert keyword_data["timestamp"], "Keyword extraction missing timestamp"
        
        # Check for proper error handling structure (even in success cases)
        assert "error" in health_data, "Health check missing error field"
        assert "error" in keyword_data, "Keyword extraction missing error field"
        assert health_data["error"] is None, "Health check error should be null on success"
        assert keyword_data["error"] is None, "Keyword extraction error should be null on success"
        
        # Step 4: Advanced Validation - Language Detection Accuracy
        print("  Step 4: Validating language detection accuracy...")
        
        # Check if prompt version indicates Traditional Chinese processing
        if "prompt_version_used" in kw_data:
            prompt_version = kw_data["prompt_version_used"]
            assert "zh-TW" in prompt_version or "chinese" in prompt_version.lower(), \
                f"Prompt version '{prompt_version}' doesn't indicate Chinese processing"
        
        # Validate processing time is reasonable for real API
        processing_time_s = kw_data["processing_time_ms"] / 1000.0
        assert processing_time_s < 20.0, f"Processing time {processing_time_s:.3f}s too high"
        assert processing_time_s > 0.5, f"Processing time {processing_time_s:.3f}s suspiciously low"
        
        print(f"    ✅ Language detection validated (processing time: {processing_time_s:.3f}s)")
        
        # Final Summary
        print("\n📊 E2E Test Summary:")
        print(f"   Health Check: ✅ {health_duration:.3f}s")
        print(f"   Keyword Extraction: ✅ {keyword_duration:.3f}s")
        print(f"   Total Workflow Time: {total_time:.3f}s")
        print(f"   Detected Language: {kw_data['detected_language']}")
        print(f"   Keywords Extracted: {len(keywords)} total, {chinese_keywords_found} Chinese")
        print(f"   Sample Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
        
        # Save E2E test summary
        log_dir = "test/logs"
        os.makedirs(log_dir, exist_ok=True)
        summary_file = f"{log_dir}/e2e_field_validation_API-KW-301-E2E.txt"
        
        with open(summary_file, 'w') as f:
            f.write("API-KW-301-E2E Field Validation Summary:\n")
            f.write(f"Health Check Duration: {health_duration:.3f}s\n")
            f.write(f"Keyword Processing Time: {processing_time_s:.3f}s\n")
            f.write(f"Total Workflow Time: {total_time:.3f}s\n")
            f.write(f"Detected Language: {kw_data['detected_language']}\n")
            f.write(f"Keywords Count: {len(keywords)}\n")
            f.write(f"Chinese Keywords: {chinese_keywords_found}\n")
        
        print(f"   Summary saved: {summary_file}")
        print("\n🎉 Complete E2E workflow test passed!")
EOF
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running Performance Tests (1 test)${NC}"
    echo "Testing file: test/performance/test_keyword_extraction_performance.py"
    echo "⚠️  Performance tests may take longer and use real Azure OpenAI APIs"
    echo
    
    # Ensure performance test file exists
    setup_performance_test_file
    
    # Performance test configurations
    local performance_tests=(
        "API-KW-201-PT:test/performance/test_keyword_extraction_performance.py::TestKeywordExtractionPerformance::test_keyword_extraction_performance"
    )
    
    # Check if specific tests requested
    if [ -n "$SPECIFIC_PERF_TESTS" ]; then
        echo -e "${BLUE}Running Specific Performance Tests: $SPECIFIC_PERF_TESTS${NC}"
        
        # Convert comma-separated list to array
        IFS=',' read -ra TEST_IDS <<< "$SPECIFIC_PERF_TESTS"
        
        # Run only specified tests
        for test_id in "${TEST_IDS[@]}"; do
            # Trim whitespace
            test_id=$(echo "$test_id" | xargs)
            
            # Convert shortcuts
            case "$test_id" in
                "keyword"|"kw"|"API-KW-201-PT")
                    test_id="API-KW-201-PT"
                    ;;
            esac
            
            # Find matching test entry
            for test_entry in "${performance_tests[@]}"; do
                if [[ "$test_entry" == "$test_id:"* ]]; then
                    local test_path="${test_entry#*:}"
                    run_test "$test_id" "$test_path" 180 "performance" "keyword"
                    break
                fi
            done
        done
    else
        # Run all performance tests
        for test_entry in "${performance_tests[@]}"; do
            local test_id="${test_entry%%:*}"
            local test_path="${test_entry#*:}"
            run_test "$test_id" "$test_path" 180 "performance" "keyword"
        done
    fi
}

# Function to run E2E tests
run_e2e_tests() {
    echo -e "${BLUE}Running E2E Tests (1 test)${NC}"
    echo "Testing file: test/e2e_standalone/test_health_keyword_e2e.py"
    echo "⚠️  E2E tests use real Azure OpenAI API"
    echo
    
    # Ensure e2e_standalone directory and test file exist
    setup_e2e_test_file
    
    # Change to test directory for E2E tests
    cd test/e2e_standalone
    
    # E2E test configurations
    local e2e_tests=(
        "API-KW-301-E2E:test_health_keyword_e2e.py::TestHealthKeywordE2E::test_API_KW_301_E2E_complete_health_keyword_workflow"
    )
    
    # Run E2E tests with proper isolation
    for test_entry in "${e2e_tests[@]}"; do
        local test_id="${test_entry%%:*}"
        local test_path="${test_entry#*:}"
        
        # Set environment variables for E2E
        export PYTEST_CURRENT_TEST_TYPE="e2e"
        export REAL_E2E_TEST="true"
        
        log_and_print "${BLUE}Running ${test_id}...${NC}"
        local test_start=$(date +%s)
        local test_output_file="$LOG_DIR/test_health_keyword_real_api_${TIMESTAMP}_${test_id}.log"
        
        # Determine timeout command
        local timeout_cmd=""
        if command -v gtimeout >/dev/null 2>&1; then
            timeout_cmd="gtimeout 120s"
        elif command -v timeout >/dev/null 2>&1; then
            timeout_cmd="timeout 120s"
        else
            timeout_cmd=""
        fi
        
        if [ -n "$timeout_cmd" ]; then
            timeout_exec_cmd="$timeout_cmd python -m pytest"
        else
            timeout_exec_cmd="python -m pytest"
        fi
        
        if $timeout_exec_cmd "${test_path}" -v --tb=short --durations=0 --confcutdir=. > "$test_output_file" 2>&1; then
            local test_end=$(date +%s)
            local duration=$((test_end - test_start))
            TEST_TIMES+=("${test_id}:${duration}s")
            
            echo -e "  ${GREEN}✓ PASSED${NC} (${duration}s)"
            log_message "TEST PASSED: $test_id - Duration: ${duration}s"
            PASSED_TESTS+=("${test_id}")
            E2E_PASSED+=("${test_id}")
            P0_PASSED+=("${test_id}")
            HEALTH_PASSED+=("${test_id}")
            KEYWORD_PASSED+=("${test_id}")
            
            if [ "$VERBOSE" = false ]; then
                rm -f "$test_output_file"
            fi
        else
            local test_end=$(date +%s)
            local duration=$((test_end - test_start))
            TEST_TIMES+=("${test_id}:${duration}s")
            
            echo -e "  ${RED}✗ FAILED${NC} (${duration}s)"
            log_message "TEST FAILED: $test_id - Duration: ${duration}s"
            FAILED_TESTS+=("${test_id}")
            E2E_FAILED+=("${test_id}")
            P0_FAILED+=("${test_id}")
            HEALTH_FAILED+=("${test_id}")
            KEYWORD_FAILED+=("${test_id}")
            
            echo "  Error details saved to: $(basename "$test_output_file")"
            if [ "$VERBOSE" = true ]; then
                echo "  Last few lines of error:"
                tail -10 "$test_output_file" | sed 's/^/    /'
            fi
        fi
        echo
    done
    
    # Clean up environment variables
    unset PYTEST_CURRENT_TEST_TYPE
    unset REAL_E2E_TEST
    
    # Return to project root
    cd "$PROJECT_ROOT"
}

# Function to read performance results
read_performance_results() {
    local test_id="$1"
    local log_pattern="$LOG_DIR/performance_${test_id}_*.json"
    local latest_log=$(ls -t $log_pattern 2>/dev/null | head -n1)
    
    if [ -f "$latest_log" ]; then
        # Extract key metrics from JSON log
        local p50=$(grep -o '"p50_time_s": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        local p95=$(grep -o '"p95_time_s": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        local success_rate=$(grep -o '"success_rate": [0-9.]*' "$latest_log" 2>/dev/null | cut -d' ' -f2)
        
        echo "${p50:-N/A}|${p95:-N/A}|${success_rate:-N/A}"
    else
        echo "N/A|N/A|N/A"
    fi
}

# Function to format performance results table
format_performance_results() {
    echo
    echo "=== 效能測試詳細結果 ==="
    echo
    echo "| 測試編號 | 測試名稱 | P50 (秒) | P95 (秒) | 成功率 | 目標 | 狀態 |"
    echo "|----------|----------|----------|----------|--------|------|------|"
    
    # API-KW-201-PT
    local result=$(read_performance_results "API-KW-201-PT")
    IFS='|' read -r p50 p95 success_rate <<< "$result"
    
    local status="✅"
    if [[ " ${FAILED_TESTS[@]} " =~ " API-KW-201-PT " ]]; then
        status="❌"
    elif [ "$p95" != "N/A" ] && (( $(echo "$p95 > 15" | bc -l 2>/dev/null || echo "0") )); then
        status="❌"
    fi
    
    # Convert decimal to percentage for display
    local success_rate_pct=$(echo "${success_rate:-0} * 100" | bc -l 2>/dev/null || echo "0")
    
    printf "| API-KW-201-PT | 關鍵字提取響應時間 | %.3f | %.3f | %.1f%% | < 15s | %s |\n" \
        "${p50:-0}" "${p95:-0}" "${success_rate_pct}" "$status"
    
    echo
}

# Function to generate report
generate_report() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    echo
    echo "==============================================="
    echo "Health & Keyword Real API 測試報告 (Performance + E2E)"
    echo "==============================================="
    echo "執行日期: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "測試規格: TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0"
    echo "測試總數: 2 個測試案例 (1 Performance + 1 E2E)"
    echo "執行環境: $(python --version 2>&1 | cut -d' ' -f2)"
    echo "總執行時間: ${total_duration}s"
    echo "日誌檔案: $(basename "$LOG_FILE")"
    echo
    
    # Test summary
    local total_tests=$((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]} + ${#SKIPPED_TESTS[@]}))
    local pass_rate=0
    if [ $total_tests -gt 0 ]; then
        pass_rate=$(( ${#PASSED_TESTS[@]} * 100 / total_tests ))
    fi
    
    echo "測試檔案清單"
    echo "------------"
    echo "效能測試 (1個測試):"
    echo "  - test/performance/test_keyword_extraction_performance.py"
    echo ""
    echo "E2E測試 (1個測試):"
    echo "  - test/e2e_standalone/test_health_keyword_e2e.py"
    echo
    
    echo "測試摘要"
    echo "--------"
    echo "總測試數: $total_tests / 2"
    echo "通過: ${#PASSED_TESTS[@]} (${pass_rate}%)"
    echo "失敗: ${#FAILED_TESTS[@]}"
    echo "跳過: ${#SKIPPED_TESTS[@]}"
    echo
    
    # Detailed test type statistics
    echo "測試類型統計"
    echo "------------"
    local performance_total=$((${#PERFORMANCE_PASSED[@]} + ${#PERFORMANCE_FAILED[@]}))
    local e2e_total=$((${#E2E_PASSED[@]} + ${#E2E_FAILED[@]}))
    
    local performance_rate=0
    local e2e_rate=0
    
    if [ $performance_total -gt 0 ]; then
        performance_rate=$(( ${#PERFORMANCE_PASSED[@]} * 100 / performance_total ))
    fi
    if [ $e2e_total -gt 0 ]; then
        e2e_rate=$(( ${#E2E_PASSED[@]} * 100 / e2e_total ))
    fi
    
    echo "效能測試 (Performance): ${#PERFORMANCE_PASSED[@]}/${performance_total} (${performance_rate}%)"
    echo "端對端測試 (E2E): ${#E2E_PASSED[@]}/${e2e_total} (${e2e_rate}%)"
    echo
    
    # Module statistics
    echo "模組統計"
    echo "--------"
    local health_total=$((${#HEALTH_PASSED[@]} + ${#HEALTH_FAILED[@]}))
    local keyword_total=$((${#KEYWORD_PASSED[@]} + ${#KEYWORD_FAILED[@]}))
    
    local health_rate=0
    local keyword_rate=0
    
    if [ $health_total -gt 0 ]; then
        health_rate=$(( ${#HEALTH_PASSED[@]} * 100 / health_total ))
    fi
    if [ $keyword_total -gt 0 ]; then
        keyword_rate=$(( ${#KEYWORD_PASSED[@]} * 100 / keyword_total ))
    fi
    
    echo "健康檢查 (Health): ${#HEALTH_PASSED[@]}/${health_total} (${health_rate}%)"
    echo "關鍵字提取 (Keyword): ${#KEYWORD_PASSED[@]}/${keyword_total} (${keyword_rate}%)"
    echo
    
    # Priority statistics
    echo "優先級統計"
    echo "----------"
    local p0_total=$((${#P0_PASSED[@]} + ${#P0_FAILED[@]}))
    local p1_total=$((${#P1_PASSED[@]} + ${#P1_FAILED[@]}))
    
    local p0_rate=0
    local p1_rate=0
    
    if [ $p0_total -gt 0 ]; then
        p0_rate=$(( ${#P0_PASSED[@]} * 100 / p0_total ))
    fi
    if [ $p1_total -gt 0 ]; then
        p1_rate=$(( ${#P1_PASSED[@]} * 100 / p1_total ))
    fi
    
    echo "P0 (Critical): ${#P0_PASSED[@]}/${p0_total} (${p0_rate}%)"
    echo "P1 (Important): ${#P1_PASSED[@]}/${p1_total} (${p1_rate}%)"
    echo
    
    # Detailed table
    echo "=== 詳細測試統計表 ==="
    echo
    echo "| 測試類型     | 通過/總數 | 成功率 | 失敗測試案例 |"
    echo "|--------------|-----------|--------|--------------|"
    echo "| 健康檢查     | ${#HEALTH_PASSED[@]}/${health_total} | ${health_rate}% | $(IFS=','; echo "${HEALTH_FAILED[*]}") |"
    echo "| 關鍵字提取   | ${#KEYWORD_PASSED[@]}/${keyword_total} | ${keyword_rate}% | $(IFS=','; echo "${KEYWORD_FAILED[*]}") |"
    echo "| 效能測試     | ${#PERFORMANCE_PASSED[@]}/${performance_total} | ${performance_rate}% | $(IFS=','; echo "${PERFORMANCE_FAILED[*]}") |"
    echo "| 端對端測試   | ${#E2E_PASSED[@]}/${e2e_total} | ${e2e_rate}% | $(IFS=','; echo "${E2E_FAILED[*]}") |"
    echo "| **總計**     | **${#PASSED_TESTS[@]}/${total_tests}** | **${pass_rate}%** | $(IFS=','; echo "${FAILED_TESTS[*]}") |"
    echo
    
    # Show performance test results if any were run
    if [ ${#PERFORMANCE_PASSED[@]} -gt 0 ] || [ ${#PERFORMANCE_FAILED[@]} -gt 0 ]; then
        format_performance_results
    fi
    
    # Show E2E field validation summaries if available
    if [ ${#E2E_PASSED[@]} -gt 0 ] || [ ${#E2E_FAILED[@]} -gt 0 ]; then
        echo
        echo "=== E2E 測試欄位驗證結果 ==="
        echo
        
        local e2e_summary_file="$LOG_DIR/e2e_field_validation_API-KW-301-E2E.txt"
        if [ -f "$e2e_summary_file" ]; then
            echo "📋 **API-KW-301-E2E** 回應欄位驗證摘要："
            echo
            # Display the summary content with proper formatting
            while IFS= read -r line; do
                if [[ "$line" == "API-KW-301-E2E Field Validation Summary:" ]]; then
                    continue  # Skip the header line
                elif [[ "$line" == "Health Check Duration:"* ]]; then
                    echo "   🏥 健康檢查時間: $(echo "$line" | cut -d':' -f2 | xargs)"
                elif [[ "$line" == "Keyword Processing Time:"* ]]; then
                    echo "   ⏱️  關鍵字處理時間: $(echo "$line" | cut -d':' -f2 | xargs)"
                elif [[ "$line" == "Total Workflow Time:"* ]]; then
                    echo "   🕐 總工作流程時間: $(echo "$line" | cut -d':' -f2 | xargs)"
                elif [[ "$line" == "Detected Language:"* ]]; then
                    echo "   🌐 偵測語言: $(echo "$line" | cut -d':' -f2 | xargs)"
                elif [[ "$line" == "Keywords Count:"* ]]; then
                    echo "   📝 關鍵字數量: $(echo "$line" | cut -d':' -f2 | xargs)"
                elif [[ "$line" == "Chinese Keywords:"* ]]; then
                    echo "   🈳 中文關鍵字: $(echo "$line" | cut -d':' -f2 | xargs)"
                fi
            done < "$e2e_summary_file"
            echo
        else
            echo "   ⚠️  未找到 API-KW-301-E2E 的欄位驗證摘要"
            echo
        fi
    fi
    
    # Show failed tests for debugging
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo "失敗的測試案例詳情:"
        echo "-------------------"
        for test_id in "${FAILED_TESTS[@]}"; do
            local priority=$(get_test_priority "$test_id")
            echo "❌ $test_id ($priority) - 日誌: $LOG_DIR/test_health_keyword_real_api_*_${test_id}.log"
        done
        echo
        echo "修復建議:"
        echo "1. 檢查 Azure OpenAI API 密鑰和端點配置"
        echo "2. 確認網路連接和服務可用性"
        echo "3. 檢查 API 配額和速率限制"
        echo "4. 查看詳細錯誤日誌進行除錯"
        echo
    fi
    
    # Success celebration or failure summary
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "🎉 ${GREEN}所有 Health & Keyword Real API 測試全部通過！${NC}"
        echo "   Performance 和 E2E 測試都成功使用真實 Azure OpenAI API"
    else
        log_and_print "❌ ${RED}${#FAILED_TESTS[@]} 個測試失敗，總成功率: ${pass_rate}%${NC}"
        if [ ${#P0_FAILED[@]} -gt 0 ]; then
            echo "   ⚠️  有 ${#P0_FAILED[@]} 個 P0 (Critical) 測試失敗，需要優先修復"
        fi
    fi
}

# Main execution
main() {
    # Get script directory and project root
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Setup logging with absolute path
    LOG_DIR="$PROJECT_ROOT/test/logs"
    mkdir -p "$LOG_DIR"
    # Generate timestamp once for consistent naming
    TIMESTAMP=$(date +%Y%m%d_%H%M)
    LOG_FILE="$LOG_DIR/test_health_keyword_real_api_${TIMESTAMP}.log"
    
    # Initialize logging
    log_message "=== Health & Keyword Real API Test Suite Started ==="
    log_message "Testing Performance and E2E with real Azure OpenAI APIs"
    
    echo -e "${BLUE}=== Health & Keyword Real API Test Suite (Performance + E2E) ===${NC}"
    echo "Timestamp: $(date)"
    echo "Log file: $(basename "$LOG_FILE")"
    echo "⚠️  This uses REAL Azure OpenAI APIs and will incur costs!"
    echo
    
    # Environment check
    echo -e "${BLUE}Environment Check${NC}"
    if [ ! -f ".env" ]; then
        echo -e "  ${RED}❌ Error: .env file not found${NC}"
        log_message "ERROR: .env file not found"
        exit 1
    fi
    
    # Load environment variables
    source .env
    
    # Check API keys
    if [ -z "$AZURE_OPENAI_API_KEY" ] && [ -z "$GPT41_MINI_JAPANEAST_API_KEY" ]; then
        echo -e "  ${RED}❌ Error: No Azure OpenAI API keys found in .env${NC}"
        log_message "ERROR: No Azure OpenAI API keys configured"
        exit 1
    fi
    
    # Log environment info after loading .env and validating
    log_environment_info
    
    # Start API server for performance and E2E tests
    echo -e "${BLUE}Starting API Server${NC}"
    API_PID=""
    
    # Set up cleanup trap
    cleanup_api() {
        if [ -n "$API_PID" ]; then
            echo -e "
${BLUE}Cleaning up...${NC}"
            kill $API_PID 2>/dev/null
            wait $API_PID 2>/dev/null
            echo -e "  ${GREEN}✓${NC} API server stopped"
        fi
    }
    trap cleanup_api EXIT
    
    # Check if API is already running
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} API already running on port 8000"
        log_message "API already running on port 8000"
    else
        echo -e "  Starting API server on port 8000..."
        log_message "Starting API server..."
        
        # Start the API in background with environment variables
        # Load environment variables for the uvicorn process
        set -a  # automatically export all variables
        source .env
        set +a  # stop automatically exporting
        
        uvicorn src.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api_server_${TIMESTAMP}.log" 2>&1 &
        API_PID=$!
        
        # Wait for API to be ready (max 30 seconds)
        echo -n "  Waiting for API to be ready"
        for i in {1..30}; do
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo -e " ${GREEN}✓${NC}"
                echo -e "  ${GREEN}✓${NC} API server started (PID: $API_PID)"
                log_message "API server started successfully (PID: $API_PID)"
                break
            fi
            echo -n "."
            sleep 1
        done
        
        # Check if API started successfully
        if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e " ${RED}✗${NC}"
            echo -e "  ${RED}❌ Failed to start API server${NC}"
            log_message "ERROR: Failed to start API server"
            [ -n "$API_PID" ] && kill $API_PID 2>/dev/null
            exit 1
        fi
    fi
    
    echo -e "  Environment: ${GREEN}✓ .env file found${NC}"
    echo -e "  API Key: ${GREEN}✓ Azure OpenAI key configured${NC}"
    echo -e "  Python: $(python --version 2>&1)"
    echo -e "  Working Directory: $(pwd)"
    echo
    
    # Execute based on stage or run all tests
    case "$STAGE_EXEC" in
        "performance")
            run_performance_tests
            ;;
        "e2e")
            run_e2e_tests
            ;;
        "")
            # Run all tests in order
            run_performance_tests
            run_e2e_tests
            ;;
        *)
            echo -e "${RED}Unknown stage: $STAGE_EXEC${NC}"
            echo "Valid stages: performance, e2e"
            exit 1
            ;;
    esac
    
    # Generate report
    generate_report
    
    # Clean up API server if we started it
    if [ -n "$API_PID" ]; then
        echo -e "${BLUE}Stopping API server${NC}"
        kill $API_PID 2>/dev/null
        wait $API_PID 2>/dev/null
        echo -e "  ${GREEN}✓${NC} API server stopped"
        log_message "API server stopped (PID: $API_PID)"
    fi
    
    # Log test summary before completion
    log_message "=== TEST SUMMARY ==="
    log_message "Total Tests Run: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
    log_message "Passed: ${#PASSED_TESTS[@]} - ${PASSED_TESTS[*]}"
    log_message "Failed: ${#FAILED_TESTS[@]} - ${FAILED_TESTS[*]}"
    log_message "Health Tests: ${#HEALTH_PASSED[@]} passed, ${#HEALTH_FAILED[@]} failed"
    log_message "Keyword Tests: ${#KEYWORD_PASSED[@]} passed, ${#KEYWORD_FAILED[@]} failed"
    log_message "Performance Tests: ${#PERFORMANCE_PASSED[@]} passed, ${#PERFORMANCE_FAILED[@]} failed"
    log_message "E2E Tests: ${#E2E_PASSED[@]} passed, ${#E2E_FAILED[@]} failed"
    
    # Create consolidated performance JSON if performance tests were run
    if [ ${#PERFORMANCE_PASSED[@]} -gt 0 ] || [ ${#PERFORMANCE_FAILED[@]} -gt 0 ]; then
        create_consolidated_performance_json
    fi
    
    log_message "=== Test Suite Completed ==="
    
    # Final result
    if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
        log_and_print "${GREEN}🎉 All Health & Keyword Real API tests passed!${NC}"
        exit 0
    else
        log_and_print "${RED}❌ ${#FAILED_TESTS[@]} tests failed. Check logs for details.${NC}"
        exit 1
    fi
}

# Function to create consolidated performance JSON
create_consolidated_performance_json() {
    local consolidated_file="$LOG_DIR/test_health_keyword_real_api_${TIMESTAMP}_summary.json"
    
    echo '{' > "$consolidated_file"
    echo '  "test_suite": "Health & Keyword Extraction Performance",' >> "$consolidated_file"
    echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$consolidated_file"
    echo '  "environment": {' >> "$consolidated_file"
    echo '    "python_version": "'$(python --version 2>&1 | cut -d' ' -f2)'",' >> "$consolidated_file"
    echo '    "api_endpoint": "'${AZURE_OPENAI_ENDPOINT:-Not Set}'",' >> "$consolidated_file"
    echo '    "gpt41_mini_endpoint": "'${GPT41_MINI_JAPANEAST_ENDPOINT:-Not Set}'"' >> "$consolidated_file"
    echo '  },' >> "$consolidated_file"
    echo '  "summary": {' >> "$consolidated_file"
    echo '    "total_tests": '$(ls -1 $LOG_DIR/performance_API-KW-*-PT_*.json 2>/dev/null | wc -l | xargs)',' >> "$consolidated_file"
    echo '    "passed": '${#PERFORMANCE_PASSED[@]}',' >> "$consolidated_file"
    echo '    "failed": '${#PERFORMANCE_FAILED[@]} >> "$consolidated_file"
    echo '  },' >> "$consolidated_file"
    echo '  "tests": [' >> "$consolidated_file"
    
    # Add individual test results
    local first=true
    for json_file in $(ls -t $LOG_DIR/performance_API-KW-*-PT_*.json 2>/dev/null | head -5); do
        if [ "$first" = true ]; then
            first=false
        else
            echo ',' >> "$consolidated_file"
        fi
        # Include the full JSON content of each test
        cat "$json_file" >> "$consolidated_file"
    done
    
    echo '' >> "$consolidated_file"
    echo '  ]' >> "$consolidated_file"
    echo '}' >> "$consolidated_file"
    
    log_message "Created consolidated performance summary: $(basename "$consolidated_file")"
    
    # Clean up individual performance JSON files after consolidation
    for json_file in $(ls $LOG_DIR/performance_API-KW-*-PT_*.json 2>/dev/null); do
        rm -f "$json_file"
        log_message "Removed individual performance JSON: $(basename "$json_file")"
    done
}

# Handle background execution
if [ "$BACKGROUND_EXEC" = true ]; then
    echo "Running Health & Keyword Real API tests in background..."
    echo "Log file: $LOG_FILE"
    echo "Monitor with: tail -f $LOG_FILE"
    main &
    echo "Background process PID: $!"
else
    main
fi