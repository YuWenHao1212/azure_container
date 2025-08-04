#!/usr/bin/env python3
"""
Collect and format all test logs from the latest test run
"""

import os
import re
from datetime import datetime
from pathlib import Path


def parse_test_log(log_content):
    """Parse pytest output to extract individual test results"""
    tests = []

    # Find all test lines (format: test_file.py::TestClass::test_method PASSED/FAILED)
    test_pattern = r'(test/.*?\.py::[^\s]+)\s+(PASSED|FAILED|SKIPPED)\s*\[\s*(\d+)%\]'
    matches = re.findall(test_pattern, log_content)

    for match in matches:
        test_path, status, progress = match
        tests.append({
            'path': test_path,
            'status': status,
            'progress': progress
        })

    # Extract summary
    summary_pattern = r'=+\s*(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+skipped)?(?:,\s*(\d+)\s+warnings)?\s+in\s+([\d.]+)s'
    summary_match = re.search(summary_pattern, log_content)

    summary = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'warnings': 0,
        'duration': 0
    }

    if summary_match:
        summary['passed'] = int(summary_match.group(1) or 0)
        summary['failed'] = int(summary_match.group(2) or 0)
        summary['skipped'] = int(summary_match.group(3) or 0)
        summary['warnings'] = int(summary_match.group(4) or 0)
        summary['duration'] = float(summary_match.group(5) or 0)

    return tests, summary

def format_test_results(suite_name, tests, summary):
    """Format test results in markdown"""
    output = f"\n## {suite_name}\n\n"
    output += f"**Summary**: {summary['passed']} passed"

    if summary['failed'] > 0:
        output += f", {summary['failed']} failed"
    if summary['skipped'] > 0:
        output += f", {summary['skipped']} skipped"
    if summary['warnings'] > 0:
        output += f", {summary['warnings']} warnings"

    output += f" in {summary['duration']:.2f}s\n\n"

    if tests:
        output += "### Test Results:\n\n"
        output += "| Test | Status | Progress |\n"
        output += "|------|--------|----------|\n"

        for test in tests:
            status_icon = "✅" if test['status'] == "PASSED" else "❌" if test['status'] == "FAILED" else "⏭️"
            output += f"| `{test['path']}` | {status_icon} {test['status']} | {test['progress']}% |\n"

    return output

def main():
    # Log files to process
    log_files = [
        ('Unit Tests - Health Check', '/tmp/unit_health_output.log'),  # noqa: S108
        ('Unit Tests - Keyword Extraction', '/tmp/unit_keyword_extraction_output.log'),  # noqa: S108
        ('Unit Tests - Keyword Extraction Extended', '/tmp/unit_keyword_extended_output.log'),  # noqa: S108
        ('Unit Tests - Language Detection', '/tmp/unit_language_detection_output.log'),  # noqa: S108
        ('Unit Tests - Prompt Manager', '/tmp/unit_prompt_manager_output.log'),  # noqa: S108
        ('Integration Tests - Keyword Language', '/tmp/integration_keyword_language_output.log'),  # noqa: S108
        ('Integration Tests - Health Check', '/tmp/integration_health_output.log'),  # noqa: S108
        ('Integration Tests - Azure OpenAI', '/tmp/integration_azure_openai_output.log'),  # noqa: S108
        ('Performance Tests - Keyword Extraction', '/tmp/performance_keyword_output.log')  # noqa: S108
    ]

    # Output file
    output_file = Path('test/reports/all_tests_detailed_log_20250731.md')

    # Header
    content = f"""# Complete Test Logs - Azure Container API

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Test Suite Overview

This document contains detailed logs from all test suites executed during the complete test run.

---
"""

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_warnings = 0

    # Process each log file
    for suite_name, log_file in log_files:
        if os.path.exists(log_file):
            with open(log_file) as f:
                log_content = f.read()

            tests, summary = parse_test_log(log_content)
            content += format_test_results(suite_name, tests, summary)

            # Update totals
            total_tests += len(tests)
            total_passed += summary['passed']
            total_failed += summary['failed']
            total_warnings += summary['warnings']

            # Add raw log in collapsible section
            content += "\n<details>\n<summary>View Raw Log</summary>\n\n```\n"
            content += log_content[:5000]  # Limit to first 5000 chars to avoid huge file
            if len(log_content) > 5000:
                content += f"\n... (truncated, total length: {len(log_content)} characters)\n"
            content += "```\n</details>\n\n---\n"
        else:
            content += f"\n## {suite_name}\n\n"
            content += f"**Error**: Log file not found at `{log_file}`\n\n---\n"

    # Add summary at the end
    content += f"""
## Overall Summary

- **Total Test Cases**: {total_tests}
- **Total Passed**: {total_passed} ✅
- **Total Failed**: {total_failed} ❌
- **Total Warnings**: {total_warnings} ⚠️

### Test Coverage by Module:

1. **Health Check Module**: Unit (9) + Integration (1) = 10 tests
2. **Keyword Extraction Module**: Unit (10 + 16) + Integration (14) = 40 tests
3. **Language Detection Module**: Unit (29) = 29 tests
4. **Prompt Manager Module**: Unit (24) = 24 tests
5. **Azure OpenAI Integration**: Integration tests
6. **Performance Tests**: Keyword extraction performance benchmarks

---

*Note: This report was automatically generated from test logs located in `/tmp/` directory.*
"""

    # Write output
    with open(output_file, 'w') as f:
        f.write(content)

    print(f"✅ Test logs collected and saved to: {output_file}")
    print(f"📊 Summary: {total_tests} tests, {total_passed} passed, {total_failed} failed")

if __name__ == "__main__":
    main()
