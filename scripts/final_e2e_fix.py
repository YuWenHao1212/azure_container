#!/usr/bin/env python3
"""Final comprehensive fix for e2e test file."""

def fix_e2e_indentation():
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace problematic sections with correctly indented versions
    
    # Fix the first indentation issue around line 144-147
    content = content.replace(
        """                            )
                    processing_time = time.time() - start_time

                        # Step 2: Verify response structure and content
                        assert response.status_code == 200""",
        """                            )
                        processing_time = time.time() - start_time

                        # Step 2: Verify response structure and content
                        assert response.status_code == 200"""
    )
    
    # Fix the second indentation issue around line 277-280
    content = content.replace(
        """                        )
                        # AzureOpenAI errors should return 503
                    assert response1.status_code == 503
                    assert response1.json()["success"] is False""",
        """                        )
                    # AzureOpenAI errors should return 503
                    assert response1.status_code == 503
                    assert response1.json()["success"] is False"""
    )
    
    with open("test/e2e/test_index_calculation_v2_e2e.py", 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed all indentation issues in test_index_calculation_v2_e2e.py")

if __name__ == "__main__":
    fix_e2e_indentation()