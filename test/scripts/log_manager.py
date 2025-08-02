#!/usr/bin/env python3
"""
Log management utilities for test scripts.
Provides functions to manage log files and implement rotation.
"""

import os
import glob
from pathlib import Path
from datetime import datetime


def get_project_root():
    """Get project root directory."""
    # Works in both local and CI environments
    github_workspace = os.environ.get('GITHUB_WORKSPACE')
    if github_workspace:
        return Path(github_workspace)
    
    # Get relative to this script
    return Path(__file__).parent.parent.parent.absolute()


def get_log_dir():
    """Get standard log directory."""
    return get_project_root() / "test" / "logs"


def clean_old_logs(log_dir, pattern, keep_count=6):
    """
    Clean old log files, keeping only the most recent ones.
    
    Args:
        log_dir: Directory containing log files
        pattern: Glob pattern for log files (e.g., "level2_unit_*.log")
        keep_count: Number of most recent files to keep (default: 6)
    """
    log_dir = Path(log_dir)
    
    # Find all matching files
    files = list(log_dir.glob(pattern))
    
    # Sort by modification time (newest first)
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Delete files beyond keep_count
    for file_to_delete in files[keep_count:]:
        try:
            file_to_delete.unlink()
            print(f"Deleted old log: {file_to_delete.name}")
        except Exception as e:
            print(f"Error deleting {file_to_delete}: {e}")


def prepare_log_dir(log_dir, pattern=None, keep_count=6):
    """
    Prepare log directory: create if needed and clean old logs.
    
    Args:
        log_dir: Directory path
        pattern: Optional glob pattern for cleanup
        keep_count: Number of files to keep
    """
    log_dir = Path(log_dir)
    
    # Create directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean old logs if pattern provided
    if pattern:
        clean_old_logs(log_dir, pattern, keep_count)


def get_log_path(prefix, extension=".log"):
    """
    Generate a log file path with timestamp.
    
    Args:
        prefix: Log file prefix (e.g., "level2_unit")
        extension: File extension (default: ".log")
    
    Returns:
        Path object for the log file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}{extension}"
    return get_log_dir() / filename


if __name__ == "__main__":
    # Example usage
    log_dir = get_log_dir()
    print(f"Log directory: {log_dir}")
    
    # Clean old logs
    prepare_log_dir(log_dir, "level2_unit_*.log")
    
    # Get new log path
    log_path = get_log_path("test_example")
    print(f"New log path: {log_path}")