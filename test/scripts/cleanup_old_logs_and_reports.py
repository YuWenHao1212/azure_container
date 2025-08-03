#!/usr/bin/env python3
"""
Clean up old logs and reports, keeping only the latest 5 files in each directory
"""

import os
from datetime import datetime
from pathlib import Path


def get_file_timestamp(filepath):
    """Extract timestamp from filename or use modification time"""
    filename = os.path.basename(filepath)

    # Try to extract timestamp from filename patterns
    # Pattern 1: YYYYMMDD_HHMMSS
    import re
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except:  # noqa: S110, E722
            pass

    # Pattern 2: YYYYMMDD
    match = re.search(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except:  # noqa: S110, E722
            pass

    # Fallback to file modification time
    return datetime.fromtimestamp(os.path.getmtime(filepath))

def cleanup_directory(directory_path, keep_count=5, dry_run=False):
    """Clean up directory keeping only the latest files"""
    if not os.path.exists(directory_path):
        print(f"❌ Directory not found: {directory_path}")
        return

    # Get all files in the directory
    files = []
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        if os.path.isfile(item_path):
            files.append(item_path)

    if len(files) <= keep_count:
        print(f"✅ {directory_path}: Has {len(files)} files, no cleanup needed")
        return

    # Sort files by timestamp (newest first)
    files_with_time = [(f, get_file_timestamp(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)

    # Files to keep and delete
    files_to_keep = files_with_time[:keep_count]
    files_to_delete = files_with_time[keep_count:]

    print(f"\n📁 {directory_path}:")
    print(f"   Total files: {len(files)}")
    print(f"   Files to keep: {len(files_to_keep)}")
    print(f"   Files to delete: {len(files_to_delete)}")

    # Show files to keep
    print("\n   ✅ Keeping (newest 5):")
    for filepath, timestamp in files_to_keep:
        filename = os.path.basename(filepath)
        print(f"      - {filename} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

    # Show files to delete
    print("\n   🗑️  Deleting:")
    for filepath, timestamp in files_to_delete:
        filename = os.path.basename(filepath)
        print(f"      - {filename} ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

    # Actually delete files if not dry run
    if not dry_run:
        for filepath, _ in files_to_delete:
            try:
                os.remove(filepath)
                print(f"      ✓ Deleted: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"      ✗ Error deleting {os.path.basename(filepath)}: {e}")

def main():
    # Base directory
    base_dir = Path("/Users/yuwenhao/Documents/GitHub/azure_container")

    # Directories to clean
    directories = [
        base_dir / "test" / "logs",
        base_dir / "test" / "reports"
    ]

    print("🧹 Cleaning up old logs and reports...")
    print("=" * 60)

    # Directly perform cleanup
    for directory in directories:
        cleanup_directory(str(directory), keep_count=5, dry_run=False)

    print("\n✅ Cleanup completed!")

if __name__ == "__main__":
    main()
