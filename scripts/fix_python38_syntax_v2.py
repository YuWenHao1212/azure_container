#!/usr/bin/env python3
"""Fix Python 3.8 syntax compatibility issues - Version 2."""

import os
import re


def fix_conftest(file_path):
    """Fix conftest.py specific issues."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if file_path.endswith('test/conftest.py'):
        # Fix the mock_openai_clients fixture
        content = content.replace(
            """    with patch('src.services.openai_client.get_azure_openai_client'):
        with patch('src.services.openai_client_gpt41.get_gpt41_mini_client'):
            with patch('src.services.keyword_extraction.get_keyword_extraction_service'):
        yield""",
            """    with patch('src.services.openai_client.get_azure_openai_client'):
        with patch('src.services.openai_client_gpt41.get_gpt41_mini_client'):
            with patch('src.services.keyword_extraction.get_keyword_extraction_service'):
                yield"""
        )
    
    # Add newline at end of file if missing
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_test_azure_openai_integration(file_path):
    """Fix test_azure_openai_integration.py specific issues."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the patch.dict environment variables
    if 'test_azure_openai_integration.py' in file_path:
        # Find and fix the broken patch.dict pattern
        content = re.sub(
            r'with patch\.dict\(os\.environ, \{:\s*\n\s*with.*?\n.*?with \}\):\s*\n\s*with # Global patches',
            """with patch.dict(os.environ, {
                    'MONITORING_ENABLED': 'false',
                    'LIGHTWEIGHT_MONITORING': 'false',
                    'ERROR_CAPTURE_ENABLED': 'false',
                    'CONTAINER_APP_API_KEY': ''
                }):
                    # Global patches for LLM factory functions
                    with patch('src.services.llm_factory.get_llm_client', return_value=AsyncMock()):
                        with patch('src.services.llm_factory.get_llm_client_smart', return_value=AsyncMock()):""",
            content,
            flags=re.DOTALL
        )
    
    return content


def fix_test_e2e(file_path):
    """Fix e2e test file specific issues."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix indentation after with statements
    lines = content.splitlines()
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)
        
        # Check if this line ends with a with statement and colon
        if re.match(r'^(\s*)with .+:$', line) and i + 1 < len(lines):
            next_line = lines[i + 1]
            # If next line doesn't have proper indentation
            if next_line.strip() and not next_line.startswith(line[:len(line) - len(line.lstrip())] + '    '):
                # Check if it's a comment or code
                if next_line.strip().startswith('#'):
                    # Properly indent the comment
                    indent = len(line) - len(line.lstrip()) + 4
                    fixed_lines.append(' ' * indent + next_line.strip())
                    i += 1
                    continue
        
        i += 1
    
    content = '\n'.join(fixed_lines)
    
    # Add newline at end if missing
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_test_prompt_manager(file_path):
    """Fix test_prompt_manager.py specific issues."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix line 357 indentation issue
    content = re.sub(
        r'with pytest\.raises\(PromptNotAvailableError\) as exc_info:\s*\n\s*prompt_manager\.get_prompt',
        """with pytest.raises(PromptNotAvailableError) as exc_info:
                prompt_manager.get_prompt""",
        content
    )
    
    # Add newline at end if missing
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def fix_integration_conftest(file_path):
    """Fix integration conftest.py."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add newline at end if missing
    if not content.endswith('\n'):
        content += '\n'
    
    return content


def main():
    """Fix Python 3.8 compatibility issues in test files."""
    fixes = {
        'test/conftest.py': fix_conftest,
        'test/integration/test_azure_openai_integration.py': fix_test_azure_openai_integration,
        'test/e2e/test_index_calculation_v2_e2e.py': fix_test_e2e,
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