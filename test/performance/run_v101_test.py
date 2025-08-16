#!/usr/bin/env python3
"""
Performance test for v1.0.1 Resume Structure Analyzer
Executes 20 tests to compare with previous results
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import aiohttp

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
""" * 3  # Repeat to make it longer

async def test_api_call(session, test_case):
    """Execute single API test"""
    start_time = time.time()

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

                # Extract timing details
                metadata = data.get("metadata", {})
                timing_breakdown = metadata.get("timing_breakdown", {})

                return {
                    "test_case": test_case,
                    "success": True,
                    "duration": duration,
                    "timing_breakdown": timing_breakdown,
                    "metadata": metadata
                }
            else:
                return {
                    "test_case": test_case,
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "duration": time.time() - start_time
                }
    except Exception as e:
        return {
            "test_case": test_case,
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time
        }

async def run_tests():
    """Run all performance tests"""
    print("🚀 Starting v1.0.1 Performance Tests")
    print(f"   API: {API_URL}")
    print(f"   Tests: {len(TEST_CASES)}")
    print("")

    results = []
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"[{i}/{len(TEST_CASES)}] Testing {test_case['company']} - {test_case['position']}...", end="")
            result = await test_api_call(session, test_case)

            if result["success"]:
                print(f" ✅ {result['duration']:.2f}s")
                if "timing_breakdown" in result:
                    tb = result["timing_breakdown"]
                    structure_time = tb.get("structure_analysis_time", 0)
                    gap_time = tb.get("gap_analysis_time", 0)
                    print(f"      Structure: {structure_time:.0f}ms, Gap: {gap_time:.0f}ms")
            else:
                print(f" ❌ {result.get('error', 'Unknown error')}")

            results.append(result)

            # Brief delay between requests
            await asyncio.sleep(1)

    return results

def analyze_results(results):
    """Analyze and summarize test results"""
    successful = [r for r in results if r["success"]]

    if not successful:
        print("\n❌ No successful tests to analyze")
        return None

    # Calculate statistics
    durations = [r["duration"] for r in successful]
    durations.sort()

    # Extract timing breakdowns
    timing_data = {}
    for r in successful:
        if "timing_breakdown" in r:
            for key, value in r["timing_breakdown"].items():
                if key not in timing_data:
                    timing_data[key] = []
                timing_data[key].append(value)

    # Calculate percentiles
    def percentile(data, p):
        n = len(data)
        idx = int(n * p / 100)
        return data[min(idx, n-1)] if n > 0 else 0

    stats = {
        "total_tests": len(results),
        "successful_tests": len(successful),
        "failed_tests": len(results) - len(successful),
        "min_time": min(durations) if durations else 0,
        "max_time": max(durations) if durations else 0,
        "mean_time": sum(durations) / len(durations) if durations else 0,
        "median_time": percentile(durations, 50),
        "p50": percentile(durations, 50),
        "p95": percentile(durations, 95),
        "p99": percentile(durations, 99),
    }

    # Calculate timing statistics
    timing_stats = {}
    for key, values in timing_data.items():
        values.sort()
        timing_stats[key] = {
            "mean": sum(values) / len(values) if values else 0,
            "median": percentile(values, 50),
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
        }

    return {
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "configuration": {
            "num_tests": len(TEST_CASES),
            "api_endpoint": ENDPOINT,
            "prompt_version": "v1.0.1"
        },
        "statistics": stats,
        "timing_breakdown": timing_stats,
        "test_results": [
            {
                "test_id": f"{i:03d}",
                "company": r["test_case"]["company"],
                "position": r["test_case"]["position"],
                "total_time": r["duration"],
                "success": r["success"],
                "error": r.get("error")
            }
            for i, r in enumerate(results, 1)
        ]
    }

def main():
    """Main execution"""
    # Run tests
    results = asyncio.run(run_tests())

    # Analyze results
    analysis = analyze_results(results)

    if analysis:
        # Save results
        timestamp = analysis["timestamp"]
        output_dir = Path("docs/issues/index-cal-gap-analysis-evolution/performance")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"performance_v101_{timestamp}.json"
        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2)

        print(f"\n📊 Results saved to: {output_file}")

        # Print summary
        stats = analysis["statistics"]
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY (v1.0.1)")
        print("="*60)
        print(f"Total Tests: {stats['total_tests']}")
        print(f"Successful: {stats['successful_tests']}")
        print(f"Failed: {stats['failed_tests']}")
        print("\nResponse Times:")
        print(f"  P50: {stats['p50']:.2f}s")
        print(f"  P95: {stats['p95']:.2f}s")
        print(f"  Min: {stats['min_time']:.2f}s")
        print(f"  Max: {stats['max_time']:.2f}s")

        # Print timing breakdown
        if "timing_breakdown" in analysis:
            print("\nTiming Breakdown (median):")
            tb = analysis["timing_breakdown"]
            if "structure_analysis_time" in tb:
                print(f"  Structure Analysis: {tb['structure_analysis_time']['median']:.0f}ms")
            if "gap_analysis_time" in tb:
                print(f"  Gap Analysis: {tb['gap_analysis_time']['median']:.0f}ms")
            if "course_availability_time" in tb:
                print(f"  Course Availability: {tb['course_availability_time']['median']:.0f}ms")

if __name__ == "__main__":
    main()
