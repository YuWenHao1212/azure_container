#!/usr/bin/env python3
"""
Test script to verify Gap Analysis API course availability functionality
Tests if the API correctly returns available_course_ids and has_available_courses
"""

import asyncio
import json
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Force Gap Analysis to use v2.1.8 prompt which includes skill_development_priorities
os.environ['GAP_ANALYSIS_PROMPT_VERSION'] = '2.1.8'
print(f"🔧 Set GAP_ANALYSIS_PROMPT_VERSION=2.1.8")

# API Configuration
API_BASE_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk")

# Test data with realistic JD and Resume
TEST_JD = """
Senior Data Scientist - Machine Learning Engineer

We are seeking an experienced Data Scientist/ML Engineer to lead our AI initiatives. 

Required Skills:
- 5+ years in machine learning and data science
- Expert in Python, TensorFlow, PyTorch, and Scikit-learn
- Deep understanding of neural networks, CNNs, RNNs, and Transformers
- Experience with MLOps, model deployment, and monitoring
- Proficiency in Apache Spark, Hadoop, and distributed computing
- Strong knowledge of statistics, A/B testing, and experimental design
- Experience with cloud ML platforms (AWS SageMaker, Azure ML, GCP Vertex AI)
- Expertise in NLP, computer vision, and reinforcement learning
- Knowledge of Kubernetes, Docker, and microservices for ML
- Experience with real-time model serving and edge deployment
- Strong SQL and NoSQL database skills
- Proficiency in data visualization (Tableau, Power BI)
- Experience with feature engineering and data pipelines
- Knowledge of model interpretability and fairness
- Strong communication skills to explain complex models to stakeholders
"""

TEST_RESUME = """
John Doe
Junior Software Developer

Professional Summary:
Entry-level software developer with 2 years of experience in web development. Basic knowledge of Python and JavaScript.

Technical Skills:
- Programming Languages: Python, JavaScript, HTML, CSS
- Web Frameworks: Basic Django knowledge
- Frontend: HTML, CSS, Basic React
- Databases: MySQL
- Tools: Git, VS Code

Professional Experience:

Junior Developer | Small Company | 2022-Present
- Assisted in developing simple web applications
- Wrote basic Python scripts for data processing
- Fixed bugs in existing codebase
- Created simple HTML/CSS pages

Intern | Local Startup | 2021-2022
- Learned basic web development
- Shadowed senior developers
- Wrote documentation
- Performed manual testing

Education:
Bachelor of Science in Computer Science | University Name | 2021

Note: No experience with the following technologies:
- No Flask, TypeScript, or Node.js experience
- No AWS or Azure cloud experience
- No Docker or Kubernetes knowledge
- No MongoDB or PostgreSQL experience
- No microservices architecture experience
- No CI/CD pipeline experience
- No Machine Learning or AI experience
- No GraphQL, Rust, or Go knowledge
"""


async def test_gap_analysis_with_courses():
    """Test the Gap Analysis API to verify course availability functionality"""
    
    print("\n" + "="*80)
    print("🧪 Testing Gap Analysis API - Course Availability Feature")
    print("="*80)
    print(f"📍 API URL: {API_BASE_URL}")
    print(f"🕐 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*80)
    
    endpoint = f"{API_BASE_URL}/api/v1/index-cal-and-gap-analysis"
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_description": TEST_JD,
        "resume": TEST_RESUME,
        "keywords": ["Python", "JavaScript", "React", "Django", "Flask", "AWS", "Azure", 
                     "Docker", "Kubernetes", "PostgreSQL", "MongoDB", "Machine Learning"]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("\n📤 Sending request to Gap Analysis API...")
            response = await client.post(endpoint, json=payload, headers=headers)
            
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n✅ API Response Received Successfully")
                print("-"*80)
                
                # Print full structure to understand response
                print("\n📋 Response Structure:")
                print(f"   Top Keys: {list(data.keys())}")
                
                # Check data field
                actual_data = data.get("data", {})
                if actual_data:
                    print(f"   Data Keys: {list(actual_data.keys())}")
                
                # Extract gap analysis data - might be in data.data
                gap_analysis = actual_data.get("gap_analysis", {}) or data.get("gap_analysis", {})
                
                if gap_analysis:
                    print(f"\n📊 Gap Analysis Keys: {list(gap_analysis.keys())}")
                
                # Check KeyGaps - the new format
                key_gaps = gap_analysis.get("KeyGaps", [])
                print(f"\n📊 Key Gaps Found: {len(key_gaps) if isinstance(key_gaps, list) else 'Not a list'}")
                
                # Also check SkillSearchQueries which might contain course info
                skill_queries = gap_analysis.get("SkillSearchQueries", [])
                print(f"📊 Skill Search Queries: {len(skill_queries) if isinstance(skill_queries, list) else 'Not a list'}")
                
                # Print the actual content to understand the structure
                if key_gaps:
                    print(f"\n🔍 KeyGaps Content Type: {type(key_gaps)}")
                    if isinstance(key_gaps, list):
                        for i, gap in enumerate(key_gaps[:3], 1):
                            print(f"   Gap {i}: {gap}")
                    else:
                        print(f"   Content: {str(key_gaps)[:200]}")
                
                if skill_queries:
                    print(f"\n🔍 SkillSearchQueries Content Type: {type(skill_queries)}")
                    if isinstance(skill_queries, list):
                        for i, query in enumerate(skill_queries[:3], 1):
                            print(f"   Query {i}: {query}")
                    else:
                        print(f"   Content: {str(skill_queries)[:200]}")
                
                # Original missing_skills check for backward compatibility
                missing_skills = gap_analysis.get("missing_skills", [])
                
                if missing_skills:
                    print("\n🔍 Analyzing Course Availability for Each Missing Skill:")
                    print("-"*80)
                    
                    skills_with_courses = 0
                    skills_without_courses = 0
                    total_course_ids = []
                    
                    for i, skill in enumerate(missing_skills[:10], 1):  # Check first 10 skills
                        skill_name = skill.get("skill", "Unknown")
                        has_courses = skill.get("has_available_courses", False)
                        course_ids = skill.get("available_course_ids", [])
                        course_count = skill.get("course_count", 0)
                        
                        # New fields from quota system
                        type_diversity = skill.get("type_diversity", 0)
                        course_types = skill.get("course_types", [])
                        
                        print(f"\n{i}. Skill: {skill_name}")
                        print(f"   ├─ Has Courses: {has_courses}")
                        print(f"   ├─ Course Count: {course_count}")
                        print(f"   ├─ Type Diversity: {type_diversity}")
                        print(f"   ├─ Course Types: {course_types}")
                        print(f"   └─ Course IDs: {len(course_ids) if course_ids else 0} IDs")
                        
                        if course_ids:
                            print(f"      Sample IDs: {course_ids[:3]}")
                            skills_with_courses += 1
                            total_course_ids.extend(course_ids)
                        else:
                            skills_without_courses += 1
                    
                    print("\n" + "="*80)
                    print("📈 Summary Statistics:")
                    print("-"*80)
                    print(f"✅ Skills WITH courses: {skills_with_courses}")
                    print(f"❌ Skills WITHOUT courses: {skills_without_courses}")
                    print(f"📚 Total unique course IDs collected: {len(set(total_course_ids))}")
                    
                    # Identify the issue
                    if skills_without_courses > skills_with_courses:
                        print("\n⚠️  WARNING: Most skills are returning no courses!")
                        print("   This indicates a potential issue with:")
                        print("   1. Database connection")
                        print("   2. Embedding service")
                        print("   3. Similarity thresholds")
                        print("   4. SQL query logic")
                    else:
                        print("\n✅ Course availability feature is working correctly!")
                    
                    # Save response for debugging
                    debug_file = f"gap_analysis_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(debug_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"\n💾 Full response saved to: {debug_file}")
                    
                else:
                    print("⚠️  No missing skills found in the gap analysis")
                
            else:
                print(f"\n❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()


async def test_direct_course_search():
    """Test the course search API directly to verify database connectivity"""
    
    print("\n" + "="*80)
    print("🧪 Testing Direct Course Search API")
    print("="*80)
    
    endpoint = f"{API_BASE_URL}/api/v1/courses/search"
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Test with a common skill
    test_skills = ["Python", "Machine Learning", "Docker", "React"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for skill in test_skills:
            payload = {
                "keywords": [skill],
                "max_results": 5
            }
            
            try:
                print(f"\n🔍 Searching courses for: {skill}")
                response = await client.post(endpoint, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    courses = data.get("courses", [])
                    print(f"   ✅ Found {len(courses)} courses")
                    if courses:
                        print(f"   Sample: {courses[0].get('name', 'Unknown')[:50]}...")
                else:
                    print(f"   ❌ Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Failed: {e}")


if __name__ == "__main__":
    print("\n🚀 Starting Gap Analysis Course Availability Tests")
    print("="*80)
    
    # Run tests
    asyncio.run(test_gap_analysis_with_courses())
    asyncio.run(test_direct_course_search())
    
    print("\n" + "="*80)
    print("✅ All tests completed!")
    print("="*80)