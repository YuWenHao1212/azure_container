#!/usr/bin/env python3
"""Fix final syntax issues in test_azure_openai_integration.py."""

import re


def main():
    """Fix syntax issues with 'with' statements ending with comma followed by another 'with'."""
    file_path = 'test/integration/test_azure_openai_integration.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix patterns like:
    # with patch(...), # noqa: E501:
    #     with patch(...):
    # Should be:
    # with patch(...): # noqa: E501
    #     with patch(...):
    
    # Pattern 1: Fix lines ending with "),  # noqa: E501:" followed by "with"
    content = re.sub(
        r'\),  # noqa: E501:\s*\n(\s*)with ',
        r'):  # noqa: E501\n\1with ',
        content
    )
    
    # Pattern 2: Fix lines ending with just "):" followed by indented "with"
    content = re.sub(
        r'\),\s*\n(\s+)with ',
        r'):\n\1with ',
        content
    )
    
    # Pattern 3: Fix "with patch(:" pattern (without closing parenthesis)
    content = re.sub(
        r'with patch\(:\s*\n\s*with ',
        r'with patch(',
        content
    )
    
    # Pattern 4: Fix "with ):" pattern (orphaned closing parenthesis)
    content = re.sub(
        r'with \):\s*\n',
        '',
        content
    )
    
    # Pattern 5: Fix 'with patch(...):\n                with' (missing code block)
    lines = content.splitlines()
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a 'with' statement at the end followed by another 'with' statement
        if line.strip().endswith(':') and 'with ' in line and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip().startswith('with '):
                # Missing indented block - continue to next line
                fixed_lines.append(line)
                i += 1
                continue
        
        fixed_lines.append(line)
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # Final check: ensure no "No newline at end of file" comments
    if not content.endswith('\n'):
        content += '\n'
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")


if __name__ == "__main__":
    main()