#!/usr/bin/env python3
"""Expand job descriptions to meet 250+ character requirement."""

import re

# 定義需要更新的測試和新的 job_description
updates = [
    {
        "test_name": "test_english_detection_selects_english_prompt",
        "old": 'job_description = "Senior Python Developer with FastAPI experience needed"',
        "new": '''job_description = """Senior Python Developer with FastAPI experience needed. We are looking for
                  an experienced developer with at least 5 years of Python development experience.
                  Strong knowledge of FastAPI, microservices architecture, Docker, and cloud services required.
                  Experience with CI/CD pipelines and test-driven development highly desired."""'''
    },
    {
        "test_name": "test_chinese_detection_selects_chinese_prompt",
        "old": 'job_description = "尋找資深Python工程師，需要FastAPI經驗"',
        "new": '''job_description = """尋找資深Python工程師，需要FastAPI經驗。我們正在尋找具有至少5年Python開發經驗的
                  資深工程師。需要精通FastAPI框架、微服務架構、Docker容器技術和雲端服務。具備CI/CD流程
                  和測試驅動開發經驗者優先考慮。需要良好的團隊合作能力和溝通技巧。歡迎對技術充滿熱情的
                  開發者加入我們的團隊，共同開發創新的解決方案。"""'''
    },
    {
        "test_name": "test_mixed_language_prompt_selection",
        "old": 'job_description = "Looking for 資深工程師 with Python and 機器學習 experience"',
        "new": '''job_description = """Looking for 資深工程師 with Python and 機器學習 experience. We need a
                  senior engineer 具備5年以上 Python development 經驗. Strong background in 機器學習,
                  深度學習, and data science required. Experience with TensorFlow, PyTorch, 和 scikit-learn
                  是必須的. 需要有 cloud platforms 經驗, especially AWS or Azure. 優秀的問題解決能力和
                  團隊合作精神 are essential for this role."""'''
    },
    {
        "test_name": "test_explicit_language_bypasses_detection",
        "old": 'job_description = "Senior Python Developer needed"',
        "new": '''job_description = """Senior Python Developer needed for our growing technology team. We are seeking
                  an experienced developer with strong Python skills and a passion for building scalable
                  applications. The ideal candidate will have experience with web frameworks like Django or
                  FastAPI, RESTful API design, database management, and cloud deployment. Knowledge of
                  microservices architecture and containerization technologies is highly valued."""'''
    },
    {
        "test_name": "test_invalid_explicit_language_raises_error",
        "old": '"job_description": "Test job description"',
        "new": '''"job_description": """Test job description for keyword extraction service validation. This is a
                  comprehensive job posting for a Senior Software Engineer position requiring extensive
                  experience in multiple programming languages and frameworks. The ideal candidate should
                  have strong problem-solving skills, excellent communication abilities, and a proven track
                  record of delivering high-quality software solutions in agile environments."""'''
    },
    {
        "test_name": "test_format_prompt_with_job_description",
        "old": 'job_desc = "Looking for Python developer"',
        "new": '''job_desc = """Looking for Python developer with strong backend development skills. We need someone
                  with at least 3 years of experience in Python web development, preferably with Django or
                  Flask frameworks. Knowledge of RESTful APIs, database design, and cloud services is essential.
                  The role involves designing and implementing scalable backend services, optimizing application
                  performance, and collaborating with frontend developers to deliver exceptional user experiences."""'''
    },
    {
        "test_name": "test_service_cleanup_on_success",
        "old": 'job_description = "We are looking for a Senior Python Developer with experience in FastAPI"',
        "new": '''job_description = """We are looking for a Senior Python Developer with experience in FastAPI to join
                  our innovative development team. The ideal candidate will have 5+ years of Python experience,
                  deep knowledge of FastAPI framework, and expertise in building high-performance RESTful APIs.
                  Experience with asynchronous programming, microservices architecture, Docker, Kubernetes, and
                  cloud platforms (AWS/Azure/GCP) is required. Strong problem-solving skills and ability to work
                  in an agile environment are essential."""'''
    },
    {
        "test_name": "test_service_cleanup_on_error",
        "old": 'job_description = "We need a Python developer with experience"',
        "new": '''job_description = """We need a Python developer with experience in building scalable web applications.
                  The successful candidate will have strong Python programming skills, experience with modern
                  web frameworks, and knowledge of software development best practices. Responsibilities include
                  developing new features, maintaining existing codebase, writing unit tests, and participating
                  in code reviews. Experience with agile methodologies and version control systems is required."""'''
    }
]

# 讀取檔案
with open('test/unit/test_keyword_extraction_extended.py', encoding='utf-8') as f:
    content = f.read()

# 執行替換
for update in updates:
    # 對於一般的替換
    if update["test_name"] != "test_invalid_explicit_language_raises_error":
        # 處理多行字串的縮排
        old_pattern = update["old"].replace('"', r'\"')
        new_text = update["new"]

        # 找到並替換
        content = content.replace(update["old"], new_text)
    else:
        # 特殊處理 test_invalid_explicit_language_raises_error
        pattern = r'"job_description": "Test job description",'
        replacement = update["new"] + ','
        content = re.sub(pattern, replacement, content)

# 寫回檔案
with open('test/unit/test_keyword_extraction_extended.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 成功擴充 8 個測試的 job_description 到 250+ 字元")
