#!/usr/bin/env python3
"""
Ruff System Cleanup Script
清理 Ruff-checker 系統的臨時檔案和舊資料
"""

import os
import glob
import time
from datetime import datetime, timedelta


def cleanup_temp_files():
    """清理臨時檔案"""
    cleaned_count = 0
    
    # 清理觸發請求檔案（保留最新的 5 個）
    trigger_files = glob.glob("/tmp/claude_ruff_trigger_*.json*")
    trigger_files.sort(key=os.path.getmtime, reverse=True)
    
    for file_path in trigger_files[5:]:  # 保留最新的 5 個
        try:
            os.remove(file_path)
            cleaned_count += 1
            print(f"Removed: {os.path.basename(file_path)}")
        except OSError:
            pass
    
    # 清理超過 1 天的鎖檔案
    lock_files = [
        "/tmp/ruff_trigger_manager.lock.dir",
        "/tmp/claude_ruff_checker.lock",
        "/tmp/claude_ruff_checker_v2.lock.dir"
    ]
    
    for lock_path in lock_files:
        if os.path.exists(lock_path):
            try:
                # 檢查檔案年齡
                file_time = datetime.fromtimestamp(os.path.getmtime(lock_path))
                if datetime.now() - file_time > timedelta(hours=1):
                    if os.path.isdir(lock_path):
                        os.rmdir(lock_path)
                    else:
                        os.remove(lock_path)
                    cleaned_count += 1
                    print(f"Removed stale lock: {os.path.basename(lock_path)}")
            except OSError:
                pass
    
    return cleaned_count


def show_system_status():
    """顯示系統狀態"""
    print("🧹 Ruff System Cleanup Status")
    print("═" * 50)
    
    # 檢查觸發請求檔案
    trigger_files = glob.glob("/tmp/claude_ruff_trigger_*.json*")
    print(f"📄 Trigger files: {len(trigger_files)}")
    
    # 檢查執行狀態檔案
    status_files = [
        "/tmp/claude_last_ruff_check.txt",
        "/tmp/claude_last_ruff_trigger.txt", 
        "/tmp/ruff_last_execution.json"
    ]
    
    active_files = []
    for file_path in status_files:
        if os.path.exists(file_path):
            active_files.append(os.path.basename(file_path))
    
    print(f"📊 Status files: {len(active_files)} ({', '.join(active_files)})")
    
    # 檢查日誌檔案
    log_files = [
        "/tmp/claude_hook_debug.log",
        "/tmp/claude_unified_trigger.log"
    ]
    
    active_logs = []
    for file_path in log_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            active_logs.append(f"{os.path.basename(file_path)} ({size} bytes)")
    
    print(f"📝 Log files: {len(active_logs)}")
    for log in active_logs:
        print(f"   • {log}")
    
    # 檢查活躍程序
    pid_files = [
        "/tmp/claude_ruff_checker.pid",
        "/tmp/claude_ruff_checker_v2.pid"
    ]
    
    active_pids = []
    for pid_file in pid_files:
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # 檢查程序是否仍在運行（簡單檢查）
                try:
                    os.kill(pid, 0)
                    active_pids.append(f"{os.path.basename(pid_file)} (PID: {pid})")
                except (OSError, ProcessLookupError):
                    # 程序已死亡，清理 PID 檔案
                    os.remove(pid_file)
            except (ValueError, OSError):
                pass
    
    print(f"⚙️  Active processes: {len(active_pids)}")
    for pid_info in active_pids:
        print(f"   • {pid_info}")
    
    print("═" * 50)


def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        show_system_status()
    elif len(sys.argv) > 1 and sys.argv[1] == "--clean":
        print("🧹 Starting Ruff system cleanup...")
        cleaned = cleanup_temp_files()
        print(f"✅ Cleanup completed: {cleaned} files removed")
        print()
        show_system_status()
    else:
        print("Ruff System Cleanup Tool")
        print("Usage:")
        print("  --status  Show system status")
        print("  --clean   Perform cleanup and show status")


if __name__ == "__main__":
    main()