#!/usr/bin/env python3
"""
修復 f-string 未結束的引號問題
"""

import re
from pathlib import Path

def fix_fstring_quotes(file_path):
    """修復檔案中的 f-string 引號問題"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修復未結束的 f-string
        # 模式：f" 開頭但行尾沒有結束引號的情況
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 檢查是否有未結束的 f-string
            if 'f"' in line or "f'" in line:
                # 計算雙引號 f-string
                if 'f"' in line:
                    # 確保 f-string 有結束引號
                    if line.strip().startswith('f"') and not line.rstrip().endswith('"') and not line.rstrip().endswith('",'):
                        if not line.rstrip().endswith('f'):
                            line = line.rstrip() + '"'
                        else:
                            # 如果以 f 結尾，可能是格式化字串的一部分
                            line = line.rstrip() + '"'
                
                # 計算單引號 f-string
                if "f'" in line:
                    if line.strip().startswith("f'") and not line.rstrip().endswith("'") and not line.rstrip().endswith("',"):
                        line = line.rstrip() + "'"
            
            fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # 如果有修改，寫回檔案
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修復了 {file_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ 處理 {file_path} 時發生錯誤: {e}")
        return False

def main():
    """主函數"""
    project_root = Path(__file__).parent.parent
    
    # 定義要檢查的目錄
    directories = ['src', 'test']
    
    fixed_count = 0
    
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            continue
            
        # 遞迴尋找所有 Python 檔案
        for py_file in dir_path.rglob('*.py'):
            if fix_fstring_quotes(py_file):
                fixed_count += 1
    
    print(f"\n總共修復了 {fixed_count} 個檔案")

if __name__ == "__main__":
    main()