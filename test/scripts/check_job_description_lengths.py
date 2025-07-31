#!/usr/bin/env python3
"""Check job_description lengths in test files."""

job_descriptions = [
    ("test_english_detection_selects_english_prompt", "Senior Python Developer with FastAPI experience needed"),
    ("test_chinese_detection_selects_chinese_prompt", "尋找資深Python工程師，需要FastAPI經驗"),
    ("test_mixed_language_prompt_selection", "Looking for 資深工程師 with Python and 機器學習 experience"),
    ("test_unsupported_language_raises_error", "Pythonエンジニアを募集しています"),
    ("test_explicit_language_bypasses_detection", "Senior Python Developer needed"),
    ("test_invalid_explicit_language_raises_error", "Test job description"),
    ("test_format_prompt_with_job_description", "Looking for Python developer"),
    ("test_very_short_job_description", "Python Developer needed with experience in Django and REST APIs"),
    ("test_numbers_and_symbols_only", "5+ years, $100k-150k, 401k, PTO"),
    ("test_service_cleanup_on_success", "We are looking for a Senior Python Developer with experience in FastAPI"),
    ("test_service_cleanup_on_error", "We need a Python developer with experience"),
]

print("檢查 job_description 長度（最小需求: 200 字元）\n")
print(f"{'測試函數':<50} {'長度':<10} {'狀態':<10} {'描述'}")
print("-" * 100)

issues = []

for test_name, job_desc in job_descriptions:
    length = len(job_desc)
    status = "❌ 太短" if length < 200 else "✅ OK"
    if length < 200:
        issues.append((test_name, length, job_desc))
    print(f"{test_name:<50} {length:<10} {status:<10} {job_desc[:50]}...")

print(f"\n總計: {len(issues)} 個測試使用了少於 200 字元的 job_description")

if issues:
    print("\n需要修正的測試：")
    for test_name, length, job_desc in issues:
        print(f"- {test_name}: {length} 字元")
        print(f"  內容: {job_desc}")
        print()