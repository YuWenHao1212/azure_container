#!/usr/bin/env python
"""
Test script to verify deficit filling mechanism in production
Stage 3 verification
"""
import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path

import aiohttp


async def test_deficit_filling():
    """Test that deficit filling is working in production"""
    url = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/index-cal-and-gap-analysis"

    # Test case specifically designed to trigger deficit filling
    # This resume lacks many skills, creating large deficits
    test_data = {
        "resume": """<div>
            <h2>Junior Developer</h2>
            <p>Entry-level developer with basic web development experience.</p>
            <h3>Skills</h3>
            <ul>
                <li>HTML and CSS basics</li>
                <li>JavaScript fundamentals</li>
                <li>Git version control</li>
            </ul>
        </div>""",
        "job_description": """We are looking for a Full Stack Engineer with expertise in:
        - Python programming and FastAPI framework
        - React and modern JavaScript
        - Docker and container orchestration
        - AWS cloud services
        - Microservices architecture
        - Database design with PostgreSQL
        - CI/CD pipelines
        Must have 5+ years experience building scalable applications.""",
        "keywords": ["Python", "FastAPI", "React", "Docker", "AWS", "PostgreSQL", "Microservices"],
        "language": "en"
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk"
    }

    print("=" * 70)
    print("🧪 TESTING DEFICIT FILLING MECHANISM")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    async with aiohttp.ClientSession() as session:
        print("📤 Sending request to production API...")
        print("   Resume: Junior developer (minimal skills)")
        print("   Job: Senior Full Stack (many requirements)")
        print()

        async with session.post(url, json=test_data, headers=headers) as response:
            print(f"📥 Response Status: {response.status}")
            result = await response.json()

            if result.get('success'):
                data = result['data']
                gap_analysis = data.get('gap_analysis', {})
                skill_queries = gap_analysis.get('SkillSearchQueries', [])

                print("✅ API Response Success")
                print(f"   Similarity: {data.get('similarity_percentage')}%")
                print(f"   Skills with gaps: {len(skill_queries)}")
                print()

                # Analyze course distribution to verify deficit filling
                print("📊 Course Type Distribution Analysis:")
                print("-" * 50)

                total_courses = 0
                type_counts = {}

                for skill in skill_queries:
                    skill_name = skill.get('skill_name')
                    skill_category = skill.get('skill_category')
                    course_ids = skill.get('available_course_ids', [])
                    course_count = skill.get('course_count', 0)

                    print(f"\n🎯 {skill_name} ({skill_category}):")
                    print(f"   Course count: {course_count}")
                    print(f"   Course IDs: {len(course_ids)} returned")

                    # Check for type diversity (if available)
                    type_diversity = skill.get('type_diversity', 0)
                    course_types = skill.get('course_types', [])

                    if type_diversity > 0:
                        print(f"   Type diversity: {type_diversity}")
                        print(f"   Course types: {course_types}")

                    # Analyze course ID patterns
                    if course_ids:
                        # Count course types by ID prefix
                        for cid in course_ids:
                            if 'crse' in cid:
                                type_counts['course'] = type_counts.get('course', 0) + 1
                            elif 'spzn' in cid:
                                type_counts['specialization'] = type_counts.get('specialization', 0) + 1
                            elif 'proj' in cid:
                                type_counts['project'] = type_counts.get('project', 0) + 1
                            elif 'cert' in cid:
                                type_counts['certification'] = type_counts.get('certification', 0) + 1
                            elif 'dgre' in cid:
                                type_counts['degree'] = type_counts.get('degree', 0) + 1

                        total_courses += len(course_ids)

                        # Check if this looks like deficit filling is active
                        if skill_category == "SKILL" and course_count == 25:
                            print("   ✅ Maximum quota reached (25) - deficit filling likely active")
                        elif skill_category == "SKILL" and course_count > 15:
                            print("   ✅ Above basic quota (>15) - reserves may be used")

                print("\n" + "=" * 50)
                print("📈 Overall Statistics:")
                print(f"   Total courses across all skills: {total_courses}")
                print(f"   Average courses per skill: {total_courses / len(skill_queries):.1f}")

                if type_counts:
                    print("\n   Course type distribution:")
                    for ctype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total_courses) * 100
                        print(f"     • {ctype}: {count} ({percentage:.1f}%)")

                # Check for deficit filling indicators
                print("\n🔍 Deficit Filling Indicators:")
                indicators = []

                # Check 1: High course counts for SKILL category
                skill_cats = [s for s in skill_queries if s.get('skill_category') == 'SKILL']
                if skill_cats:
                    avg_skill_courses = sum(s.get('course_count', 0) for s in skill_cats) / len(skill_cats)
                    if avg_skill_courses > 20:
                        indicators.append(f"✅ High average courses for SKILL category: {avg_skill_courses:.1f}")
                    else:
                        indicators.append(f"⚠️  Average courses for SKILL category: {avg_skill_courses:.1f}")

                # Check 2: Course type heavily dominant (indicating reserves used)
                if type_counts.get('course', 0) > total_courses * 0.7:
                    indicators.append(f"✅ Course type dominant ({type_counts.get('course', 0)}/{total_courses}) - reserves likely used")

                # Check 3: Maximum quotas reached
                max_quota_skills = [s for s in skill_queries if s.get('course_count', 0) >= 25]
                if max_quota_skills:
                    indicators.append(f"✅ {len(max_quota_skills)} skills reached maximum quota (25)")

                for indicator in indicators:
                    print(f"   {indicator}")

                # Save detailed response using secure temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(result, f, indent=2)
                    temp_path = f.name
                print(f"\n💾 Full response saved to {temp_path}")

            else:
                print(f"❌ API Error: {result.get('error', {}).get('message', 'Unknown error')}")

    print("\n" + "=" * 70)
    print("✅ DEFICIT FILLING TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_deficit_filling())
