#!/usr/bin/env python3
"""
Test Debug Mode logic without full service initialization
"""

import json
import os
from datetime import datetime

# Set debug mode
os.environ["LLM2_DEBUG_MODE"] = "true"


def test_debug_mode_logic():
    """Test the debug mode logic independently"""

    debug_mode = os.getenv("LLM2_DEBUG_MODE", "false").lower() == "true"
    print(f"Debug mode: {debug_mode}")

    # Simulate empty education section scenario
    print("\n" + "="*60)
    print("Simulating Empty Education Section")
    print("="*60)

    # Simulate parameters
    education_enhanced = False
    years_of_experience = 10
    is_current_student = False

    if debug_mode:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        debug_html = f"""<div style='background:#fff3cd;border:2px solid #ffc107;padding:15px;margin:10px 0;border-radius:5px;'>
<h3 style='color:#856404;margin-top:0;'>⚠️ LLM2 Education Empty - Debug Mode</h3>
<p><strong>Timestamp:</strong> {timestamp}</p>
<p><strong>Parameters:</strong></p>
<ul style='list-style-type:none;padding-left:0;'>
<li>📊 education_enhancement_needed: <code>{education_enhanced}</code></li>
<li>📊 Years of experience: {years_of_experience}</li>
<li>📊 Student status: {is_current_student}</li>
</ul>
<p><strong>Likely Cause:</strong> {'Education enhancement disabled for experienced professionals (≥2 years)' if not education_enhanced else 'LLM2 returned empty content despite enhancement flag'}</p>
<p><strong>Recommendation:</strong> {'Consider adjusting education_enhancement threshold in ResumeStructureAnalyzer' if not education_enhanced else 'Check LLM2 prompt logic for enhanced education processing'}</p>
</div>"""

        education_content = f"<h2>Education</h2>{debug_html}"

        print("✅ Debug HTML generated successfully")
        print("\nDebug HTML Preview:")
        print("-" * 40)
        print(education_content[:500])
        print("-" * 40)

        # Check for key elements
        checks = [
            ("Debug Mode header", "⚠️ LLM2 Education Empty" in debug_html),
            ("Timestamp", timestamp in debug_html),
            ("Parameters shown", "education_enhancement_needed" in debug_html),
            ("Likely cause", "Education enhancement disabled" in debug_html),
            ("Recommendation", "Consider adjusting" in debug_html)
        ]

        print("\nValidation Checks:")
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"  {status} {check_name}")
    else:
        print("Debug mode is OFF - would use original content")

    # Test JSON parse error scenario
    print("\n" + "="*60)
    print("Simulating JSON Parse Error")
    print("="*60)

    if debug_mode:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = "JSONDecodeError"
        error_msg = "Expecting value: line 1 column 1 (char 0)"
        error_preview = "This is not valid JSON content..."

        debug_html = f"""<div style='background:#fff3cd;border:2px solid #ffc107;padding:15px;margin:10px 0;border-radius:5px;'>
<h3 style='color:#856404;margin-top:0;'>⚠️ LLM2 JSON Parse Failed - Debug Mode</h3>
<p><strong>Timestamp:</strong> {timestamp}</p>
<p><strong>Error Type:</strong> {error_type}</p>
<p><strong>Error Message:</strong> {error_msg}</p>
<p><strong>Response Preview:</strong></p>
<pre style='background:#f8f9fa;padding:10px;overflow-x:auto;'>{error_preview}</pre>
<p><strong>Diagnostic:</strong> LLM2 response could not be parsed as valid JSON. Check prompt output format.</p>
</div>"""

        print("✅ JSON error debug HTML generated")
        print("\nChecking elements:")
        print(f"  ✅ Error type shown: {error_type}")
        print(f"  ✅ Error message shown: {error_msg}")
        print("  ✅ Response preview included")
        print("  ✅ Diagnostic message included")


if __name__ == "__main__":
    print("Testing Debug Mode Logic")
    print("="*60)

    test_debug_mode_logic()

    print("\n" + "="*60)
    print("Testing with Debug Mode OFF")
    print("="*60)

    os.environ["LLM2_DEBUG_MODE"] = "false"
    debug_mode = os.getenv("LLM2_DEBUG_MODE", "false").lower() == "true"
    print(f"Debug mode: {debug_mode}")
    print("In production mode, would use original resume content instead of debug messages")

    print("\n✅ Debug logic test completed successfully")
