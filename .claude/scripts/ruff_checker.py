#!/usr/bin/env python3
"""
Simple Ruff Checker for Sub Agent Use
Provides comprehensive Python code quality analysis with statistical reporting
"""

import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class RuffChecker:
    def __init__(self, line_length=120):
        self.line_length = line_length
        self.results_file = "/tmp/claude_last_ruff_check.txt"

    def run_ruff_check(self, fix=False, paths=None):
        """Run ruff check with optional fix and specific paths"""
        if paths is None:
            paths = ["src/", "test/"]

        cmd = ["ruff", "check", *paths, f"--line-length={self.line_length}"]
        if fix:
            cmd.append("--fix")

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                cwd=Path.cwd()
            )
            return result
        except FileNotFoundError:
            return None

    def parse_ruff_output(self, output):
        """Parse ruff output to extract statistics"""
        if not output:
            return {"files": 0, "errors": 0, "by_type": {}, "details": []}

        lines = output.strip().split('\n')
        files = set()
        errors_by_type = defaultdict(int)
        details = []

        error_count = 0
        for line in lines:
            if ':' in line and any(x in line for x in ['E', 'W', 'F', 'N', 'C', 'R', 'S']):
                error_count += 1

                # Extract file path
                if line.count(':') >= 2:
                    file_path = line.split(':')[0]
                    files.add(file_path)

                # Extract error code
                for part in line.split():
                    if len(part) > 2 and part[0].isalpha() and part[1:].replace('-', '').isdigit():
                        error_type = part[:3] if len(part) >= 3 else part
                        errors_by_type[error_type] += 1
                        break

                details.append(line)

        return {
            "files": len(files),
            "errors": error_count,
            "by_type": dict(errors_by_type),
            "details": details
        }

    def generate_report(self, check_result, fix_result=None):
        """Generate comprehensive analysis report"""
        if not check_result:
            return "❌ Error: ruff command not found"

        report_lines = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Header
        report_lines.extend([
            "═══════════════════════════════════════════════════════════════",
            f"⚠️  Ruff Check Results - {timestamp.split()[1]}",
            "═══════════════════════════════════════════════════════════════"
        ])

        # Parse results
        stats = self.parse_ruff_output(check_result.stderr)

        if check_result.returncode == 0:
            report_lines.extend([
                "🎉 程式碼品質檢查通過！",
                "",
                "📊 統計數據:",
                f"   • 檢查完成: {timestamp}",
                "   • 掃描檔案: 完整專案",
                "   • 發現問題: 0 個",
                "   • 程式碼狀態: ✅ 優秀"
            ])
        else:
            # Statistics
            report_lines.extend([
                "📊 統計數據:",
                f"   • 檢查檔案: {stats['files']}",
                f"   • 總錯誤數: {stats['errors']}",
                f"   • 自動修復: {len(fix_result.stdout.split('Fixed')) - 1 if fix_result else 0}",
                f"   • 剩餘問題: {stats['errors'] - (len(fix_result.stdout.split('Fixed')) - 1 if fix_result else 0)}"
            ])

            # Error breakdown
            if stats['by_type']:
                report_lines.extend([
                    "",
                    "📋 錯誤分類:"
                ])
                for error_type, count in sorted(stats['by_type'].items(), key=lambda x: x[1], reverse=True):
                    report_lines.append(f"   • {count:2d}  {error_type}")

            # Detailed errors (first 20)
            if stats['details']:
                report_lines.extend([
                    "",
                    "⚠️  剩餘問題詳情:"
                ])
                for detail in stats['details'][:20]:
                    report_lines.append(detail)

                if len(stats['details']) > 20:
                    report_lines.append(f"... and {len(stats['details']) - 20} more issues")

        report_lines.extend([
            "═══════════════════════════════════════════════════════════════",
            ""
        ])

        return "\n".join(report_lines)

    def save_results(self, report):
        """Save results to file"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                f.write(report)
            return True
        except Exception as e:
            print(f"Warning: Could not save results to {self.results_file}: {e}")
            return False

    def run_analysis(self, fix=True):
        """Run complete ruff analysis"""
        print("🔍 Running Ruff code quality analysis...")

        # Initial check
        check_result = self.run_ruff_check(fix=False)
        fix_result = None

        # Auto-fix if requested and issues found
        if fix and check_result and check_result.returncode != 0:
            print("🔧 Auto-fixing issues...")
            fix_result = self.run_ruff_check(fix=True)
            # Re-check after fixes
            check_result = self.run_ruff_check(fix=False)

        # Generate report
        report = self.generate_report(check_result, fix_result)

        # Save and display
        self.save_results(report)
        print(report)

        # Display clickable file path for Claude Code CLI
        print(f"📁 詳細報告已儲存: {self.results_file}")
        print(f"💡 快速查看: cat {self.results_file}")

        return check_result.returncode == 0 if check_result else False


def main():
    """Main entry point"""
    checker = RuffChecker()

    # Check if fix mode requested
    fix_mode = "--fix" in sys.argv or "-f" in sys.argv

    success = checker.run_analysis(fix=fix_mode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
