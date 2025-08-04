#!/usr/bin/env python3
"""Fix Python 3.8 syntax compatibility issues."""

import re


def fix_parentheses_with_statements(file_path):
    """Fix 'with (...)' syntax for Python 3.8 compatibility."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match 'with (' at the beginning of a with statement
    # This is a simple fix - for complex cases, manual review might be needed
    lines = content.splitlines()
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Check if this is a 'with (' statement
        if stripped.startswith('with ('):
            indent = line[:len(line) - len(line.lstrip())]
            
            # Collect all the context managers until we find '):'
            context_managers = []
            j = i
            while j < len(lines):
                current_line = lines[j].strip()
                
                if j == i:
                    # First line - extract content after 'with ('
                    current_line = current_line[6:]  # Remove 'with ('
                
                # Check if this line ends the with statement
                if current_line.endswith('):'):
                    # Remove the trailing '):'
                    current_line = current_line[:-2].strip()
                    if current_line and not current_line.endswith(','):
                        context_managers.append(current_line.rstrip(','))
                    break
                elif current_line.endswith(','):
                    context_managers.append(current_line.rstrip(','))
                elif current_line:
                    context_managers.append(current_line.rstrip(','))
                
                j += 1
            
            # Now create nested with statements
            if context_managers:
                for idx, cm in enumerate(context_managers):
                    # Clean up the context manager
                    cm = cm.strip()
                    if cm:
                        fixed_lines.append(f"{indent}{'    ' * idx}with {cm}:")
                
                # Skip the original lines
                i = j + 1
            else:
                fixed_lines.append(line)
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    return '\n'.join(fixed_lines)


def main():
    """Fix Python 3.8 compatibility issues in test files."""
    files_to_fix = [
        'test/unit/test_prompt_manager.py',
        'test/conftest.py',
        'test/integration/conftest.py',
        'test/integration/test_azure_openai_integration.py',
        'test/e2e/test_index_calculation_v2_e2e.py',
        'test/unit/test_gap_analysis_v2.py'
    ]
    
    for file_path in files_to_fix:
        try:
            print(f"Fixing {file_path}...")
            fixed_content = fix_parentheses_with_statements(file_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"  ✓ Fixed")
        except FileNotFoundError:
            print(f"  ✗ File not found")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    main()