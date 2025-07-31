#!/usr/bin/env python3
"""Script to add TEST_SPEC IDs to integration test functions."""

# 定義測試函數和對應的 TEST_SPEC ID
test_mappings = [
    ("test_english_job_description_uses_english_prompt", "API-KW-301-IT", "英文 JD 使用英文 prompt"),
    ("test_traditional_chinese_job_description_uses_chinese_prompt", "API-KW-302-IT", "繁中 JD 使用繁中 prompt"),
    ("test_mixed_chinese_english_above_threshold", "API-KW-303-IT", "混合語言（>20%繁中）"),
    ("test_mixed_chinese_english_below_threshold", "API-KW-304-IT", "混合語言（<20%繁中）"),
    ("test_reject_simplified_chinese", "API-KW-305-IT", "拒絕簡體中文"),
    ("test_reject_japanese", "API-KW-306-IT", "拒絕日文"),
    ("test_reject_korean", "API-KW-307-IT", "拒絕韓文"),
    ("test_reject_mixed_with_unsupported_languages", "API-KW-308-IT", "拒絕混合不支援語言"),
    ("test_explicit_language_parameter_override", "API-KW-309-IT", "語言參數覆蓋測試"),
    ("test_unsupported_language_error_response_format", "API-KW-310-IT", "錯誤回應格式驗證"),
    ("test_exactly_twenty_percent_chinese_threshold_integration", "API-KW-311-IT", "20%閾值整合測試"),
    ("test_minimum_length_validation_integration", "API-KW-312-IT", "最小長度驗證整合"),
    ("test_language_detection_metadata_in_response", "API-KW-313-IT", "語言檢測元資料回應"),
    ("test_comprehensive_error_details_for_unsupported_language", "API-KW-314-IT", "不支援語言詳細錯誤"),
]

# 讀取檔案
with open('test/integration/test_keyword_extraction_language.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替換每個測試函數的 docstring
for test_name, test_id, description in test_mappings:
    # 找到測試函數定義
    import re
    
    # 建立 regex pattern 來匹配函數定義和現有的 docstring
    pattern = rf'(\s+def {test_name}\([^)]*\):\s*\n)(\s+"""[^"]*""")?'
    
    # 新的 docstring
    new_docstring = f'        """TEST: {test_id} - {description}"""'
    
    # 替換
    def replacer(match):
        func_def = match.group(1)
        return func_def + new_docstring
    
    content = re.sub(pattern, replacer, content)

# 寫回檔案
with open('test/integration/test_keyword_extraction_language.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 成功添加 14 個 TEST_SPEC IDs 到 test_keyword_extraction_language.py")