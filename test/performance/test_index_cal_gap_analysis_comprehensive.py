#!/usr/bin/env python3
"""
Comprehensive Performance Testing for /api/v1/index-cal-and-gap-analysis API

This script performs detailed performance analysis with:
- 20 unique test cases to avoid cache impacts
- Function block timing breakdown
- Gantt chart visualization
- P50/P95/worst-case statistics
- Detailed timing analysis for each component

Author: Claude Code + WenHao
Date: 2025-01-17
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import median, quantiles
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from httpx import AsyncClient

# Project root and test data paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_FIXTURES_DIR = PROJECT_ROOT / "test/fixtures/performance_test_data"
PERFORMANCE_RESULTS_DIR = PROJECT_ROOT / "docs/issues/index-cal-gap-analysis-evolution/performance"

# Ensure results directory exists
PERFORMANCE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
API_BASE_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_ENDPOINT = "/api/v1/index-cal-and-gap-analysis"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "")

# Performance Test Configuration
NUM_TEST_RUNS = 20
DELAY_BETWEEN_TESTS = 2.0  # seconds to avoid rate limiting


class PerformanceTestRunner:
    """Performance test runner for index-cal-and-gap-analysis API"""

    def __init__(self):
        self.test_fixtures_dir = TEST_FIXTURES_DIR
        self.results_dir = PERFORMANCE_RESULTS_DIR
        self.test_registry = None
        self.resume_content = None
        self.test_results = []
        self.timing_breakdown = []

    def load_test_data(self):
        """Load all test data from fixtures"""
        print("📂 Loading test data from fixtures...")

        # Load test registry
        registry_path = self.test_fixtures_dir / "test_data_registry.json"
        with open(registry_path, encoding='utf-8') as f:
            self.test_registry = json.load(f)

        # Load resume
        resume_path = self.test_fixtures_dir / self.test_registry["metadata"]["resume_file"]
        with open(resume_path, encoding='utf-8') as f:
            self.resume_content = f.read()

        print(f"✅ Loaded {len(self.test_registry['test_cases'])} test cases")
        print(f"✅ Resume loaded: {len(self.resume_content)} characters")

    def prepare_api_request(self, test_case: dict) -> dict:
        """Prepare API request payload for a test case"""
        # Load JD content
        jd_path = self.test_fixtures_dir / test_case["job_description_file"]
        with open(jd_path, encoding='utf-8') as f:
            jd_content = f.read()

        # Load keywords
        keywords_path = self.test_fixtures_dir / test_case["keywords_file"]
        with open(keywords_path, encoding='utf-8') as f:
            keywords = json.load(f)

        return {
            "resume": self.resume_content,
            "job_description": jd_content,
            "keywords": keywords
        }

    async def call_api(self, client: AsyncClient, payload: dict, test_id: str) -> tuple[dict, dict]:
        """Call the API and measure detailed timings"""
        headers = {
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        }

        # Record start time
        start_time = time.time()
        timing_details = {
            "test_id": test_id,
            "start_time": start_time,
            "request_sent": None,
            "first_byte": None,
            "response_complete": None,
            "total_time": None
        }

        # Send request
        timing_details["request_sent"] = time.time()

        try:
            response = await client.post(
                f"{API_BASE_URL}{API_ENDPOINT}",
                json=payload,
                headers=headers,
                timeout=60.0
            )

            timing_details["first_byte"] = time.time()
            response_data = response.json()
            timing_details["response_complete"] = time.time()

            # Calculate total time
            timing_details["total_time"] = timing_details["response_complete"] - start_time

            # Extract server-side timing if available from metadata
            if "metadata" in response_data and "detailed_timings_ms" in response_data["metadata"]:
                timing_details["server_timings"] = response_data["metadata"]["detailed_timings_ms"]

            return response_data, timing_details

        except Exception as e:
            print(f"❌ Error calling API for test {test_id}: {e}")
            timing_details["error"] = str(e)
            timing_details["total_time"] = time.time() - start_time
            return None, timing_details

    async def run_performance_tests(self):
        """Run all performance tests"""
        print("\n🚀 Starting performance tests...")
        print(f"   Running {NUM_TEST_RUNS} tests with {DELAY_BETWEEN_TESTS}s delay between tests")

        async with AsyncClient() as client:
            for i, test_case in enumerate(self.test_registry["test_cases"][:NUM_TEST_RUNS]):
                test_id = test_case["id"]
                print(f"\n📊 Test {i+1}/{NUM_TEST_RUNS}: {test_case['company']} - {test_case['position']}")

                # Prepare request
                payload = self.prepare_api_request(test_case)

                # Call API and measure
                response, timing = await self.call_api(client, payload, test_id)

                # Store results
                self.test_results.append({
                    "test_case": test_case,
                    "response": response,
                    "timing": timing
                })

                # Extract timing breakdown if available
                if response and "metadata" in response and "detailed_timings_ms" in response["metadata"]:
                    self.timing_breakdown.append({
                        "test_id": test_id,
                        "company": test_case["company"],
                        "timings": response["metadata"]["detailed_timings_ms"]
                    })

                # Print summary
                if timing["total_time"]:
                    print(f"   ⏱️  Total time: {timing['total_time']:.2f}s")
                    if "server_timings" in timing:
                        server_timings = timing["server_timings"]
                        if isinstance(server_timings, dict):
                            print("   📈 Server breakdown:")
                            for key, value in server_timings.items():
                                if key not in ["total_time"] and value and isinstance(value, int | float):
                                    # Convert ms to seconds for display
                                    print(f"      - {key}: {value/1000:.3f}s")

                # Delay between tests (except last one)
                if i < NUM_TEST_RUNS - 1:
                    print(f"   ⏳ Waiting {DELAY_BETWEEN_TESTS}s before next test...")
                    await asyncio.sleep(DELAY_BETWEEN_TESTS)

    def calculate_statistics(self):
        """Calculate P50, P95, and worst-case statistics"""
        print("\n📈 Calculating statistics...")

        # Extract valid response times
        response_times = []
        for result in self.test_results:
            if result["timing"]["total_time"] and not result["timing"].get("error"):
                response_times.append(result["timing"]["total_time"])

        if not response_times:
            print("❌ No valid response times to analyze")
            return None

        # Sort for percentile calculations
        response_times.sort()

        # Calculate statistics
        stats = {
            "total_tests": NUM_TEST_RUNS,
            "successful_tests": len(response_times),
            "failed_tests": NUM_TEST_RUNS - len(response_times),
            "min_time": min(response_times),
            "max_time": max(response_times),
            "mean_time": sum(response_times) / len(response_times),
            "median_time": median(response_times),
            "p50": response_times[int(len(response_times) * 0.5)],
            "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0],
            "p99": response_times[int(len(response_times) * 0.99)] if len(response_times) > 2 else response_times[-1],
            "worst_case": max(response_times),
            "all_times": response_times
        }

        # Function block statistics if available
        if self.timing_breakdown:
            stats["function_blocks"] = self.analyze_function_blocks()

        return stats

    def analyze_function_blocks(self) -> dict:
        """Analyze timing breakdown by function blocks"""
        block_timings = {}

        # Collect timings from all test results
        for result in self.test_results:
            if result.get("response") and "metadata" in result["response"]:
                metadata = result["response"]["metadata"]

                # Parse detailed_timings_ms from metadata
                if "detailed_timings_ms" in metadata:
                    timings = metadata["detailed_timings_ms"]
                    for key, value in timings.items():
                        if key != "total_time" and value and isinstance(value, int | float):
                            if key not in block_timings:
                                block_timings[key] = []
                            block_timings[key].append(value)

        # Calculate statistics for each block
        block_stats = {}
        for block, times in block_timings.items():
            if times:
                times.sort()
                block_stats[block] = {
                    "mean": sum(times) / len(times),
                    "median": median(times),
                    "min": min(times),
                    "max": max(times),
                    "p50": times[int(len(times) * 0.5)],
                    "p95": times[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                }

        return block_stats

    def create_gantt_chart(self, stats: dict):
        """Create Gantt chart visualization of execution timeline"""
        print("\n📊 Creating Gantt chart visualization...")

        if not self.timing_breakdown:
            print("⚠️  No timing breakdown data available for Gantt chart")
            return

        # Prepare data for visualization
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Chart 1: Individual test execution timeline
        test_labels = []
        for i, result in enumerate(self.test_results[:10]):  # Show first 10 tests
            if result["timing"]["total_time"]:
                test_case = result["test_case"]
                test_labels.append(f"{test_case['company'][:15]}")

                # Draw bar for total time
                ax1.barh(i, result["timing"]["total_time"],
                        left=0, height=0.8,
                        color='steelblue', alpha=0.7)

                # Add timing label
                ax1.text(result["timing"]["total_time"] + 0.1, i,
                        f'{result["timing"]["total_time"]:.2f}s',
                        va='center', fontsize=9)

        ax1.set_yticks(range(len(test_labels)))
        ax1.set_yticklabels(test_labels)
        ax1.set_xlabel('Time (seconds)')
        ax1.set_title('API Response Times by Test Case (First 10)')
        ax1.grid(True, alpha=0.3)

        # Chart 2: Function block breakdown (average)
        if "function_blocks" in stats:
            blocks = stats["function_blocks"]
            block_names = list(blocks.keys())

            # Create stacked bar chart for function blocks
            block_means = [blocks[b]["mean"] for b in block_names]
            block_p95s = [blocks[b]["p95"] for b in block_names]

            x = np.arange(len(block_names))
            width = 0.35

            ax2.bar(x - width/2, block_means, width, label='Mean', color='green', alpha=0.7)
            ax2.bar(x + width/2, block_p95s, width, label='P95', color='red', alpha=0.7)

            ax2.set_xlabel('Function Block')
            ax2.set_ylabel('Time (seconds)')
            ax2.set_title('Function Block Timing Analysis')
            ax2.set_xticks(x)
            ax2.set_xticklabels(block_names, rotation=45, ha='right')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save chart
        chart_path = self.results_dir / f"gantt_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        print(f"✅ Gantt chart saved to: {chart_path}")

        plt.show()

    def create_enhanced_gantt_chart(self, stats: dict):
        """Create enhanced Gantt chart with parallel execution timeline"""
        print("\n📊 Creating enhanced Gantt chart visualization...")

        if not self.test_results:
            print("⚠️  No test results available for visualization")
            return

        # Create figure with 3 subplots
        plt.figure(figsize=(16, 12))

        # Subplot 1: Parallel Execution Timeline (for first test)
        ax1 = plt.subplot(3, 1, 1)

        # Get first test with detailed timeline
        first_test = None
        for result in self.test_results:
            if result.get("response") and "metadata" in result["response"]:
                metadata = result["response"]["metadata"]
                if "execution_timeline" in metadata:
                    first_test = result
                    break

        if first_test:
            timeline = first_test["response"]["metadata"]["execution_timeline"]
            test_info = first_test["test_case"]

            # Define task colors
            colors = {
                "keywords": "#FF6B6B",        # Red
                "embeddings": "#4ECDC4",      # Teal
                "structure_analysis": "#95E77E", # Green
                "pgvector_warmup": "#FFE66D",  # Yellow
                "index_calculation": "#A8DADC", # Light Blue
                "gap_analysis": "#457B9D",     # Dark Blue
                "course_availability": "#1D3557" # Navy
            }

            # Plot parallel tasks
            y_pos = 0
            task_positions = {}

            for task_name, task_data in timeline.get("parallel_tasks", {}).items():
                if task_data["end"] > 0:
                    ax1.barh(y_pos, task_data["end"] - task_data["start"],
                            left=task_data["start"], height=0.8,
                            color=colors.get(task_name, "gray"),
                            alpha=0.8, label=task_name)

                    # Add task name and duration
                    ax1.text(task_data["start"] + 5, y_pos,
                            f"{task_name}: {task_data['end']:.0f}ms",
                            va='center', fontsize=9, color='white', weight='bold')

                    task_positions[task_name] = y_pos
                    y_pos += 1

            # Plot sequential tasks
            for task_name, task_data in timeline.get("sequential_tasks", {}).items():
                if task_data["end"] > task_data["start"]:
                    ax1.barh(y_pos, task_data["end"] - task_data["start"],
                            left=task_data["start"], height=0.8,
                            color=colors.get(task_name, "gray"),
                            alpha=0.8, label=task_name)

                    # Add task name and duration
                    duration = task_data["end"] - task_data["start"]
                    ax1.text(task_data["start"] + 5, y_pos,
                            f"{task_name}: {duration:.0f}ms",
                            va='center', fontsize=9, color='white', weight='bold')

                    task_positions[task_name] = y_pos
                    y_pos += 1

            ax1.set_ylim(-0.5, y_pos - 0.5)
            ax1.set_xlabel('Time (milliseconds)')
            ax1.set_title(f'Parallel Execution Timeline - {test_info["company"]} {test_info["position"]}')
            ax1.grid(True, alpha=0.3, axis='x')
            ax1.set_yticks([])

            # Add vertical lines for phase transitions
            if "detailed_timings_ms" in first_test["response"]["metadata"]:
                timings = first_test["response"]["metadata"]["detailed_timings_ms"]
                if "embedding_time" in timings:
                    embedding_end = timings["embedding_time"]
                    ax1.axvline(x=embedding_end, color='red', linestyle='--', alpha=0.5, label='Phase 2 Start')

        # Subplot 2: Response Time Distribution
        ax2 = plt.subplot(3, 1, 2)
        self.plot_response_times(ax2, stats)

        # Subplot 3: Function Block Statistics
        ax3 = plt.subplot(3, 1, 3)
        self.plot_function_blocks(ax3, stats)

        plt.tight_layout()

        # Save chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_path = self.results_dir / f"enhanced_gantt_chart_{timestamp}.png"
        plt.savefig(chart_path, dpi=150, bbox_inches='tight')
        print(f"✅ Enhanced Gantt chart saved to: {chart_path}")

        plt.show()

    def plot_response_times(self, ax, stats):
        """Plot response time distribution"""
        if not self.test_results:
            return

        # Extract response times
        times = []
        labels = []
        for _, result in enumerate(self.test_results[:15]):  # First 15
            if result["timing"]["total_time"]:
                times.append(result["timing"]["total_time"])
                labels.append(f"{result['test_case']['company'][:10]}")

        if not times:
            return

        # Create bar chart
        colors = ['green' if t < stats['p50'] else 'yellow' if t < stats['p95'] else 'red' for t in times]
        ax.bar(range(len(times)), times, color=colors, alpha=0.7)

        # Add P50 and P95 lines
        ax.axhline(y=stats['p50'], color='green', linestyle='--', label=f'P50: {stats["p50"]:.2f}s')
        ax.axhline(y=stats['p95'], color='red', linestyle='--', label=f'P95: {stats["p95"]:.2f}s')

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Response Time (seconds)')
        ax.set_title('Response Time Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def plot_function_blocks(self, ax, stats):
        """Plot function block statistics"""
        if "function_blocks" not in stats:
            return

        blocks = stats["function_blocks"]
        block_names = list(blocks.keys())

        if not block_names:
            return

        # Prepare data
        block_means = [blocks[b]["mean"] for b in block_names]
        block_p95s = [blocks[b]["p95"] for b in block_names]

        x = np.arange(len(block_names))
        width = 0.35

        # Create bars
        bars1 = ax.bar(x - width/2, block_means, width, label='Mean', color='green', alpha=0.7)
        bars2 = ax.bar(x + width/2, block_p95s, width, label='P95', color='red', alpha=0.7)

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}', ha='center', va='bottom', fontsize=8)

        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}', ha='center', va='bottom', fontsize=8)

        ax.set_xlabel('Function Block')
        ax.set_ylabel('Time (milliseconds)')
        ax.set_title('Function Block Performance Statistics')
        ax.set_xticks(x)
        ax.set_xticklabels(block_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def save_results(self, stats: dict):
        """Save performance test results"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save detailed results as JSON
        results_file = self.results_dir / f"performance_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "configuration": {
                    "num_tests": NUM_TEST_RUNS,
                    "delay_between_tests": DELAY_BETWEEN_TESTS,
                    "api_endpoint": API_ENDPOINT
                },
                "statistics": stats,
                "test_results": [
                    {
                        "test_id": r["test_case"]["id"],
                        "company": r["test_case"]["company"],
                        "position": r["test_case"]["position"],
                        "total_time": r["timing"]["total_time"],
                        "error": r["timing"].get("error")
                    }
                    for r in self.test_results
                ]
            }, f, indent=2, default=str)

        print(f"✅ Results saved to: {results_file}")

        # Generate markdown report
        self.generate_markdown_report(stats, timestamp)

    def generate_markdown_report(self, stats: dict, timestamp: str):
        """Generate comprehensive markdown report"""
        report_file = self.results_dir / f"performance_report_{timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Performance Test Report - {timestamp}\n\n")
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests**: {stats['total_tests']}\n")
            f.write(f"- **Successful**: {stats['successful_tests']}\n")
            f.write(f"- **Failed**: {stats['failed_tests']}\n")
            f.write(f"- **P50 Response Time**: {stats['p50']:.2f}s\n")
            f.write(f"- **P95 Response Time**: {stats['p95']:.2f}s\n")
            f.write(f"- **Worst Case**: {stats['worst_case']:.2f}s\n\n")

            f.write("## Detailed Statistics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            f.write(f"| Minimum | {stats['min_time']:.3f}s |\n")
            f.write(f"| Median (P50) | {stats['median_time']:.3f}s |\n")
            f.write(f"| Mean | {stats['mean_time']:.3f}s |\n")
            f.write(f"| P95 | {stats['p95']:.3f}s |\n")
            f.write(f"| P99 | {stats['p99']:.3f}s |\n")
            f.write(f"| Maximum | {stats['max_time']:.3f}s |\n\n")

            if "function_blocks" in stats:
                f.write("## Function Block Analysis\n\n")
                f.write("| Block | Mean | P50 | P95 | Min | Max |\n")
                f.write("|-------|------|-----|-----|-----|-----|\n")

                for block, block_stats in stats["function_blocks"].items():
                    f.write(f"| {block} | {block_stats['mean']:.3f}s | ")
                    f.write(f"{block_stats['median']:.3f}s | ")
                    f.write(f"{block_stats['p95']:.3f}s | ")
                    f.write(f"{block_stats['min']:.3f}s | ")
                    f.write(f"{block_stats['max']:.3f}s |\n")

            f.write("\n## Test Case Details\n\n")
            f.write("| Test ID | Company | Position | Time (s) | Status |\n")
            f.write("|---------|---------|----------|----------|--------|\n")

            for result in self.test_results:
                test_case = result["test_case"]
                timing = result["timing"]
                status = "❌ Failed" if timing.get("error") else "✅ Success"
                time_str = f"{timing['total_time']:.3f}" if timing["total_time"] else "N/A"

                f.write(f"| {test_case['id']} | {test_case['company']} | ")
                f.write(f"{test_case['position']} | {time_str} | {status} |\n")

        print(f"✅ Report saved to: {report_file}")

    def print_summary(self, stats: dict):
        """Print performance test summary to console"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("="*60)
        print("\n🎯 Key Metrics:")
        print(f"   • P50 (Median): {stats['p50']:.2f}s")
        print(f"   • P95: {stats['p95']:.2f}s")
        print(f"   • Worst Case: {stats['worst_case']:.2f}s")
        print(f"   • Success Rate: {stats['successful_tests']}/{stats['total_tests']} ")
        print(f"     ({100*stats['successful_tests']/stats['total_tests']:.1f}%)")

        if "function_blocks" in stats:
            print("\n⚡ Top Time-Consuming Blocks (by P95):")
            blocks = stats["function_blocks"]
            sorted_blocks = sorted(blocks.items(),
                                 key=lambda x: x[1]["p95"],
                                 reverse=True)[:5]
            for block, block_stats in sorted_blocks:
                print(f"   • {block}: {block_stats['p95']:.3f}s (P95)")

        print("\n" + "="*60)

    async def run(self):
        """Main execution method"""
        print("🔧 Index-Cal-Gap-Analysis Performance Testing Suite")
        print("="*60)

        # Load test data
        self.load_test_data()

        # Run performance tests
        await self.run_performance_tests()

        # Calculate statistics
        stats = self.calculate_statistics()

        if stats:
            # Print summary
            self.print_summary(stats)

            # Create visualizations
            self.create_gantt_chart(stats)
            self.create_enhanced_gantt_chart(stats)

            # Save results
            self.save_results(stats)

            print("\n✅ Performance testing completed successfully!")
        else:
            print("\n❌ Performance testing failed - no valid results")


async def main():
    """Main entry point"""
    runner = PerformanceTestRunner()
    await runner.run()


if __name__ == "__main__":
    # Check for API key
    if not API_KEY:
        print("⚠️  Warning: CONTAINER_APP_API_KEY not set in environment")
        print("   Please set it to run live API tests")
        print("   export CONTAINER_APP_API_KEY=your-api-key")

    # Run async main
    asyncio.run(main())
