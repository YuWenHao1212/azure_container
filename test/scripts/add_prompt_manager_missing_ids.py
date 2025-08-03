#!/usr/bin/env python3
"""Script to add missing TEST_SPEC IDs to prompt manager tests."""

import re

# 定義測試函數和對應的 TEST_SPEC ID 映射
test_mappings = [
    # TestPromptManagerIntegration class
    ("test_language_override_workflow", "API-KW-261-UT", "語言覆蓋工作流程"),
    ("test_unsupported_language_chain", "API-KW-262-UT", "不支援語言鏈"),
    ("test_format_prompt_with_job_description", "API-KW-263-UT", "JD 格式化測試"),
    ("test_prompt_template_validation_edge_cases", "API-KW-264-UT", "Prompt 模板邊界案例"),
]

# 讀取檔案
with open('test/unit/test_prompt_manager.py', encoding='utf-8') as f:
    content = f.read()

# 替換每個測試函數的 docstring
for test_name, test_id, description in test_mappings:
    # 找到測試函數定義
    pattern = rf'(def {test_name}\([^)]*\):\s*\n\s*)("""[^"]*""")?'

    # 新的 docstring
    new_docstring = f'"""TEST: {test_id} - {description}"""'

    # 替換
    def replacer(match):
        func_def = match.group(1)
        return func_def + new_docstring  # noqa: B023

    content = re.sub(pattern, replacer, content)

# 寫回檔案
with open('test/unit/test_prompt_manager.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 成功添加 4 個缺失的 TEST_SPEC IDs 到 test_prompt_manager.py")
