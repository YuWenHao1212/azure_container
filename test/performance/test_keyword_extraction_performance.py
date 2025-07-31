#!/usr/bin/env python3
"""
Performance test for keyword extraction API.
Test ID: API-KW-105-PT

Measures response time and throughput for the keyword extraction endpoint.
"""

import time
import statistics
import json
import requests
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.keyword_extraction import KeywordExtractionRequest


class KeywordExtractionPerformanceTest:
    """Performance test for keyword extraction API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/extract-jd-keywords"
        self.results: List[Dict[str, Any]] = []
        
    def get_test_data(self) -> List[Dict[str, Any]]:
        """Get test job descriptions of various sizes."""
        return [
            {
                "name": "Small JD (200 chars)",
                "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required.",
                "expected_keywords": 10
            },
            {
                "name": "Medium JD (500 chars)",
                "job_description": """We are seeking an experienced Full Stack Developer to join our growing team. The ideal candidate will have:
                - 5+ years of experience with Python, FastAPI, and Django
                - Strong proficiency in React, TypeScript, and modern JavaScript
                - Experience with microservices architecture and RESTful APIs
                - Hands-on experience with Docker, Kubernetes, and CI/CD pipelines
                - Familiarity with AWS or Azure cloud services
                - Knowledge of PostgreSQL, MongoDB, and Redis
                - Experience with Agile methodologies and version control (Git)
                - Excellent communication and problem-solving skills""",
                "expected_keywords": 15
            },
            {
                "name": "Large JD (1000 chars)",
                "job_description": """Senior Backend Engineer - Python/FastAPI

We are looking for a talented Senior Backend Engineer to join our engineering team. You will be responsible for designing, developing, and maintaining scalable backend services.

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
- AWS certifications""",
                "expected_keywords": 25
            }
        ]
    
    def run_single_request(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single API request and measure response time."""
        payload = {
            "job_description": test_case["job_description"],
            "top_k": 30
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(self.endpoint, json=payload, timeout=10)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            return {
                "test_case": test_case["name"],
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "keywords_count": len(response.json().get("keywords", [])) if response.status_code == 200 else 0,
                "success": response.status_code == 200,
                "error": response.json().get("detail") if response.status_code != 200 else None
            }
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return {
                "test_case": test_case["name"],
                "status_code": 0,
                "response_time_ms": response_time,
                "keywords_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def run_concurrent_requests(self, test_case: Dict[str, Any], concurrent_requests: int = 10) -> List[Dict[str, Any]]:
        """Run multiple concurrent requests to test throughput."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(self.run_single_request, test_case) for _ in range(concurrent_requests)]
            return [future.result() for future in concurrent.futures.as_completed(futures)]
    
    def run_performance_test(self) -> Dict[str, Any]:
        """Run complete performance test suite."""
        print(f"\n{'='*60}")
        print(f"Keyword Extraction Performance Test (API-KW-105-PT)")
        print(f"{'='*60}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Endpoint: {self.endpoint}")
        print(f"{'='*60}\n")
        
        test_cases = self.get_test_data()
        all_results = []
        
        # Test 1: Sequential requests with different payload sizes
        print("Test 1: Sequential Requests (Different Payload Sizes)")
        print("-" * 50)
        
        for test_case in test_cases:
            result = self.run_single_request(test_case)
            all_results.append(result)
            
            print(f"Test Case: {result['test_case']}")
            print(f"  Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
            print(f"  Response Time: {result['response_time_ms']:.2f} ms")
            print(f"  Keywords Found: {result['keywords_count']}")
            if result['error']:
                print(f"  Error: {result['error']}")(f"  Error: {result['error']}")
                print()
        
        # Test 2: Concurrent requests
        print("\nTest 2: Concurrent Requests (Load Test)")
        print("-" * 50)
        
        concurrent_counts = [5, 10, 20]
        for concurrent in concurrent_counts:
            print(f"\nTesting with {concurrent} concurrent requests...")
            
            # Use medium-sized test case for concurrent testing
            medium_test = test_cases[1]
            concurrent_results = self.run_concurrent_requests(medium_test, concurrent)
            
            response_times = [r['response_time_ms'] for r in concurrent_results if r['success']]
            success_count = sum(1 for r in concurrent_results if r['success'])
            
            if response_times:
                print(f"  Success Rate: {success_count}/{concurrent} ({success_count/concurrent*100:.1f}%)")
                print(f"  Min Response Time: {min(response_times):.2f} ms")
                print(f"  Max Response Time: {max(response_times):.2f} ms")
                print(f"  Avg Response Time: {statistics.mean(response_times):.2f} ms")
                print(f"  Median Response Time: {statistics.median(response_times):.2f} ms")
                if len(response_times) > 1:
                    print(f"  Std Dev: {statistics.stdev(response_times):.2f} ms")
            else:
                print(f"  All requests failed!")
            
            all_results.extend(concurrent_results)
        
        # Calculate overall statistics
        print(f"\n{'='*60}")
        print("Overall Performance Summary")
        print(f"{'='*60}")
        
        all_response_times = [r['response_time_ms'] for r in all_results if r['success']]
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r['success'])
        
        if all_response_times:
            print(f"Total Requests: {total_requests}")
            print(f"Successful Requests: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
            print(f"Failed Requests: {total_requests - successful_requests}")
            print(f"\nResponse Time Statistics:")
            print(f"  Min: {min(all_response_times):.2f} ms")
            print(f"  Max: {max(all_response_times):.2f} ms")
            print(f"  Average: {statistics.mean(all_response_times):.2f} ms")
            print(f"  Median: {statistics.median(all_response_times):.2f} ms")
            
            # Calculate percentiles
            sorted_times = sorted(all_response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 100 else sorted_times[-1]
            
            print(f"\nPercentiles:")
            print(f"  P50: {p50:.2f} ms")
            print(f"  P90: {p90:.2f} ms")
            print(f"  P95: {p95:.2f} ms")
            print(f"  P99: {p99:.2f} ms")
            
            # Check against SLA
            sla_3000ms = sum(1 for t in all_response_times if t < 3000)
            print(f"\nSLA Compliance (< 3 seconds):")
            print(f"  {sla_3000ms}/{len(all_response_times)} requests ({sla_3000ms/len(all_response_times)*100:.1f}%)")
            
            # Performance verdict
            print(f"\n{'='*60}")
            print("Performance Test Verdict")
            print(f"{'='*60}")
            
            avg_time = statistics.mean(all_response_times)
            if avg_time < 1000 and p95 < 2000:
                print("✅ EXCELLENT: Average response time < 1s, P95 < 2s")
            elif avg_time < 2000 and p95 < 3000:
                print("✅ PASS: Average response time < 2s, P95 < 3s (meets SLA)")
            elif avg_time < 3000:
                print("⚠️  WARNING: Average response time approaching 3s limit")
            else:
                print("❌ FAIL: Average response time exceeds 3s SLA")
        else:
            print("❌ All requests failed - cannot calculate statistics")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test/logs/performance_test_{timestamp}.json"
        
        test_summary = {
            "test_id": "API-KW-105-PT",
            "timestamp": datetime.now().isoformat(),
            "endpoint": self.endpoint,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "statistics": {
                "min_ms": min(all_response_times) if all_response_times else None,
                "max_ms": max(all_response_times) if all_response_times else None,
                "avg_ms": statistics.mean(all_response_times) if all_response_times else None,
                "median_ms": statistics.median(all_response_times) if all_response_times else None,
                "p50_ms": p50 if all_response_times else None,
                "p90_ms": p90 if all_response_times else None,
                "p95_ms": p95 if all_response_times else None,
                "p99_ms": p99 if all_response_times else None,
            } if all_response_times else {},
            "sla_compliance": {
                "target_ms": 3000,
                "compliant_requests": sla_3000ms if all_response_times else 0,
                "compliance_rate": sla_3000ms/len(all_response_times) if all_response_times else 0
            },
            "detailed_results": all_results
        }
        
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(test_summary, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        return test_summary


def main():
    """Main function to run performance tests."""
    # Check if the API is running
    test = KeywordExtractionPerformanceTest()
    
    try:
        response = requests.get(f"{test.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API health check failed. Make sure the API is running.")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API at {test.base_url}")
        print(f"   Error: {e}")
        print("\nPlease start the API server first:")
        print("  cd /Users/yuwenhao/Documents/GitHub/azure_container")
        print("  uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    # Run performance tests
    test.run_performance_test()


if __name__ == "__main__":
    main()