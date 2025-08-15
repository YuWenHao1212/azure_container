#!/usr/bin/env python
"""
診斷測試：檢查 API 回應中是否包含 Course Availability 欄位
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ENDPOINT = "http://localhost:8000/api/v1/index-cal-and-gap-analysis"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "test-api-key")


async def test_api_with_course_availability():
    """測試 API 回應是否包含 course availability 欄位"""

    # Test data
    test_case = {
        "job_description": """
            We are looking for a Senior Backend Engineer.
            Requirements:
            - 5+ years of experience with Python and FastAPI
            - Strong knowledge of PostgreSQL and Redis
            - Experience with Docker and Kubernetes
            - Microservices architecture expertise
        """,
        "resume": """
            <h2>Experience</h2>
            <p>Backend Developer at TechCorp (3 years)</p>
            <ul>
                <li>Developed RESTful APIs using Python and Django</li>
                <li>Managed PostgreSQL databases</li>
            </ul>
            <h2>Skills</h2>
            <ul>
                <li>Python</li>
                <li>PostgreSQL</li>
                <li>Docker</li>
            </ul>
        """,
        "keywords": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
        "language": "en"
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    print("=" * 80)
    print("Testing Course Availability in API Response")
    print(f"Endpoint: {API_ENDPOINT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_ENDPOINT, json=test_case, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()

                    # Check if gap_analysis exists
                    if "gap_analysis" in result:
                        print("✅ Gap Analysis found in response")

                        # Check for SkillSearchQueries
                        gap_analysis = result["gap_analysis"]
                        if "SkillSearchQueries" in gap_analysis:
                            skills = gap_analysis["SkillSearchQueries"]
                            print(f"✅ SkillSearchQueries found with {len(skills)} skills")

                            # Check each skill for course availability fields
                            print("\n📚 Checking Course Availability Fields:")
                            print("-" * 40)

                            for i, skill in enumerate(skills, 1):
                                skill_name = skill.get("skill_name", "Unknown")
                                has_courses = skill.get("has_available_courses")
                                course_count = skill.get("course_count")

                                print(f"\n{i}. {skill_name}")
                                print(f"   - skill_category: {skill.get('skill_category', 'N/A')}")
                                print(f"   - description: {skill.get('description', 'N/A')[:50]}...")

                                if has_courses is not None:
                                    print(f"   ✅ has_available_courses: {has_courses}")
                                else:
                                    print("   ❌ has_available_courses: MISSING")

                                if course_count is not None:
                                    print(f"   ✅ course_count: {course_count}")
                                else:
                                    print("   ❌ course_count: MISSING")

                            # Summary
                            print("\n" + "=" * 40)
                            skills_with_availability = sum(1 for s in skills if "has_available_courses" in s)
                            skills_with_count = sum(1 for s in skills if "course_count" in s)

                            if skills_with_availability == len(skills):
                                print(f"✅ SUCCESS: All {len(skills)} skills have course availability info")
                            else:
                                print(f"❌ PROBLEM: Only {skills_with_availability}/{len(skills)} skills have availability info")
                                print(f"❌ PROBLEM: Only {skills_with_count}/{len(skills)} skills have course count")

                        else:
                            print("❌ SkillSearchQueries NOT found in gap_analysis")
                    else:
                        print("❌ gap_analysis NOT found in response")

                    # Check metadata for timing
                    if "metadata" in result:
                        metadata = result["metadata"]
                        timing = metadata.get("timing_breakdown", {})
                        course_time = timing.get("course_availability_time")

                        print("\n⏱️ Timing Information:")
                        print(f"   - Total time: {timing.get('total_time', 'N/A')}ms")
                        if course_time is not None:
                            print(f"   ✅ Course availability time: {course_time}ms")
                        else:
                            print("   ❌ Course availability time: NOT RECORDED")

                    # Save full response for debugging
                    output_file = f"test/logs/api_course_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, "w") as f:
                        json.dump(result, f, indent=2)
                    print(f"\n💾 Full response saved to: {output_file}")

                else:
                    print(f"❌ API Error: HTTP {response.status}")
                    print(await response.text())

        except Exception as e:
            print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_api_with_course_availability())
