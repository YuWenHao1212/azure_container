#!/usr/bin/env python3
"""
Controlled performance experiments for keyword extraction API.
This script runs systematic experiments to identify the root cause of
Medium JD performance anomalies.
"""

import json
import os
import statistics
import time
from datetime import datetime
from typing import Any, Optional

import requests


class ControlledPerformanceExperiments:
    """Systematic performance experiments with controlled variables."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.endpoint = f"{base_url}/api/v1/extract-jd-keywords"
        self.api_key = os.getenv("CONTAINER_APP_API_KEY")

    def get_original_test_cases(self) -> list[dict[str, Any]]:
        """Get original test cases from the performance test."""
        return [
            {
                "name": "Small JD",
                "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and Django. Must have strong knowledge of microservices architecture, Docker, Kubernetes, and AWS cloud services. Excellent problem-solving skills required."
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

    def make_request(self, job_description: str, request_id: str | None = None) -> dict[str, Any]:
        """Make a single API request with precise timing."""
        payload = {
            "job_description": job_description,
            "top_k": 30
        }

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        # High precision timing
        start_time = time.perf_counter()

        try:
            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=15)
            end_time = time.perf_counter()

            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            result = {
                "request_id": request_id or f"req_{int(time.time() * 1000)}",
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200,
                "timestamp": datetime.now().isoformat(),
                "start_time": start_time,
                "end_time": end_time
            }

            if response.status_code == 200:
                data = response.json()
                result["keywords_count"] = len(data.get("keywords", []))
                result["keywords"] = data.get("keywords", [])[:5]  # First 5 for verification
            else:
                result["error"] = response.text[:200]  # Truncated error

            return result

        except Exception as e:
            end_time = time.perf_counter()
            return {
                "request_id": request_id or f"req_error_{int(time.time() * 1000)}",
                "status_code": 0,
                "response_time_ms": (end_time - start_time) * 1000,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "start_time": start_time,
                "end_time": end_time
            }

    def experiment_1_order_effects(self) -> dict[str, Any]:
        """Experiment 1: Test if request order affects performance."""
        print("\n" + "="*80)
        print("EXPERIMENT 1: ORDER EFFECTS")
        print("="*80)
        print("Testing if the order of requests affects performance...")

        test_cases = self.get_original_test_cases()

        # Test multiple orders
        orders = [
            [0, 1, 2],  # Original order: Small, Medium, Large
            [2, 1, 0],  # Reverse order: Large, Medium, Small
            [1, 0, 2],  # Medium first: Medium, Small, Large
            [0, 2, 1],  # Medium last: Small, Large, Medium
            [1, 2, 0],  # Random order 1
            [2, 0, 1]   # Random order 2
        ]

        results_by_order = []

        for i, order in enumerate(orders):
            print(f"\nOrder {i+1}: {[test_cases[j]['name'] for j in order]}")

            order_results = []

            # Add 2-second delay between order tests
            if i > 0:
                print("  Waiting 2 seconds between order tests...")
                time.sleep(2)

            for position, case_idx in enumerate(order):
                test_case = test_cases[case_idx]
                request_id = f"order{i+1}_pos{position+1}_{test_case['name'].replace(' ', '_')}"

                result = self.make_request(test_case['job_description'], request_id)
                result['test_case'] = test_case['name']
                result['order'] = i + 1
                result['position'] = position + 1
                result['case_index'] = case_idx

                order_results.append(result)

                print(f"    {test_case['name']}: {result['response_time_ms']:.2f}ms")

                # Small delay between requests in same order
                time.sleep(0.5)

            results_by_order.append(order_results)

        # Analyze order effects
        print(f"\n{'-'*60}")
        print("ORDER EFFECTS ANALYSIS")
        print(f"{'-'*60}")

        # Group results by test case across all orders
        by_case = {"Small JD": [], "Medium JD": [], "Large JD": []}

        for order_results in results_by_order:
            for result in order_results:
                if result['success']:
                    by_case[result['test_case']].append(result['response_time_ms'])

        # Calculate statistics for each case
        for case_name, times in by_case.items():
            if times:
                avg = statistics.mean(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                min_time = min(times)
                max_time = max(times)

                print(f"{case_name}:")
                print(f"  Average: {avg:.2f}ms")
                print(f"  Std Dev: {std_dev:.2f}ms")
                print(f"  Range: {min_time:.2f}ms - {max_time:.2f}ms")
                print(f"  Variance: {std_dev/avg*100:.1f}%" if avg > 0 else "  Variance: N/A")

        return {
            "experiment": "order_effects",
            "results_by_order": results_by_order,
            "summary": by_case
        }

    def experiment_2_content_formatting(self) -> dict[str, Any]:
        """Experiment 2: Test if text formatting affects performance."""
        print("\n" + "="*80)
        print("EXPERIMENT 2: CONTENT FORMATTING EFFECTS")
        print("="*80)
        print("Testing if bullet points and formatting affect performance...")

        original_medium = self.get_original_test_cases()[1]['job_description']

        # Create variations of Medium JD
        variations = [
            {
                "name": "Medium Original (with bullets)",
                "content": original_medium
            },
            {
                "name": "Medium Plain Text",
                "content": original_medium.replace('\n- ', ' ').replace('\n', ' ').replace('  ', ' ')
            },
            {
                "name": "Medium Single Line",
                "content": ' '.join(original_medium.split())
            },
            {
                "name": "Medium No Dashes",
                "content": original_medium.replace('- ', '')
            }
        ]

        results = []

        for variation in variations:
            print(f"\nTesting: {variation['name']}")
            print(f"Length: {len(variation['content'])} chars")

            # Test each variation multiple times
            variation_results = []
            for i in range(5):
                request_id = f"format_test_{variation['name'].replace(' ', '_')}_run{i+1}"
                result = self.make_request(variation['content'], request_id)
                result['variation'] = variation['name']
                result['run'] = i + 1
                variation_results.append(result)

                if result['success']:
                    print(f"  Run {i+1}: {result['response_time_ms']:.2f}ms")
                else:
                    print(f"  Run {i+1}: ERROR - {result.get('error', 'Unknown error')}")

                time.sleep(0.5)  # Small delay between runs

            # Calculate statistics for this variation
            successful_results = [r for r in variation_results if r['success']]
            if successful_results:
                times = [r['response_time_ms'] for r in successful_results]
                avg_time = statistics.mean(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0

                print(f"  Average: {avg_time:.2f}ms (±{std_dev:.2f}ms)")

            results.extend(variation_results)

        return {
            "experiment": "content_formatting",
            "results": results
        }

    def experiment_3_isolated_requests(self) -> dict[str, Any]:
        """Experiment 3: Test each case in complete isolation."""
        print("\n" + "="*80)
        print("EXPERIMENT 3: ISOLATED REQUESTS")
        print("="*80)
        print("Testing each case in complete isolation with warm-up...")

        test_cases = self.get_original_test_cases()
        results = []

        for test_case in test_cases:
            print(f"\nTesting {test_case['name']} in isolation...")

            # Warm-up request (not counted)
            print("  Warm-up request...")
            self.make_request(test_case['job_description'], "warmup")
            time.sleep(1)

            # Actual test requests
            test_results = []
            for i in range(10):  # More samples for better statistics
                request_id = f"isolated_{test_case['name'].replace(' ', '_')}_run{i+1}"
                result = self.make_request(test_case['job_description'], request_id)
                result['test_case'] = test_case['name']
                result['run'] = i + 1
                test_results.append(result)

                if result['success']:
                    print(f"    Run {i+1}: {result['response_time_ms']:.2f}ms")

                time.sleep(1)  # 1 second between requests

            # Statistics
            successful_results = [r for r in test_results if r['success']]
            if successful_results:
                times = [r['response_time_ms'] for r in successful_results]
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                std_dev = statistics.stdev(times) if len(times) > 1 else 0
                min_time = min(times)
                max_time = max(times)

                print(f"  Results for {test_case['name']}:")
                print(f"    Successful requests: {len(successful_results)}/10")
                print(f"    Average: {avg_time:.2f}ms")
                print(f"    Median: {median_time:.2f}ms")
                print(f"    Std Dev: {std_dev:.2f}ms")
                print(f"    Range: {min_time:.2f}ms - {max_time:.2f}ms")
                print(f"    CV: {std_dev/avg_time*100:.1f}%" if avg_time > 0 else "    CV: N/A")

            results.extend(test_results)

            # Cool-down between test cases
            print("  Cool-down (3 seconds)...")
            time.sleep(3)

        return {
            "experiment": "isolated_requests",
            "results": results
        }

    def experiment_4_statistical_power(self) -> dict[str, Any]:
        """Experiment 4: High-sample statistical analysis."""
        print("\n" + "="*80)
        print("EXPERIMENT 4: HIGH-SAMPLE STATISTICAL ANALYSIS")
        print("="*80)
        print("Running large sample sizes to detect real performance differences...")

        test_cases = self.get_original_test_cases()
        results = []

        sample_size = 20  # Larger sample for statistical power

        for test_case in test_cases:
            print(f"\nTesting {test_case['name']} with {sample_size} samples...")

            case_results = []
            times = []

            for i in range(sample_size):
                request_id = f"stats_{test_case['name'].replace(' ', '_')}_sample{i+1}"
                result = self.make_request(test_case['job_description'], request_id)
                result['test_case'] = test_case['name']
                result['sample'] = i + 1
                case_results.append(result)

                if result['success']:
                    times.append(result['response_time_ms'])
                    if i % 5 == 4:  # Print every 5th result
                        print(f"    Samples 1-{i+1}: Current avg = {statistics.mean(times):.2f}ms")

                time.sleep(0.3)  # Short delay

            # Comprehensive statistics
            if times:
                n = len(times)
                mean_time = statistics.mean(times)
                median_time = statistics.median(times)
                std_dev = statistics.stdev(times) if n > 1 else 0

                # Calculate percentiles
                sorted_times = sorted(times)
                p25 = sorted_times[int(n * 0.25)]
                p75 = sorted_times[int(n * 0.75)]
                p90 = sorted_times[int(n * 0.90)]
                p95 = sorted_times[int(n * 0.95)]

                # Calculate confidence interval (95%)
                if n > 1:
                    se = std_dev / (n ** 0.5)  # Standard error
                    ci_margin = 1.96 * se  # 95% CI
                    ci_lower = mean_time - ci_margin
                    ci_upper = mean_time + ci_margin
                else:
                    ci_lower = ci_upper = mean_time

                print(f"\n  Statistical Summary for {test_case['name']}:")
                print(f"    Sample size: {n}")
                print(f"    Mean: {mean_time:.2f}ms")
                print(f"    Median: {median_time:.2f}ms")
                print(f"    Std Dev: {std_dev:.2f}ms")
                print(f"    95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]ms")
                print(f"    Percentiles: P25={p25:.2f}, P75={p75:.2f}, P90={p90:.2f}, P95={p95:.2f}")
                print(f"    CV: {std_dev/mean_time*100:.1f}%")

            results.extend(case_results)

        return {
            "experiment": "statistical_power",
            "results": results
        }

    def run_all_experiments(self) -> dict[str, Any]:
        """Run all controlled experiments."""
        print("🧪 CONTROLLED PERFORMANCE EXPERIMENTS")
        print("🎯 Goal: Identify root cause of Medium JD performance anomaly")
        print(f"📊 API Endpoint: {self.endpoint}")
        print(f"🕐 Start Time: {datetime.now().isoformat()}")

        # Check API health
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ API health check failed!")
                return {"error": "API not available"}
            print("✅ API is healthy")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return {"error": f"API connection failed: {e}"}

        all_results = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "api_endpoint": self.endpoint,
                "experiments_planned": 4
            },
            "experiments": {}
        }

        try:
            # Run experiments
            all_results["experiments"]["order_effects"] = self.experiment_1_order_effects()
            all_results["experiments"]["content_formatting"] = self.experiment_2_content_formatting()
            all_results["experiments"]["isolated_requests"] = self.experiment_3_isolated_requests()
            all_results["experiments"]["statistical_power"] = self.experiment_4_statistical_power()

            # Final analysis
            self.analyze_all_results(all_results)

        except Exception as e:
            print(f"❌ Experiment failed: {e}")
            all_results["error"] = str(e)

        all_results["metadata"]["end_time"] = datetime.now().isoformat()

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test/performance/controlled_experiments_{timestamp}.json"

        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)

        print(f"\n📋 All results saved to: {results_file}")

        return all_results

    def analyze_all_results(self, all_results: dict[str, Any]):
        """Analyze all experiment results and provide conclusions."""
        print("\n" + "="*80)
        print("COMPREHENSIVE ANALYSIS & CONCLUSIONS")
        print("="*80)

        # Extract key findings from each experiment
        findings = []

        # Analyze order effects
        if "order_effects" in all_results["experiments"]:
            order_data = all_results["experiments"]["order_effects"]["summary"]

            medium_times = order_data.get("Medium JD", [])
            small_times = order_data.get("Small JD", [])
            large_times = order_data.get("Large JD", [])

            if medium_times and small_times and large_times:
                medium_avg = statistics.mean(medium_times)
                small_avg = statistics.mean(small_times)
                large_avg = statistics.mean(large_times)

                print("\n1. ORDER EFFECTS FINDINGS:")
                print(f"   Small JD average: {small_avg:.2f}ms")
                print(f"   Medium JD average: {medium_avg:.2f}ms")
                print(f"   Large JD average: {large_avg:.2f}ms")

                if medium_avg > small_avg and medium_avg > large_avg:
                    findings.append("❌ Medium JD consistently slower regardless of order")
                elif medium_avg > max(small_avg, large_avg) * 1.2:
                    findings.append("⚠️  Medium JD shows 20%+ performance penalty")
                else:
                    findings.append("✅ Order effects may explain the anomaly")

        # Analyze formatting effects
        if "content_formatting" in all_results["experiments"]:
            formatting_results = all_results["experiments"]["content_formatting"]["results"]

            # Group by variation
            by_variation = {}
            for result in formatting_results:
                if result['success']:
                    var_name = result['variation']
                    if var_name not in by_variation:
                        by_variation[var_name] = []
                    by_variation[var_name].append(result['response_time_ms'])

            print("\n2. FORMATTING EFFECTS FINDINGS:")
            for var_name, times in by_variation.items():
                if times:
                    avg_time = statistics.mean(times)
                    print(f"   {var_name}: {avg_time:.2f}ms")

            # Check if formatting makes a difference
            if len(by_variation) >= 2:
                times_list = list(by_variation.values())
                if len(times_list) >= 2:
                    original_times = by_variation.get("Medium Original (with bullets)", [])
                    plain_times = by_variation.get("Medium Plain Text", [])

                    if original_times and plain_times:
                        original_avg = statistics.mean(original_times)
                        plain_avg = statistics.mean(plain_times)

                        if abs(original_avg - plain_avg) / min(original_avg, plain_avg) > 0.1:
                            findings.append("❌ Text formatting significantly affects performance")
                        else:
                            findings.append("✅ Text formatting has minimal impact")

        # Final verdict
        print("\n" + "="*80)
        print("FINAL VERDICT")
        print("="*80)

        if findings:
            for finding in findings:
                print(f"{finding}")
        else:
            print("🤔 Results inconclusive - more investigation needed")

        print("\nRECOMMENDATIONS:")
        if any("Medium JD consistently slower" in f for f in findings):
            print("1. ✅ The performance anomaly is REAL and reproducible")
            print("2. 🔍 Investigate LLM processing of bullet-point formatted text")
            print("3. 📊 Analyze token count and model attention patterns")
            print("4. 🧪 Test with different LLM models to confirm")
        elif any("formatting significantly affects" in f for f in findings):
            print("1. ✅ Text formatting is the root cause")
            print("2. 🔧 Consider preprocessing bullet points before LLM processing")
            print("3. 📝 Update documentation to warn about formatting impact")
        else:
            print("1. 🧪 The issue may be intermittent or environment-specific")
            print("2. 📊 Collect more data over longer time periods")
            print("3. 🔍 Check system resources and API server health during tests")


def main():
    """Main function to run controlled experiments."""
    print("🚀 Starting Controlled Performance Experiments")
    print("🎯 Investigating Medium JD performance anomaly")

    experiments = ControlledPerformanceExperiments()
    results = experiments.run_all_experiments()

    if "error" not in results:
        print("\n✅ All experiments completed successfully!")
    else:
        print(f"\n❌ Experiments failed: {results['error']}")


if __name__ == "__main__":
    main()
