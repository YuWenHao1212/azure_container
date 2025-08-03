#!/usr/bin/env python3
"""Script to fix ALL Ruff errors systematically."""

import re
import subprocess


def run_ruff_fix(select=None, fix_type="--fix"):
    """Run ruff fix with specific parameters."""
    cmd = ["ruff", "check", ".", "--line-length=120", fix_type]
    if select:
        cmd.extend(["--select", select])

    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    return result


def fix_unicode_errors():
    """Fix RUF001, RUF002, RUF003 - Unicode character issues."""
    print("Fixing Unicode character errors...")

    # Get files with Unicode errors
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120", "--select=RUF001,RUF002,RUF003"],  # noqa: S607
        capture_output=True,
        text=True
    )

    files_to_fix = {}
    for line in result.stderr.splitlines():
        if ".py:" in line and ("RUF001" in line or "RUF002" in line or "RUF003" in line):
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])

                if file_path not in files_to_fix:
                    files_to_fix[file_path] = []
                files_to_fix[file_path].append((line_num, line))

    # Unicode replacements
    unicode_replacements = {
        '，': ',',  # Fullwidth comma
        '。': '.',  # Fullwidth period
        '：': ':',  # Fullwidth colon
        '；': ';',  # Fullwidth semicolon
        '！': '!',  # Fullwidth exclamation
        '？': '?',  # Fullwidth question mark
        '（': '(',  # Fullwidth left paren
        '）': ')',  # Fullwidth right paren
        '「': '"',  # Left corner bracket
        '」': '"',  # Right corner bracket
        '『': "'",  # Left white corner bracket
        '』': "'",  # Right white corner bracket
        '【': '[',  # Left black lenticular bracket
        '】': ']',  # Right black lenticular bracket
        '《': '<',  # Left double angle bracket
        '》': '>',  # Right double angle bracket
        '、': ',',  # Ideographic comma
        '～': '~',  # Fullwidth tilde
        '－': '-',  # Fullwidth hyphen
        '＿': '_',  # Fullwidth underscore
        '＝': '=',  # Fullwidth equals
        '＋': '+',  # Fullwidth plus
        '＊': '*',  # Fullwidth asterisk
        '／': '/',  # Fullwidth slash
        '＼': '\\', # Fullwidth backslash
        '｜': '|',  # Fullwidth vertical bar
        '＆': '&',  # Fullwidth ampersand
        '＃': '#',  # Fullwidth hash
        '＄': '$',  # Fullwidth dollar
        '％': '%',  # Fullwidth percent
        '＠': '@',  # Fullwidth at
        '＾': '^',  # Fullwidth caret
        '｛': '{',  # Fullwidth left brace
        '｝': '}',  # Fullwidth right brace
        '［': '[',  # Fullwidth left bracket
        '］': ']',  # Fullwidth right bracket
        '＜': '<',  # Fullwidth less than
        '＞': '>',  # Fullwidth greater than
    }

    for file_path, _errors in files_to_fix.items():
        print(f"  Fixing Unicode in {file_path}...")
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            # Replace all Unicode characters
            for old, new in unicode_replacements.items():
                content = content.replace(old, new)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            print(f"    Error: {e}")


def fix_long_lines_smart():
    """Fix E501 errors with smarter line breaking."""
    print("\nFixing long lines (E501)...")

    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120", "--select=E501"],  # noqa: S607
        capture_output=True,
        text=True
    )

    files_to_fix = {}
    for line in result.stderr.splitlines():
        if ".py:" in line and "E501" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])

                # Skip docs files with URLs
                if "docs/" in file_path or ".md" in file_path:
                    continue

                if file_path not in files_to_fix:
                    files_to_fix[file_path] = []
                files_to_fix[file_path].append(line_num)

    for file_path, line_nums in files_to_fix.items():
        print(f"  Fixing {file_path} ({len(line_nums)} long lines)...")
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()

            # Process in reverse order
            for line_num in sorted(line_nums, reverse=True):
                line_idx = line_num - 1
                if line_idx < len(lines):
                    line = lines[line_idx]

                    # Skip URLs and file paths
                    if "http://" in line or "https://" in line or ".md" in line:
                        continue

                    # Handle different cases
                    indent = len(line) - len(line.lstrip())
                    indent_str = " " * indent

                    # Case 1: Long strings in dictionaries or JSON
                    if '": "' in line and len(line) > 120:
                        # Split at the colon
                        parts = line.split('": "', 1)
                        if len(parts) == 2:
                            key_part = parts[0] + '": '
                            value_part = '"' + parts[1].rstrip()

                            if len(value_part) > 80:
                                # Find a good break point
                                break_pos = 80
                                for sep in ['. ', ', ', ' - ', ' and ', ' or ', ' with ', ' for ', ' in ']:
                                    pos = value_part.find(sep, 40, 100)
                                    if pos > 0:
                                        break_pos = pos + len(sep)
                                        break

                                line1 = key_part + value_part[:break_pos] + '"\n'
                                line2 = indent_str + '    "' + value_part[break_pos:-1] + '\n'
                                lines[line_idx] = line1
                                lines.insert(line_idx + 1, line2)
                                continue

                    # Case 2: Long function calls with multiple parameters
                    if "(" in line and ")" in line and ", " in line:
                        # Extract function call
                        match = re.match(r'(\s*)(.*?)\((.*)\)(.*)', line)
                        if match:
                            indent_part = match.group(1)
                            func_part = match.group(2)
                            params_part = match.group(3)
                            end_part = match.group(4)

                            if len(params_part) > 60:
                                # Split parameters
                                params = params_part.split(", ")
                                if len(params) > 1:
                                    new_lines = [f"{indent_part}{func_part}(\n"]
                                    param_indent = " " * (indent + 4)

                                    for i, param in enumerate(params):
                                        if i < len(params) - 1:
                                            new_lines.append(f"{param_indent}{param},\n")
                                        else:
                                            new_lines.append(f"{param_indent}{param}\n")

                                    new_lines.append(f"{indent_str}){end_part}")

                                    # Replace the line
                                    lines[line_idx] = new_lines[0]
                                    for i, new_line in enumerate(new_lines[1:]):
                                        lines.insert(line_idx + i + 1, new_line)
                                    continue

                    # Case 3: Long with statements
                    if "with patch(" in line and len(line) > 120:
                        # Split after 'return_value='
                        if "return_value=" in line:
                            parts = line.split("return_value=", 1)
                            if len(parts) == 2:
                                lines[line_idx] = parts[0] + "\n"
                                lines.insert(line_idx + 1, indent_str + "    return_value=" + parts[1])
                                continue

                    # Case 4: Long assert statements
                    if line.strip().startswith("assert ") and " == " in line:
                        parts = line.split(" == ", 1)
                        if len(parts) == 2:
                            lines[line_idx] = parts[0] + " == \\\n"
                            lines.insert(line_idx + 1, indent_str + "    " + parts[1])
                            continue

                    # Case 5: Long decorators
                    if line.strip().startswith("@") and len(line) > 120:
                        # Split at commas
                        if ", " in line:
                            parts = line.split(", ")
                            if len(parts) > 1:
                                lines[line_idx] = parts[0] + ",\n"
                                for i, part in enumerate(parts[1:]):
                                    if i < len(parts) - 2:
                                        lines.insert(line_idx + i + 1, indent_str + "    " + part + ",\n")
                                    else:
                                        lines.insert(line_idx + i + 1, indent_str + "    " + part)
                                continue

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        except Exception as e:
            print(f"    Error: {e}")


def fix_nested_with_statements():
    """Manually fix SIM117 errors."""
    print("\nFixing nested with statements (SIM117)...")

    # This is complex, so we'll do targeted fixes for common patterns
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120", "--select=SIM117"],  # noqa: S607
        capture_output=True,
        text=True
    )

    files_to_fix = {}
    for line in result.stderr.splitlines():
        if ".py:" in line and "SIM117" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])

                if file_path not in files_to_fix:
                    files_to_fix[file_path] = []
                files_to_fix[file_path].append(line_num)

    print(f"  Found {len(files_to_fix)} files with nested with statements")
    print("  Note: These require manual fixing due to complexity")


def fix_security_issues():
    """Fix security-related issues."""
    print("\nFixing security issues...")

    # S110 - try-except-pass
    print("  Fixing S110 (try-except-pass)...")
    run_ruff_fix("S110", "--fix")

    # S311 - random usage
    print("  Fixing S311 (random usage)...")
    # This typically requires switching to secrets module

    # S603, S607 - subprocess issues
    print("  Note: S603/S607 subprocess issues require manual review")


def main():
    """Main function to fix all Ruff errors."""
    print("=== Fixing ALL Ruff Errors ===\n")

    # Step 1: Apply all safe fixes first
    print("Step 1: Applying all safe fixes...")
    result = run_ruff_fix(fix_type="--fix")

    # Step 2: Apply unsafe fixes
    print("\nStep 2: Applying unsafe fixes...")
    result = run_ruff_fix(fix_type="--fix --unsafe-fixes")

    # Step 3: Fix Unicode issues
    fix_unicode_errors()

    # Step 4: Fix long lines
    fix_long_lines_smart()

    # Step 5: Fix security issues
    fix_security_issues()

    # Step 6: Apply fixes again
    print("\nStep 6: Final fix pass...")
    run_ruff_fix(fix_type="--fix")
    run_ruff_fix(fix_type="--fix --unsafe-fixes")

    # Show remaining errors
    print("\n" + "="*60)
    print("FINAL CHECK:")
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120"],  # noqa: S607
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ ALL CHECKS PASSED!")
    else:
        # Count remaining errors
        error_count = 0
        error_types = {}

        for line in result.stderr.splitlines():
            if ".py:" in line:
                error_count += 1
                # Extract error code
                match = re.search(r'\b([A-Z]\d{3,4})\b', line)
                if match:
                    error_code = match.group(1)
                    error_types[error_code] = error_types.get(error_code, 0) + 1

        print(f"\n❌ Remaining errors: {error_count}")
        print("\nError breakdown:")
        for code, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {code}: {count}")

        # Show sample errors
        print("\nSample remaining errors:")
        shown = 0
        for line in result.stderr.splitlines():
            if ".py:" in line and shown < 10:
                print(f"  {line}")
                shown += 1


if __name__ == "__main__":
    main()
