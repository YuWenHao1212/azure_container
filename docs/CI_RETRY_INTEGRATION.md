# CI/CD Retry Mechanism for Keyword Extraction

## Overview
This document describes how to integrate retry logic for the Keyword Extraction API test in your CI/CD pipeline to handle transient performance issues.

## Problem
- Keyword Extraction occasionally exceeds the 4500ms SLA due to Azure OpenAI service latency
- This causes false-positive CI failures
- Most of the time, a retry succeeds within the SLA

## Solution
Implement a retry mechanism that:
1. Tests Keyword Extraction normally
2. If it exceeds 4500ms, automatically retries once
3. Only fails the CI if BOTH attempts exceed the SLA

## Integration Options

### Option 1: Update Existing Shell Script
If your CI uses a shell script, add this retry logic:

```bash
# Function to test keyword extraction with timing
test_keyword_extraction() {
    local attempt=$1
    local start_time=$(date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000)))
    
    # Make API call
    local response=$(curl -s -w "\n%{http_code}" -X POST \
        "${API_URL}/api/v1/extract-jd-keywords" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "${KEYWORD_TEST_DATA}" \
        --max-time 30)
    
    local end_time=$(date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000)))
    local response_time=$((end_time - start_time))
    local http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] && [ "$response_time" -lt 4500 ]; then
        echo "✓ Attempt $attempt: ${response_time}ms"
        return 0
    elif [ "$http_code" = "200" ]; then
        echo "⚠️ Attempt $attempt: ${response_time}ms (exceeded SLA)"
        return 1
    else
        echo "✗ Attempt $attempt: HTTP $http_code"
        return 2
    fi
}

# Test with retry
echo "Testing Keyword Extraction..."
if test_keyword_extraction 1; then
    echo "✅ PASS: First attempt within SLA"
else
    echo "Retrying..."
    sleep 3
    if test_keyword_extraction 2; then
        echo "✅ PASS: Second attempt within SLA"
    else
        echo "❌ FAIL: Both attempts exceeded SLA"
        exit 1
    fi
fi
```

### Option 2: Use Python Script
Add the provided `keyword_extraction_retry_test.py` to your CI:

```yaml
# In your GitHub Actions workflow
- name: Test Keyword Extraction with Retry
  run: |
    python scripts/keyword_extraction_retry_test.py
  env:
    CONTAINER_APP_API_KEY: ${{ secrets.CONTAINER_APP_API_KEY }}
```

### Option 3: Update GitHub Actions Directly
If your CI is in GitHub Actions, update the step:

```yaml
- name: Test Keyword Extraction with Retry
  run: |
    # First attempt
    response=$(curl -s -w "\n%{http_code}\n%{time_total}" -X POST \
      "${{ env.API_URL }}/api/v1/extract-jd-keywords" \
      -H "X-API-Key: ${{ secrets.CONTAINER_APP_API_KEY }}" \
      -H "Content-Type: application/json" \
      -d '{"job_description":"Senior Software Engineer...","min_keywords":10,"max_keywords":20,"include_soft_skills":false,"language":"auto"}' \
      --max-time 30)
    
    http_code=$(echo "$response" | tail -n2 | head -n1)
    time_total=$(echo "$response" | tail -n1)
    time_ms=$(echo "$time_total * 1000" | bc | cut -d. -f1)
    
    if [ "$http_code" = "200" ] && [ "$time_ms" -lt "4500" ]; then
      echo "✅ First attempt passed: ${time_ms}ms"
    elif [ "$http_code" = "200" ]; then
      echo "⚠️ First attempt exceeded SLA: ${time_ms}ms, retrying..."
      sleep 3
      
      # Second attempt
      response2=$(curl -s -w "\n%{http_code}\n%{time_total}" -X POST \
        "${{ env.API_URL }}/api/v1/extract-jd-keywords" \
        -H "X-API-Key: ${{ secrets.CONTAINER_APP_API_KEY }}" \
        -H "Content-Type: application/json" \
        -d '{"job_description":"Senior Software Engineer...","min_keywords":10,"max_keywords":20,"include_soft_skills":false,"language":"auto"}' \
        --max-time 30)
      
      http_code2=$(echo "$response2" | tail -n2 | head -n1)
      time_total2=$(echo "$response2" | tail -n1)
      time_ms2=$(echo "$time_total2 * 1000" | bc | cut -d. -f1)
      
      if [ "$http_code2" = "200" ] && [ "$time_ms2" -lt "4500" ]; then
        echo "✅ Second attempt passed: ${time_ms2}ms"
      else
        echo "❌ Both attempts failed SLA"
        exit 1
      fi
    else
      echo "❌ API call failed: HTTP $http_code"
      exit 1
    fi
```

## Testing Locally

To test the retry mechanism locally:

```bash
# Using shell script
chmod +x test_keyword_with_retry.sh
./test_keyword_with_retry.sh YOUR_API_KEY

# Using Python script
python scripts/keyword_extraction_retry_test.py YOUR_API_KEY

# Or with environment variable
export CONTAINER_APP_API_KEY=YOUR_API_KEY
python scripts/keyword_extraction_retry_test.py
```

## Expected Behavior

### Scenario 1: First Attempt Succeeds
```
Attempt 1: ✓ 2341ms (processing: 2100ms, 16 keywords)
✅ PASS: First attempt successful (2341ms < 4500ms)
```

### Scenario 2: First Fails, Retry Succeeds
```
Attempt 1: ⚠️ 5234ms (processing: 5000ms, 16 keywords)
  ⚠️ First attempt exceeded SLA (5234ms > 4500ms)
  Waiting 3 seconds before retry...
Attempt 2: ✓ 2456ms (processing: 2200ms, 16 keywords)
✅ PASS: Second attempt successful (2456ms < 4500ms)
```

### Scenario 3: Both Attempts Fail
```
Attempt 1: ⚠️ 6234ms (processing: 6000ms, 16 keywords)
  ⚠️ First attempt exceeded SLA (6234ms > 4500ms)
  Waiting 3 seconds before retry...
Attempt 2: ⚠️ 5456ms (processing: 5200ms, 16 keywords)
❌ FAIL: Both attempts exceeded SLA
  Attempt 1: 6234ms
  Attempt 2: 5456ms
  SLA: 4500ms
```

## Benefits
1. **Reduces false-positive failures** from transient Azure OpenAI latency
2. **Maintains quality standards** - still fails for persistent performance issues
3. **Provides visibility** - logs both attempts for troubleshooting
4. **Minimal overhead** - only retries when needed

## Monitoring
Track these metrics to understand retry effectiveness:
- Retry rate: How often first attempt exceeds SLA
- Retry success rate: How often retry succeeds
- Average response times for both attempts

## Future Improvements
1. Consider implementing exponential backoff for multiple retries
2. Add telemetry to track retry patterns
3. Adjust SLA based on historical performance data
4. Implement circuit breaker pattern for persistent failures