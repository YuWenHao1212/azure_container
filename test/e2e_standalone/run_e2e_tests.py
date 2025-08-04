#!/usr/bin/env python
"""
獨立執行 E2E 測試的腳本
繞過根目錄的 conftest.py 和全局 mock
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """執行獨立的 E2E 測試"""
    # 取得當前腳本目錄
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    
    # 設置環境變數
    env = os.environ.copy()
    
    # 設置 PYTHONPATH，只包含 src 目錄
    env['PYTHONPATH'] = str(project_root / 'src')
    
    # 設置測試標記
    env['RUNNING_STANDALONE_E2E'] = 'true'
    
    # 建構 pytest 命令
    cmd = [
        sys.executable, '-m', 'pytest',
        'test_gap_analysis_v2_e2e.py',
        '-v',  # 詳細輸出
        '-s',  # 顯示 print 輸出
        '--tb=short',  # 簡短的錯誤追蹤
        '--confcutdir=.',  # 限制 conftest.py 搜索範圍到當前目錄
        '--no-cov',  # 禁用覆蓋率
        '-p', 'no:warnings'  # 減少警告輸出
    ]
    
    # 添加任何額外的命令行參數
    cmd.extend(sys.argv[1:])
    
    print("🚀 Running E2E Tests in Standalone Mode")
    print(f"Working directory: {script_dir}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    # 執行測試
    result = subprocess.run(cmd, env=env, cwd=str(script_dir))
    
    # 返回測試結果
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()