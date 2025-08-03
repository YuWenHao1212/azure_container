#!/usr/bin/env python3
"""Script to fix common Ruff errors systematically."""

import re
import subprocess


def fix_sim117_errors():
    """Fix SIM117 errors by combining nested with statements."""
    print("Fixing SIM117 errors...")

    # Get all Python files with SIM117 errors
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120", "--select=SIM117"],  # noqa: S607
        capture_output=True,
        text=True
    )

    files_to_fix = set()
    for line in result.stderr.splitlines():
        if ".py:" in line and "SIM117" in line:
            file_path = line.split(":")[0]
            files_to_fix.add(file_path)

    print(f"Found {len(files_to_fix)} files with SIM117 errors")

    # Apply unsafe fixes for SIM117
    for file_path in files_to_fix:
        print(f"  Fixing {file_path}...")
        subprocess.run(  # noqa: S603
            ["ruff", "check", file_path, "--fix", "--unsafe-fixes", "--select=SIM117"],  # noqa: S607
            capture_output=True
        )


def fix_long_lines():
    """Fix E501 errors by breaking long lines."""
    print("\nFixing E501 (long line) errors...")

    # Get all files with E501 errors
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120", "--select=E501"],  # noqa: S607
        capture_output=True,
        text=True
    )

    errors = []
    for line in result.stderr.splitlines():
        if ".py:" in line and "E501" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                line_num = int(parts[1])
                errors.append((file_path, line_num))

    print(f"Found {len(errors)} long lines to fix")

    # Group errors by file
    errors_by_file = {}
    for file_path, line_num in errors:
        if file_path not in errors_by_file:
            errors_by_file[file_path] = []
        errors_by_file[file_path].append(line_num)

    # Fix each file
    for file_path, line_nums in errors_by_file.items():
        print(f"  Fixing {file_path} ({len(line_nums)} lines)...")

        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()

            # Sort line numbers in reverse to avoid offset issues
            for line_num in sorted(line_nums, reverse=True):
                line_idx = line_num - 1
                if line_idx < len(lines):
                    line = lines[line_idx]

                    # Skip comment lines with URLs or file paths
                    if "http" in line or "docs/" in line or ".md" in line:
                        continue

                    # Handle different types of long lines
                    if '"' in line and len(line) > 120:
                        # Try to break long strings
                        lines[line_idx] = break_long_string(line)
                    elif "patch(" in line and len(line) > 120:
                        # Break long patch statements
                        lines[line_idx] = break_long_patch(line)
                    elif "assert" in line and len(line) > 120:
                        # Break long assert statements
                        lines[line_idx] = break_long_assert(line)

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

        except Exception as e:
            print(f"    Error fixing {file_path}: {e}")


def break_long_string(line):
    """Break a long string into multiple lines."""
    indent = len(line) - len(line.lstrip())

    # If it's a multiline string, leave it as is
    if '"""' in line or "'''" in line:
        return line

    # Try to find a good breaking point
    if '": "' in line:
        # JSON-like structure
        parts = line.split('": "', 1)
        if len(parts) == 2 and len(parts[1]) > 60:
            # Break the value part
            value = parts[1].rstrip('",\n')
            if " " in value:
                # Find a good break point
                words = value.split(" ")
                first_part = []
                current_len = len(parts[0]) + 4  # account for ": "

                for word in words:
                    if current_len + len(word) + 1 > 100:
                        break
                    first_part.append(word)
                    current_len += len(word) + 1

                if first_part and len(first_part) < len(words):
                    remaining = " ".join(words[len(first_part):])
                    return (f'{parts[0]}": "{" ".join(first_part)} "\n' +
                           f'{" " * (indent + 4)}"{remaining}",\n')

    return line


def break_long_patch(line):
    """Break a long patch statement."""
    indent = len(line) - len(line.lstrip())

    if "patch(" in line and "return_value=" in line:
        # Extract the parts
        match = re.match(r'(\s*with patch\([\'"])(.*?)([\'"],\s*return_value=)(.*?)(\):?\s*)$', line)
        if match:
            prefix = match.group(1)
            path = match.group(2)
            middle = match.group(3)
            value = match.group(4)
            suffix = match.group(5)

            # Break after the path
            return (f"{prefix}{path}{middle[:-16]}\n" +
                   f"{' ' * (indent + 13)}return_value={value}{suffix}")

    return line


def break_long_assert(line):
    """Break a long assert statement."""
    indent = len(line) - len(line.lstrip())

    if "assert" in line and " == " in line:
        parts = line.split(" == ", 1)
        if len(parts) == 2:
            return (f"{parts[0]} == \\\n" +
                   f"{' ' * (indent + 4)}{parts[1]}")

    return line


def main():
    """Main function."""
    print("Fixing Ruff errors...")

    # First, apply all safe fixes
    print("\nApplying safe fixes...")
    subprocess.run(["ruff", "check", ".", "--fix", "--line-length=120"])  # noqa: S607

    # Then fix SIM117 errors
    fix_sim117_errors()

    # Finally, try to fix long lines
    fix_long_lines()

    # Show remaining errors
    print("\n" + "="*60)
    print("Remaining errors:")
    result = subprocess.run(  # noqa: S603
        ["ruff", "check", ".", "--line-length=120"],  # noqa: S607
        capture_output=True,
        text=True
    )

    error_count = 0
    for line in result.stderr.splitlines():
        if ".py:" in line:
            error_count += 1

    print(f"\nTotal remaining errors: {error_count}")


if __name__ == "__main__":
    main()
