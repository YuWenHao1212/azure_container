#!/usr/bin/env python3
"""Final fix for e2e test indentation issues."""

with open("test/e2e/test_index_calculation_v2_e2e.py", 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix specific line numbers with indentation issues
fixes = {
    146: "                        # Step 2: Verify response structure and content\n",
    278: "                        # AzureOpenAI errors should return 503\n",
    279: "                        assert response1.status_code == 503\n",
}

for line_num, new_line in fixes.items():
    if line_num <= len(lines):
        lines[line_num - 1] = new_line

with open("test/e2e/test_index_calculation_v2_e2e.py", 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation issues in test_index_calculation_v2_e2e.py")