#!/usr/bin/env python3
"""
Quick test to verify Medium JD performance anomaly.
This is a simplified version to quickly confirm the issue before running full experiments.
"""

import os
import statistics
import time

import requests


def quick_test():
    """Quick test to reproduce the Medium JD anomaly."""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/extract-jd-keywords"

    # Check API health
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not available")
            return
        print("✅ API is healthy")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return

    # Test cases
    test_cases = [
        {
            "name": "Small JD",
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required."  # noqa: E501
        },
        {
            "name": "Medium JD",
            "job_description": """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have:  # noqa: E501
- 5+ years of experience with Python, FastAPI, and Django
- Strong proficiency in React, TypeScript, and modern JavaScript
- Experience with microservices architecture and RESTful APIs
- Hands-on experience with Docker, Kubernetes, and CI/CD pipelines
- Familiarity with AWS or Azure cloud services
- Knowledge of PostgreSQL, MongoDB, and Redis
- Experience with Agile methodologies and version control (Git)
- Excellent communication and problem-solving skills"""
        },
        {
            "name": "Large JD",
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

    print(f"\n{'='*60}")
    print("QUICK ANOMALY VERIFICATION TEST")
    print(f"{'='*60}")

    # Get API key if available
    headers = {}
    api_key = os.getenv("CONTAINER_APP_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
        print("🔑 Using API key authentication")
    else:
        print("⚠️  No API key found - using anonymous access")

    results = {}

    # Test each case 3 times quickly
    for test_case in test_cases:
        print(f"\nTesting {test_case['name']}...")
        print(f"Length: {len(test_case['job_description'])} chars")

        times = []

        for i in range(3):
            payload = {
                "job_description": test_case["job_description"],
                "top_k": 30
            }

            start_time = time.perf_counter()

            try:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
                end_time = time.perf_counter()

                response_time = (end_time - start_time) * 1000
                times.append(response_time)

                if response.status_code == 200:
                    data = response.json()
                    keywords_count = len(data.get("keywords", []))
                    print(f"  Run {i+1}: {response_time:.2f}ms ({keywords_count} keywords)")
                else:
                    print(f"  Run {i+1}: {response_time:.2f}ms - ERROR {response.status_code}")

            except Exception as e:
                print(f"  Run {i+1}: ERROR - {e}")

            time.sleep(0.5)  # Short delay between runs

        # Calculate stats
        if times:
            avg_time = statistics.mean(times)
            results[test_case['name']] = avg_time
            print(f"  Average: {avg_time:.2f}ms")

    # Analysis
    print(f"\n{'='*60}")
    print("QUICK ANALYSIS")
    print(f"{'='*60}")

    if len(results) == 3:
        small_avg = results.get("Small JD", 0)
        medium_avg = results.get("Medium JD", 0)
        large_avg = results.get("Large JD", 0)

        print(f"Small JD:  {small_avg:.2f}ms")
        print(f"Medium JD: {medium_avg:.2f}ms")
        print(f"Large JD:  {large_avg:.2f}ms")

        # Check for anomaly
        if medium_avg > small_avg and medium_avg > large_avg:
            difference_vs_small = ((medium_avg - small_avg) / small_avg) * 100
            difference_vs_large = ((medium_avg - large_avg) / large_avg) * 100

            print("\n❌ ANOMALY CONFIRMED:")
            print(f"   Medium JD is {difference_vs_small:.1f}% slower than Small JD")
            print(f"   Medium JD is {difference_vs_large:.1f}% slower than Large JD")

            if difference_vs_small > 20 or difference_vs_large > 20:
                print("   🔴 SIGNIFICANT anomaly (>20% difference)")
                print("   📋 Recommend running full controlled experiments")
            else:
                print("   🟡 MILD anomaly (<20% difference)")
                print("   📋 May be within normal variance")

        elif medium_avg > max(small_avg, large_avg) * 1.1:
            print("\n⚠️  POSSIBLE ANOMALY:")
            print("   Medium JD appears slower but pattern unclear")

        else:
            print("\n✅ NO CLEAR ANOMALY:")
            print("   Performance follows expected pattern")
    else:
        print("❌ Insufficient data for analysis")

    return results


if __name__ == "__main__":
    quick_test()
