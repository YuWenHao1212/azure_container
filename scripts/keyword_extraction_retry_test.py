#!/usr/bin/env python3
"""
Keyword Extraction API Test with Retry Logic

Tests the keyword extraction endpoint with automatic retry if the first attempt
exceeds the SLA. Only fails if both attempts exceed the SLA threshold.

Usage:
    python keyword_extraction_retry_test.py [api_key]
    
Environment Variables:
    CONTAINER_APP_API_KEY: API key for authentication
    API_URL: Override the default API URL
    KEYWORD_SLA_MS: Override the default SLA (4500ms)
"""

import sys
import time
import json
import os
import requests
from typing import Tuple, Optional

# Configuration
API_URL = os.getenv(
    "API_URL", 
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
)
SLA_MS = int(os.getenv("KEYWORD_SLA_MS", "4500"))
RETRY_DELAY = 3  # seconds

# Test data
TEST_JD = {
    "job_description": """Senior Software Engineer
    
    Requirements:
    - 5+ years experience with Python, SQL, Docker, Kubernetes
    - Strong knowledge of AWS or Azure cloud platforms
    - Experience with REST APIs, microservices, backend development
    - Understanding of scalability and system architecture
    
    Nice to have:
    - React or Vue.js experience
    - CI/CD and DevOps knowledge""",
    "min_keywords": 10,
    "max_keywords": 20,
    "include_soft_skills": False,
    "language": "auto"
}


def test_keyword_extraction(api_key: str, attempt: int = 1) -> Tuple[bool, int, Optional[str]]:
    """
    Test keyword extraction endpoint.
    
    Returns:
        Tuple of (success, response_time_ms, error_message)
    """
    print(f"Attempt {attempt}: ", end="", flush=True)
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_URL}/api/v1/extract-jd-keywords",
            json=TEST_JD,
            headers=headers,
            timeout=30
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            keywords = data.get("data", {}).get("keywords", [])
            processing_time = data.get("data", {}).get("processing_time_ms", 0)
            
            within_sla = elapsed_ms < SLA_MS
            status_symbol = "✓" if within_sla else "⚠️"
            
            print(f"{status_symbol} {elapsed_ms}ms (processing: {processing_time:.0f}ms, {len(keywords)} keywords)")
            
            # Log some keywords for verification
            if keywords:
                print(f"   Sample keywords: {', '.join(keywords[:5])}")
            
            return within_sla, elapsed_ms, None
            
        else:
            error_msg = f"HTTP {response.status_code}"
            print(f"✗ {error_msg}")
            
            # Try to get error details
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_details = error_data["error"].get("message", "")
                    if error_details:
                        print(f"   Error: {error_details}")
            except:
                pass
                
            return False, elapsed_ms, error_msg
            
    except requests.exceptions.Timeout:
        print("✗ Timeout (30s)")
        return False, 30000, "Timeout"
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        print(f"✗ Error: {e}")
        return False, elapsed_ms, str(e)


def main():
    """Main test execution with retry logic."""
    print("=" * 60)
    print("Keyword Extraction API Test with Retry")
    print("=" * 60)
    print(f"API URL: {API_URL}")
    print(f"SLA Threshold: {SLA_MS}ms")
    
    # Get API key
    api_key = os.getenv("CONTAINER_APP_API_KEY")
    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    if not api_key:
        print("\n❌ Error: No API key provided")
        print("Usage: python keyword_extraction_retry_test.py [api_key]")
        print("Or set CONTAINER_APP_API_KEY environment variable")
        return 1
    
    print(f"API Key: {'*' * 10}{api_key[-4:]}")
    print()
    
    # First attempt
    success1, time1, error1 = test_keyword_extraction(api_key, attempt=1)
    
    if success1:
        print(f"\n✅ PASS: First attempt successful ({time1}ms < {SLA_MS}ms)")
        return 0
    
    if error1:
        # If there was an error (not just slow), fail immediately
        print(f"\n❌ FAIL: First attempt failed with error: {error1}")
        return 1
    
    # First attempt exceeded SLA, retry
    print(f"  ⚠️  First attempt exceeded SLA ({time1}ms > {SLA_MS}ms)")
    print(f"  Waiting {RETRY_DELAY} seconds before retry...")
    time.sleep(RETRY_DELAY)
    
    # Second attempt
    success2, time2, error2 = test_keyword_extraction(api_key, attempt=2)
    
    if success2:
        print(f"\n✅ PASS: Second attempt successful ({time2}ms < {SLA_MS}ms)")
        print(f"  Note: First attempt was {time1}ms, retry strategy worked!")
        return 0
    
    if error2:
        print(f"\n❌ FAIL: Second attempt failed with error: {error2}")
    else:
        print(f"\n❌ FAIL: Both attempts exceeded SLA")
        print(f"  Attempt 1: {time1}ms")
        print(f"  Attempt 2: {time2}ms")
        print(f"  SLA: {SLA_MS}ms")
    
    return 1


if __name__ == "__main__":
    sys.exit(main())