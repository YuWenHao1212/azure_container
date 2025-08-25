#!/usr/bin/env python3
"""
Test script for Bubble.io API integration.
Tests Gap Analysis and Resume Tailoring endpoints with Bubble-compatible formats.
"""

import asyncio
import json
import httpx
from typing import Dict, Any
from datetime import datetime

# API Configuration
BASE_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = "your-api-key-here"  # Replace with actual API key

# Test data
TEST_JD = """
We are looking for a Senior Full Stack Developer with expertise in:
- Python and FastAPI for backend development
- React.js and TypeScript for frontend
- PostgreSQL and Redis for data management
- Docker and Kubernetes for containerization
- CI/CD pipelines with GitHub Actions
- Cloud platforms (AWS or Azure)
- RESTful API design and microservices architecture
- Test-driven development (TDD)
- Agile methodologies

Responsibilities:
- Design and implement scalable web applications
- Collaborate with cross-functional teams
- Code review and mentoring junior developers
- Performance optimization and monitoring
- Writing technical documentation

Required: 5+ years of experience in full-stack development
"""

TEST_RESUME = """
John Doe
Senior Software Engineer

Experience:
Software Engineer at TechCorp (2020-Present)
- Developed web applications using Python and JavaScript
- Worked with databases including MySQL
- Participated in code reviews
- Used Git for version control
- Deployed applications to production

Junior Developer at StartupXYZ (2018-2020)
- Built REST APIs using Node.js
- Created frontend interfaces with HTML/CSS
- Learned agile development practices
- Assisted in debugging and testing

Skills:
- Programming: Python, JavaScript, Java
- Databases: MySQL, MongoDB
- Tools: Git, VS Code, Postman
- Other: Problem-solving, Team collaboration

Education:
Bachelor's in Computer Science (2018)
"""


async def test_gap_analysis():
    """Test Gap Analysis API endpoint."""
    print("\n" + "=" * 60)
    print("Testing Gap Analysis API")
    print("=" * 60)
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "job_description": TEST_JD,
        "resume": TEST_RESUME,
        "language": "en"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/index-cal-and-gap-analysis",
                json=payload,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("\nResponse Structure:")
                print_response_structure(data)
                
                # Check Bubble compatibility
                check_bubble_compatibility(data, "Gap Analysis")
                
                # Save response for analysis
                with open("gap_analysis_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("\n✅ Response saved to gap_analysis_response.json")
                
                return data
            else:
                print(f"❌ Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None


async def test_resume_tailoring(gap_analysis_result: Dict[str, Any]):
    """Test Resume Tailoring API endpoint."""
    print("\n" + "=" * 60)
    print("Testing Resume Tailoring API")
    print("=" * 60)
    
    if not gap_analysis_result:
        print("❌ Skipping: No gap analysis result available")
        return
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Extract gap analysis data
    gap_data = gap_analysis_result.get("data", {})
    
    payload = {
        "job_description": TEST_JD,
        "original_resume": TEST_RESUME,
        "gap_analysis": {
            "covered_keywords": gap_data.get("covered_keywords", []),
            "missing_keywords": gap_data.get("missing_keywords", []),
            "similarity_percentage": gap_data.get("similarity_score", 0),
            "coverage_percentage": gap_data.get("keyword_match_score", 0),
            "recommendations": gap_data.get("recommendations", [])
        },
        "options": {
            "language": "en",
            "style": "professional"
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/tailor-resume",
                json=payload,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("\nResponse Structure:")
                print_response_structure(data)
                
                # Check Bubble compatibility
                check_bubble_compatibility(data, "Resume Tailoring")
                
                # Save response for analysis
                with open("resume_tailoring_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("\n✅ Response saved to resume_tailoring_response.json")
                
                return data
            else:
                print(f"❌ Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None


def print_response_structure(data: Dict[str, Any], indent: int = 0):
    """Print the structure of the response for analysis."""
    for key, value in data.items():
        spaces = "  " * indent
        if isinstance(value, dict):
            print(f"{spaces}{key}: dict")
            if indent < 2:  # Limit depth for readability
                print_response_structure(value, indent + 1)
        elif isinstance(value, list):
            if value:
                print(f"{spaces}{key}: list[{len(value)} items]")
            else:
                print(f"{spaces}{key}: [] (empty array)")
        else:
            value_type = type(value).__name__
            if isinstance(value, str) and len(value) > 50:
                print(f"{spaces}{key}: {value_type} (truncated)")
            else:
                print(f"{spaces}{key}: {value_type} = {value}")


def check_bubble_compatibility(data: Dict[str, Any], api_name: str):
    """Check if response is compatible with Bubble.io requirements."""
    print(f"\n🔍 Bubble.io Compatibility Check for {api_name}:")
    
    issues = []
    
    # Check for consistent top-level structure
    required_fields = ["success", "data"]
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing required field: {field}")
    
    # Check that arrays are not null
    def check_arrays(obj: Any, path: str = ""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if value is None:
                    # Check if this should be an array
                    if any(arr_indicator in key.lower() for arr_indicator in 
                           ["keywords", "improvements", "recommendations", "details", "warnings"]):
                        issues.append(f"Null array at {current_path} (should be [])")
                check_arrays(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_arrays(item, f"{path}[{i}]")
    
    check_arrays(data)
    
    # Check for consistent field naming
    if "data" in data:
        data_obj = data["data"]
        
        # For Resume Tailoring
        if api_name == "Resume Tailoring":
            expected_fields = ["optimized_resume", "applied_improvements", "keyword_tracking"]
            for field in expected_fields:
                if field not in data_obj:
                    issues.append(f"Missing expected field in data: {field}")
            
            # Check for old field names
            if "resume" in data_obj:
                issues.append("Found 'resume' field (should be 'optimized_resume')")
            if "improvements" in data_obj:
                issues.append("Found 'improvements' field (should be 'applied_improvements')")
    
    # Report results
    if issues:
        print("❌ Compatibility issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Response is Bubble.io compatible")
    
    return len(issues) == 0


async def main():
    """Run all integration tests."""
    print("\n" + "🚀 Starting Bubble.io Integration Tests " + "🚀")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Base URL: {BASE_URL}")
    
    # Test Gap Analysis
    gap_result = await test_gap_analysis()
    
    # Test Resume Tailoring using Gap Analysis result
    if gap_result:
        await test_resume_tailoring(gap_result)
    
    print("\n" + "=" * 60)
    print("✅ Integration tests completed")
    print("=" * 60)
    
    # Summary
    print("\n📊 Summary:")
    print("1. Check gap_analysis_response.json for Gap Analysis response")
    print("2. Check resume_tailoring_response.json for Resume Tailoring response")
    print("3. Review any compatibility issues reported above")
    print("\n💡 Tips for Bubble.io:")
    print("- Use the saved JSON files to initialize data types in Bubble")
    print("- Ensure all array fields are properly initialized as lists")
    print("- Check that field names match exactly (case-sensitive)")


if __name__ == "__main__":
    # Note: Replace API_KEY with actual key before running
    if API_KEY == "your-api-key-here":
        print("⚠️  Please set the API_KEY variable before running tests")
        print("You can find the API key in Azure Portal or .env file")
    else:
        asyncio.run(main())