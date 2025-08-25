#!/usr/bin/env python3
"""
Local test for Debug Mode functionality
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set debug mode before importing
os.environ["LLM2_DEBUG_MODE"] = "true"

from src.services.resume_tailoring_v31 import ResumeTailoringServiceV31


def test_debug_fallback():
    """Test debug mode fallback messages"""

    # Create a mock service instance without full initialization
    class MockService:
        def __init__(self):
            self.debug_mode = os.getenv("LLM2_DEBUG_MODE", "false").lower() == "true"

        def _extract_original_section(self, section_name, original_resume):
            return f"<h2>{section_name.title()}</h2><p>Original content</p>"

    service = MockService()
    print(f"Debug mode enabled: {service.debug_mode}")

    # Test JSON parse error fallback
    print("\n" + "="*60)
    print("Testing JSON Parse Error Fallback")
    print("="*60)

    result = service._parse_llm_response(
        "This is not valid JSON",
        is_llm2=True,
        original_resume="<h3>Education:</h3><p>Test University</p>"
    )

    print("Result keys:", result.keys())
    if "debug_info" in result:
        print("Debug info:", json.dumps(result["debug_info"], indent=2))

    education_section = result["optimized_sections"].get("education", "")
    if "Debug Mode" in education_section:
        print("✅ Debug mode message found in education section")
        print("Preview:", education_section[:500])
    else:
        print("❌ No debug message found")

    # Test empty section fallback
    print("\n" + "="*60)
    print("Testing Empty Section Fallback")
    print("="*60)

    # Simulate empty LLM2 sections
    llm1_result = {
        "optimized_sections": {
            "summary": "Test summary",
            "skills": "Test skills",
            "experience": "Test experience"
        }
    }

    llm2_result = {
        "optimized_sections": {
            "education": "",  # Empty
            "projects": "",   # Empty
            "certifications": ""  # Empty
        },
        "bundle": {
            "education_enhancement_needed": False,
            "key_gaps": "Power BI, Superset, Data Analyst"
        }
    }

    resume_structure = {
        "education_enhancement_needed": False,
        "metadata": {
            "years_of_experience": 10,
            "is_current_student": False
        }
    }

    merged = service._merge_sections(
        llm1_result,
        llm2_result,
        resume_structure,
        "<h3>Education:</h3><p>Original education content</p>"
    )

    # Check if debug messages are present
    for section in ["education", "projects", "certifications"]:
        content = merged.get(section, "")
        if "Debug Mode" in content:
            print(f"✅ Debug message found in {section}")
        else:
            print(f"❌ No debug message in {section}")

    # Check debug_info
    if "debug_info" in llm2_result:
        print("\nDebug info collected:", json.dumps(llm2_result["debug_info"], indent=2))


if __name__ == "__main__":
    print("Testing Debug Mode Locally")
    print("="*60)

    try:
        test_debug_fallback()
        print("\n✅ Debug mode test completed")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
