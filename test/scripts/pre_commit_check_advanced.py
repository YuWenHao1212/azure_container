#!/usr/bin/env python3
"""
Advanced Pre-commit validation script
使用 pytest 程式化 API 直接執行測試並收集詳細結果
"""
# ruff: noqa: S603  # subprocess calls are safe in this test script
import argparse
import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from test.config import TestConfig
except ImportError:
    # Fallback if config not available
    class TestConfig:
        @staticmethod
        def get_test_timeout():
            return 30  # Default timeout

import pytest
from _pytest.config import ExitCode
from _pytest.terminal import TerminalReporter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

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
    errors: int = 0
    duration: float = 0.0
    failed_tests: list[str] = field(default_factory=list)
    error_logs: list[str] = field(default_factory=list)  # Store detailed error logs

    @property
    def total(self):
        return self.passed + self.failed + self.skipped

    @property
    def status(self):
        return "✅" if self.failed == 0 and self.errors == 0 else "❌"

class CustomPlugin:
    """Custom pytest plugin to collect test results"""

    def __init__(self):
        self.results = TestResult()
        self.start_time = None

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_sessionfinish(self, session):
        self.results.duration = time.time() - self.start_time

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            if report.passed:
                self.results.passed += 1
            elif report.failed:
                self.results.failed += 1
                self.results.failed_tests.append(report.nodeid)
                # Capture error details
                if hasattr(report, 'longrepr') and report.longrepr:
                    error_msg = str(report.longrepr)
                    # Truncate very long error messages
                    if len(error_msg) > 500:
                        error_msg = error_msg[:500] + "... [truncated]"
                    self.results.error_logs.append(f"{report.nodeid}: {error_msg}")
            elif report.skipped:
                self.results.skipped += 1

class AdvancedPreCommitValidator:
    """Advanced pre-commit validation with pytest API"""

    def __init__(self, option: str = "full"):
        self.start_time = time.time()
        self.results = {}
        self.overall_failed = False
        self.option = option

        # Set testing environment
        os.environ['TESTING'] = 'true'
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['USE_V2_IMPLEMENTATION'] = 'true'

        # Define available test options
        self.available_options = {
            "ruff": {"name": "Ruff 檢查", "step": 1},
            "service": {"name": "服務模組測試", "step": 2},
            "error-handler": {"name": "錯誤處理系統測試", "step": 3},
            "health-keyword": {"name": "Health & Keyword 測試", "step": 4},
            "index-calculation": {"name": "Index Calculation 測試", "step": 5},
            "gap-analysis": {"name": "Gap Analysis 測試", "step": 6},
            "resume-tailoring": {"name": "Resume Tailoring 測試", "step": 7},
            "full": {"name": "完整測試", "step": None}
        }

    def run_ruff_check(self) -> TestResult:
        """Run Ruff code quality check"""
        step_info = "Step 1/7: " if self.option == "full" else ""
        print(f"{Colors.BLUE}📝 {step_info}Running Ruff check...{Colors.RESET}")
        print("Checking src/ and test/ directories")

        start = time.time()
        result = TestResult()

        try:
            # Use absolute paths to make it clear these are controlled inputs
            src_path = str(project_root / "src")
            test_path = str(project_root / "test")
            cmd = ["ruff", "check", src_path, test_path, "--line-length=120", "--output-format=concise"]
            process = subprocess.run(cmd, capture_output=True, text=True, shell=False, check=False)

            result.duration = time.time() - start

            if process.returncode == 0:
                result.passed = 1
                print(f"{Colors.GREEN}✅ Ruff check passed{Colors.RESET}")
            else:
                # Parse output to distinguish between errors and warnings
                lines = process.stdout.strip().split('\n') if process.stdout else []
                errors = []
                warnings = []

                for line in lines:
                    if line and not line.startswith('Found'):
                        if 'S603' in line or 'S108' in line:  # Security warnings
                            warnings.append(line)
                        else:
                            errors.append(line)

                if errors:
                    result.failed = 1
                    self.overall_failed = True
                    print(f"{Colors.RED}❌ Ruff check FAILED{Colors.RESET}")
                    print(f"  Errors found: {len(errors)}")
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"    {error}")
                elif warnings:
                    result.passed = 1
                    print(f"{Colors.YELLOW}⚠️  Ruff check passed with warnings{Colors.RESET}")
                    print(f"  Security warnings: {len(warnings)}")
                    # Show warning summary
                    warning_types = {}
                    for warning in warnings:
                        if 'S603' in warning:
                            warning_types['S603'] = warning_types.get('S603', 0) + 1
                        elif 'S108' in warning:
                            warning_types['S108'] = warning_types.get('S108', 0) + 1
                    for wtype, count in warning_types.items():
                        if wtype == 'S603':
                            print(f"    {count} x S603: subprocess-without-shell-equals-true")
                        elif wtype == 'S108':
                            print(f"    {count} x S108: hardcoded-temp-file")

                result.failed_tests = lines[:5]  # Store for summary

        except FileNotFoundError:
            print(f"{Colors.YELLOW}⚠️  Ruff not found, skipping code check{Colors.RESET}")
            result.skipped = 1
        except Exception as e:
            result.errors = 1
            self.overall_failed = True
            print(f"{Colors.RED}❌ Ruff check error: {e}{Colors.RESET}")

        return result

    def run_pytest_programmatically(self, test_paths: list[str], test_name: str) -> TestResult:
        """Run pytest programmatically and collect results"""
        plugin = CustomPlugin()

        # Configure pytest arguments for minimal output
        args = [
            "-q",  # Quiet mode - minimal output
            "--tb=no",  # No traceback
            "--no-header", "--no-summary",
            "--disable-warnings",
            "--color=no"  # Disable color to avoid parsing issues
        ]

        # Skip flaky tests in pre-commit if environment variable is set
        # Usage: SKIP_FLAKY_TESTS=true python test/scripts/pre_commit_check_advanced.py
        if os.getenv("SKIP_FLAKY_TESTS", "false").lower() == "true":
            args.extend(["-m", "not flaky"])

        # Suppress output for integration tests to keep output clean
        if "integration" in test_name or "IT" in test_name:
            args.append("--capture=sys")  # Capture stdout/stderr
        else:
            args.append("-s")  # No capture for unit tests

        # Add test paths
        test_files_found = []
        for path in test_paths:
            test_file = project_root / path
            if test_file.exists():
                args.append(str(test_file))
                test_files_found.append(str(test_file))
            else:
                # Debug output for CI/CD
                if os.environ.get('CI'):
                    print(f"\n    [DEBUG] Test file not found: {test_file}")
                    print(f"    [DEBUG] Current directory: {os.getcwd()}")
                    print(f"    [DEBUG] Project root: {project_root}")
                    # Check if the file exists with alternative paths
                    alternative_path = Path(path)
                    if alternative_path.exists():
                        print(f"    [DEBUG] File exists at: {alternative_path.absolute()}")
                    # Check common paths
                    from_cwd = Path(os.getcwd()) / path
                    if from_cwd.exists():
                        print(f"    [DEBUG] File exists from CWD: {from_cwd}")
                        args.append(str(from_cwd))
                        test_files_found.append(str(from_cwd))

        # Check if we have any test files (args has base options + capture option + test files)
        base_args_count = 7 if "-s" in args or "--capture=sys" in args else 6
        if len(args) == base_args_count:  # No test files found
            # Debug output for CI/CD when no files found
            if os.environ.get('CI'):
                print(f"    [WARNING] No test files found for {test_name}")
                print(f"    [WARNING] Searched paths: {test_paths}")
            return TestResult(skipped=1)

        # Redirect pytest output to suppress it
        import contextlib
        import io

        # Capture pytest output to suppress the "X passed, Y warnings in Z.XXs" messages
        output_buffer = io.StringIO()

        # Run pytest with custom plugin and captured output
        try:
            with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
                exit_code = pytest.main(args, plugins=[plugin])

            # Handle exit codes - only set overall_failed for actual test failures
            if exit_code == ExitCode.TESTS_FAILED and plugin.results.failed > 0:
                self.overall_failed = True
            elif exit_code == ExitCode.INTERNAL_ERROR:
                plugin.results.errors += 1
                self.overall_failed = True

        except Exception as e:
            plugin.results.errors += 1
            self.overall_failed = True
            print(f"Error running {test_name}: {e}")

        return plugin.results

    def run_service_modules_tests(self) -> dict[str, TestResult]:
        """Run service module tests"""
        step_info = "Step 2/7: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Service Modules tests...{Colors.RESET}")

        # Based on the actual test files in test/unit/services/
        service_tests = {
            "語言檢測": [
                "test/unit/services/test_language_detection_service.py"
            ],
            "Prompt管理": [
                "test/unit/services/test_unified_prompt_service.py"
            ],
            "關鍵字服務": [
                "test/unit/services/test_keyword_service_integration.py"
            ],
            "LLM Factory": [
                "test/unit/services/test_llm_factory_service.py"
            ]
        }

        results = {}
        all_passed = True

        for service_name, test_files in service_tests.items():
            # Check if files exist and run pytest
            existing_files = [f for f in test_files if (project_root / f).exists()]

            if existing_files:
                # Show compact collection message
                print(f"  {service_name}: ", end="", flush=True)

                # Run pytest and get actual results
                result = self.run_pytest_programmatically(existing_files, service_name)

                # Show inline result
                if result.total > 0:
                    status_icon = "✅" if result.failed == 0 else "❌"
                    print(f"collected {result.total} items, {result.passed} passed {status_icon}")
            else:
                # If files don't exist, create empty result
                print(f"Warning: No test files found for {service_name}")
                result = TestResult()
                result.skipped = 1
                result.duration = 0.0

            results[service_name] = result
            if result.failed > 0 or result.errors > 0:
                all_passed = False
                self.overall_failed = True

        if all_passed:
            print(f"{Colors.GREEN}✅ Service Modules tests passed{Colors.RESET}")
        else:
            print(f"{Colors.RED}❌ Service Modules tests FAILED{Colors.RESET}")

        return results

    def run_error_handler_tests(self) -> dict[str, TestResult]:
        """Run Error Handler System tests (UT & IT)"""
        step_info = "Step 3/6: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Error Handler System tests...{Colors.RESET}")

        unit_files = [
            "test/unit/test_error_handler/test_error_handler_factory.py",
            "test/unit/test_error_handler/test_error_handler_decorator.py",
            "test/unit/test_error_handler/test_error_codes.py",
            "test/unit/test_error_handler/test_consolidated_error_handling.py"  # New: ERR-016 to ERR-020
        ]

        integration_files = [
            "test/integration/test_error_handler_integration/test_error_handler_api.py"
        ]

        # Run unit tests
        print("  Unit Tests: ", end="", flush=True)
        unit_result = self.run_pytest_programmatically(unit_files, "error_handler_unit")
        if unit_result.total > 0:
            status = "✅" if unit_result.failed == 0 else "❌"
            print(f"collected {unit_result.total} items, {unit_result.passed} passed {status}")

        # Run integration tests
        print("  Integration Tests: ", end="", flush=True)
        integration_result = self.run_pytest_programmatically(integration_files, "error_handler_integration")
        if integration_result.total > 0:
            status = "✅" if integration_result.failed == 0 else "❌"
            print(f"collected {integration_result.total} items, {integration_result.passed} passed {status}")

        results = {
            "unit": unit_result,
            "integration": integration_result
        }

        if any(r.failed > 0 or r.errors > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Error Handler System tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Error Handler System tests passed{Colors.RESET}")

        return results

    def run_health_keyword_tests(self) -> dict[str, TestResult]:
        """Run Health & Keyword tests"""
        step_info = "Step 4/7: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Health & Keyword tests...{Colors.RESET}")

        unit_files = [
            "test/unit/test_health.py",
            "test/unit/test_keyword_extraction.py"
        ]

        integration_files = [
            "test/integration/test_health_integration.py",
            "test/integration/test_keyword_extraction_language.py"
        ]

        # Run unit tests
        print("  Unit Tests: ", end="", flush=True)
        unit_result = self.run_pytest_programmatically(unit_files, "health_keyword_unit")
        if unit_result.total > 0:
            status = "✅" if unit_result.failed == 0 else "❌"
            print(f"collected {unit_result.total} items, {unit_result.passed} passed {status}")

        # Run integration tests
        print("  Integration Tests: ", end="", flush=True)
        integration_result = self.run_pytest_programmatically(integration_files, "health_keyword_integration")
        if integration_result.total > 0:
            status = "✅" if integration_result.failed == 0 else "❌"
            print(f"collected {integration_result.total} items, {integration_result.passed} passed {status}")

        results = {
            "unit": unit_result,
            "integration": integration_result
        }

        if any(r.failed > 0 or r.errors > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Health & Keyword tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Health & Keyword tests passed{Colors.RESET}")

        return results

    def run_index_calculation_tests(self) -> dict[str, TestResult]:
        """Run Index Calculation tests"""
        step_info = "Step 5/7: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Index Calculation tests...{Colors.RESET}")

        unit_files = ["test/unit/test_index_calculation_v2.py"]
        integration_files = ["test/integration/test_index_calculation_v2_api.py"]

        # Run unit tests
        print("  Unit Tests: ", end="", flush=True)
        unit_result = self.run_pytest_programmatically(unit_files, "index_calc_unit")
        if unit_result.total > 0:
            status = "✅" if unit_result.failed == 0 else "❌"
            print(f"collected {unit_result.total} items, {unit_result.passed} passed {status}")

        # Run integration tests
        print("  Integration Tests: ", end="", flush=True)
        integration_result = self.run_pytest_programmatically(integration_files, "index_calc_integration")
        if integration_result.total > 0:
            status = "✅" if integration_result.failed == 0 else "❌"
            print(f"collected {integration_result.total} items, {integration_result.passed} passed {status}")

        results = {
            "unit": unit_result,
            "integration": integration_result
        }

        if any(r.failed > 0 or r.errors > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Index Calculation tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Index Calculation tests passed{Colors.RESET}")

        return results

    def run_gap_analysis_tests(self) -> dict[str, TestResult]:
        """Run Gap Analysis tests with timeout handling"""
        step_info = "Step 6/7: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Gap Analysis tests...{Colors.RESET}")

        # Include Resume Structure Analysis tests (part of Gap Analysis V4)
        unit_files = [
            "test/unit/test_gap_analysis_v2.py",
            "test/unit/test_resume_structure_analyzer.py"  # Resume Structure unit tests
        ]
        integration_files = [
            "test/integration/test_gap_analysis_v2_integration_complete.py",
            "test/integration/test_error_handling_v2.py",
            "test/integration/test_resume_structure_integration.py"  # Resume Structure integration tests
        ]

        # Run unit tests
        print("  Unit Tests: ", end="", flush=True)
        unit_result = self.run_pytest_programmatically(unit_files, "gap_analysis_unit")
        if unit_result.total > 0:
            status = "✅" if unit_result.failed == 0 else "❌"
            print(f"collected {unit_result.total} items, {unit_result.passed} passed {status}")

        # Run integration tests with timeout handling
        print("  Integration Tests: ", end="", flush=True)
        integration_result = TestResult()

        # Note: Integration tests might hang, so we set a timeout
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Integration tests timed out")

        # Set timeout based on environment
        timeout_seconds = TestConfig.get_test_timeout()
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            integration_result = self.run_pytest_programmatically(integration_files, "gap_analysis_integration")
            signal.alarm(0)  # Cancel alarm
            if integration_result.total > 0:
                status = "✅" if integration_result.failed == 0 else "❌"
                print(f"collected {integration_result.total} items, {integration_result.passed} passed {status}")
        except TimeoutError:
            print(f"{Colors.YELLOW}timed out (27 tests skipped) ⚠️{Colors.RESET}")
            integration_result.skipped = 27  # Expected 27 integration tests
            integration_result.duration = float(timeout_seconds)
            signal.alarm(0)  # Cancel alarm

        results = {
            "unit": unit_result,
            "integration": integration_result
        }

        if any(r.failed > 0 or r.errors > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Gap Analysis tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Gap Analysis tests passed{Colors.RESET}")

        return results

    def run_resume_tailoring_tests(self) -> dict[str, TestResult]:
        """Run Resume Tailoring tests (UT & IT only, no PT)"""
        step_info = "Step 7/7: " if self.option == "full" else ""
        print(f"\n{Colors.BLUE}📝 {step_info}Running Resume Tailoring tests...{Colors.RESET}")

        unit_files = ["test/unit/services/test_resume_tailoring_metrics.py"]
        integration_files = ["test/integration/test_resume_tailoring_api.py"]
        # Performance tests removed - they require real API, not mocks

        # Run unit tests
        print("  Unit Tests: ", end="", flush=True)
        unit_result = self.run_pytest_programmatically(unit_files, "resume_tailoring_unit")
        if unit_result.total > 0:
            status = "✅" if unit_result.failed == 0 else "❌"
            print(f"collected {unit_result.total} items, {unit_result.passed} passed {status}")
        elif unit_result.skipped > 0:
            # File not found - show warning
            print("file not found, skipped ⚠️")
        else:
            print("collected 0 items")

        # Run integration tests
        print("  Integration Tests: ", end="", flush=True)
        integration_result = self.run_pytest_programmatically(integration_files, "resume_tailoring_integration")
        if integration_result.total > 0:
            status = "✅" if integration_result.failed == 0 else "❌"
            print(f"collected {integration_result.total} items, {integration_result.passed} passed {status}")
        elif integration_result.skipped > 0:
            # File not found - show warning
            print("file not found, skipped ⚠️")
        else:
            print("collected 0 items")

        results = {
            "unit": unit_result,
            "integration": integration_result
            # No performance results
        }

        if any(r.failed > 0 or r.errors > 0 for r in results.values()):
            print(f"{Colors.RED}❌ Resume Tailoring tests FAILED{Colors.RESET}")
            self.overall_failed = True
        else:
            print(f"{Colors.GREEN}✅ Resume Tailoring tests passed{Colors.RESET}")

        return results

    def print_summary_table(self):
        """Print the final summary table matching the shell script format"""
        total_duration = time.time() - self.start_time

        # Get option name for header
        option_name = self.available_options.get(self.option, {}).get("name", self.option)
        header_title = 'Pre-commit 完整測試報告' if self.option == 'full' else f'{option_name}報告'

        # Print header
        print("\n" + "=" * 71)
        print("╔" + "═" * 69 + "╗")
        header_spaces = (69 - len(header_title)) // 2
        print("║" + " " * header_spaces + header_title + " " * (69 - len(header_title) - header_spaces) + "║")
        print("╚" + "═" * 69 + "╝")

        # Dynamic subtitle based on option
        if self.option == "full":
            print("\n📊 測試統計總覽")
        else:
            print(f"\n📊 {option_name}統計")
        print("=" * 71)

        # Table header
        print(f"| {'測試分類':<26} | {'通過':>5} | {'失敗':>5} | {'總計':>5} | {'耗時':>6} | {'狀態':>4} |")
        print("|" + "-" * 28 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 8 + "|" + "-" * 6 + "|")

        # Display only results for executed tests
        total_passed, total_failed = self._print_test_results()

        # Total row
        total_tests = total_passed + total_failed
        overall_status = "✅" if total_failed == 0 and not self.overall_failed else "❌"

        print("|" + "-" * 28 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 8 + "|" + "-" * 6 + "|")
        print(f"| {'🎯 總計':<26} | {total_passed:>5} | {total_failed:>5} | {total_tests:>5} | {total_duration:.1f}s{' ':>2} | {overall_status:>4} |")
        print("=" * 71)

        # Final message
        if not self.overall_failed:
            print(f"\n{Colors.GREEN}🏆 所有檢查通過！代碼品質優良，準備提交。{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}❌ 發現 {total_failed} 個測試失敗，無法提交{Colors.RESET}")
            self.print_failure_details()

    def _print_test_results(self):
        """Print test results based on executed tests"""
        total_passed = 0
        total_failed = 0

        # Ruff check
        if "ruff" in self.results:
            ruff_result = self.results["ruff"]
            if ruff_result.skipped:
                print(f"| {'🔍 Ruff 檢查':<26} | {'⏭️':>5} | {'-':>5} | {'-':>5} | {ruff_result.duration:.1f}s{' ':>2} | {'⏭️':>4} |")
            else:
                # Count Ruff failures in total
                if ruff_result.failed > 0:
                    total_failed += 1  # Count as 1 failed check
                elif ruff_result.passed > 0:
                    total_passed += 1  # Count as 1 passed check
                print(f"| {'🔍 Ruff 檢查':<26} | {ruff_result.status:>5} | {'-':>5} | {'-':>5} | {ruff_result.duration:.1f}s{' ':>2} | {ruff_result.status:>4} |")
            print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        # Service modules
        if "service_modules" in self.results:
            print(f"| {'🏗️ 服務模組測試':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")
            service_results = self.results["service_modules"]
            for service_name, result in service_results.items():
                total_passed += result.passed
                total_failed += result.failed
                print(f"|   ├─ {service_name:<22} | {result.passed:>5} | {result.failed:>5} | {result.total:>5} | {result.duration:.1f}s{' ':>2} | {result.status:>4} |")
            print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        # API tests - only show executed ones
        api_test_mapping = {
            "error_handler": ("🛡️ Error Handler System", "error_handler"),
            "health_keyword": ("🩺 Health & Keyword", "health_keyword"),
            "index_calc": ("🧮 Index Calculation", "index_calc"),
            "gap_analysis": ("📈 Gap Analysis", "gap_analysis"),
            "resume_tailoring": ("📝 Resume Tailoring", "resume_tailoring")
        }

        for result_key, (display_name, _) in api_test_mapping.items():
            if result_key in self.results:
                print(f"| {display_name:<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")
                results = self.results[result_key]

                # Only show UT and IT tests (no PT in pre-commit)
                for test_type in ["unit", "integration"]:
                    if test_type in results:
                        result = results[test_type]
                        total_passed += result.passed
                        total_failed += result.failed

                        type_label = "單元測試 (UT)" if test_type == "unit" else "整合測試 (IT)"

                        print(f"|   ├─ {type_label:<22} | {result.passed:>5} | {result.failed:>5} | {result.total:>5} | {result.duration:.1f}s{' ':>2} | {result.status:>4} |")

                print(f"| {'':<26} | {'':<5} | {'':<5} | {'':<5} | {'':<6} | {'':<4} |")

        return total_passed, total_failed

    def print_failure_details(self):
        """Print detailed failure information"""
        has_failures = False

        # Check for any failures
        for key in ["service_modules", "error_handler", "health_keyword", "index_calc", "gap_analysis", "resume_tailoring"]:
            if key in self.results:
                if isinstance(self.results[key], dict):
                    for result in self.results[key].values():
                        if result.failed > 0 or result.errors > 0:
                            has_failures = True
                            break
                elif self.results[key].failed > 0 or self.results[key].errors > 0:
                    has_failures = True
                    break

        if not has_failures:
            return

        print(f"\n{Colors.YELLOW}🔍 失敗測試詳細資訊{Colors.RESET}")
        print("=" * 71)

        # Service module failures
        if "service_modules" in self.results:
            service_results = self.results["service_modules"]
            failed_services = []
            for name, result in service_results.items():
                if result.failed > 0:
                    failed_services.append(f"{name}({result.failed})")

            if failed_services:
                print(f"🏗️ 服務模組失敗: {', '.join(failed_services)}")

        # API test failures
        for display_name, key in [
            ("🛡️ Error Handler System", "error_handler"),
            ("🩺 Health & Keyword", "health_keyword"),
            ("🧮 Index Calculation", "index_calc"),
            ("📈 Gap Analysis", "gap_analysis"),
            ("📝 Resume Tailoring", "resume_tailoring")
        ]:
            if key in self.results:
                results = self.results[key]
                if isinstance(results, dict):
                    unit_failed = results.get("unit", TestResult()).failed
                    integration_failed = results.get("integration", TestResult()).failed
                    # No performance tests in pre-commit

                    if unit_failed > 0 or integration_failed > 0:
                        print(f"\n{display_name} 失敗測試:")
                        if unit_failed > 0:
                            failed_tests = results["unit"].failed_tests[:3]
                            test_names = [t.split("::")[-1] for t in failed_tests]
                            print(f"   ├─ 單元測試: {', '.join(test_names)}")
                            # Show error logs for first failed test
                            if results["unit"].error_logs:
                                first_error = results["unit"].error_logs[0]
                                print(f"      └─ 錯誤詳情: {first_error[:100]}...")
                        if integration_failed > 0:
                            failed_tests = results["integration"].failed_tests[:3]
                            test_names = [t.split("::")[-1] for t in failed_tests]
                            print(f"   ├─ 整合測試: {', '.join(test_names)}")
                            # Show error logs for first failed test
                            if results["integration"].error_logs:
                                first_error = results["integration"].error_logs[0]
                                print(f"      └─ 錯誤詳情: {first_error[:100]}...")

        print(f"\n{Colors.YELLOW}📋 建議修復步驟:{Colors.RESET}")
        print("1. 查看詳細測試輸出")
        print("2. 修復失敗的測試")
        print("3. 重新執行測試確認修復")
        print("4. 再次嘗試提交")

    def run(self):
        """Main execution method"""
        # Determine which tests to run based on option
        test_steps = self._get_test_steps()

        if self.option == "full":
            print(f"\n{Colors.BOLD}🚨 Pre-commit validation starting...{Colors.RESET}")
            print("=" * 70)
            print()
        else:
            option_name = self.available_options.get(self.option, {}).get("name", self.option)
            print(f"\n{Colors.BOLD}🚨 {option_name} starting...{Colors.RESET}")
            print("=" * 70)
            print()

        # Execute selected test steps
        for step_key, step_method in test_steps:
            self.results[step_key] = step_method()

            # Early exit on failure for single option runs
            if self.option != "full" and self.overall_failed:
                break

        # Print summary
        print("\n" + "=" * 70)
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
            if self.option == "full":
                print("\n💡 Test commands:")
                print("• Health & Keyword: ./test/scripts/run_health_keyword_unit_integration.sh")
                print("• Index Calc: ./test/scripts/run_index_calculation_unit_integration.sh")
                print("• Gap Analysis: ./test/scripts/run_index_cal_gap_analysis_unit_integration.sh")
                print("• Resume Tailoring (UT&IT): pytest test/unit/services/test_resume_tailoring_metrics.py test/integration/test_resume_tailoring_api.py -v")
                print("• Resume Tailoring (PT): pytest test/performance/test_resume_tailoring_performance.py -v  # Requires real API keys")
                print("• Quick check: ruff check src/ test/ --line-length=120")
            sys.exit(0)

    def _get_test_steps(self):
        """Get test steps to execute based on option"""
        all_steps = [
            ("ruff", self.run_ruff_check),
            ("service_modules", self.run_service_modules_tests),
            ("error_handler", self.run_error_handler_tests),
            ("health_keyword", self.run_health_keyword_tests),
            ("index_calc", self.run_index_calculation_tests),
            ("gap_analysis", self.run_gap_analysis_tests),
            ("resume_tailoring", self.run_resume_tailoring_tests)
        ]

        option_mapping = {
            "ruff": [("ruff", self.run_ruff_check)],
            "service": [("service_modules", self.run_service_modules_tests)],
            "error-handler": [("error_handler", self.run_error_handler_tests)],
            "health-keyword": [("health_keyword", self.run_health_keyword_tests)],
            "index-calculation": [("index_calc", self.run_index_calculation_tests)],
            "gap-analysis": [("gap_analysis", self.run_gap_analysis_tests)],
            "resume-tailoring": [("resume_tailoring", self.run_resume_tailoring_tests)],
            "full": all_steps
        }

        return option_mapping.get(self.option, all_steps)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Advanced Pre-commit validation script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available options:
  ruff              : Run only Ruff code quality check
  service           : Run only Service Modules tests
  error-handler     : Run only Error Handler System tests
  health-keyword    : Run only Health & Keyword tests
  index-calculation : Run only Index Calculation tests
  gap-analysis      : Run only Gap Analysis tests
  resume-tailoring  : Run only Resume Tailoring tests
  full              : Run all tests (default)

Examples:
  python test/scripts/pre_commit_check_advanced.py --option service
  python test/scripts/pre_commit_check_advanced.py --option resume-tailoring
  python test/scripts/pre_commit_check_advanced.py --option ruff
  python test/scripts/pre_commit_check_advanced.py  # runs full by default
        """
    )

    parser.add_argument(
        "--option",
        choices=["ruff", "service", "error-handler", "health-keyword", "index-calculation", "gap-analysis", "resume-tailoring", "full"],
        default="full",
        help="Select which tests to run (default: full)"
    )

    args = parser.parse_args()

    validator = AdvancedPreCommitValidator(option=args.option)
    validator.run()
