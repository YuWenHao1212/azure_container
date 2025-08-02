"""
Keyword extraction performance tests using pytest framework.
Test ID: API-KW-105-PT, API-KW-315-PT
"""

import time
import statistics
import json
import pytest
import requests
from datetime import datetime
import os
from typing import List, Dict, Any


class TestKeywordExtractionPerformance:
    """Performance tests for keyword extraction API."""
    
    @pytest.fixture(scope="class")
    def api_base_url(self):
        """API base URL."""
        return "http://localhost:8000"
    
    @pytest.fixture(scope="class")
    def test_cases(self):
        """Define test cases with different job description sizes."""
        return [
            {
                "name": "Small JD (200 chars)",
                "job_description": (
                    "We are looking for a skilled Software Engineer proficient in Python "
                    "and Django. Experience with Docker and Kubernetes is a plus. "
                    "Join our team to build scalable web applications. "
                    "Competitive salary and benefits offered."
                ),
                "language": "en"
            },
            {
                "name": "Medium JD (500 chars)",
                "job_description": (
                    "Our company is seeking an experienced Full Stack Developer with expertise "
                    "in React, Node.js, and PostgreSQL. The ideal candidate will have 5+ years "
                    "of experience building enterprise applications. Responsibilities include "
                    "designing RESTful APIs, implementing responsive UI components, optimizing "
                    "database queries, and mentoring junior developers. We offer remote work "
                    "options, continuous learning opportunities, and a collaborative environment. "
                    "Strong communication skills and experience with Agile methodologies required."
                ),
                "language": "en"
            },
            {
                "name": "Large JD (1000+ chars)",
                "job_description": (
                    "Join our innovative technology team as a Senior DevOps Engineer. We are "
                    "looking for a passionate professional with deep expertise in cloud infrastructure, "
                    "automation, and continuous integration/deployment. Key responsibilities include:\n\n"
                    "- Design and implement scalable AWS/Azure infrastructure using Terraform\n"
                    "- Build and maintain CI/CD pipelines with Jenkins, GitLab CI, or GitHub Actions\n"
                    "- Implement monitoring solutions using Prometheus, Grafana, and ELK stack\n"
                    "- Manage containerized applications with Docker and Kubernetes\n"
                    "- Automate infrastructure provisioning and configuration management\n"
                    "- Ensure security best practices and compliance requirements\n\n"
                    "Required qualifications:\n"
                    "- Bachelor's degree in Computer Science or related field\n"
                    "- 7+ years of experience in DevOps or Site Reliability Engineering\n"
                    "- Strong scripting skills in Python, Bash, or Go\n"
                    "- Experience with microservices architecture and service mesh\n"
                    "- Excellent problem-solving and communication skills\n\n"
                    "We offer competitive compensation, equity options, comprehensive health benefits, "
                    "and opportunities for professional growth in a fast-paced startup environment."
                ),
                "language": "en"
            }
        ]
    
    def test_keyword_extraction_performance(self, api_base_url, test_cases):
        """TEST: API-KW-315-PT - 關鍵字提取效能測試
        
        驗證不同大小的職缺描述的處理效能。
        SLA: 平均回應時間 < 3000ms
        """
        endpoint = f"{api_base_url}/api/v1/extract-jd-keywords"
        num_requests = 5
        sla_target = 3000  # milliseconds
        
        all_results = []
        all_response_times = []
        
        for test_case in test_cases:
            response_times = []
            
            # Perform multiple requests for statistical significance
            for i in range(num_requests):
                start_time = time.time()
                
                response = requests.post(
                    endpoint,
                    json={
                        "job_description": test_case["job_description"],
                        "language": test_case["language"]
                    },
                    timeout=10
                )
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                response_times.append(response_time_ms)
                
                # Validate response
                assert response.status_code == 200, f"Request failed with status {response.status_code}"
                data = response.json()
                assert data["success"] is True
                assert "keywords" in data["data"]
                
                # Small delay between requests
                if i < num_requests - 1:
                    time.sleep(0.1)
            
            # Calculate statistics
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            # Check SLA compliance
            sla_passed = avg_time < sla_target
            assert sla_passed, f"{test_case['name']} failed SLA: {avg_time:.2f}ms > {sla_target}ms"
            
            result = {
                "test_case": test_case["name"],
                "response_times": response_times,
                "average_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time,
                "sla_passed": sla_passed
            }
            all_results.append(result)
            all_response_times.extend(response_times)
            
            # Print results for this test case
            print(f"\n{test_case['name']}:")
            print(f"  Average: {avg_time:.2f} ms")
            print(f"  Min: {min_time:.2f} ms")
            print(f"  Max: {max_time:.2f} ms")
            print(f"  SLA: {'✅ PASS' if sla_passed else '❌ FAIL'}")
        
        # Overall statistics
        overall_avg = statistics.mean(all_response_times)
        overall_sla_passed = overall_avg < sla_target
        
        print(f"\nOverall Performance:")
        print(f"  Average: {overall_avg:.2f} ms")
        print(f"  SLA: {'✅ PASS' if overall_sla_passed else '❌ FAIL'}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(os.path.dirname(__file__), "../logs")
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, f"performance_test_{timestamp}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "test_id": "API-KW-315-PT",
                "endpoint": endpoint,
                "sla_target_ms": sla_target,
                "results": all_results,
                "overall": {
                    "average_ms": overall_avg,
                    "sla_passed": overall_sla_passed
                }
            }, f, indent=2)
        
        print(f"\nDetailed results saved to: {report_file}")
        
        # Final assertion for overall performance
        assert overall_sla_passed, f"Overall performance failed SLA: {overall_avg:.2f}ms > {sla_target}ms"