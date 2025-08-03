#!/usr/bin/env python3
"""Check current Ruff errors in src/ and test/ directories."""

import subprocess
import re
from collections import defaultdict

def main():
    print("=== Checking Current Ruff Errors ===\n")
    
    # Run Ruff check
    result = subprocess.run(
        ["ruff", "check", "src/", "test/", "--line-length=120"],
        capture_output=True,
        text=True
    )
    
    # Parse error output
    error_counts = defaultdict(int)
    error_details = defaultdict(list)
    
    for line in result.stdout.splitlines():
        # Match error pattern: filename:line:col: CODE message
        match = re.match(r'^(.*?):(\d+):(\d+): ([A-Z]\d+) (.*)$', line)
        if match:
            filename, line_num, col, error_code, message = match.groups()
            error_counts[error_code] += 1
            error_details[error_code].append({
                'file': filename,
                'line': line_num,
                'col': col,
                'message': message
            })
    
    # Display summary
    total_errors = sum(error_counts.values())
    print(f"Total errors found: {total_errors}")
    print("\nError breakdown:")
    for code, count in sorted(error_counts.items(), key=lambda x: -x[1]):
        print(f"  {code}: {count}")
    
    # Show details for critical errors
    critical_codes = ['F821', 'E999', 'SyntaxError']
    for code in critical_codes:
        if code in error_details:
            print(f"\n{code} errors:")
            for error in error_details[code][:5]:  # Show first 5
                print(f"  {error['file']}:{error['line']} - {error['message']}")
            if len(error_details[code]) > 5:
                print(f"  ... and {len(error_details[code]) - 5} more")
    
    # Also check for syntax errors specifically
    print("\n=== Checking for Syntax Errors ===")
    syntax_result = subprocess.run(
        ["python", "-m", "py_compile", "test/e2e/test_index_calculation_v2_e2e.py"],
        capture_output=True,
        text=True
    )
    
    if syntax_result.returncode != 0:
        print("❌ Syntax errors found:")
        print(syntax_result.stderr)
    else:
        print("✅ No syntax errors in test_index_calculation_v2_e2e.py")
    
    return total_errors

if __name__ == "__main__":
    main()