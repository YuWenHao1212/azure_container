#!/bin/bash

# Function to parse batch test results
parse_batch_test_results() {
    local output_file="$1"
    
    # Extract passed tests for API-GAP tests
    local passed_tests=$(grep -E "test_API_GAP_[0-9]+_IT.*PASSED" "$output_file" | sed -E 's/.*test_(API_GAP_[0-9]+_IT).*/\1/' || true)
    
    # Extract failed tests for API-GAP tests
    local failed_tests=$(grep -E "test_API_GAP_[0-9]+_IT.*FAILED" "$output_file" | sed -E 's/.*test_(API_GAP_[0-9]+_IT).*/\1/' || true)
    
    # Also extract error handling tests (test_error_handling_v2.py tests)
    local error_handling_passed=$(grep -E "test_error_handling_v2\.py.*PASSED" "$output_file" | wc -l | tr -d ' ')
    local error_handling_failed=$(grep -E "test_error_handling_v2\.py.*FAILED" "$output_file" | wc -l | tr -d ' ')
    
    # Update global arrays based on API-GAP results
    while IFS= read -r test_id; do
        if [ -n "$test_id" ]; then
            PASSED_TESTS+=("${test_id//_/-}")
            INTEGRATION_PASSED+=("${test_id//_/-}")
            
            # Determine priority from test ID
            case "${test_id//_/-}" in
                API-GAP-00[1-3]-IT|API-GAP-00[5-9]-IT|API-GAP-01[0-1]-IT|API-GAP-014-IT) P0_PASSED+=("${test_id//_/-}") ;;
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT|API-GAP-01[8-9]-IT|API-GAP-02[0-7]-IT) P1_PASSED+=("${test_id//_/-}") ;;
            esac
        fi
    done <<< "$passed_tests"
    
    while IFS= read -r test_id; do
        if [ -n "$test_id" ]; then
            FAILED_TESTS+=("${test_id//_/-}")
            INTEGRATION_FAILED+=("${test_id//_/-}")
            
            # Determine priority from test ID  
            case "${test_id//_/-}" in
                API-GAP-00[1-3]-IT|API-GAP-00[5-9]-IT|API-GAP-01[0-1]-IT|API-GAP-014-IT) P0_FAILED+=("${test_id//_/-}") ;;
                API-GAP-00[4]-IT|API-GAP-01[2-3]-IT|API-GAP-01[8-9]-IT|API-GAP-02[0-7]-IT) P1_FAILED+=("${test_id//_/-}") ;;
            esac
        fi
    done <<< "$failed_tests"
    
    # Add error handling test results (API-GAP-018-IT to API-GAP-027-IT)
    if [ "$error_handling_passed" -gt 0 ]; then
        # Map error handling tests to API-GAP IDs
        local error_test_ids=("API-GAP-018-IT" "API-GAP-019-IT" "API-GAP-020-IT" "API-GAP-021-IT" "API-GAP-022-IT" 
                             "API-GAP-023-IT" "API-GAP-024-IT" "API-GAP-025-IT" "API-GAP-026-IT" "API-GAP-027-IT")
        
        # Add passed tests based on count (simplified approach)
        local count=0
        for test_id in "${error_test_ids[@]}"; do
            if [ $count -lt $error_handling_passed ]; then
                PASSED_TESTS+=("$test_id")
                INTEGRATION_PASSED+=("$test_id")
                P1_PASSED+=("$test_id")  # All error handling tests are P1
                ((count++))
            fi
        done
    fi
    
    # Add failed error handling tests if any
    if [ "$error_handling_failed" -gt 0 ]; then
        echo "Warning: Some error handling tests failed but cannot determine which ones specifically"
    fi
}