#!/usr/bin/env python
"""
診斷腳本：測試 Course Availability 功能
透過 Gap Analysis API 觸發 Course Availability 檢查
"""
import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "")

# Test data
TEST_DATA = {
    "job_description": """
        We are looking for a Senior Full Stack Developer with expertise in:
        - Python and FastAPI for backend development
        - React and TypeScript for frontend
        - Docker and Kubernetes for containerization
        - PostgreSQL and Redis for databases
        - AWS or Azure cloud services
        - Machine Learning fundamentals
        - Minimum 5 years of experience in software development
    """,
    "resume": """
        <h2>Professional Experience</h2>
        <p>Software Developer at TechCorp (3 years)</p>
        <ul>
            <li>Developed web applications using Python and Django</li>
            <li>Created responsive UIs with HTML, CSS, and JavaScript</li>
            <li>Managed MySQL databases</li>
            <li>Used Git for version control</li>
        </ul>

        <h2>Education</h2>
        <p>Bachelor's Degree in Computer Science</p>

        <h2>Skills</h2>
        <ul>
            <li>Programming: Python, JavaScript, HTML, CSS</li>
            <li>Frameworks: Django, Bootstrap</li>
            <li>Databases: MySQL, SQLite</li>
            <li>Tools: Git, VS Code, Linux</li>
        </ul>
    """,
    "keywords": [
        "Python", "FastAPI", "React", "TypeScript", "Docker",
        "Kubernetes", "PostgreSQL", "Redis", "AWS", "Azure",
        "Machine Learning"
    ],
    "language": "en"
}


async def test_gap_analysis_api():
    """測試 Gap Analysis API 並檢查 Course Availability 結果"""

    print("=" * 80)
    print("🔍 Testing Course Availability via Gap Analysis API")
    print(f"📍 API URL: {API_URL}")
    print(f"🕒 Time: {datetime.now().isoformat()}")
    print("=" * 80)

    if not API_KEY:
        print("❌ Error: CONTAINER_APP_API_KEY not set in environment")
        return

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    endpoint = f"{API_URL}/api/v1/index-cal-and-gap-analysis"

    async with aiohttp.ClientSession() as session:
        try:
            print("\n📤 Sending request to Gap Analysis API...")
            print(f"   Keywords: {', '.join(TEST_DATA['keywords'][:5])}...")

            async with session.post(
                endpoint,
                json=TEST_DATA,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:

                print(f"\n📥 Response Status: {response.status}")

                if response.status == 200:
                    result = await response.json()

                    # Extract Gap Analysis results
                    gap_analysis = result.get("gap_analysis", {})
                    skill_queries = gap_analysis.get("SkillSearchQueries", [])

                    print("\n📊 Gap Analysis Results:")
                    print(f"   Total skills identified: {len(skill_queries)}")

                    if skill_queries:
                        print("\n📚 Course Availability Check Results:")
                        print("-" * 60)

                        for i, skill in enumerate(skill_queries, 1):
                            skill_name = skill.get("skill_name", "Unknown")
                            skill_category = skill.get("skill_category", "N/A")
                            has_courses = skill.get("has_available_courses", False)
                            course_count = skill.get("course_count", 0)

                            # Use emoji to highlight the issue
                            status = "✅" if has_courses else "❌"

                            print(f"\n   {i}. {skill_name}")
                            print(f"      Category: {skill_category}")
                            print(f"      Has Courses: {status} {has_courses}")
                            print(f"      Course Count: {course_count}")

                            # Check for additional details
                            if "preferred_courses" in skill:
                                print(f"      Preferred: {skill.get('preferred_courses', 0)}")
                                print(f"      Other: {skill.get('other_courses', 0)}")

                        # Summary statistics
                        total_with_courses = sum(
                            1 for s in skill_queries
                            if s.get("has_available_courses", False)
                        )

                        print("\n" + "=" * 60)
                        print("📈 Summary:")
                        print(f"   Skills with courses: {total_with_courses}/{len(skill_queries)}")
                        print(f"   Success rate: {total_with_courses/len(skill_queries)*100:.1f}%")

                        if total_with_courses == 0:
                            print("\n⚠️  WARNING: No skills have available courses!")
                            print("   This indicates a potential issue with:")
                            print("   1. Similarity thresholds being too high")
                            print("   2. Database connection issues")
                            print("   3. Embedding model mismatch")
                    else:
                        print("❌ No skill queries found in response")

                    # Check metadata for timing
                    metadata = result.get("metadata", {})
                    timing = metadata.get("detailed_timings_ms", {})
                    if "course_availability_time" in timing:
                        print(f"\n⏱️  Course Availability Check Time: {timing['course_availability_time']}ms")

                    # Save full response for analysis
                    output_file = f"course_availability_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(output_file, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"\n💾 Full response saved to: {output_file}")

                else:
                    error_text = await response.text()
                    print(f"❌ API Error: {error_text}")

        except TimeoutError:
            print("❌ Request timeout (60s)")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 80)
    print("✅ Test completed")
    print("=" * 80)


async def main():
    """Run multiple tests to generate logs"""
    print("🚀 Starting Course Availability diagnostics\n")

    # Run test 3 times to generate enough logs
    for i in range(3):
        print(f"\n--- Test Run {i+1}/3 ---")
        await test_gap_analysis_api()

        if i < 2:
            print("\n⏳ Waiting 5 seconds before next test...")
            await asyncio.sleep(5)

    print("\n" + "=" * 80)
    print("📊 All tests completed!")
    print("💡 Now check Application Insights for detailed logs")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
