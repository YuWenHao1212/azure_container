#!/usr/bin/env python3
"""
驗證所有測試中的 job_description 長度是否符合 API 要求（至少 200 字元）
包含特殊測試案例的例外處理
"""

import os
import re
import sys


def check_job_descriptions_in_file(file_path):
    """檢查檔案中所有 job_description 的長度"""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # 找出所有 job_description 定義
    # 匹配 job_description = """...""" 或 job_description = "..."
    pattern = r'job_description\s*=\s*("""[\s\S]*?"""|"[^"]*")'

    # 特殊測試案例的例外清單
    exceptions = {
        'test_numbers_and_symbols_only': "測試純數字符號的邊界情況",
        'test_very_short_job_description': "測試短 JD 的驗證錯誤"
    }

    issues = []
    exceptions_found = []

    for match in re.finditer(pattern, content):
        job_desc = match.group(1)
        # 移除引號和多餘的空白
        cleaned_desc = job_desc.strip('"').strip()
        # 計算實際長度
        actual_length = len(cleaned_desc)

        # 找出這個 job_description 所在的測試函數
        # 從匹配位置往前找最近的 def test_
        start_pos = match.start()
        before_text = content[:start_pos]
        test_match = re.findall(r'def\s+(test_\w+)', before_text)
        test_name = test_match[-1] if test_match else "Unknown"

        # 檢查是否為例外案例
        if test_name in exceptions:
            exceptions_found.append({
                'test': test_name,
                'length': actual_length,
                'reason': exceptions[test_name],
                'snippet': cleaned_desc[:50] + "..."
            })
        elif actual_length < 200:
            issues.append({
                'test': test_name,
                'length': actual_length,
                'snippet': cleaned_desc[:50] + "..."
            })

    return issues, exceptions_found

def main():
    # 檢查所有相關測試檔案
    test_files = [
        'test/unit/test_keyword_extraction_extended.py',
        'test/unit/test_keyword_extraction.py',
        'test/integration/test_keyword_extraction_language.py',
        'test/integration/test_azure_openai_integration.py'
    ]

    print("檢查所有測試中的 job_description 長度...\n")

    total_issues = 0
    total_exceptions = 0

    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"檢查 {file_path}:")
            issues, exceptions_found = check_job_descriptions_in_file(file_path)

            if exceptions_found:
                print(f"  發現 {len(exceptions_found)} 個合理的例外案例:")
                for exc in exceptions_found:
                    print(f"    - {exc['test']}: {exc['length']} 字元 (✓ {exc['reason']})")
                total_exceptions += len(exceptions_found)

            if issues:
                print(f"  發現 {len(issues)} 個長度不足的 job_description:")
                for issue in issues:
                    print(f"    - {issue['test']}: {issue['length']} 字元")
                    print(f"      開頭: {issue['snippet']}")
                total_issues += len(issues)

            if not issues and not exceptions_found:
                print("  ✓ 所有 job_description 都符合長度要求")
            print()

    print("\n" + "="*60)
    print("總結:")
    print(f"  例外案例: {total_exceptions} 個（故意設計的邊界測試）")
    print(f"  問題案例: {total_issues} 個（需要修正）")

    if total_issues == 0:
        print("\n✅ 太好了！所有需要符合長度要求的 job_description 都已達標")
    else:
        print(f"\n❌ 發現 {total_issues} 個需要修正的 job_description")
        sys.exit(1)

if __name__ == "__main__":
    main()
