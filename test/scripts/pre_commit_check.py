#!/usr/bin/env python3
"""
Pre-commit validation script - Python version
直接執行測試而不需要調用多個 shell 腳本
"""
# ruff: noqa: S603  # subprocess calls are safe in this test script
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Colors for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[0;33m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

@dataclass
class TestResult:
    """Store test result information"""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    failed_tests: list[str] = None

    def __post_init__(self):
        if self.failed_tests is None:
            self.failed_tests = []

    @property
    def total(self):
        return self.passed + self.failed + self.skipped

    @property
    def status(self):
        return "✅" if self.failed == 0 else "❌"

class PreCommitValidator:
    """Main pre-commit validation class"""

    def __init__(self):
        self.start_time = time.time()
        self.results = {}
        self.overall_failed = False

    def run_ruff_check(self) -> TestResult:
        """Run Ruff code quality check"""
        print(f"{Colors.BLUE}📝 Step 1/5: Running Ruff check...{Colors.RESET}")
        print("Checking src/ and test/ directories")

        start = time.time()
        result = TestResult()

        try:
            # Use absolute paths to make it clear these are controlled inputs
            src_path = str(project_root / "src")
            test_path = str(project_root / "test")
            cmd = ["ruff", "check", src_path, test_path, "--line-length=120"]
            process = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)

            result.duration = time.time() - start

            if process.returncode == 0:
                result.passed = 1
                print(f"{Colors.GREEN}✅ Ruff check passed{Colors.RESET}")
            else:
                result.failed = 1
                self.overall_failed = True
                print(f"{Colors.RED}❌ Ruff check FAILED{Colors.RESET}")
                if process.stdout:
                    result.failed_tests = process.stdout.split('\n')[:5]  # First 5 errors
        except Exception as e:
            result.failed = 1
            self.overall_failed = True
            print(f"{Colors.RED}❌ Ruff check error: {e}{Colors.RESET}")

        return result

    def run_pytest_tests(self, test_files: list[str], name: str) -> dict[str, TestResult]:
        """Run pytest on specified test files"""
        results = {"unit": TestResult(), "integration": TestResult()}

        # Set environment for testing
        env = os.environ.copy()
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['TESTING'] = 'true'

        for test_file in test_files:
            test_path = project_root / test_file
            if not test_path.exists():
                continue

            # Determine if unit or integration test
            test_type = "unit" if "unit" in test_file else "integration"

            # Use tempfile for pytest report
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_report:
                report_path = tmp_report.name

            # Run pytest with JSON output
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v", "--tb=short",
                "--json-report", f"--json-report-file={report_path}",
                "--no-header", "--no-summary", "-q"
            ]

            start = time.time()
            process = subprocess.run(cmd, capture_output=True, text=True, env=env, shell=False, check=False)
            duration = time.time() - start

            # Parse pytest JSON report if available
            try:
                with open(report_path) as f:
                    report = json.load(f)
                    summary = report.get("summary", {})
                    results[test_type].passed += summary.get("passed", 0)
                    results[test_type].failed += summary.get("failed", 0)
                    results[test_type].skipped += summary.get("skipped", 0)
                    results[test_type].duration += duration

                    # Collect failed test names
                    if summary.get("failed", 0) > 0:
                        for test in report.get("tests", []):
                            if test.get("outcome") == "failed":
                                results[test_type].failed_tests.append(test.get("nodeid", "Unknown"))
            except Exception:
                # Fallback: parse stdout if JSON report fails
                output = process.stdout
                if "passed" in output:
                    # Simple parsing from pytest output
                    import re
                    match = re.search(r'(\d+) passed', output)
                    if match:
                        results[test_type].passed += int(match.group(1))
                    match = re.search(r'(\d+) failed', output)
                    if match:
                        results[test_type].failed += int(match.group(1))
                        self.overall_failed = True

                results[test_type].duration += duration
            finally:
                # Clean up temp file
                if 'report_path' in locals() and os.path.exists(report_path):
                    os.unlink(report_path)

        return results

    def run_service_modules_tests(self) -> dict[str, TestResult]:
        """Run service module tests"""
        print(f"\n{Colors.BLUE}📝 Step 2/5: Running Service Modules tests...{Colors.RESET}")

        service_tests = {
            "語言檢測": ["test/unit/test_language_detection.py"],
            "Prompt管理": ["test/unit/test_prompt_manager.py", "test/unit/test_unified_prompt_service.py"],
            "關鍵字服務": ["test/unit/test_keyword_extraction_service_v2.py"],
            "LLM Factory": ["test/unit/test_llm_factory.py"]
        }

        results = {}
        all_passed = True

        for service_name, test_files in service_tests.items():
            result = TestResult()
            for test_file in test_files:
                test_path = project_root / test_file
                if test_path.exists():
                    test_results = self.run_pytest_tests([test_file], service_name)
                    for test_type in test_results.values():
                        result.passed += test_type.passed
                        result.failed += test_type.failed
                        result.duration += test_type.duration
                        result.failed_tests.extend(test_type.failed_tests)

            results[service_name] = result
            if result.failed > 0:
                all_passed = False
                self.overall_failed = True

        if all_passed:
            print(f"{Colors.GREEN}✅ Service Modules tests passed{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Service Modules tests FAILED{Colors.RESET}")

        return results

    def run_health_keyword_tests(self) -> dict[str, TestResult]:
        """Run Health & Keyword tests"""
        print(f"\n{Colors.BLUE}📝 Step 3/5: Running Health & Keyword tests...{Colors.RESET}")

        test_files = [
            "test/unit/test_health.py",
            "test/unit/test_keyword_extraction.py",
            "test/integration/test_health_integration.py",
            "test/integration/test_keyword_extraction_language.py"
        ]

        results = self.run_pytest_tests(test_files, "health_keyword")

        if any(r.failed > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Health & Keyword tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Health & Keyword tests passed{Colors.RESET}")

        return results

    def run_index_calculation_tests(self) -> dict[str, TestResult]:
        """Run Index Calculation tests"""
        print(f"\n{Colors.BLUE}📝 Step 4/5: Running Index Calculation tests...{Colors.RESET}")

        test_files = [
            "test/unit/test_index_calculation_v2.py",
            "test/integration/test_index_calculation_v2_api.py"
        ]

        results = self.run_pytest_tests(test_files, "index_calc")

        if any(r.failed > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Index Calculation tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Index Calculation tests passed{Colors.RESET}")

        return results

    def run_gap_analysis_tests(self) -> dict[str, TestResult]:
        """Run Gap Analysis tests"""
        print(f"\n{Colors.BLUE}📝 Step 5/5: Running Gap Analysis tests...{Colors.RESET}")

        test_files = [
            "test/unit/test_gap_analysis_v2.py",
            "test/integration/test_gap_analysis_v2_integration_complete.py",
            "test/integration/test_error_handling_v2.py"
        ]

        results = self.run_pytest_tests(test_files, "gap_analysis")

        if any(r.failed > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Gap Analysis tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Gap Analysis tests passed{Colors.RESET}")

        return results

    def print_summary_table(self):
        """Print the final summary table"""
        total_duration = time.time() - self.start_time
        total_passed = 0
        total_failed = 0

        print("\n" + "=" * 70)
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 20 + "Pre-commit 完整測試報告" + " " * 25 + "║")
        print("╚" + "═" * 68 + "╝")
        print("\n📊 測試統計總覽")
        print("=" * 70)
        print(f"| {'測試分類':<26} | {'通過':>5} | {'失敗':>5} | {'總計':>5} | {'耗時':>6} | {'狀態':>4} |")
        print("|" + "-" * 28 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 8 + "|" + "-" * 6 + "|")

        # Ruff check
        ruff_result = self.results.get("ruff", TestResult())
        ruff_status = ruff_result.status
        print(f"| {'🔍 Ruff 檢查':<26} | {ruff_status:>5} | {'-':>5} | {'-':>5} | {ruff_result.duration:.1f}s{' ':>2} | {ruff_status:>4} |")
        print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        # Service modules
        print(f"| {'🏗️ 服務模組測試':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")
        service_results = self.results.get("service_modules", {})
        for service_name, result in service_results.items():
            total_passed += result.passed
            total_failed += result.failed
            print(f"|   ├─ {service_name:<22} | {result.passed:>5} | {result.failed:>5} | {result.total:>5} | {result.duration:.1f}s{' ':>2} | {result.status:>4} |")

        print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        # API tests
        api_tests = [
            ("🩺 Health & Keyword", "health_keyword"),
            ("🧮 Index Calculation", "index_calc"),
            ("📈 Gap Analysis", "gap_analysis")
        ]

        for display_name, key in api_tests:
            print(f"| {display_name:<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")
            results = self.results.get(key, {})

            for test_type in ["unit", "integration"]:
                if test_type in results:
                    result = results[test_type]
                    total_passed += result.passed
                    total_failed += result.failed
                    type_label = "單元測試 (UT)" if test_type == "unit" else "整合測試 (IT)"
                    print(f"|   ├─ {type_label:<22} | {result.passed:>5} | {result.failed:>5} | {result.total:>5} | {result.duration:.1f}s{' ':>2} | {result.status:>4} |")

            print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        # Total row
        total_tests = total_passed + total_failed
        overall_status = "✅" if total_failed == 0 else "❌"
        print("|" + "-" * 28 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 8 + "|" + "-" * 6 + "|")
        print(f"| {'🎯 總計':<26} | {total_passed:>5} | {total_failed:>5} | {total_tests:>5} | {total_duration:.1f}s{' ':>2} | {overall_status:>4} |")
        print("=" * 70)

        # Final message
        if total_failed == 0:
            print(f"\n{Colors.GREEN}🏆 所有檢查通過！代碼品質優良，準備提交。{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}❌ 發現 {total_failed} 個測試失敗，無法提交{Colors.RESET}")
            self.print_failure_details()

    def print_failure_details(self):
        """Print detailed failure information"""
        print(f"\n{Colors.YELLOW}🔍 失敗測試詳細資訊{Colors.RESET}")
        print("=" * 70)

        # Service module failures
        service_results = self.results.get("service_modules", {})
        service_failures = [name for name, r in service_results.items() if r.failed > 0]
        if service_failures:
            print(f"🏗️ 服務模組失敗: {', '.join(service_failures)}")

        # API test failures
        for display_name, key in [("🩺 Health & Keyword", "health_keyword"),
                                  ("🧮 Index Calculation", "index_calc"),
                                  ("📈 Gap Analysis", "gap_analysis")]:
            results = self.results.get(key, {})
            has_failures = False

            for test_type in ["unit", "integration"]:
                if test_type in results and results[test_type].failed > 0:
                    if not has_failures:
                        print(f"\n{display_name} 失敗測試:")
                        has_failures = True

                    type_label = "單元測試" if test_type == "unit" else "整合測試"
                    failed_tests = results[test_type].failed_tests[:3]  # Show first 3
                    if failed_tests:
                        print(f"   ├─ {type_label}: {', '.join(failed_tests)}")

        print(f"\n{Colors.YELLOW}📋 建議修復步驟:{Colors.RESET}")
        print("1. 查看詳細測試輸出")
        print("2. 修復失敗的測試")
        print("3. 重新執行測試確認修復")
        print("4. 再次嘗試提交")

    def run(self):
        """Main execution method"""
        print(f"\n{Colors.BOLD}🚨 Pre-commit validation starting...{Colors.RESET}")
        print("=" * 70)
        print()

        # Step 1: Ruff check
        self.results["ruff"] = self.run_ruff_check()

        # Step 2: Service Modules
        self.results["service_modules"] = self.run_service_modules_tests()

        # Step 3: Health & Keyword
        self.results["health_keyword"] = self.run_health_keyword_tests()

        # Step 4: Index Calculation
        self.results["index_calc"] = self.run_index_calculation_tests()

        # Step 5: Gap Analysis
        self.results["gap_analysis"] = self.run_gap_analysis_tests()

        # Print summary
        self.print_summary_table()

        # Exit with appropriate code
        if self.overall_failed:
            print(f"\n{Colors.RED}⛔ BLOCKING COMMIT - Fix test failures first{Colors.RESET}")
            print(f"\n{Colors.YELLOW}🔧 Next steps:{Colors.RESET}")
            print("1. Fix the failed tests shown in the summary above")
            print("2. Run individual test suites to verify fixes")
            print("3. Re-run this pre-commit check")
            print("4. Once all tests pass, try committing again")
            sys.exit(1)
        else:
            sys.exit(0)

if __name__ == "__main__":
    validator = PreCommitValidator()
    validator.run()
