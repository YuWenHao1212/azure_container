#!/usr/bin/env python3
"""Test script to verify which Gap Analysis prompt version is actually being used"""

import requests
import json
import re

# API Configuration
API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = "hUjQoHxaWoUUvqGxD4eMFYpT4dYXyFmgIK0fwtEePFk"  # Production API key

# Test data (minimum 200 chars)
test_jd = """
Senior Software Engineer Position at Tech Company
We are looking for an experienced software engineer with expertise in Python, FastAPI, 
Azure cloud services, and machine learning. The ideal candidate should have strong skills 
in building scalable microservices, containerization with Docker, and experience with 
Kubernetes orchestration. Knowledge of OpenAI APIs and prompt engineering is a plus.
Must have 5+ years of experience in software development.
"""

test_resume = """
Software Engineer with 5 years of experience
Skills: Python, Django, Flask, AWS, JavaScript, React, PostgreSQL, MongoDB, Git
Experience: Built multiple web applications using Python frameworks. Developed REST APIs 
for e-commerce platforms. Worked with cloud services for deployment. Familiar with Docker 
containers and basic CI/CD pipelines. Some exposure to machine learning through online courses.
Strong problem-solving skills and ability to work in agile teams.
"""

def analyze_overall_assessment(assessment):
    """Analyze the Overall Assessment to determine which version is being used"""
    
    word_count = len(assessment.split())
    char_count = len(assessment)
    paragraph_count = len([p for p in assessment.split('\n') if p.strip()])
    
    # Check for numerical predictions
    numerical_patterns = [r'\d+%', r'\d+\s*percent', r'probability']
    has_numbers = any(re.search(pattern, assessment, re.IGNORECASE) for pattern in numerical_patterns)
    
    print("\n=== Overall Assessment Analysis ===")
    print(f"Word count: {word_count} words")
    print(f"Character count: {char_count} chars")
    print(f"Paragraph count: {paragraph_count}")
    print(f"Has numerical predictions: {has_numbers}")
    
    # Version detection logic
    if word_count <= 105:  # Allow 5 word margin
        print("\n✅ Appears to be v2.1.1 (100-word limit version)")
        version = "2.1.1"
    elif word_count <= 155:  # Allow 5 word margin
        print("\n⚠️ Appears to be v2.1.1 (150-word limit version - OLD)")
        version = "2.1.1-old"
    elif word_count <= 255:
        print("\n📝 Appears to be v2.1.0 (150-250 word version)")
        version = "2.1.0"
    else:
        print("\n❓ Unknown version or older format")
        version = "unknown"
    
    print(f"\n=== Assessment Content ===")
    print(assessment)
    
    return version, word_count

def test_gap_analysis():
    """Test Gap Analysis API to determine actual version being used"""
    
    print("\n" + "="*60)
    print("Testing Gap Analysis Prompt Version")
    print("="*60)
    
    url = f"{API_URL}/api/v1/index-cal-and-gap-analysis"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_description": test_jd,
        "resume": test_resume,
        "keywords": ["Python", "FastAPI", "Azure", "Docker", "Kubernetes", "Machine Learning", "Microservices"]
    }
    
    print(f"\nSending request to: {url}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Debug: print response structure
            print("\n=== Response Structure ===")
            print("Keys in response:", list(data.keys()))
            
            # Check if gap_analysis is in data field
            if "data" in data and "gap_analysis" in data["data"]:
                gap_data = data["data"]["gap_analysis"]
                print("Keys in gap_analysis:", list(gap_data.keys()))
            elif "gap_analysis" in data:
                gap_data = data["gap_analysis"]
                print("Keys in gap_analysis:", list(gap_data.keys()))
            else:
                gap_data = None
                
                # Check different possible field names
                assessment_key = None
                for key in ["OverallAssessment", "overall_assessment", "Overall Assessment"]:
                    if key in data["gap_analysis"]:
                        assessment_key = key
                        break
                
                if assessment_key:
                    assessment = data["gap_analysis"][assessment_key]
                    version, word_count = analyze_overall_assessment(assessment)
                    
                    # Check other sections for version clues
                    gaps_key = None
                    for key in ["KeyGaps", "key_gaps", "Key Gaps"]:
                        if key in data["gap_analysis"]:
                            gaps_key = key
                            break
                    
                    if gaps_key:
                        gaps = data["gap_analysis"][gaps_key]
                        has_markers = any("[Skill Gap]" in gap or "[Presentation Gap]" in gap for gap in gaps)
                        print(f"\nHas gap classification markers: {has_markers}")
                        if has_markers:
                            print("✅ Gap classification markers present (v2.1.x feature)")
                    
                    return version, word_count
                else:
                    print("❌ No OverallAssessment found in gap_analysis")
                    print("Available fields:", list(data["gap_analysis"].keys())[:10])  # Show first 10 fields
                    return None, 0
            else:
                print("❌ No gap_analysis field in response")
                return None, 0
                
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None, 0
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, 0

def main():
    """Run multiple tests to verify version consistency"""
    
    print("Testing Azure Container Apps deployment")
    print(f"Expected version from env var: 2.1.1 (100-word limit)")
    
    # Run test 3 times to check consistency
    results = []
    for i in range(3):
        print(f"\n\n{'='*20} Test {i+1}/3 {'='*20}")
        version, word_count = test_gap_analysis()
        if version:
            results.append((version, word_count))
    
    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if results:
        versions = [r[0] for r in results]
        word_counts = [r[1] for r in results]
        
        print(f"Tests run: {len(results)}")
        print(f"Versions detected: {set(versions)}")
        print(f"Word counts: {word_counts}")
        print(f"Average word count: {sum(word_counts)/len(word_counts):.1f}")
        
        if len(set(versions)) == 1:
            detected_version = versions[0]
            if detected_version == "2.1.1":
                print("\n✅ SUCCESS: Using v2.1.1 with 100-word limit")
            elif detected_version == "2.1.1-old":
                print("\n⚠️ WARNING: Using old v2.1.1 with 150-word limit")
                print("The container may be using cached prompt file")
                print("\nTroubleshooting:")
                print("1. Container may need a full restart")
                print("2. Try: az containerapp revision restart --name airesumeadvisor-api-production --resource-group airesumeadvisorfastapi")
            else:
                print(f"\n⚠️ WARNING: Detected version {detected_version}, expected 2.1.1")
        else:
            print("\n❌ ERROR: Inconsistent versions detected")
    else:
        print("❌ No successful tests")

if __name__ == "__main__":
    main()