#!/usr/bin/env python3
"""Simple test runner to check if tests are working."""

import subprocess
import sys
import os

# Change to test directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run a simple test
cmd = [
    sys.executable, "-m", "pytest", 
    "unit/test_health.py::TestHealthCheck::test_health_check_success",
    "-v", "-s"
]

print("Running simple test to verify setup...")
print(f"Command: {' '.join(cmd)}")
print("-" * 80)

result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:")
    print(result.stderr)

print("-" * 80)
print(f"Exit code: {result.returncode}")

if result.returncode == 0:
    print("✅ Test setup is working!")
else:
    print("❌ Test setup failed. Please check the output above.")
    
sys.exit(result.returncode)