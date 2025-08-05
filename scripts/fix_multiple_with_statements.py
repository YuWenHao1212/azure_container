#!/usr/bin/env python3
"""Fix SIM117 multiple-with-statements errors for Python 3.8 compatibility."""
import ast
import os
import re


def fix_multiple_with_statements(file_path):
    """Fix multiple with statements in parentheses for Python 3.8."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match: with (..., ...) as ...:
    # This is a complex pattern that matches multi-line with statements
    pattern = r'with\s*\(\s*([^)]+)\s*\)\s*:'
    
    def replace_with_statement(match):
        # Get the content inside parentheses
        inner_content = match.group(1)
        
        # Split by commas not inside parentheses/brackets
        # This is a simplified approach - may need refinement for complex cases
        parts = []
        current_part = []
        paren_depth = 0
        bracket_depth = 0
        
        for char in inner_content:
            if char == '(' and bracket_depth == 0:
                paren_depth += 1
            elif char == ')' and bracket_depth == 0:
                paren_depth -= 1
            elif char == '[':
                bracket_depth += 1
            elif char == ']':
                bracket_depth -= 1
            elif char == ',' and paren_depth == 0 and bracket_depth == 0:
                parts.append(''.join(current_part).strip())
                current_part = []
                continue
            current_part.append(char)
        
        if current_part:
            parts.append(''.join(current_part).strip())
        
        # Now we need to identify the indentation
        lines_before = content[:match.start()].split('\n')
        if lines_before:
            last_line = lines_before[-1]
            indent = len(last_line) - len(last_line.lstrip())
            indent_str = ' ' * indent
        else:
            indent_str = ''
        
        # Build nested with statements
        result = []
        for i, part in enumerate(parts):
            result.append(f"{' ' * (indent + i * 4)}with {part}:")
        
        # Join with newlines but remove the first indentation
        final_result = '\n'.join(result)
        if final_result.startswith(indent_str):
            final_result = final_result[len(indent_str):]
        
        return final_result
    
    # Apply the replacement
    content = re.sub(pattern, replace_with_statement, content, flags=re.MULTILINE | re.DOTALL)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def process_file_with_ast(file_path):
    """Process file using AST to handle complex cases."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Check if this line starts with 'with ('
            if stripped.startswith('with (') or (i > 0 and lines[i-1].strip() == 'with ('):
                # Find the closing parenthesis
                start_line = i
                if not stripped.startswith('with ('):
                    start_line = i - 1
                
                # Collect all lines until we find the closing ')'
                with_content = []
                j = start_line
                paren_count = 0
                found_closing = False
                
                while j < len(lines):
                    current_line = lines[j]
                    for char in current_line:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                found_closing = True
                                break
                    
                    with_content.append(current_line)
                    if found_closing:
                        break
                    j += 1
                
                if found_closing:
                    # Extract the content and parse it
                    full_content = ''.join(with_content)
                    
                    # Extract indent
                    base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
                    indent_str = ' ' * base_indent
                    
                    # Parse the with statement content
                    match = re.search(r'with\s*\(\s*([^)]+)\s*\)\s*:', full_content, re.DOTALL)
                    if match:
                        contexts = match.group(1)
                        
                        # Split contexts (simplified - assumes no nested parentheses in contexts)
                        context_list = []
                        current = []
                        depth = 0
                        
                        for char in contexts:
                            if char in '([':
                                depth += 1
                            elif char in ')]':
                                depth -= 1
                            elif char == ',' and depth == 0:
                                context_list.append(''.join(current).strip())
                                current = []
                                continue
                            current.append(char)
                        
                        if current:
                            context_list.append(''.join(current).strip())
                        
                        # Build nested with statements
                        new_lines = []
                        for idx, ctx in enumerate(context_list):
                            new_lines.append(f"{indent_str}{' ' * (idx * 4)}with {ctx}:\n")
                        
                        # Replace the original lines
                        lines[start_line:j+1] = new_lines
                        modified = True
                        i = start_line + len(new_lines)
                        continue
            
            i += 1
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False


def main():
    """Main function to fix all Python files."""
    fixed_files = []
    
    # Get all Python files with SIM117 errors
    for root, dirs, files in os.walk('src'):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if process_file_with_ast(file_path):
                    fixed_files.append(file_path)
    
    for root, dirs, files in os.walk('test'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if process_file_with_ast(file_path):
                    fixed_files.append(file_path)
    
    print(f"Fixed {len(fixed_files)} files:")
    for f in fixed_files:
        print(f"  - {f}")


if __name__ == "__main__":
    main()