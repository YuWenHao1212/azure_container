#!/usr/bin/env python3
"""
Comprehensive Performance Test Suite for Index-Cal-Gap-Analysis API
Supports configurable test runs (1-20) with detailed timing analysis and visualization
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiohttp
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

# API configuration
API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk"
ENDPOINT = "/api/v1/index-cal-and-gap-analysis"

# Test data
TEST_CASES = [
    {"company": "TSMC", "position": "Senior Data Analyst"},
    {"company": "NVIDIA", "position": "Senior Data Scientist"},
    {"company": "foodpanda", "position": "Data Analyst"},
    {"company": "Apple", "position": "Senior Business Analyst"},
    {"company": "Google", "position": "Data Engineering Manager"},
    {"company": "Meta", "position": "Product Data Scientist"},
    {"company": "Microsoft", "position": "Business Intelligence Lead"},
    {"company": "Amazon", "position": "Analytics Manager"},
    {"company": "Goldman Sachs", "position": "Quantitative Analyst"},
    {"company": "McKinsey", "position": "Management Consultant"},
    {"company": "Tesla", "position": "Operations Analytics Manager"},
    {"company": "Uber", "position": "Decision Science Manager"},
    {"company": "JPMorgan", "position": "Risk Analytics Manager"},
    {"company": "BCG", "position": "Data Strategy Consultant"},
    {"company": "Deloitte", "position": "Digital Transformation Manager"},
    {"company": "Boeing", "position": "Supply Chain Data Analyst"},
    {"company": "Spotify", "position": "Growth Analytics Manager"},
    {"company": "Airbnb", "position": "Business Operations Manager"},
    {"company": "Morgan Stanley", "position": "Business Data Analyst"},
    {"company": "BlackRock", "position": "Investment Analytics Lead"},
]

KEYWORDS = [
    "Data Analytics", "Python", "SQL", "Machine Learning",
    "Business Intelligence", "Data Visualization", "Statistical Analysis",
    "Tableau", "Power BI", "Excel", "R", "AWS",
    "Big Data", "ETL", "Dashboard", "Predictive Modeling"
]

# Sample resume content (meets minimum length requirement)
RESUME_CONTENT = """
John Smith | Data Analyst
Email: john.smith@email.com | Phone: (555) 123-4567
LinkedIn: linkedin.com/in/johnsmith | GitHub: github.com/johnsmith

PROFESSIONAL SUMMARY
Experienced Data Analyst with 8+ years of expertise in transforming complex data into actionable business insights.
Proven track record of developing data-driven solutions that improved operational efficiency by 35% and reduced costs by $2M annually.
Expert in Python, SQL, and machine learning with strong business acumen and communication skills.

SKILLS
Programming: Python, R, SQL, Scala
Databases: PostgreSQL, MySQL, MongoDB, Snowflake, BigQuery
Analytics Tools: Tableau, Power BI, Looker, Excel
Machine Learning: Scikit-learn, TensorFlow, PyTorch
Cloud Platforms: AWS, GCP, Azure
Big Data: Spark, Hadoop, Kafka

EXPERIENCE
Senior Data Analyst | TechCorp Inc. | 2020 - Present
• Led analytics initiatives that generated $5M in additional revenue through customer segmentation
• Built automated dashboards reducing reporting time by 70%
• Developed ML models for demand forecasting with 92% accuracy
• Managed team of 4 junior analysts and mentored on best practices

Data Analyst | DataDriven Co. | 2018 - 2020
• Implemented ETL pipelines processing 10TB+ of daily data
• Created executive dashboards tracking 50+ KPIs
• Conducted A/B tests that improved conversion rates by 25%
• Collaborated with cross-functional teams to drive data initiatives

Junior Data Analyst | Analytics Start | 2016 - 2018
• Performed statistical analysis on customer behavior patterns
• Automated weekly reports saving 20 hours per week
• Maintained SQL databases and optimized query performance
• Presented findings to stakeholders and C-suite executives

EDUCATION
Master of Science in Data Science | Stanford University | 2016
Bachelor of Science in Statistics | UC Berkeley | 2014

CERTIFICATIONS
• AWS Certified Data Analytics – Specialty
• Google Cloud Professional Data Engineer
• Microsoft Certified: Azure Data Scientist Associate
• Tableau Desktop Specialist

PROJECTS
Customer Churn Prediction Model
• Developed ensemble model achieving 94% accuracy in predicting customer churn
• Implemented real-time scoring system processing 1M+ predictions daily
• Resulted in 30% reduction in customer attrition rate

Supply Chain Optimization Dashboard
• Built end-to-end analytics solution for supply chain visibility
• Integrated data from 15+ sources using Apache Airflow
• Reduced inventory costs by 20% through optimization insights
""" * 3  # Repeat to make it longer to meet API requirements


async def test_api_call(session: aiohttp.ClientSession, test_case: dict[str, str], test_num: int) -> dict[str, Any]:
    """
    Execute a single API test call with comprehensive timing capture

    Args:
        session: aiohttp session for making requests
        test_case: Test case with company and position
        test_num: Test number for identification

    Returns:
        Dictionary with test results and timing breakdown
    """
    start_time = time.time()

    # Generate job description
    job_description = f"""
    {test_case['company']} is seeking a {test_case['position']} to join our team.

    Required Qualifications:
    - 5+ years of experience in data analytics or related field
    - Strong proficiency in SQL and Python
    - Experience with data visualization tools (Tableau, Power BI)
    - Knowledge of statistical analysis and machine learning
    - Excellent communication and presentation skills

    Preferred Qualifications:
    - Advanced degree in Data Science, Statistics, or related field
    - Experience with cloud platforms (AWS, GCP, Azure)
    - Knowledge of big data technologies (Spark, Hadoop)
    - Industry experience in technology or consulting

    Key Responsibilities:
    - Analyze large datasets to identify trends and insights
    - Build and maintain dashboards for business stakeholders
    - Develop predictive models to support decision making
    - Collaborate with cross-functional teams
    - Present findings to executive leadership
    """

    payload = {
        "job_description": job_description,
        "resume": RESUME_CONTENT,
        "keywords": KEYWORDS,
        "language": "en"
    }

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    try:
        async with session.post(
            f"{API_URL}{ENDPOINT}",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status == 200:
                data = await response.json()
                duration = time.time() - start_time

                # Extract metadata and timing information
                metadata = data.get("metadata", {})
                timing_breakdown = metadata.get("detailed_timings_ms", {})

                # Build comprehensive result
                return {
                    "test_id": f"{test_num:03d}",
                    "test_case": test_case,
                    "success": True,
                    "total_time": duration,
                    "timings": timing_breakdown,
                    "metadata": metadata,
                    "similarity": data.get("similarity_percentage", 0),
                    "keyword_coverage": data.get("keyword_coverage", {}).get("coverage_percentage", 0),
                    "skills_count": len(data.get("gap_analysis", {}).get("SkillSearchQueries", [])),
                    "error": None
                }
            else:
                error_text = await response.text()
                return {
                    "test_id": f"{test_num:03d}",
                    "test_case": test_case,
                    "success": False,
                    "total_time": time.time() - start_time,
                    "error": f"HTTP {response.status}: {error_text[:200]}",
                    "timings": {}
                }
    except TimeoutError:
        return {
            "test_id": f"{test_num:03d}",
            "test_case": test_case,
            "success": False,
            "total_time": 30.0,
            "error": "Request timeout (30s)",
            "timings": {}
        }
    except Exception as e:
        return {
            "test_id": f"{test_num:03d}",
            "test_case": test_case,
            "success": False,
            "total_time": time.time() - start_time,
            "error": str(e),
            "timings": {}
        }


async def run_performance_tests(num_tests: int) -> list[dict[str, Any]]:
    """
    Run multiple performance tests

    Args:
        num_tests: Number of tests to run (1-20)

    Returns:
        List of test results
    """
    print("🚀 Starting Performance Test Suite")
    print(f"   API: {API_URL}")
    print(f"   Tests: {num_tests}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    results = []
    async with aiohttp.ClientSession() as session:
        for i in range(num_tests):
            test_case = TEST_CASES[i % len(TEST_CASES)]
            print(f"\n[{i+1}/{num_tests}] Testing {test_case['company']} - {test_case['position']}...")

            result = await test_api_call(session, test_case, i+1)

            if result["success"]:
                timings = result["timings"]
                print(f"  ✅ Total: {result['total_time']:.2f}s")
                print(f"     Structure: {timings.get('structure_analysis_time', 0):.0f}ms")
                print(f"     Gap Analysis: {timings.get('gap_analysis_time', 0):.0f}ms")
                print(f"     Index Calc: {timings.get('index_calculation_time', 0):.0f}ms")
                print(f"     Keywords: {timings.get('keyword_matching_time', 0):.0f}ms")
                print(f"     Embedding: {timings.get('embedding_time', 0):.0f}ms")
            else:
                print(f"  ❌ Failed: {result['error']}")

            results.append(result)

            # Brief delay between requests to avoid overwhelming the API
            if i < num_tests - 1:
                await asyncio.sleep(1)

    return results


def calculate_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate comprehensive statistics from test results

    Args:
        results: List of test results

    Returns:
        Dictionary with statistics
    """
    successful = [r for r in results if r["success"]]

    if not successful:
        return {"error": "No successful tests"}

    # Total time statistics
    total_times = [r["total_time"] for r in successful]
    total_times.sort()

    def percentile(data, p):
        n = len(data)
        idx = int(n * p / 100)
        return data[min(idx, n-1)] if n > 0 else 0

    # Component timing statistics
    component_stats = {}
    component_keys = [
        "structure_analysis_time",
        "structure_wait_time",
        "gap_analysis_time",
        "index_calculation_time",
        "keyword_matching_time",
        "embedding_time",
        "pgvector_warmup_time",
        "course_availability_time",
        "total_time"
    ]

    for key in component_keys:
        values = []
        for r in successful:
            if key in r.get("timings", {}):
                values.append(r["timings"][key])

        if values:
            values.sort()
            component_stats[key] = {
                "mean": sum(values) / len(values),
                "median": percentile(values, 50),
                "p50": percentile(values, 50),
                "p95": percentile(values, 95),
                "min": min(values),
                "max": max(values),
                "samples": len(values)
            }

    return {
        "total_tests": len(results),
        "successful_tests": len(successful),
        "failed_tests": len(results) - len(successful),
        "success_rate": len(successful) / len(results) * 100,
        "total_time_stats": {
            "mean": sum(total_times) / len(total_times),
            "median": percentile(total_times, 50),
            "p50": percentile(total_times, 50),
            "p95": percentile(total_times, 95),
            "p99": percentile(total_times, 99),
            "min": min(total_times),
            "max": max(total_times)
        },
        "component_stats": component_stats
    }


def create_gantt_chart(results: list[dict[str, Any]], output_path: Path) -> Path:
    """
    Create a Gantt chart showing parallel and sequential execution

    Args:
        results: Test results with timing data
        output_path: Path to save the chart

    Returns:
        Path to saved chart
    """
    # Get median timings from successful tests
    successful = [r for r in results if r["success"] and r.get("timings")]
    if not successful:
        print("⚠️ No successful tests with timing data for Gantt chart")
        return None

    # Use the first successful test with complete timing data
    sample_timing = successful[0]["timings"]

    # Define task structure
    colors = {
        "Structure Analysis": "#2E86AB",
        "Keywords Matching": "#A23B72",
        "Embedding": "#F18F01",
        "pgvector Warmup": "#C73E1D",
        "Index Calculation": "#6A994E",
        "Gap Analysis": "#BC4B51",
        "Course Availability": "#8B5A3C"
    }

    # Parallel tasks (start at 0)
    parallel_tasks = [
        ("Structure Analysis", sample_timing.get("structure_analysis_time", 0)),
        ("Keywords Matching", sample_timing.get("keyword_matching_time", 0)),
        ("Embedding", sample_timing.get("embedding_time", 0)),
        ("pgvector Warmup", sample_timing.get("pgvector_warmup_time", 0))
    ]

    # Sequential tasks (start after longest parallel task)
    max_parallel = max(sample_timing.get("embedding_time", 0),
                      sample_timing.get("keyword_matching_time", 0))

    sequential_start = max_parallel
    sequential_tasks = [
        ("Index Calculation", sample_timing.get("index_calculation_time", 0)),
        ("Gap Analysis", sample_timing.get("gap_analysis_time", 0)),
        ("Course Availability", sample_timing.get("course_availability_time", 0))
    ]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    y_pos = 0
    y_labels = []

    # Plot parallel tasks
    for task_name, duration in parallel_tasks:
        if duration > 0:
            ax.barh(y_pos, duration, left=0, height=0.8,
                   color=colors.get(task_name, "#999999"), alpha=0.8,
                   label=task_name)
            ax.text(duration/2, y_pos, f"{duration:.0f}ms",
                   ha='center', va='center', color='white', fontweight='bold')
            y_labels.append(task_name)
            y_pos += 1

    # Add separator
    if y_pos > 0:
        ax.axhline(y=y_pos-0.5, color='gray', linestyle='--', alpha=0.5)

    # Plot sequential tasks
    current_start = sequential_start
    for task_name, duration in sequential_tasks:
        if duration > 0:
            ax.barh(y_pos, duration, left=current_start, height=0.8,
                   color=colors.get(task_name, "#999999"), alpha=0.8,
                   label=task_name)
            ax.text(current_start + duration/2, y_pos, f"{duration:.0f}ms",
                   ha='center', va='center', color='white', fontweight='bold')
            y_labels.append(task_name)
            current_start += duration
            y_pos += 1

    # Formatting
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel('Time (milliseconds)', fontsize=12)
    ax.set_title('API Execution Timeline - Parallel and Sequential Tasks', fontsize=14, fontweight='bold')
    ax.grid(True, axis='x', alpha=0.3)

    # Add phase annotations
    ax.axvline(x=max_parallel, color='red', linestyle='--', alpha=0.5)
    ax.text(max_parallel/2, -1, 'Parallel Phase', ha='center', fontsize=10, style='italic')
    ax.text(max_parallel + (current_start - max_parallel)/2, -1, 'Sequential Phase',
           ha='center', fontsize=10, style='italic')

    # Add total time
    total_time = sample_timing.get("total_time", current_start)
    ax.text(0.99, 0.02, f'Total Time: {total_time:.0f}ms',
           transform=ax.transAxes, ha='right', fontsize=12,
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_file = output_path / f"gantt_chart_{timestamp}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"📊 Gantt chart saved to: {chart_file}")
    return chart_file


def create_component_analysis(results: list[dict[str, Any]], output_path: Path) -> Path:
    """
    Create component timing analysis charts

    Args:
        results: Test results with timing data
        output_path: Path to save the chart

    Returns:
        Path to saved chart
    """
    successful = [r for r in results if r["success"] and r.get("timings")]
    if not successful:
        print("⚠️ No successful tests with timing data for analysis")
        return None

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Component Performance Analysis', fontsize=16, fontweight='bold')

    # 1. Pie chart - Average time distribution
    ax1 = axes[0, 0]

    # Calculate average times for each component
    components = {
        "Structure Analysis": [],
        "Gap Analysis": [],
        "Index Calculation": [],
        "Keywords": [],
        "Embedding": [],
        "Course Check": [],
        "Other": []
    }

    for r in successful:
        timings = r["timings"]
        components["Structure Analysis"].append(timings.get("structure_analysis_time", 0))
        components["Gap Analysis"].append(timings.get("gap_analysis_time", 0))
        components["Index Calculation"].append(timings.get("index_calculation_time", 0))
        components["Keywords"].append(timings.get("keyword_matching_time", 0))
        components["Embedding"].append(timings.get("embedding_time", 0))
        components["Course Check"].append(timings.get("course_availability_time", 0))

    avg_times = {k: sum(v)/len(v) if v else 0 for k, v in components.items()}

    # Filter out zero values for pie chart
    pie_data = {k: v for k, v in avg_times.items() if v > 0}

    if pie_data:
        colors_pie = ['#2E86AB', '#BC4B51', '#6A994E', '#A23B72', '#F18F01', '#8B5A3C', '#999999']
        wedges, texts, autotexts = ax1.pie(pie_data.values(), labels=pie_data.keys(),
                                            autopct='%1.1f%%', colors=colors_pie)
        ax1.set_title('Average Time Distribution by Component')

        # Make percentage text more readable
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

    # 2. Box plot - Time distribution for major components
    ax2 = axes[0, 1]

    major_components = ["Structure Analysis", "Gap Analysis", "Index Calculation"]
    box_data = []
    for comp in major_components:
        if components.get(comp):
            box_data.append([v for v in components[comp] if v > 0])

    if box_data:
        bp = ax2.boxplot(box_data, labels=major_components, patch_artist=True)
        for patch, color in zip(bp['boxes'], ['#2E86AB', '#BC4B51', '#6A994E'], strict=False):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax2.set_ylabel('Time (ms)')
        ax2.set_title('Time Distribution for Major Components')
        ax2.grid(True, alpha=0.3)

    # 3. Line chart - Performance over test runs
    ax3 = axes[1, 0]

    test_numbers = list(range(1, len(successful) + 1))
    total_times = [r["total_time"] * 1000 for r in successful]  # Convert to ms

    ax3.plot(test_numbers, total_times, 'b-o', linewidth=2, markersize=6)
    ax3.set_xlabel('Test Number')
    ax3.set_ylabel('Total Time (ms)')
    ax3.set_title('Performance Across Test Runs')
    ax3.grid(True, alpha=0.3)

    # Add average line
    avg_time = sum(total_times) / len(total_times)
    ax3.axhline(y=avg_time, color='r', linestyle='--', alpha=0.5, label=f'Average: {avg_time:.0f}ms')
    ax3.legend()

    # 4. Stacked bar chart - Component breakdown per test
    ax4 = axes[1, 1]

    # Show all tests if 10 or fewer, otherwise show first 10
    show_tests = successful if len(successful) <= 10 else successful[:10]

    test_labels = [f"Test {i+1}" for i in range(len(show_tests))]

    # Prepare data for stacked bar
    structure_times = [r["timings"].get("structure_analysis_time", 0) for r in show_tests]
    gap_times = [r["timings"].get("gap_analysis_time", 0) for r in show_tests]
    index_times = [r["timings"].get("index_calculation_time", 0) for r in show_tests]
    other_times = [
        r["timings"].get("keyword_matching_time", 0) +
        r["timings"].get("embedding_time", 0) +
        r["timings"].get("course_availability_time", 0)
        for r in show_tests
    ]

    x = np.arange(len(test_labels))
    width = 0.6

    ax4.bar(x, structure_times, width, label='Structure', color='#2E86AB', alpha=0.8)
    ax4.bar(x, gap_times, width, bottom=structure_times, label='Gap Analysis', color='#BC4B51', alpha=0.8)
    ax4.bar(x, index_times, width, bottom=np.array(structure_times)+np.array(gap_times),
                label='Index Calc', color='#6A994E', alpha=0.8)
    ax4.bar(x, other_times, width,
                bottom=np.array(structure_times)+np.array(gap_times)+np.array(index_times),
                label='Other', color='#999999', alpha=0.8)

    ax4.set_xlabel('Test')
    ax4.set_ylabel('Time (ms)')
    ax4.set_title(f'Component Breakdown per Test (First {len(show_tests)} tests)')
    ax4.set_xticks(x)
    ax4.set_xticklabels(test_labels, rotation=45, ha='right')
    ax4.legend(loc='upper right')
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # Save chart
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_file = output_path / f"component_analysis_{timestamp}.png"
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"📊 Component analysis saved to: {chart_file}")
    return chart_file


def save_results(results: list[dict[str, Any]], statistics: dict[str, Any],
                 output_path: Path, args: argparse.Namespace) -> Path:
    """
    Save comprehensive test results to JSON

    Args:
        results: Test results
        statistics: Calculated statistics
        output_path: Path to save results
        args: Command line arguments

    Returns:
        Path to saved JSON file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Prepare comprehensive output
    output_data = {
        "timestamp": timestamp,
        "test_date": datetime.now().isoformat(),
        "configuration": {
            "num_tests": args.tests,
            "api_endpoint": ENDPOINT,
            "api_url": API_URL,
            "test_cases_used": args.tests
        },
        "statistics": statistics,
        "test_details": [
            {
                "test_id": r["test_id"],
                "company": r["test_case"]["company"],
                "position": r["test_case"]["position"],
                "success": r["success"],
                "total_time_seconds": r["total_time"],
                "timings_ms": r.get("timings", {}),
                "similarity_score": r.get("similarity", None),
                "keyword_coverage": r.get("keyword_coverage", None),
                "skills_identified": r.get("skills_count", None),
                "error": r.get("error", None)
            }
            for r in results
        ]
    }

    # Save to JSON
    json_file = output_path / f"performance_test_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {json_file}")
    return json_file


def print_summary(statistics: dict[str, Any]):
    """
    Print comprehensive test summary

    Args:
        statistics: Calculated statistics
    """
    print("\n" + "="*60)
    print("PERFORMANCE TEST SUMMARY")
    print("="*60)

    if "error" in statistics:
        print(f"❌ {statistics['error']}")
        return

    print(f"Total Tests: {statistics['total_tests']}")
    print(f"Successful: {statistics['successful_tests']}")
    print(f"Failed: {statistics['failed_tests']}")
    print(f"Success Rate: {statistics['success_rate']:.1f}%")

    print("\n📊 Response Time Statistics (seconds):")
    total_stats = statistics['total_time_stats']
    print(f"  P50 (Median): {total_stats['p50']:.2f}s")
    print(f"  P95: {total_stats['p95']:.2f}s")
    print(f"  Mean: {total_stats['mean']:.2f}s")
    print(f"  Min: {total_stats['min']:.2f}s")
    print(f"  Max: {total_stats['max']:.2f}s")

    print("\n⏱️ Component Timing Breakdown (median values in ms):")
    components = statistics.get('component_stats', {})

    # Display in execution order
    component_order = [
        ("Structure Analysis", "structure_analysis_time"),
        ("Keywords Matching", "keyword_matching_time"),
        ("Embedding", "embedding_time"),
        ("pgvector Warmup", "pgvector_warmup_time"),
        ("Index Calculation", "index_calculation_time"),
        ("Gap Analysis", "gap_analysis_time"),
        ("Course Availability", "course_availability_time")
    ]

    for display_name, key in component_order:
        if key in components:
            median = components[key]['median']
            samples = components[key]['samples']
            print(f"  {display_name}: {median:.0f}ms (n={samples})")

    # Calculate and display percentages
    if 'total_time' in components:
        total_median = components['total_time']['median']
        print("\n📈 Component Time Percentages:")
        for display_name, key in component_order:
            if key in components and key != 'total_time':
                median = components[key]['median']
                percentage = (median / total_median) * 100
                if percentage > 0.1:  # Only show if > 0.1%
                    print(f"  {display_name}: {percentage:.1f}%")


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Performance Test Suite for Index-Cal-Gap-Analysis API'
    )
    parser.add_argument(
        '--tests',
        type=int,
        default=5,
        choices=range(1, 21),
        metavar='N',
        help='Number of tests to run (1-20, default: 5)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='docs/issues/index-cal-gap-analysis-evolution/performance',
        help='Output directory for results (default: docs/issues/...)'
    )
    parser.add_argument(
        '--no-charts',
        action='store_true',
        help='Skip chart generation'
    )

    args = parser.parse_args()

    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Run performance tests
    results = asyncio.run(run_performance_tests(args.tests))

    # Calculate statistics
    statistics = calculate_statistics(results)

    # Save results
    json_file = save_results(results, statistics, output_path, args)

    # Generate visualizations (unless disabled)
    if not args.no_charts and statistics.get('successful_tests', 0) > 0:
        gantt_file = create_gantt_chart(results, output_path)
        analysis_file = create_component_analysis(results, output_path)

    # Print summary
    print_summary(statistics)

    print("\n✅ Performance test suite completed successfully!")
    print(f"   Results: {json_file}")
    if not args.no_charts and statistics.get('successful_tests', 0) > 0:
        if gantt_file:
            print(f"   Gantt Chart: {gantt_file}")
        if analysis_file:
            print(f"   Analysis: {analysis_file}")


if __name__ == "__main__":
    main()
