#!/usr/bin/env python
"""
Standalone E2E Test Runner for Index Calculation V2.

This script runs E2E tests in isolation from global mocks, using real Azure APIs.
Based on the successful pattern from Gap Analysis V2 implementation.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Run E2E tests in standalone mode."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # Set up environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / 'src')
    env['RUNNING_STANDALONE_E2E'] = 'true'
    env['USE_V2_IMPLEMENTATION'] = 'true'
    
    # Check for required API keys
    required_keys = [
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_ENDPOINT',
        'EMBEDDING_API_KEY',
        'EMBEDDING_ENDPOINT'
    ]
    
    missing_keys = [key for key in required_keys if not env.get(key)]
    if missing_keys:
        print(f"❌ Missing required API keys: {', '.join(missing_keys)}")
        print("Please set these environment variables or add them to your .env file")
        sys.exit(1)
    
    # Build pytest command
    cmd = [
        sys.executable, '-m', 'pytest',
        'test_index_calculation_v2_e2e.py',
        '-v', '-s',
        '--tb=short',
        '--confcutdir=.',  # Limit conftest.py search to current directory
        '--no-cov',
        '-p', 'no:warnings'
    ]
    
    # Add any additional arguments passed to this script
    cmd.extend(sys.argv[1:])
    
    print("🚀 Running Index Calculation V2 E2E Tests in Standalone Mode")
    print(f"Working directory: {script_dir}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run the tests
    result = subprocess.run(cmd, env=env, cwd=str(script_dir))
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()