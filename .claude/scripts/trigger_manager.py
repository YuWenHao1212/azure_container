#!/usr/bin/env python3
"""
Trigger Manager for Ruff-checker Sub Agent
統一管理手動觸發和自動觸發，避免重複執行
"""

import os
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


class TriggerManager:
    def __init__(self):
        self.trigger_dir = "/tmp"
        self.lock_file = "/tmp/ruff_trigger_manager.lock"
        self.last_execution_file = "/tmp/ruff_last_execution.json"
        self.min_interval_seconds = 10  # 最小執行間隔
        
    def get_lock(self, timeout=5):
        """獲取執行鎖，防止並發執行"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 嘗試創建鎖目錄
                os.makedirs(f"{self.lock_file}.dir", exist_ok=False)
                return True
            except FileExistsError:
                time.sleep(0.1)
        return False
    
    def release_lock(self):
        """釋放執行鎖"""
        try:
            os.rmdir(f"{self.lock_file}.dir")
        except (OSError, FileNotFoundError):
            pass
    
    def get_last_execution_info(self):
        """獲取最後執行資訊"""
        try:
            if os.path.exists(self.last_execution_file):
                with open(self.last_execution_file, 'r') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['timestamp']), data.get('trigger_type', 'unknown')
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
        return None, None
    
    def should_skip_execution(self, trigger_type):
        """檢查是否應該跳過執行"""
        last_time, last_type = self.get_last_execution_info()
        
        if last_time is None:
            return False, None
        
        # 檢查時間間隔
        elapsed = datetime.now() - last_time
        if elapsed.total_seconds() < self.min_interval_seconds:
            return True, f"Too soon since last execution ({elapsed.total_seconds():.1f}s < {self.min_interval_seconds}s)"
        
        # 手動觸發總是執行
        if trigger_type == 'manual':
            return False, None
        
        # 自動觸發：如果最近有手動觸發，則跳過
        if last_type == 'manual' and elapsed.total_seconds() < 60:
            return True, f"Recent manual trigger detected ({elapsed.total_seconds():.1f}s ago)"
        
        return False, None
    
    def record_execution(self, trigger_type, result):
        """記錄執行資訊"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'trigger_type': trigger_type,
            'result': result,
            'pid': os.getpid()
        }
        
        try:
            with open(self.last_execution_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not record execution info: {e}")
    
    def get_pending_trigger_requests(self):
        """獲取待處理的觸發請求"""
        trigger_files = []
        try:
            for file_path in Path(self.trigger_dir).glob("claude_ruff_trigger_*.json"):
                if not str(file_path).endswith('.processed'):
                    trigger_files.append(str(file_path))
        except Exception:
            pass
        
        # 按時間排序，最新的在前
        trigger_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return trigger_files
    
    def execute_ruff_check(self, trigger_type='manual', files=None):
        """執行 Ruff 檢查"""
        if not self.get_lock():
            return False, "Could not acquire execution lock"
        
        try:
            # 檢查是否應該跳過
            should_skip, skip_reason = self.should_skip_execution(trigger_type)
            if should_skip:
                return False, f"Skipped: {skip_reason}"
            
            # 執行 Ruff 檢查腳本
            script_path = ".claude/scripts/ruff_checker.py"
            if not os.path.exists(script_path):
                return False, f"Ruff checker script not found: {script_path}"
            
            cmd = ["python", script_path]
            if files:
                cmd.extend(files)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # 記錄執行
            execution_result = {
                'returncode': result.returncode,
                'stdout_length': len(result.stdout),
                'stderr_length': len(result.stderr),
                'files_checked': len(files) if files else 'auto-detect'
            }
            
            self.record_execution(trigger_type, execution_result)
            
            if result.returncode == 0:
                return True, "Ruff check completed successfully"
            else:
                return True, f"Ruff check completed with warnings (exit code: {result.returncode})"
        
        except subprocess.TimeoutExpired:
            return False, "Ruff check timed out after 5 minutes"
        except Exception as e:
            return False, f"Error executing Ruff check: {e}"
        
        finally:
            self.release_lock()
    
    def process_auto_trigger(self):
        """處理自動觸發請求"""
        trigger_files = self.get_pending_trigger_requests()
        
        if not trigger_files:
            return False, "No pending trigger requests"
        
        latest_trigger = trigger_files[0]
        
        try:
            with open(latest_trigger, 'r') as f:
                trigger_data = json.load(f)
            
            files = trigger_data.get('files', [])
            file_count = trigger_data.get('file_count', len(files))
            
            print(f"🤖 Processing auto-trigger request: {file_count} files")
            
            success, message = self.execute_ruff_check('auto', files)
            
            # 標記觸發請求為已處理
            try:
                os.rename(latest_trigger, f"{latest_trigger}.processed")
            except OSError:
                pass
            
            return success, message
            
        except (json.JSONDecodeError, KeyError, OSError) as e:
            return False, f"Error processing trigger request: {e}"
    
    def process_manual_trigger(self, files=None):
        """處理手動觸發請求"""
        print("🔧 Processing manual trigger request")
        return self.execute_ruff_check('manual', files)
    
    def show_status(self):
        """顯示觸發管理器狀態"""
        print("🎛️  Ruff Trigger Manager Status")
        print("═══════════════════════════════════════════════════════════════")
        
        # 執行鎖狀態
        lock_active = os.path.exists(f"{self.lock_file}.dir")
        print(f"🔒 Execution lock: {'ACTIVE' if lock_active else 'FREE'}")
        
        # 最後執行資訊
        last_time, last_type = self.get_last_execution_info()
        if last_time:
            elapsed = datetime.now() - last_time
            print(f"⏰ Last execution: {elapsed.total_seconds():.1f}s ago ({last_type})")
        else:
            print("⏰ Last execution: Never")
        
        # 待處理請求
        pending_requests = self.get_pending_trigger_requests()
        print(f"📋 Pending requests: {len(pending_requests)}")
        
        if pending_requests:
            for i, req in enumerate(pending_requests[:3]):
                req_time = datetime.fromtimestamp(os.path.getmtime(req))
                age = datetime.now() - req_time
                print(f"   {i+1}. {os.path.basename(req)} ({age.total_seconds():.1f}s ago)")
            if len(pending_requests) > 3:
                print(f"   ... and {len(pending_requests) - 3} more")
        
        print("═══════════════════════════════════════════════════════════════")


def main():
    import sys
    
    manager = TriggerManager()
    
    if len(sys.argv) < 2:
        manager.show_status()
        return
    
    command = sys.argv[1]
    
    if command == '--status':
        manager.show_status()
    elif command == '--auto':
        success, message = manager.process_auto_trigger()
        print(f"Auto-trigger result: {message}")
        sys.exit(0 if success else 1)
    elif command == '--manual':
        files = sys.argv[2:] if len(sys.argv) > 2 else None
        success, message = manager.process_manual_trigger(files)
        print(f"Manual trigger result: {message}")
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        print("Usage: trigger_manager.py [--status|--auto|--manual [files...]]")
        sys.exit(1)


if __name__ == "__main__":
    main()