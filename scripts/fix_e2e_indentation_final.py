#!/usr/bin/env python3
"""Final fix for e2e test indentation issues."""

import re

def fix_indentation():
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 144 area - processing_time line
    for i, line in enumerate(lines):
        if i >= 143 and i <= 145 and "processing_time = time.time() - start_time" in line:
            # Should have 24 spaces (6 levels of 4 spaces)
            lines[i] = "                        processing_time = time.time() - start_time\n"
        
        # Fix the assert response.status_code == 200 line
        if i >= 146 and i <= 150 and line.strip() == "assert response.status_code == 200":
            lines[i] = "                        assert response.status_code == 200\n"
        
        # Fix data = response.json() line
        if i >= 149 and i <= 151 and line.strip() == "data = response.json()":
            lines[i] = "                        data = response.json()\n"
    
    # Fix lines 278-283 area
    for i, line in enumerate(lines):
        # Fix "# AzureOpenAI errors should return 503" comment
        if i >= 277 and i <= 279 and "# AzureOpenAI errors should return 503" in line:
            lines[i] = "                    # AzureOpenAI errors should return 503\n"
        
        # Fix assert response1.status_code == 503
        if i >= 278 and i <= 281 and line.strip() == "assert response1.status_code == 503":
            lines[i] = "                    assert response1.status_code == 503\n"
        
        # Fix assert response1.json()["success"] is False
        if i >= 279 and i <= 283 and 'assert response1.json()["success"] is False' in line:
            lines[i] = '                    assert response1.json()["success"] is False\n'
    
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed indentation issues")

if __name__ == "__main__":
    fix_indentation()