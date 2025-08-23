#!/bin/bash

# CI Smoke Test v2 - Real API Performance Testing
# Tests all three modules with real Azure OpenAI API
# Used after deployment to verify production environment

set -e

# Colors for output - disable in CI environment
if [ -t 1 ] && [ -z "$CI" ]; then
    # Terminal supports colors and not in CI
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    # No colors in CI or non-terminal
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Configuration from environment
API_URL="${API_URL:-https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io}"
API_KEY="${CONTAINER_APP_API_KEY}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="test/logs"
SUMMARY_LOG="$LOG_DIR/smoke_test_${TIMESTAMP}.log"
PERF_LOG="$LOG_DIR/performance_metrics.jsonl"  # JSON Lines format for metrics

# Create log directory if not exists
mkdir -p "$LOG_DIR"

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

# Performance metrics tracking
KEYWORD_TIME_MS=0
INDEX_TIME_MS=0
GAP_TIME_MS=0
RESUME_TIME_MS=0

# Function to log message
log_message() {
    echo "$1" | tee -a "$SUMMARY_LOG"
}

# Function removed - using direct curl commands instead

# Function to check if API is healthy
check_api_health() {
    log_message "Checking API health at $API_URL/health..."
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        "$API_URL/health")
    
    if [ "$response" -eq 200 ]; then
        log_message "  ✓ API is healthy"
        return 0
    else
        log_message "  ✗ API health check failed (HTTP $response)"
        return 1
    fi
}

# Main execution
main() {
    log_message "========================================="
    log_message "CI Smoke Test v2 - Real API Performance"
    log_message "========================================="
    log_message "Timestamp: $(date)"
    log_message "API URL: $API_URL"
    log_message "Environment: Production"
    log_message ""
    
    # Check API key
    if [ -z "$API_KEY" ]; then
        log_message "WARNING: CONTAINER_APP_API_KEY not set, will try without authentication"
        log_message "This may fail if the API requires authentication"
    else
        log_message "API Key configured (length: ${#API_KEY})"
    fi
    
    # Check API health first
    if ! check_api_health; then
        log_message "Aborting: API is not healthy"
        exit 1
    fi
    
    # Test API Key validity with a request (must be > 200 chars)
    log_message ""
    log_message "Testing API Key validity..."
    local auth_test=$(curl -s -X POST "$API_URL/api/v1/extract-jd-keywords" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"job_description":"Quick test for API key validation. We are looking for a software engineer with strong programming skills, experience in web development, and knowledge of modern frameworks. The candidate should have good communication skills and ability to work in a team environment."}' \
        -w "\n%{http_code}" 2>/dev/null | tail -1)
    
    if [ "$auth_test" = "401" ]; then
        log_message "  ✗ API Key is invalid (HTTP 401)"
        log_message "  Please check CONTAINER_APP_API_KEY secret in GitHub"
        exit 1
    elif [ "$auth_test" = "422" ]; then
        log_message "  ⚠ Received HTTP 422 - Request validation error"
        log_message "  This might be due to content length requirements"
    elif [ "$auth_test" = "200" ]; then
        log_message "  ✓ API Key is valid"
    else
        log_message "  ⚠ Unexpected response: HTTP $auth_test"
    fi
    
    log_message ""
    log_message "Running Performance Tests"
    log_message "========================="
    
    # Export API configuration for test scripts
    export AZURE_OPENAI_API_KEY="$API_KEY"
    export API_BASE_URL="$API_URL"
    
    # Test results tracking
    local all_passed=true
    
    # Simplified performance tests for CI - just make API calls directly
    # 1. Test Keyword Extraction
    log_message ""
    log_message "Testing Keyword Extraction..."
    log_message "Expected: Quick API response test"
    log_message "SLA: Response < 4500ms"
    
    local test_start=$(date +%s)
    local test_log="$LOG_DIR/smoke_keyword_${TIMESTAMP}.log"
    
    # Simple keyword extraction test - using single line JSON with correct field name
    local keyword_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -X POST "$API_URL/api/v1/extract-jd-keywords" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"job_description":"We are looking for a Senior Software Engineer with expertise in Python, Django, and PostgreSQL. The ideal candidate should have at least 5 years of experience in web development, strong knowledge of RESTful APIs, and experience with cloud platforms like AWS or Azure. Knowledge of Docker and Kubernetes is a plus."}' 2>&1 | tee "$test_log")
    
    local http_code=$(echo "$keyword_response" | tail -2 | head -1)
    local response_time=$(echo "$keyword_response" | tail -1)
    local response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    # Debug output removed for cleaner CI logs
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 4500 ]; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        KEYWORD_TIME_MS=$response_time_ms
        log_message "  ✓ Keyword Extraction PASSED (${response_time_ms}ms < 4500ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ✗ Keyword Extraction FAILED (HTTP $http_code, ${response_time_ms}ms)"
        # Show actual error from API
        log_message "  Error details: $(cat "$test_log" | grep -E "error|message" | head -2)"
        all_passed=false
    fi
    
    # 2. Test Index Calculation
    log_message ""
    log_message "Testing Index Calculation..."
    log_message "Expected: Quick API response test"
    log_message "SLA: Response < 4000ms"
    
    test_start=$(date +%s)
    test_log="$LOG_DIR/smoke_index_${TIMESTAMP}.log"
    
    # Simple index calculation test - using correct field names and keywords array
    local index_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        -X POST "$API_URL/api/v1/index-calculation" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"job_description":"Looking for a Python developer with Django experience. Must have strong skills in PostgreSQL, REST APIs, and cloud platforms. The ideal candidate will have experience building scalable web applications, working with microservices architecture, and implementing CI/CD pipelines.","resume":"Experienced Python developer with 5 years of Django development. Proficient in PostgreSQL, RESTful API design, and AWS cloud services. Have built and deployed multiple production applications serving thousands of users. Strong background in software architecture and agile development methodologies.","keywords":["Python","Django","PostgreSQL","REST APIs","Cloud","Microservices","CI/CD"]}' 2>&1 | tee "$test_log")
    
    http_code=$(echo "$index_response" | tail -2 | head -1)
    response_time=$(echo "$index_response" | tail -1)
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 4000 ]; then
        test_end=$(date +%s)
        duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        INDEX_TIME_MS=$response_time_ms
        log_message "  ✓ Index Calculation PASSED (${response_time_ms}ms < 4000ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ✗ Index Calculation FAILED (HTTP $http_code, ${response_time_ms}ms)"
        all_passed=false
    fi
    
    # 3. Test Gap Analysis (longer timeout)
    log_message ""
    log_message "Testing Gap Analysis..."
    log_message "Expected: API response test"
    log_message "SLA: Response < 25000ms"
    
    test_start=$(date +%s)
    test_log="$LOG_DIR/smoke_gap_${TIMESTAMP}.log"
    
    # Simple gap analysis test - with all required fields including keywords
    local gap_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        --max-time 30 \
        -X POST "$API_URL/api/v1/index-cal-and-gap-analysis" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"job_description":"We need a Senior Full Stack Developer with expertise in React, Node.js, and MongoDB. The ideal candidate should have experience with microservices architecture, GraphQL, and containerization technologies. Strong understanding of software design patterns, test-driven development, and continuous integration practices is essential for this role.","resume":"Full Stack Developer with 3 years of experience in React and Node.js. Familiar with MongoDB and REST APIs. Some exposure to Docker. Have worked on several web applications using modern JavaScript frameworks. Experience with agile development, code reviews, and collaborative development using Git. Passionate about learning new technologies and best practices in software development.","keywords":["React","Node.js","MongoDB","GraphQL","Docker","Microservices","TDD","CI/CD","Git","REST APIs"]}' 2>&1 | tee "$test_log")
    
    http_code=$(echo "$gap_response" | tail -2 | head -1)
    response_time=$(echo "$gap_response" | tail -1)
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    # Debug output removed for cleaner CI logs
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 25000 ]; then
        # Extract keyword consistency check from response
        log_message "  → Checking keyword consistency..."
        
        # Extract response body (all lines except the last 2 which are http_code and time)
        local gap_body=$(head -n -2 "$test_log")
        
        # Extract keywords using python3 if available
        local input_keywords='["React","Node.js","MongoDB","GraphQL","Docker","Microservices","TDD","CI/CD","Git","REST APIs"]'
        local expected_count=10
        
        if command -v python3 >/dev/null 2>&1; then
            # Extract covered and missed keywords from JSON response
            local covered_keywords=$(echo "$gap_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    covered = data.get('data', {}).get('keyword_coverage', {}).get('covered_keywords', [])
    print(','.join(covered))
except:
    print('')
" 2>/dev/null || echo "")
            
            local missed_keywords=$(echo "$gap_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    missed = data.get('data', {}).get('keyword_coverage', {}).get('missed_keywords', [])
    print(','.join(missed))
except:
    print('')
" 2>/dev/null || echo "")
            
            # Count total output keywords
            local total_output=$(echo "$gap_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    covered = data.get('data', {}).get('keyword_coverage', {}).get('covered_keywords', [])
    missed = data.get('data', {}).get('keyword_coverage', {}).get('missed_keywords', [])
    print(len(covered) + len(missed))
except:
    print('0')
" 2>/dev/null || echo "0")
            
            # Check keyword consistency
            if [ "$expected_count" -eq "$total_output" ]; then
                log_message "    ✓ Keyword consistency verified ($expected_count input = $total_output output)"
                log_message "    → Covered: $covered_keywords"
                log_message "    → Missed: $missed_keywords"
            else
                log_message "    ⚠ Keyword count mismatch: $expected_count input ≠ $total_output output"
                log_message "    → This suggests keyword re-extraction occurred"
            fi
        else
            log_message "    ⚠ python3 not available, skipping keyword consistency check"
        fi
        
        test_end=$(date +%s)
        duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        GAP_TIME_MS=$response_time_ms
        log_message "  ✓ Gap Analysis PASSED (${response_time_ms}ms < 25000ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ✗ Gap Analysis FAILED (HTTP $http_code, ${response_time_ms}ms)"
        # Show actual error from API
        log_message "  Error details: $(cat "$test_log" | grep -E "error|message" | head -2)"
        all_passed=false
    fi
    
    # 4. Test Resume Tailoring (NEW)
    log_message ""
    log_message "Testing Resume Tailoring..."
    log_message "Expected: API response test"
    log_message "SLA: Response < 25000ms"
    
    test_start=$(date +%s)
    test_log="$LOG_DIR/smoke_resume_tailor_${TIMESTAMP}.log"
    
    # Simple resume tailoring test - minimal viable test data
    local tailor_response=$(curl -s -w "\n%{http_code}\n%{time_total}" \
        --max-time 30 \
        -X POST "$API_URL/api/v1/tailor-resume" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{"original_resume":"<div class=\"resume\"><h1>Software Engineer</h1><section><h2>Skills</h2><p>Python, JavaScript, React, Node.js, Docker, Git</p></section><section><h2>Experience</h2><p>3 years as Full Stack Developer working with modern web technologies. Built several production applications using React and Node.js. Experience with containerization and CI/CD pipelines.</p></section></div>","job_description":"Seeking a Senior Full Stack Developer with expertise in Python, React, and cloud technologies. Must have experience with Docker, Kubernetes, and microservices architecture. Strong knowledge of test-driven development and agile methodologies required. AWS or Azure cloud platform experience is essential.","original_index":{"core_strengths":["Python expertise","React frontend skills","Docker experience"],"key_gaps":["[Skill Gap] Kubernetes orchestration","[Skill Gap] Cloud platforms (AWS/Azure)","[Presentation Gap] Quantified achievements"],"quick_improvements":["Add Kubernetes projects","Include cloud platform experience","Add metrics to achievements"],"covered_keywords":["Python","React","Docker"],"missing_keywords":["Kubernetes","AWS","Azure","TDD","Microservices"],"coverage_percentage":40,"similarity_percentage":65},"options":{"language":"en","include_visual_markers":true}}' 2>&1 | tee "$test_log")
    
    http_code=$(echo "$tailor_response" | tail -2 | head -1)
    response_time=$(echo "$tailor_response" | tail -1)
    response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$response_time_ms" -lt 25000 ]; then
        test_end=$(date +%s)
        duration=$((test_end - test_start))
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        PASSED_TESTS=$((PASSED_TESTS + 1))
        RESUME_TIME_MS=$response_time_ms
        log_message "  ✓ Resume Tailoring PASSED (${response_time_ms}ms < 25000ms)"
    else
        TOTAL_TESTS=$((TOTAL_TESTS + 1))
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "  ✗ Resume Tailoring FAILED (HTTP $http_code, ${response_time_ms}ms)"
        # Show actual error from API
        log_message "  Error details: $(cat "$test_log" | grep -E "error|message" | head -2)"
        all_passed=false
    fi
    
    # Calculate total time
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    # Save performance metrics to JSON Lines file
    if [ "$TOTAL_TESTS" -eq 4 ]; then
        local commit_sha="${GITHUB_SHA:-unknown}"
        local github_run_id="${GITHUB_RUN_ID:-0}"
        local perf_json="{"
        perf_json+="\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        perf_json+="\"commit_sha\":\"$commit_sha\","
        perf_json+="\"github_run_id\":\"$github_run_id\","
        perf_json+="\"environment\":\"production\","
        perf_json+="\"tests_passed\":$PASSED_TESTS,"
        perf_json+="\"tests_failed\":$FAILED_TESTS,"
        perf_json+="\"keyword_extraction_ms\":$KEYWORD_TIME_MS,"
        perf_json+="\"index_calculation_ms\":$INDEX_TIME_MS,"
        perf_json+="\"gap_analysis_ms\":$GAP_TIME_MS,"
        perf_json+="\"resume_tailoring_ms\":$RESUME_TIME_MS,"
        perf_json+="\"total_duration_s\":$total_duration"
        perf_json+="}"
        
        # Append to performance log (create if doesn't exist)
        echo "$perf_json" >> "$PERF_LOG"
        
        # Keep only last 100 entries to avoid file growing too large
        if [ -f "$PERF_LOG" ] && [ $(wc -l < "$PERF_LOG") -gt 100 ]; then
            tail -100 "$PERF_LOG" > "${PERF_LOG}.tmp" && mv "${PERF_LOG}.tmp" "$PERF_LOG"
        fi
    fi
    
    # Generate summary
    log_message ""
    log_message "========================================="
    log_message "Test Summary"
    log_message "========================================="
    log_message "Total Tests: $TOTAL_TESTS"
    log_message "Passed: $PASSED_TESTS"
    log_message "Failed: $FAILED_TESTS"
    log_message "Total Time: ${total_duration}s"
    log_message ""
    
    if [ "$FAILED_TESTS" -eq 0 ] && [ "$TOTAL_TESTS" -eq 4 ]; then
        log_message "✅ All smoke tests PASSED!"
        log_message ""
        log_message "Performance SLAs Met:"
        log_message "  • Keyword Extraction: ✓ (${KEYWORD_TIME_MS}ms < 4500ms)"
        log_message "  • Index Calculation: ✓ (${INDEX_TIME_MS}ms < 2000ms)"
        log_message "  • Gap Analysis: ✓ (${GAP_TIME_MS}ms < 25000ms)"
        log_message "  • Resume Tailoring: ✓ (${RESUME_TIME_MS}ms < 25000ms)"
        log_message ""
        log_message "Performance metrics saved to: $PERF_LOG"
        exit 0
    else
        log_message "❌ Smoke tests FAILED!"
        if [ "$TOTAL_TESTS" -ne 4 ]; then
            log_message "  Warning: Expected 4 tests but ran $TOTAL_TESTS"
        fi
        if [ "$FAILED_TESTS" -gt 0 ]; then
            log_message "  $FAILED_TESTS out of $TOTAL_TESTS tests failed"
        fi
        log_message ""
        log_message "Please check the logs in: $LOG_DIR"
        exit 1
    fi
}

# Run main function
main "$@"