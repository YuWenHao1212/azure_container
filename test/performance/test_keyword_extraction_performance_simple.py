#!/usr/bin/env python3
"""
Simplified performance test for keyword extraction API.
Test ID: API-KW-105-PT
"""

import json
import os
import statistics
import sys
import time
from datetime import datetime

import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_keyword_extraction_performance():
    """TEST: API-KW-315-PT - 關鍵字提取效能"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/extract-jd-keywords"

    # Check if API is running
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API health check failed.")
            print("Please start the API server:")
            print("  cd /Users/yuwenhao/Documents/GitHub/azure_container")
            print("  uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
            return
        print("✅ API is running")
    except Exception as e:
        print(f"❌ Cannot connect to API at {base_url}")
        print(f"   Error: {e}")
        print("\nPlease start the API server:")
        print("  cd /Users/yuwenhao/Documents/GitHub/azure_container")
        print("  uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
        return

    print(f"\n{'='*60}")
    print("Keyword Extraction Performance Test (API-KW-105-PT)")
    print(f"{'='*60}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Endpoint: {endpoint}")
    print("SLA Target: < 3000ms")
    print(f"{'='*60}\n")

    # Test cases
    test_cases = [
        {
            "name": "Small JD (200 chars)",
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required."  # noqa: E501
        },
        {
            "name": "Medium JD (500 chars)",
            "job_description": """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have 5+ years of experience with Python, FastAPI, and Django. Strong proficiency in React, TypeScript, and modern JavaScript is essential. Experience with microservices architecture and RESTful APIs is required. Must have hands-on experience with Docker, Kubernetes, and CI/CD pipelines. Familiarity with AWS or Azure cloud services is important. Knowledge of PostgreSQL, MongoDB, and Redis is expected. Experience with Agile methodologies and version control (Git) is necessary. Excellent communication and problem-solving skills are a must."""  # noqa: E501
        },
        {
            "name": "Large JD (1000+ chars)",
            "job_description": """Senior Backend Engineer - Python/FastAPI

We are looking for a talented Senior Backend Engineer to join our engineering team. You will be responsible for designing, developing, and maintaining scalable backend services.  # noqa: E501

Key Responsibilities:
- Design and implement RESTful APIs using Python and FastAPI
- Build and maintain microservices architecture
- Optimize database queries and improve system performance
- Implement security best practices and data protection
- Collaborate with frontend developers and DevOps engineers
- Mentor junior developers and conduct code reviews

Requirements:
- 5+ years of backend development experience
- Expert-level Python programming skills
- Strong experience with FastAPI, Django, or Flask
- Proficiency in SQL and NoSQL databases (PostgreSQL, MongoDB, Redis)
- Experience with message queues (RabbitMQ, Kafka)
- Hands-on experience with Docker and Kubernetes
- Familiarity with AWS services (EC2, S3, Lambda, RDS)
- Understanding of software design patterns and SOLID principles
- Experience with CI/CD pipelines and automated testing
- Excellent problem-solving and analytical skills

Nice to have:
- Experience with GraphQL
- Knowledge of Golang or Rust
- Contributions to open-source projects
- AWS certifications"""
        }
    ]

    # Run tests
    results = []

    print("Running Performance Tests...")
    print("-" * 60)

    for test_case in test_cases:
        print(f"\nTest Case: {test_case['name']}")

        payload = {
            "job_description": test_case["job_description"],
            "top_k": 30
        }

        # Run multiple requests to get average
        response_times = []
        errors = []

        for i in range(5):
            start_time = time.time()

            try:
                # Add API key from environment if available
                headers = {}
                api_key = os.getenv("CONTAINER_APP_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key

                response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # ms
                response_times.append(response_time)

                if i == 0:  # Print details for first request only
                    print(f"  Request #{i+1}: {response_time:.2f} ms")
                    if response.status_code == 200:
                        data = response.json()
                        print(f"  Keywords found: {len(data.get('keywords', []))}")
                    else:
                        print(f"  Status: {response.status_code}")
                        print(f"  Error: {response.json()}")

            except Exception as e:
                errors.append(str(e))
                print(f"  Request #{i+1}: ERROR - {e}")

        # Calculate statistics
        if response_times:
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            print("\n  Statistics (5 requests):")
            print(f"    Average: {avg_time:.2f} ms")
            print(f"    Min: {min_time:.2f} ms")
            print(f"    Max: {max_time:.2f} ms")
            print(f"    SLA Compliance: {'✅ PASS' if avg_time < 3000 else '❌ FAIL'}")

            results.append({
                "test_case": test_case["name"],
                "avg_response_time_ms": avg_time,
                "min_response_time_ms": min_time,
                "max_response_time_ms": max_time,
                "sla_compliant": avg_time < 3000,
                "success_rate": len(response_times) / 5
            })
        else:
            print("\n  All requests failed!")
            results.append({
                "test_case": test_case["name"],
                "error": "All requests failed",
                "sla_compliant": False,
                "success_rate": 0
            })

    # Overall summary
    print(f"\n{'='*60}")
    print("Overall Performance Summary")
    print(f"{'='*60}")

    all_times = []
    for result in results:
        if "avg_response_time_ms" in result:
            all_times.append(result["avg_response_time_ms"])

    if all_times:
        overall_avg = statistics.mean(all_times)
        print(f"Overall Average Response Time: {overall_avg:.2f} ms")
        print(f"Overall SLA Compliance: {'✅ PASS' if overall_avg < 3000 else '❌ FAIL'}")

        if overall_avg < 1000:
            print("\n✅ EXCELLENT: Average response time < 1s")
        elif overall_avg < 2000:
            print("\n✅ GOOD: Average response time < 2s")
        elif overall_avg < 3000:
            print("\n✅ PASS: Average response time < 3s (meets SLA)")
        else:
            print("\n❌ FAIL: Average response time exceeds 3s SLA")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test/logs/performance_test_{timestamp}.json"

    test_summary = {
        "test_id": "API-KW-105-PT",
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "sla_target_ms": 3000,
        "results": results,
        "overall_average_ms": overall_avg if all_times else None,
        "overall_sla_compliant": overall_avg < 3000 if all_times else False
    }

    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(test_summary, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")

    return test_summary


if __name__ == "__main__":
    test_keyword_extraction_performance()
