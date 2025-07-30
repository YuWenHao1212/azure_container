#!/usr/bin/env python3
"""
Test runner for Level 2 unit tests.

Runs unit tests for health check and keyword extraction endpoints,
logging results to test/logs/level2_unit_YYYYMMDD_HHMMSS.log
"""

import os
import sys
import subprocess
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_tests():
    """Run Level 2 unit tests and log results."""
    # Create timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"test/logs/level2_unit_{timestamp}.log"
    
    # Ensure log directory exists
    os.makedirs("test/logs", exist_ok=True)
    
    print(f"Running Level 2 unit tests...")
    print(f"Log file: {log_file}")
    print("-" * 80)
    
    # Test files to run
    test_files = [
        "test/unit/test_health.py",
        "test/unit/test_keyword_extraction.py"
    ]
    
    # Run pytest with detailed output
    cmd = [
        "pytest",
        "-v",  # Verbose
        "-s",  # Show print statements
        "--tb=short",  # Short traceback
        "--no-header",  # No header
        "-p", "no:warnings",  # Disable warnings
        *test_files
    ]
    
    # Open log file for writing
    with open(log_file, "w") as log:
        # Write header
        log.write(f"Level 2 Unit Tests - {datetime.now().isoformat()}\n")
        log.write("=" * 80 + "\n\n")
        log.write("Test Configuration:\n")
        log.write(f"- Test files: {', '.join(test_files)}\n")
        log.write(f"- Python version: {sys.version}\n")
        log.write(f"- Working directory: {os.getcwd()}\n\n")
        log.write("Test Execution:\n")
        log.write("-" * 80 + "\n\n")
        
        # Run tests and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        # Stream output to both console and log file
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        
        # Wait for process to complete
        return_code = process.wait()
        
        # Write summary
        log.write("\n" + "=" * 80 + "\n")
        log.write("Test Summary:\n")
        log.write(f"- Exit code: {return_code}\n")
        log.write(f"- Status: {'PASSED' if return_code == 0 else 'FAILED'}\n")
        
        # Note: JSON report disabled for now (requires pytest-json-report plugin)
        log.write("- Test results saved to log file\n")
        
        log.write(f"\nCompleted at: {datetime.now().isoformat()}\n")
    
    print("-" * 80)
    print(f"Tests completed. Exit code: {return_code}")
    print(f"Full results logged to: {log_file}")
    
    # Also create a summary file for quick reference
    summary_file = f"test/logs/level2_unit_{timestamp}_summary.txt"
    with open(summary_file, "w") as sf:
        sf.write(f"Level 2 Unit Test Summary\n")
        sf.write(f"Timestamp: {timestamp}\n")
        sf.write(f"Status: {'PASSED' if return_code == 0 else 'FAILED'}\n")
        sf.write(f"Exit code: {return_code}\n")
        sf.write(f"Log file: {log_file}\n")
        
        # JSON report disabled for now
    
    return return_code


if __name__ == "__main__":
    sys.exit(run_tests())