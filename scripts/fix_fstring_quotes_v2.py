#!/usr/bin/env python3
"""
修復 f-string 未結束的引號問題 - 改進版
"""

import re
from pathlib import Path

def fix_fstring_quotes(file_path):
    """修復檔案中的 f-string 引號問題"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 檢查是否有未結束的 f-string
            if 'f"' in line or "f'" in line:
                # 檢查 logger 語句
                if 'logger.' in line and ('f"' in line or "f'" in line):
                    # 檢查是否有未結束的 f-string
                    if line.strip().endswith('f'):
                        # 這是個未結束的 f-string，需要加上引號和括號
                        line = line.rstrip() + '")'
                    elif line.strip().endswith('f,'):
                        # 這是個未結束的 f-string 且有逗號
                        line = line.rstrip()[:-1] + '")'
                    elif line.rstrip().endswith('f"'):
                        # f-string 開始但沒有結束
                        line = line.rstrip() + '")'
                
                # 處理其他 f-string 情況
                else:
                    # 雙引號 f-string
                    if 'f"' in line:
                        # 計算雙引號數量
                        quote_count = line.count('"')
                        # 如果是奇數且不是結束引號，添加結束引號
                        if quote_count % 2 == 1 and not line.rstrip().endswith('"'):
                            if line.strip().endswith('f'):
                                line = line.rstrip() + '"'
                    
                    # 單引號 f-string
                    if "f'" in line:
                        quote_count = line.count("'")
                        if quote_count % 2 == 1 and not line.rstrip().endswith("'"):
                            if line.strip().endswith('f'):
                                line = line.rstrip() + "'"
            
            fixed_lines.append(line)
            i += 1
        
        content = '\n'.join(fixed_lines)
        
        # 修復特定的模式：f-string 跨行的情況
        # 模式：f"xxx f" 在行尾
        content = re.sub(r'(\s+f"[^"]*?)\s+f"$', r'\1"', content, flags=re.MULTILINE)
        
        # 修復 logger 語句中的問題
        # 模式：logger.xxx(f"...f) 缺少結束引號
        content = re.sub(r'(logger\.\w+\(f"[^"]*?)f\)', r'\1")', content)
        content = re.sub(r"(logger\.\w+\(f'[^']*?)f\)", r"\1')", content)
        
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