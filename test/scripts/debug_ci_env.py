#!/usr/bin/env python3
"""Debug script to check CI environment detection."""

import os
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
    print(f"Rate limit initial delay: {delays['rate_limit']['initial_delay']}s")
except ImportError as e:
    print(f"\nError importing TestConfig: {e}")
    
print("\n=== All environment variables ===")
for key, value in sorted(os.environ.items()):
    if any(ci_keyword in key.upper() for ci_keyword in ['CI', 'GITHUB', 'ACTION']):
        print(f"{key}={value}")