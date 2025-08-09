#!/usr/bin/env python3
"""
Ruff Checker Script for Azure Container Project
Provides automated Python code quality checking with statistical reporting
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# 嘗試匯入輸出格式化器
try:
    from output_formatter import RuffOutputFormatter
    FORMATTER_AVAILABLE = True
except ImportError:
    FORMATTER_AVAILABLE = False


class RuffChecker:
    def __init__(self, line_length=120):
        self.line_length = line_length
        self.results_file = "/tmp/claude_last_ruff_check.txt"

    def get_modified_python_files(self):
        """Get list of modified Python files from git diff"""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            files = [
                f for f in result.stdout.strip().split('\n')
                if f.endswith('.py') and f
            ]
            return files
        except subprocess.CalledProcessError:
            return []

    def get_all_python_files(self):
        """Get all Python files in src/ and test/ directories"""
        files = []
        for directory in ['src', 'test']:
            if os.path.exists(directory):
                for py_file in Path(directory).rglob('*.py'):
                    files.append(str(py_file))

        # Also check root level Python files
        for py_file in Path('.').glob('*.py'):
            files.append(str(py_file))

        return files

    def run_ruff_check(self, files):
        """Run ruff check on specified files"""
        if not files:
            return "", "", 0

        cmd = ["ruff", "check"] + files + [f"--line-length={self.line_length}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.stderr, e.returncode

    def run_ruff_fix(self, files):
        """Run ruff check --fix on specified files"""
        if not files:
            return "", "", 0

        cmd = ["ruff", "check", "--fix"] + files + [f"--line-length={self.line_length}"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.stderr, e.returncode

    def parse_ruff_output(self, output):
        """Parse ruff output and extract error statistics"""
        if not output:
            return {}, 0, 0

        error_counts = defaultdict(int)
        total_errors = 0
        fixable_errors = 0

        # Count total errors from "Found X errors" line
        found_match = re.search(r'Found (\d+) errors?\.', output)
        if found_match:
            total_errors = int(found_match.group(1))

        # Count fixable errors
        fixable_match = re.search(r'\[?\*?\]?\s*(\d+) fixable', output)
        if fixable_match:
            fixable_errors = int(fixable_match.group(1))

        # Extract individual error types from each error line
        lines = output.split('\n')
        for line in lines:
            # Look for error code patterns like "F401 [*]" or "W292"
            error_match = re.search(r'(\w+\d+)(?:\s*\[?\*?\]?)?', line)
            if error_match:
                error_code = error_match.group(1)
                # Only count common ruff error codes
                if re.match(r'^[FWEINCUPTSIM]\d+$', error_code):
                    error_counts[error_code] += 1

        return dict(error_counts), total_errors, fixable_errors

    def generate_report(self, files, error_counts, total_errors, fixable_errors):
        """Generate formatted report with enhanced formatting"""
        # 準備統計資料
        stats = {
            'files_checked': len(files),
            'total_errors': total_errors,
            'auto_fixable': fixable_errors
        }
        
        # 如果有輸出格式化器，使用增強格式
        if FORMATTER_AVAILABLE:
            try:
                formatter = RuffOutputFormatter(theme='subagent')
                
                if error_counts:
                    return formatter.format_complete_report(
                        "Ruff 程式碼品質檢查結果",
                        stats,
                        error_counts,
                        files
                    )
                else:
                    return formatter.format_complete_report(
                        "Ruff 程式碼品質檢查結果",
                        stats
                    )
            except Exception:
                # 如果格式化器出錯，回退到原始格式
                pass
        
        # 回退到原始格式
        timestamp = datetime.now().strftime("%H:%M:%S")

        report_lines = [
            "═══════════════════════════════════════════════════════════════",
            f"⚠️  Ruff Check Results - {timestamp}",
            "═══════════════════════════════════════════════════════════════",
            "📊 Statistics:",
            f"   • Files checked: {len(files)}",
            f"   • Total errors: {total_errors}",
            f"   • Auto-fixable: {fixable_errors}",
            ""
        ]

        if error_counts:
            report_lines.append("📋 Error breakdown:")
            for error_type, count in sorted(error_counts.items()):
                report_lines.append(f"   • {error_type}: {count}")
        else:
            report_lines.append("🎉 No errors found!")

        report_lines.extend([
            "───────────────────────────────────────────────────────────────",
            f"💡 Quick fix: ruff check --fix {' '.join(files)} --line-length={self.line_length}" if files else "💡 No files to fix",
            f"📝 View details: ruff check {' '.join(files)} --line-length={self.line_length}" if files else "📝 No files to check",
            "═══════════════════════════════════════════════════════════════",
            ""
        ])

        return "\n".join(report_lines)

    def save_results(self, report):
        """Save results to temp file for persistence"""
        try:
            with open(self.results_file, 'w') as f:
                f.write(report)
        except Exception as e:
            print(f"Warning: Could not save results to {self.results_file}: {e}")

    def check_files(self, files=None, auto_fix=True):
        """Main checking function"""
        if files is None:
            # First try modified files, then all files if none modified
            files = self.get_modified_python_files()
            if not files:
                files = self.get_all_python_files()

        if not files:
            report = self.generate_report([], {}, 0, 0)
            print(report)
            self.save_results(report)
            return

        # Run initial check
        stdout, stderr, returncode = self.run_ruff_check(files)
        error_counts, total_errors, fixable_errors = self.parse_ruff_output(stdout)

        # Apply safe fixes if requested and errors found
        if auto_fix and fixable_errors > 0:
            fix_stdout, fix_stderr, fix_returncode = self.run_ruff_fix(files)

            # Re-check after fixes
            stdout, stderr, returncode = self.run_ruff_check(files)
            error_counts, total_errors, fixable_errors = self.parse_ruff_output(stdout)

        # Generate and display report
        report = self.generate_report(files, error_counts, total_errors, fixable_errors)
        print(report)
        self.save_results(report)

        return total_errors == 0


def main():
    checker = RuffChecker()

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = None

    success = checker.check_files(files)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
