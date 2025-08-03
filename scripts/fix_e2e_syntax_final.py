#!/usr/bin/env python3
"""Final fix for e2e test syntax errors."""

def fix_indentation():
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix specific indentation issues
    for i in range(len(lines)):
        # Fix line 279 (assert response1.status_code == 503)
        if i == 278 and lines[i].strip() == "assert response1.status_code == 503":
            lines[i] = "                    assert response1.status_code == 503\n"
        
        # Fix line 280 (assert response1.json()["success"] is False)
        if i == 279 and 'assert response1.json()["success"] is False' in lines[i]:
            lines[i] = '                    assert response1.json()["success"] is False\n'
        
        # Fix line 283 indentation (# Reset singleton for next request)
        if i == 282 and "# Reset singleton for next request" in lines[i]:
            lines[i] = "                    # Reset singleton for next request\n"
        
        # Fix line 286 (response2 = test_client.post)
        if i == 285 and "response2 = test_client.post(" in lines[i]:
            lines[i] = "                    response2 = test_client.post(\n"
    
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Fixed indentation issues in test_index_calculation_v2_e2e.py")

if __name__ == "__main__":
    fix_indentation()