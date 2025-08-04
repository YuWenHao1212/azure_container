#!/usr/bin/env python3
"""
修復 f-string 結尾錯誤的問題
"""

import re
from pathlib import Path

def fix_fstring_endings(file_path):
    """修復檔案中的 f-string 結尾問題"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修復 .f, 結尾的 f-string (應該是 ",)
        content = re.sub(r'\.f,$', '",', content, flags=re.MULTILINE)
        
        # 修復 .f" 結尾的 f-string (應該是 ")
        content = re.sub(r'\.f"', '"', content)
        
        # 修復 }f" 結尾的 f-string (應該是 }")
        content = re.sub(r'}f"', '}"', content)
        
        # 修復 }f, 結尾的 f-string (應該是 }",)
        content = re.sub(r'}f,', '}",', content)
        
        # 修復多餘的 f 在 f-string 中間
        # 例如：f"text f" -> f"text "
        content = re.sub(r'(f"[^"]*?)\sf"$', r'\1"', content, flags=re.MULTILINE)
        content = re.sub(r"(f'[^']*?)\sf'$", r"\1'", content, flags=re.MULTILINE)
        
        # 修復 logger 語句中的特殊情況
        # logger.xxx(f"...f, -> logger.xxx(f"...",
        content = re.sub(r'(logger\.\w+\(f"[^"]*?)f,$', r'\1",', content, flags=re.MULTILINE)
        content = re.sub(r"(logger\.\w+\(f'[^']*?)f,$", r"\1',", content, flags=re.MULTILINE)
        
        # 修復 assert 語句中的特殊情況
        # assert xxx, f"...f" -> assert xxx, f"..."
        content = re.sub(r'(assert [^,]+,\s*f"[^"]*?)f"$', r'\1"', content, flags=re.MULTILINE)
        content = re.sub(r"(assert [^,]+,\s*f'[^']*?)f'$", r"\1'", content, flags=re.MULTILINE)
        
        # 修復字典或函數調用中的 f-string
        # "key": f"value f" -> "key": f"value"
        content = re.sub(r'("[\w_]+"\s*:\s*f"[^"]*?)\sf"', r'\1"', content)
        content = re.sub(r"('[\w_]+'\s*:\s*f'[^']*?)\sf'", r"\1'", content)
        
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
            if fix_fstring_endings(py_file):
                fixed_count += 1
    
    print(f"\n總共修復了 {fixed_count} 個檔案")

if __name__ == "__main__":
    main()