#!/usr/bin/env python3
"""Test script to replicate CI smoke test Gap Analysis call."""
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_URL = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
API_KEY = os.getenv("CONTAINER_APP_API_KEY", "")

if not API_KEY:
    print("Warning: CONTAINER_APP_API_KEY not found in environment")
    print("Please set it in .env file or environment")
else:
    print(f"API Key configured (length: {len(API_KEY)})")

# Test data - exact same as CI smoke test
test_data = {
    "job_description": "We need a Senior Full Stack Developer with expertise in React, Node.js, and MongoDB. The ideal candidate should have experience with microservices architecture, GraphQL, and containerization technologies. Strong understanding of software design patterns, test-driven development, and continuous integration practices is essential for this role.",
    "resume": "Full Stack Developer with 3 years of experience in React and Node.js. Familiar with MongoDB and REST APIs. Some exposure to Docker. Have worked on several web applications using modern JavaScript frameworks. Experience with agile development, code reviews, and collaborative development using Git. Passionate about learning new technologies and best practices in software development.",
    "keywords": ["React", "Node.js", "MongoDB", "GraphQL", "Docker", "Microservices", "TDD", "CI/CD", "Git", "REST APIs"]
}

print("\nTesting Gap Analysis API...")
print(f"URL: {API_URL}/api/v1/index-cal-and-gap-analysis")
print(f"Data: {json.dumps(test_data, indent=2)[:200]}...")

# Make the request
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

try:
    response = requests.post(
        f"{API_URL}/api/v1/index-cal-and-gap-analysis",
        json=test_data,
        headers=headers,
        timeout=30
    )
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        print("✓ Success!")
        result = response.json()
        print(f"Response keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        if 'data' in result:
            print(f"Data keys: {result['data'].keys() if isinstance(result['data'], dict) else 'Not a dict'}")
    else:
        print(f"✗ Failed!")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"✗ Error: {e}")