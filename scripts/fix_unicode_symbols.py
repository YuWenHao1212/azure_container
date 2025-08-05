#!/usr/bin/env python3
"""Fix Unicode fullwidth symbols that cause RUF001 errors."""

import os
import re
from pathlib import Path

# Mapping of fullwidth symbols to their ASCII equivalents
REPLACEMENTS = {
    '，': ',',  # Fullwidth comma
    '。': '.',  # Fullwidth period
    '！': '!',  # Fullwidth exclamation
    '？': '?',  # Fullwidth question mark
    '：': ':',  # Fullwidth colon
    '；': ';',  # Fullwidth semicolon
    '（': '(',  # Fullwidth left parenthesis
    '）': ')',  # Fullwidth right parenthesis
    '「': '"',  # Left corner bracket
    '」': '"',  # Right corner bracket
    '『': '"',  # Left white corner bracket
    '』': '"',  # Right white corner bracket
    '【': '[',  # Left black lenticular bracket
    '】': ']',  # Right black lenticular bracket
    '〈': '<',  # Left angle bracket
    '〉': '>',  # Right angle bracket
    '《': '<<', # Left double angle bracket
    '》': '>>', # Right double angle bracket
    '、': ',',  # Ideographic comma
    '～': '~',  # Wave dash
    '－': '-',  # Fullwidth hyphen
    '＿': '_',  # Fullwidth underscore
    '＝': '=',  # Fullwidth equals
    '＋': '+',  # Fullwidth plus
    '＊': '*',  # Fullwidth asterisk
    '／': '/',  # Fullwidth slash
    '＼': '\\', # Fullwidth backslash
    '｜': '|',  # Fullwidth vertical bar
    '＃': '#',  # Fullwidth hash
    '＄': '$',  # Fullwidth dollar
    '％': '%',  # Fullwidth percent
    '＆': '&',  # Fullwidth ampersand
    '＠': '@',  # Fullwidth at
    '＾': '^',  # Fullwidth caret
    '｛': '{',  # Fullwidth left brace
    '｝': '}',  # Fullwidth right brace
    '［': '[',  # Fullwidth left bracket
    '］': ']',  # Fullwidth right bracket
}

def fix_file(file_path):
    """Fix fullwidth symbols in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Only replace in string literals (between quotes)
        # This regex finds strings but keeps track of whether we're in a string
        def replace_in_strings(match):
            string_content = match.group(0)
            quote_char = string_content[0]
            inner_content = string_content[1:-1]
            
            # Replace fullwidth symbols
            for full, half in REPLACEMENTS.items():
                inner_content = inner_content.replace(full, half)
            
            return quote_char + inner_content + quote_char
        
        # Match single and double quoted strings (including triple quotes)
        # Also handle raw strings and f-strings
        patterns = [
            r'"""[\s\S]*?"""',  # Triple double quotes
            r"'''[\s\S]*?'''",  # Triple single quotes
            r'"[^"\\]*(?:\\.[^"\\]*)*"',  # Double quotes
            r"'[^'\\]*(?:\\.[^'\\]*)*'",  # Single quotes
            r'f"""[\s\S]*?"""',  # f-string triple double
            r"f'''[\s\S]*?'''",  # f-string triple single
            r'f"[^"\\]*(?:\\.[^"\\]*)*"',  # f-string double
            r"f'[^'\\]*(?:\\.[^'\\]*)*'",  # f-string single
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, replace_in_strings, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Fix fullwidth symbols in all Python files."""
    project_root = Path(__file__).parent.parent
    
    # Find all Python files in src/ and test/
    fixed_count = 0
    total_count = 0
    
    for directory in ['src', 'test']:
        dir_path = project_root / directory
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob('*.py'):
            total_count += 1
            if fix_file(py_file):
                fixed_count += 1
                print(f"Fixed: {py_file.relative_to(project_root)}")
    
    print(f"\nSummary: Fixed {fixed_count} out of {total_count} files")


if __name__ == "__main__":
    main()