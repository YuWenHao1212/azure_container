#!/usr/bin/env python3
"""Debug script to check CI environment detection."""

import os
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=== CI Environment Debug ===")
print(f"CI env var: {os.environ.get('CI')}")
print(f"GITHUB_ACTIONS env var: {os.environ.get('GITHUB_ACTIONS')}")

try:
    from test.config import TestConfig
    print(f"\nTestConfig.is_ci_environment(): {TestConfig.is_ci_environment()}")
    print(f"Test timeout: {TestConfig.get_test_timeout()}s")
    delays = TestConfig.get_retry_delays()
    if isinstance(delays, dict) and 'rate_limit' in delays:
        print(f"Rate limit initial delay: {delays['rate_limit']['initial_delay']}s")
        print(f"Timeout initial delay: {delays['timeout']['initial_delay']}s")
        print(f"General initial delay: {delays['general']['initial_delay']}s")
    else:
        print(f"Retry delays structure: {delays}")
except ImportError as e:
    print(f"\nError importing TestConfig: {e}")

print("\n=== All environment variables ===")
for key, value in sorted(os.environ.items()):
    if any(ci_keyword in key.upper() for ci_keyword in ['CI', 'GITHUB', 'ACTION']):
        print(f"{key}={value}")

print("\n=== Course Batch Query Test Debug ===")
# Check fixture files
fixture_path = Path(__file__).parent.parent / "fixtures" / "course_batch"
print(f"Fixture path exists: {fixture_path.exists()}")
if fixture_path.exists():
    for file in ["test_data.json", "mock_courses.json"]:
        file_path = fixture_path / file
        print(f"  {file}: {'exists' if file_path.exists() else 'MISSING'}")

# Try to run the specific test with verbose output
print("\n=== Running Course Batch Query test with verbose output ===")

result = subprocess.run(  # noqa: S603 - diagnostic script, controlled input
    [sys.executable, "-m", "pytest",  # Use sys.executable instead of "python"
     "test/unit/test_course_batch_unit.py::TestCourseBatchUnit::test_API_CDB_001_UT_basic_batch_query",
     "-xvs", "--tb=short"],
    capture_output=True,
    text=True,
    cwd=str(Path(__file__).parent.parent.parent),
    check=False  # Don't raise exception on non-zero exit
)
print(f"Exit code: {result.returncode}")
if result.returncode != 0:
    print("STDOUT:", result.stdout[-1000:] if result.stdout else "None")
    print("STDERR:", result.stderr[-1000:] if result.stderr else "None")
