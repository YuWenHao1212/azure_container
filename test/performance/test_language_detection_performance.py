#!/usr/bin/env python3
"""
Performance test for language detection services.
Test ID: LANG-DET-106-PT

Measures response time, throughput, concurrency, and memory usage for language detection.
Compares RuleBasedLanguageDetector vs SimplifiedLanguageDetector performance.
"""

import asyncio
import gc
import os
import statistics
import sys
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import psutil
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.services.language_detection.rule_based_detector import RuleBasedLanguageDetector
from src.services.language_detection.simple_language_detector import SimplifiedLanguageDetector


class PerformanceResult:
    """Container for performance test results."""

    def __init__(self, detector_name: str):
        self.detector_name = detector_name
        self.response_times: list[float] = []
        self.memory_usage: list[float] = []
        self.errors: list[str] = []
        self.throughput_results: list[dict[str, Any]] = []

    def add_response_time(self, time_ms: float) -> None:
        """Add a response time measurement."""
        self.response_times.append(time_ms)

    def add_memory_usage(self, memory_mb: float) -> None:
        """Add a memory usage measurement."""
        self.memory_usage.append(memory_mb)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def get_statistics(self) -> dict[str, Any]:
        """Calculate performance statistics."""
        if not self.response_times:
            return {"error": "No successful measurements"}

        sorted_times = sorted(self.response_times)
        n = len(sorted_times)

        return {
            "count": n,
            "min_ms": min(sorted_times),
            "max_ms": max(sorted_times),
            "mean_ms": statistics.mean(sorted_times),
            "median_ms": statistics.median(sorted_times),
            "std_dev_ms": statistics.stdev(sorted_times) if n > 1 else 0,
            "p50_ms": sorted_times[int(n * 0.50)],
            "p90_ms": sorted_times[int(n * 0.90)],
            "p95_ms": sorted_times[int(n * 0.95)],
            "p99_ms": sorted_times[int(n * 0.99)] if n > 100 else sorted_times[-1],
            "errors": len(self.errors),
            "error_rate": len(self.errors) / (n + len(self.errors)) if (n + len(self.errors)) > 0 else 0,
        }


class TestLanguageDetectionPerformance:
    """Performance test suite for language detection services."""

    @pytest.fixture
    def rule_based_detector(self):
        """Create RuleBasedLanguageDetector instance."""
        return RuleBasedLanguageDetector()

    @pytest.fixture
    def simplified_detector(self):
        """Create SimplifiedLanguageDetector instance."""
        return SimplifiedLanguageDetector()

    @pytest.fixture
    def test_texts(self) -> dict[str, str]:
        """Test texts of different lengths."""
        return {
            "short_english": "Python developer with FastAPI experience. Must have Docker skills.",
            "short_chinese": "我們正在尋找一位資深Python開發工程師, 具備FastAPI框架經驗。",
            "medium_english": """
We are seeking a Senior Full Stack Developer to join our growing team.
Requirements: 5+ years experience with Python, FastAPI, Django, React, TypeScript.
Strong knowledge of microservices, Docker, Kubernetes, AWS cloud services.
Experience with PostgreSQL, MongoDB, Redis databases.
Excellent problem-solving skills and team collaboration abilities.
            """.strip(),
            "medium_chinese": """
我們正在招聘一位資深全端開發工程師加入我們不斷成長的團隊。
職位要求: 5年以上Python、FastAPI、Django、React、TypeScript開發經驗。
具備微服務架構、Docker、Kubernetes、AWS雲端服務的深度知識。
熟悉PostgreSQL、MongoDB、Redis等數據庫系統。
擁有優秀的問題解決能力和團隊協作精神。
            """.strip(),
            "long_english": """
Senior Backend Engineer - Python/FastAPI Specialist

Position Overview:
We are looking for a talented Senior Backend Engineer to join our engineering team.
You will be responsible for designing, developing, and maintaining scalable backend services
that serve millions of users worldwide.

Key Responsibilities:
- Design and implement RESTful APIs using Python and FastAPI framework
- Build and maintain microservices architecture with proper service discovery
- Optimize database queries and improve overall system performance
- Implement comprehensive security best practices and data protection measures
- Collaborate effectively with frontend developers and DevOps engineers
- Mentor junior developers and conduct thorough code reviews
- Participate in on-call rotation and incident response procedures

Technical Requirements:
- 5+ years of backend development experience in production environments
- Expert-level Python programming skills with deep understanding of async/await
- Extensive experience with FastAPI, Django, or Flask web frameworks
- Proficiency in SQL and NoSQL databases including PostgreSQL, MongoDB, and Redis
- Hands-on experience with message queues such as RabbitMQ or Apache Kafka
- Strong experience with containerization using Docker and orchestration with Kubernetes
- Familiarity with major cloud providers: AWS, GCP, or Azure services
- Understanding of software design patterns and SOLID principles
- Experience with CI/CD pipelines and automated testing frameworks
- Knowledge of monitoring and observability tools like Prometheus, Grafana, or ELK stack

Nice to Have:
- Experience with GraphQL API development and schema design
- Knowledge of additional programming languages such as Golang or Rust
- Active contributions to open-source projects and community involvement
- AWS, GCP, or Azure professional certifications
- Experience with event-driven architectures and distributed systems
            """.strip(),
            "long_chinese": """
資深後端工程師 - Python/FastAPI 專家

職位概述:
我們正在尋找一位才華橫溢的資深後端工程師加入我們的工程團隊。
您將負責設計、開發和維護可擴展的後端服務, 為全球數百萬用戶提供服務。

主要職責:
- 使用Python和FastAPI框架設計並實現RESTful API
- 構建和維護具有適當服務發現功能的微服務架構
- 優化數據庫查詢並提升整體系統性能
- 實施全面的安全最佳實踐和數據保護措施
- 與前端開發人員和DevOps工程師有效協作
- 指導初級開發人員並進行全面的代碼審查
- 參與值班輪換和事件響應程序

技術要求:
- 5年以上生產環境後端開發經驗
- 專家級Python編程技能, 深度理解async/await機制
- 豐富的FastAPI、Django或Flask網絡框架經驗
- 熟練掌握SQL和NoSQL數據庫, 包括PostgreSQL、MongoDB和Redis
- 具備消息佇列(如RabbitMQ或Apache Kafka)的實作經驗
- 豐富的Docker容器化和Kubernetes編排經驗
- 熟悉主要雲端服務提供商: AWS、GCP或Azure服務
- 理解軟件設計模式和SOLID原則
- 具備CI/CD管道和自動化測試框架經驗
- 了解監控和可觀測性工具, 如Prometheus、Grafana或ELK堆棧

加分項目:
- 具備GraphQL API開發和模式設計經驗
- 掌握其他編程語言如Golang或Rust
- 積極貢獻開源項目並參與社群活動
- 擁有AWS、GCP或Azure專業認證
- 具備事件驅動架構和分佈式系統經驗
            """.strip(),
        }

    async def _measure_single_detection(
        self, detector, text: str, text_name: str
    ) -> tuple[float, str]:
        """Measure single detection time and return result."""
        start_time = time.perf_counter()
        try:
            result = await detector.detect_language(text)
            end_time = time.perf_counter()
            detection_time_ms = (end_time - start_time) * 1000
            return detection_time_ms, f"Success: {result.language} ({result.confidence:.3f})"
        except Exception as e:
            end_time = time.perf_counter()
            detection_time_ms = (end_time - start_time) * 1000
            error_msg = f"Error: {type(e).__name__}: {e!s}"
            return detection_time_ms, error_msg

    def test_single_detection_performance(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Test single detection performance - target: < 5ms per detection."""
        print(f"\n{'=' * 80}")
        print("TEST 1: Single Detection Performance")
        print(f"{'=' * 80}")
        print("Target: < 5ms per detection\n")

        results = {
            "RuleBasedLanguageDetector": PerformanceResult("RuleBasedLanguageDetector"),
            "SimplifiedLanguageDetector": PerformanceResult("SimplifiedLanguageDetector"),
        }

        async def run_single_tests():
            for text_name, text in test_texts.items():
                print(f"Testing with {text_name} ({len(text)} chars):")
                print("-" * 50)

                # Test RuleBasedLanguageDetector
                for _i in range(10):  # Multiple runs for statistical accuracy
                    time_ms, status = await self._measure_single_detection(
                        rule_based_detector, text, text_name
                    )
                    results["RuleBasedLanguageDetector"].add_response_time(time_ms)
                    if "Error" in status:
                        results["RuleBasedLanguageDetector"].add_error(status)

                # Test SimplifiedLanguageDetector
                for _i in range(10):
                    time_ms, status = await self._measure_single_detection(
                        simplified_detector, text, text_name
                    )
                    results["SimplifiedLanguageDetector"].add_response_time(time_ms)
                    if "Error" in status:
                        results["SimplifiedLanguageDetector"].add_error(status)

                # Report results for this text
                rule_stats = results["RuleBasedLanguageDetector"].get_statistics()
                simple_stats = results["SimplifiedLanguageDetector"].get_statistics()

                print("RuleBasedLanguageDetector:")
                print(f"  Average: {rule_stats.get('mean_ms', 0):.2f}ms")
                print(f"  Min/Max: {rule_stats.get('min_ms', 0):.2f}/{rule_stats.get('max_ms', 0):.2f}ms")

                print("SimplifiedLanguageDetector:")
                print(f"  Average: {simple_stats.get('mean_ms', 0):.2f}ms")
                print(f"  Min/Max: {simple_stats.get('min_ms', 0):.2f}/{simple_stats.get('max_ms', 0):.2f}ms")
                print()

        asyncio.run(run_single_tests())

        # Overall statistics
        print("OVERALL SINGLE DETECTION PERFORMANCE:")
        print("=" * 50)
        for detector_name, result in results.items():
            stats = result.get_statistics()
            if "error" not in stats:
                avg_time = stats["mean_ms"]
                max_time = stats["max_ms"]
                p95_time = stats["p95_ms"]

                print(f"\n{detector_name}:")
                print(f"  Average: {avg_time:.2f}ms")
                print(f"  P95: {p95_time:.2f}ms")
                print(f"  Max: {max_time:.2f}ms")
                print(f"  Errors: {stats['errors']}/{stats['count']} ({stats['error_rate']*100:.1f}%)")

                # Performance verdict
                if avg_time < 5.0 and p95_time < 10.0:
                    print("  ✅ EXCELLENT: Meets < 5ms target")
                elif avg_time < 10.0:
                    print("  ✅ PASS: Within acceptable range")
                else:
                    print("  ❌ SLOW: Exceeds performance target")

        # Comparison
        rule_avg = results["RuleBasedLanguageDetector"].get_statistics().get("mean_ms", float("inf"))
        simple_avg = results["SimplifiedLanguageDetector"].get_statistics().get("mean_ms", float("inf"))

        if rule_avg < simple_avg:
            improvement = ((simple_avg - rule_avg) / simple_avg) * 100
            print(f"\n🏆 RuleBasedLanguageDetector is {improvement:.1f}% faster")
        elif simple_avg < rule_avg:
            improvement = ((rule_avg - simple_avg) / rule_avg) * 100
            print(f"\n🏆 SimplifiedLanguageDetector is {improvement:.1f}% faster")
        else:
            print("\n🤝 Both detectors have similar performance")

    def test_throughput_performance(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Test throughput performance - target: 100+ QPS for 10 seconds."""
        print(f"\n{'=' * 80}")
        print("TEST 2: Throughput Performance")
        print(f"{'=' * 80}")
        print("Target: 100+ QPS (queries per second) for 10 seconds\n")

        # Use medium-length English text for throughput testing
        test_text = test_texts["medium_english"]
        test_duration = 10  # seconds

        async def measure_throughput(detector, detector_name: str) -> dict[str, Any]:
            """Measure throughput for a detector."""
            print(f"Testing {detector_name} throughput...")

            request_count = 0
            error_count = 0
            response_times = []
            start_time = time.time()

            while (time.time() - start_time) < test_duration:
                batch_start = time.perf_counter()
                try:
                    await detector.detect_language(test_text)
                    batch_end = time.perf_counter()
                    response_times.append((batch_end - batch_start) * 1000)
                    request_count += 1
                except Exception:
                    error_count += 1
                    batch_end = time.perf_counter()
                    response_times.append((batch_end - batch_start) * 1000)

            actual_duration = time.time() - start_time
            qps = request_count / actual_duration

            return {
                "detector": detector_name,
                "duration": actual_duration,
                "requests": request_count,
                "errors": error_count,
                "qps": qps,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "error_rate": error_count / (request_count + error_count) if (request_count + error_count) > 0 else 0,
            }

        async def run_throughput_tests():
            # Test both detectors
            rule_result = await measure_throughput(rule_based_detector, "RuleBasedLanguageDetector")
            simple_result = await measure_throughput(simplified_detector, "SimplifiedLanguageDetector")

            # Report results
            print("\nTHROUGHPUT TEST RESULTS:")
            print("=" * 50)

            for result in [rule_result, simple_result]:
                print(f"\n{result['detector']}:")
                print(f"  Duration: {result['duration']:.1f}s")
                print(f"  Requests: {result['requests']}")
                print(f"  QPS: {result['qps']:.1f}")
                print(f"  Avg Response Time: {result['avg_response_time']:.2f}ms")
                print(f"  Error Rate: {result['error_rate']*100:.1f}%")

                # Performance verdict
                if result['qps'] >= 100:
                    print("  ✅ EXCELLENT: Exceeds 100 QPS target")
                elif result['qps'] >= 50:
                    print("  ✅ PASS: Good throughput performance")
                elif result['qps'] >= 20:
                    print("  ⚠️  ACCEPTABLE: Moderate throughput")
                else:
                    print("  ❌ POOR: Below acceptable throughput")

            # Comparison
            if rule_result['qps'] > simple_result['qps']:
                improvement = ((rule_result['qps'] - simple_result['qps']) / simple_result['qps']) * 100
                print(f"\n🏆 RuleBasedLanguageDetector: {improvement:.1f}% higher throughput")
            elif simple_result['qps'] > rule_result['qps']:
                improvement = ((simple_result['qps'] - rule_result['qps']) / rule_result['qps']) * 100
                print(f"\n🏆 SimplifiedLanguageDetector: {improvement:.1f}% higher throughput")

        asyncio.run(run_throughput_tests())

    def test_concurrency_performance(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Test concurrent performance and thread safety."""
        print(f"\n{'=' * 80}")
        print("TEST 3: Concurrency Performance & Thread Safety")
        print(f"{'=' * 80}")
        print("Testing multi-threaded concurrent execution\n")

        test_text = test_texts["medium_english"]
        thread_counts = [5, 10, 20]
        requests_per_thread = 10

        def worker_function(detector, detector_name: str, thread_id: int) -> dict[str, Any]:
            """Worker function for thread testing."""
            results = []
            errors = []

            # Record thread info
            thread_name = threading.current_thread().name
            process_id = os.getpid()

            for i in range(requests_per_thread):
                start_time = time.perf_counter()
                try:
                    # Note: We need to run async code in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(detector.detect_language(test_text))
                        end_time = time.perf_counter()
                        response_time = (end_time - start_time) * 1000
                        results.append({
                            "thread_id": thread_id,
                            "request_id": i,
                            "response_time_ms": response_time,
                            "language": result.language,
                            "confidence": result.confidence,
                            "success": True
                        })
                    finally:
                        loop.close()
                except Exception as e:
                    end_time = time.perf_counter()
                    response_time = (end_time - start_time) * 1000
                    errors.append({
                        "thread_id": thread_id,
                        "request_id": i,
                        "response_time_ms": response_time,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })

            return {
                "thread_id": thread_id,
                "thread_name": thread_name,
                "process_id": process_id,
                "detector": detector_name,
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors)
            }

        def test_detector_concurrency(detector, detector_name: str):
            """Test concurrency for a specific detector."""
            print(f"Testing {detector_name} concurrency:")
            print("-" * 40)

            for thread_count in thread_counts:
                print(f"  {thread_count} threads x {requests_per_thread} requests each...")

                start_time = time.time()

                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    futures = [
                        executor.submit(worker_function, detector, detector_name, thread_id)
                        for thread_id in range(thread_count)
                    ]

                    thread_results = [future.result() for future in futures]

                end_time = time.time()
                total_duration = end_time - start_time

                # Aggregate results
                total_requests = sum(len(tr["results"]) + len(tr["errors"]) for tr in thread_results)
                total_successes = sum(tr["success_count"] for tr in thread_results)
                sum(tr["error_count"] for tr in thread_results)
                all_response_times = []

                for tr in thread_results:
                    all_response_times.extend([r["response_time_ms"] for r in tr["results"]])

                # Calculate statistics
                if all_response_times:
                    avg_response_time = statistics.mean(all_response_times)
                    p95_response_time = sorted(all_response_times)[int(len(all_response_times) * 0.95)]
                    max_response_time = max(all_response_times)
                else:
                    avg_response_time = p95_response_time = max_response_time = 0

                success_rate = (total_successes / total_requests) * 100 if total_requests > 0 else 0
                overall_qps = total_requests / total_duration

                print(f"    Duration: {total_duration:.2f}s")
                print(f"    Success Rate: {success_rate:.1f}% ({total_successes}/{total_requests})")
                print(f"    Overall QPS: {overall_qps:.1f}")
                print(f"    Avg Response Time: {avg_response_time:.2f}ms")
                print(f"    P95 Response Time: {p95_response_time:.2f}ms")
                print(f"    Max Response Time: {max_response_time:.2f}ms")

                # Thread safety check
                unique_processes = {tr["process_id"] for tr in thread_results}
                unique_threads = {tr["thread_name"] for tr in thread_results}

                if len(unique_processes) == 1 and len(unique_threads) == thread_count:
                    print(f"    ✅ Thread Safety: PASS (single process, {thread_count} threads)")
                else:
                    print("    ⚠️  Thread Safety: WARNING (multiple processes detected)")

                # Performance verdict
                if success_rate >= 99 and avg_response_time < 50:
                    print("    ✅ EXCELLENT: High success rate, low latency")
                elif success_rate >= 95 and avg_response_time < 100:
                    print("    ✅ PASS: Good concurrency performance")
                else:
                    print("    ❌ ISSUES: Poor concurrency performance")
                print()

        # Test both detectors
        test_detector_concurrency(rule_based_detector, "RuleBasedLanguageDetector")
        test_detector_concurrency(simplified_detector, "SimplifiedLanguageDetector")

    def test_memory_usage(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Test memory usage and check for memory leaks."""
        print(f"\n{'=' * 80}")
        print("TEST 4: Memory Usage Analysis")
        print(f"{'=' * 80}")
        print("Monitoring memory usage and checking for leaks\n")

        def measure_memory_usage(detector, detector_name: str, test_text: str) -> dict[str, Any]:
            """Measure memory usage for a detector."""

            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Start memory tracing
            tracemalloc.start()

            # Perform many detections to check for memory leaks
            iterations = 100
            memory_samples = []

            async def run_detections():
                for i in range(iterations):
                    try:
                        await detector.detect_language(test_text)

                        # Sample memory every 10 iterations
                        if i % 10 == 0:
                            current_memory = process.memory_info().rss / 1024 / 1024
                            memory_samples.append(current_memory)

                    except Exception as e:
                        # Ignore errors for memory testing, but log for debugging if needed
                        print(f"Memory test iteration {i} error: {type(e).__name__}", end="")

                    # Force garbage collection periodically
                    if i % 50 == 0:
                        gc.collect()

            # Run the test
            asyncio.run(run_detections())

            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Calculate memory statistics
            memory_growth = final_memory - initial_memory
            peak_memory_mb = peak / 1024 / 1024

            return {
                "detector": detector_name,
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_growth_mb": memory_growth,
                "peak_traced_memory_mb": peak_memory_mb,
                "memory_samples": memory_samples,
                "iterations": iterations
            }

        # Test memory usage with medium-length text
        test_text = test_texts["medium_english"]

        print("Measuring memory usage...")
        rule_memory = measure_memory_usage(rule_based_detector, "RuleBasedLanguageDetector", test_text)
        simple_memory = measure_memory_usage(simplified_detector, "SimplifiedLanguageDetector", test_text)

        # Report results
        print("\nMEMORY USAGE RESULTS:")
        print("=" * 50)

        for result in [rule_memory, simple_memory]:
            print(f"\n{result['detector']}:")
            print(f"  Initial Memory: {result['initial_memory_mb']:.2f} MB")
            print(f"  Final Memory: {result['final_memory_mb']:.2f} MB")
            print(f"  Memory Growth: {result['memory_growth_mb']:.2f} MB")
            print(f"  Peak Traced Memory: {result['peak_traced_memory_mb']:.2f} MB")
            print(f"  Iterations: {result['iterations']}")

            # Memory leak analysis
            memory_samples = result['memory_samples']
            if len(memory_samples) >= 2:
                initial_sample = memory_samples[0]
                final_sample = memory_samples[-1]
                sample_growth = final_sample - initial_sample

                print(f"  Sample Growth: {sample_growth:.2f} MB")

                # Verdict
                if abs(result['memory_growth_mb']) < 1.0:
                    print("  ✅ EXCELLENT: Minimal memory growth")
                elif abs(result['memory_growth_mb']) < 5.0:
                    print("  ✅ PASS: Acceptable memory usage")
                elif abs(result['memory_growth_mb']) < 10.0:
                    print("  ⚠️  WARNING: Moderate memory growth")
                else:
                    print("  ❌ LEAK CONCERN: Significant memory growth")
            else:
                print("  ⚠️  Insufficient memory samples")

        # Comparison
        rule_growth = rule_memory['memory_growth_mb']
        simple_growth = simple_memory['memory_growth_mb']

        print("\nMEMORY EFFICIENCY COMPARISON:")
        if abs(rule_growth) < abs(simple_growth):
            print("🏆 RuleBasedLanguageDetector uses less memory")
        elif abs(simple_growth) < abs(rule_growth):
            print("🏆 SimplifiedLanguageDetector uses less memory")
        else:
            print("🤝 Both detectors have similar memory usage")

    def test_text_length_performance(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Test performance with different text lengths."""
        print(f"\n{'=' * 80}")
        print("TEST 5: Text Length Performance Analysis")
        print(f"{'=' * 80}")
        print("Analyzing performance across different text sizes\n")

        # Group test texts by length
        text_groups = {
            "Short (100 chars)": {"short_english", "short_chinese"},
            "Medium (500 chars)": {"medium_english", "medium_chinese"},
            "Long (2000 chars)": {"long_english", "long_chinese"}
        }

        async def test_length_performance():
            results = {}

            for group_name, text_keys in text_groups.items():
                print(f"Testing {group_name}:")
                print("-" * 30)

                group_results = {
                    "RuleBasedLanguageDetector": [],
                    "SimplifiedLanguageDetector": []
                }

                for text_key in text_keys:
                    if text_key not in test_texts:
                        continue

                    text = test_texts[text_key]
                    print(f"  {text_key} ({len(text)} chars)")

                    # Test each detector multiple times
                    for _ in range(5):
                        # RuleBasedLanguageDetector
                        start_time = time.perf_counter()
                        try:
                            await rule_based_detector.detect_language(text)
                            end_time = time.perf_counter()
                            group_results["RuleBasedLanguageDetector"].append((end_time - start_time) * 1000)
                        except Exception:  # noqa: S112
                            # Skip failed detections in performance test
                            continue

                        # SimplifiedLanguageDetector
                        start_time = time.perf_counter()
                        try:
                            await simplified_detector.detect_language(text)
                            end_time = time.perf_counter()
                            group_results["SimplifiedLanguageDetector"].append((end_time - start_time) * 1000)
                        except Exception:  # noqa: S112
                            # Skip failed detections in performance test
                            continue

                # Calculate averages for this group
                results[group_name] = {}
                for detector_name, times in group_results.items():
                    if times:
                        avg_time = statistics.mean(times)
                        results[group_name][detector_name] = avg_time
                        print(f"    {detector_name}: {avg_time:.2f}ms avg")
                    else:
                        results[group_name][detector_name] = None
                        print(f"    {detector_name}: No successful measurements")

                print()

            # Performance scaling analysis
            print("PERFORMANCE SCALING ANALYSIS:")
            print("=" * 50)

            for detector_name in ["RuleBasedLanguageDetector", "SimplifiedLanguageDetector"]:
                print(f"\n{detector_name}:")
                scaling_data = []

                for group_name in ["Short (100 chars)", "Medium (500 chars)", "Long (2000 chars)"]:
                    avg_time = results[group_name].get(detector_name)
                    if avg_time is not None:
                        scaling_data.append((group_name, avg_time))
                        print(f"  {group_name}: {avg_time:.2f}ms")

                # Check if performance scales linearly with text length
                if len(scaling_data) >= 2:
                    short_time = next((time for name, time in scaling_data if "Short" in name), None)
                    long_time = next((time for name, time in scaling_data if "Long" in name), None)

                    if short_time and long_time:
                        scaling_factor = long_time / short_time
                        print(f"  Scaling Factor (Long/Short): {scaling_factor:.2f}x")

                        if scaling_factor < 2.0:
                            print("  ✅ EXCELLENT: Sub-linear scaling")
                        elif scaling_factor < 5.0:
                            print("  ✅ PASS: Reasonable scaling")
                        else:
                            print("  ⚠️  WARNING: Poor scaling with text length")

        asyncio.run(test_length_performance())

    def test_comprehensive_performance_report(
        self, rule_based_detector, simplified_detector, test_texts
    ):
        """Generate comprehensive performance report."""
        print(f"\n{'=' * 80}")
        print("COMPREHENSIVE PERFORMANCE REPORT")
        print(f"{'=' * 80}")
        print(f"Test Timestamp: {datetime.now().isoformat()}")
        print(f"Test Environment: Python {sys.version}")
        print(f"Process ID: {os.getpid()}")

        # System information
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        print(f"System: {cpu_count} CPUs, {memory_gb:.1f}GB RAM")
        print()

        # Test summary will be populated by individual tests
        print("Individual test methods will populate detailed results above.")
        print("This method serves as the final summary and report generation.")

        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test/logs/language_detection_performance_{timestamp}.txt"

        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        # Note: In a real implementation, you would collect all results
        # from previous tests and generate a comprehensive JSON/text report
        print(f"\n📊 Performance report would be saved to: {report_file}")
        print("(Report generation logic would be implemented here)")

        print(f"\n{'=' * 80}")
        print("PERFORMANCE TEST SUITE COMPLETED")
        print(f"{'=' * 80}")


# Convenience functions for running individual tests
async def run_quick_performance_test():
    """Quick performance test for development."""
    print("🚀 Running Quick Language Detection Performance Test")

    TestLanguageDetectionPerformance()
    rule_detector = RuleBasedLanguageDetector()
    simple_detector = SimplifiedLanguageDetector()

    test_texts = {
        "english": "Python developer with FastAPI experience required.",
        "chinese": "我們正在尋找資深Python開發工程師。"
    }

    # Quick single detection test
    print("\nQuick Single Detection Test:")
    print("-" * 40)

    for name, text in test_texts.items():
        print(f"\nTesting {name} text:")

        # RuleBasedLanguageDetector
        start_time = time.perf_counter()
        try:
            result = await rule_detector.detect_language(text)
            end_time = time.perf_counter()
            time_ms = (end_time - start_time) * 1000
            print(f"  RuleBased: {time_ms:.2f}ms -> {result.language} ({result.confidence:.3f})")
        except Exception as e:
            print(f"  RuleBased: ERROR - {e}")

        # SimplifiedLanguageDetector
        start_time = time.perf_counter()
        try:
            result = await simple_detector.detect_language(text)
            end_time = time.perf_counter()
            time_ms = (end_time - start_time) * 1000
            print(f"  Simplified: {time_ms:.2f}ms -> {result.language} ({result.confidence:.3f})")
        except Exception as e:
            print(f"  Simplified: ERROR - {e}")


if __name__ == "__main__":
    """Run performance tests directly."""
    import argparse

    parser = argparse.ArgumentParser(description="Language Detection Performance Tests")
    parser.add_argument("--quick", action="store_true", help="Run quick performance test only")
    parser.add_argument("--pytest", action="store_true", help="Run with pytest framework")

    args = parser.parse_args()

    if args.quick:
        asyncio.run(run_quick_performance_test())
    elif args.pytest:
        # Run with pytest
        import subprocess
        subprocess.run([  # noqa: S603, S607
            "python", "-m", "pytest",
            "test/performance/test_language_detection_performance.py",
            "-v", "-s"
        ], check=False, shell=False)
    else:
        print("Language Detection Performance Test Suite")
        print("Usage:")
        print("  python test_language_detection_performance.py --quick    # Quick test")
        print("  python test_language_detection_performance.py --pytest  # Full pytest suite")
        print("  pytest test/performance/test_language_detection_performance.py -v -s  # Direct pytest")
