#!/usr/bin/env python
"""Debug script for Course Batch Query test failures in CI."""

import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("=== Debug Course Batch Query Tests ===")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")
print(f"Project root: {project_root}")
print()

# Check if test/config.py exists and can be imported
print("=== Checking test.config import ===")
try:
    from test.config import TestConfig
    print("✅ Successfully imported TestConfig")
    print(f"   is_ci_environment: {TestConfig.is_ci_environment()}")
    print(f"   test_timeout: {TestConfig.get_test_timeout()}")
except ImportError as e:
    print(f"❌ Failed to import TestConfig: {e}")
print()

# Check if fixture files exist
print("=== Checking fixture files ===")
fixture_path = project_root / "test" / "fixtures" / "course_batch"
print(f"Fixture path: {fixture_path}")
print(f"Path exists: {fixture_path.exists()}")
if fixture_path.exists():
    for file in ["test_data.json", "mock_courses.json", "course_ids.json"]:
        file_path = fixture_path / file
        if file_path.exists():
            print(f"✅ {file}: exists ({file_path.stat().st_size} bytes)")
            # Try to load JSON
            try:
                with open(file_path) as f:
                    data = json.load(f)
                print(f"   JSON valid: ✅ ({len(data)} items/keys)")
            except Exception as e:
                print(f"   JSON error: ❌ {e}")
        else:
            print(f"❌ {file}: missing")
print()

# Check imports for the test file
print("=== Checking test imports ===")
try:
    import asyncpg
    print("✅ asyncpg imported")
except ImportError as e:
    print(f"❌ asyncpg import failed: {e}")

try:
    import pytest
    print("✅ pytest imported")
except ImportError as e:
    print(f"❌ pytest import failed: {e}")

try:
    from unittest.mock import AsyncMock, MagicMock, Mock, patch
    print("✅ unittest.mock imported")
except ImportError as e:
    print(f"❌ unittest.mock import failed: {e}")
print()

# Try to import the actual test module
print("=== Trying to import test module ===")
try:
    import test.unit.test_course_batch_unit as test_module
    print("✅ Successfully imported test_course_batch_unit")

    # Check if test class exists
    if hasattr(test_module, 'TestCourseBatchUnit'):
        print("✅ TestCourseBatchUnit class found")
        test_class = test_module.TestCourseBatchUnit

        # List test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        print(f"   Found {len(test_methods)} test methods:")
        for method in test_methods[:5]:  # Show first 5
            print(f"     - {method}")
    else:
        print("❌ TestCourseBatchUnit class not found")
except Exception as e:
    print(f"❌ Failed to import test module: {e}")
    import traceback
    traceback.print_exc()
print()

# Run a simple test to see if pytest works
print("=== Running minimal pytest test ===")
try:
    import subprocess
    result = subprocess.run(
        ["python", "-m", "pytest", "--collect-only", "test/unit/test_course_batch_unit.py"],
        capture_output=True,
        text=True,
        cwd=str(project_root)
    )
    print(f"Exit code: {result.returncode}")
    if result.returncode == 0:
        # Count collected tests
        lines = result.stdout.split('\n')
        for line in lines[-10:]:  # Show last 10 lines
            if 'collected' in line.lower():
                print(f"✅ {line.strip()}")
    else:
        print("❌ Collection failed")
        print("STDOUT:", result.stdout[-500:] if result.stdout else "None")
        print("STDERR:", result.stderr[-500:] if result.stderr else "None")
except Exception as e:
    print(f"❌ Failed to run pytest: {e}")

print("\n=== Debug complete ===")
