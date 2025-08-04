#!/usr/bin/env python3
"""Fix remaining syntax issues in test files."""

import re


def fix_test_azure_openai_integration(file_path):
    """Fix test_azure_openai_integration.py."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the duplicate "for LLM factory functions" line
    content = content.replace(
        """                        with patch('src.services.llm_factory.get_llm_client_smart', return_value=AsyncMock()): for LLM factory functions:
                                            with patch('src.services.llm_factory.get_llm_client', return_value=AsyncMock()):
                                                with patch('src.services.llm_factory.get_llm_client_smart', return_value=AsyncMock()):""",
        """                        with patch('src.services.llm_factory.get_llm_client_smart', return_value=AsyncMock()):"""
    )
    
    # Fix "with patch(:" syntax errors
    content = re.sub(
        r"with patch\(:\s*\n\s*with '([^']+)':",
        r"with patch('\1'):",
        content
    )
    
    # Fix "with return_value=" syntax errors
    content = re.sub(
        r"def make_request\(\):\s*\n\s*with patch\('([^']+)':\s*\n\s*with return_value=",
        r"def make_request():\n            with patch('\1', return_value=",
        content
    )
    
    # Fix nested with statements in make_request function
    content = re.sub(
        r"with patch\('src\.services\.llm_factory\.get_llm_info':\s*\n\s*with return_value=",
        r"with patch('src.services.llm_factory.get_llm_info', return_value=",
        content
    )
    
    # Fix line 71 - remove extra lines
    lines = content.splitlines()
    fixed_lines = []
    skip_next = False
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        if "app = create_app()" in line and i > 0 and "No newline at end of file" in lines[i-1]:
            # Skip the "No newline" comment
            fixed_lines.pop()  # Remove the last added line if it was "No newline"
            fixed_lines.append(line)
        elif "No newline at end of file" in line and i < len(lines) - 1:
            # Skip this line if it's not at the end
            continue
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Add newline at end
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_test_e2e(file_path):
    """Fix e2e test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix duplicate "# Step 1: Make the API request" lines
    content = re.sub(
        r"(\s+)# Step 1: Make the API request\s*\n\s*# Step 1: Make the API request",
        r"\1# Step 1: Make the API request",
        content
    )
    
    # Fix duplicate "# First request fails" lines
    content = re.sub(
        r"(\s+)# First request fails\s*\n\s*# First request fails",
        r"\1# First request fails",
        content
    )
    
    # Fix line 465 - ensure proper newline at end
    lines = content.splitlines()
    if lines and "No newline at end of file" in lines[-1]:
        lines.pop()
    
    content = '\n'.join(lines)
    
    # Add newline at end
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_test_conftest(file_path):
    """Fix test/conftest.py."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix line 55 - remove "No newline at end of file" and ensure proper yield
    lines = content.splitlines()
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if "No newline at end of file" in line:
            continue
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Add newline at end
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_test_prompt_manager(file_path):
    """Fix test_prompt_manager.py."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix indentation in pytest.raises blocks
    lines = content.splitlines()
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if "with pytest.raises(PromptNotAvailableError) as exc_info:" in line and i + 1 < len(lines):
            fixed_lines.append(line)
            next_line = lines[i + 1]
            # If next line is not properly indented, fix it
            if next_line.strip().startswith("prompt_manager.get_prompt"):
                indent = len(line) - len(line.lstrip()) + 4
                fixed_lines.append(' ' * indent + next_line.strip())
                continue
        else:
            fixed_lines.append(line)
    
    # Remove "No newline at end of file" comments
    content = '\n'.join(l for l in fixed_lines if "No newline at end of file" not in l)
    
    # Add newline at end
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_integration_conftest(file_path):
    """Fix integration conftest.py."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove "No newline at end of file" and fix return statement
    lines = content.splitlines()
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if "No newline at end of file" in line:
            continue
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Add newline at end
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def main():
    """Fix remaining syntax issues."""
    fixes = {
        'test/integration/test_azure_openai_integration.py': fix_test_azure_openai_integration,
        'test/e2e/test_index_calculation_v2_e2e.py': fix_test_e2e,
        'test/conftest.py': fix_test_conftest,
        'test/unit/test_prompt_manager.py': fix_test_prompt_manager,
        'test/integration/conftest.py': fix_integration_conftest,
    }
    
    for file_path, fix_func in fixes.items():
        try:
            print(f"Fixing {file_path}...")
            fixed_content = fix_func(file_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print(f"  ✓ Fixed")
        except FileNotFoundError:
            print(f"  ✗ File not found")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    main()