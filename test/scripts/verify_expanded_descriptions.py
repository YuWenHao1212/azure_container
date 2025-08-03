#!/usr/bin/env python3
"""Verify expanded job descriptions meet length requirements."""

# 新的 job descriptions
updated_descriptions = [
    ("test_english_detection_selects_english_prompt",
     """Senior Python Developer with FastAPI experience needed. We are looking for
                  an experienced developer with at least 5 years of Python development experience.
                  Strong knowledge of FastAPI, microservices architecture, Docker, and cloud services required.
                  Experience with CI/CD pipelines and test-driven development highly desired."""),

    ("test_chinese_detection_selects_chinese_prompt",
     """尋找資深Python工程師，需要FastAPI經驗。我們正在尋找具有至少5年Python開發經驗的
                  資深工程師。需要精通FastAPI框架、微服務架構、Docker容器技術和雲端服務。具備CI/CD流程
                  和測試驅動開發經驗者優先考慮。需要良好的團隊合作能力和溝通技巧。歡迎對技術充滿熱情的
                  開發者加入我們的團隊，共同開發創新的解決方案。"""),

    ("test_mixed_language_prompt_selection",
     """Looking for 資深工程師 with Python and 機器學習 experience. We need a
                  senior engineer 具備5年以上 Python development 經驗. Strong background in 機器學習,
                  深度學習, and data science required. Experience with TensorFlow, PyTorch, 和 scikit-learn
                  是必須的. 需要有 cloud platforms 經驗, especially AWS or Azure. 優秀的問題解決能力和
                  團隊合作精神 are essential for this role."""),

    ("test_explicit_language_bypasses_detection",
     """Senior Python Developer needed for our growing technology team. We are seeking
                  an experienced developer with strong Python skills and a passion for building scalable
                  applications. The ideal candidate will have experience with web frameworks like Django or
                  FastAPI, RESTful API design, database management, and cloud deployment. Knowledge of
                  microservices architecture and containerization technologies is highly valued."""),

    ("test_invalid_explicit_language_raises_error",
     """Test job description for keyword extraction service validation. This is a
                  comprehensive job posting for a Senior Software Engineer position requiring extensive
                  experience in multiple programming languages and frameworks. The ideal candidate should
                  have strong problem-solving skills, excellent communication abilities, and a proven track
                  record of delivering high-quality software solutions in agile environments."""),

    ("test_format_prompt_with_job_description",
     """Looking for Python developer with strong backend development skills. We need someone
                  with at least 3 years of experience in Python web development, preferably with Django or
                  Flask frameworks. Knowledge of RESTful APIs, database design, and cloud services is essential.
                  The role involves designing and implementing scalable backend services, optimizing application
                  performance, and collaborating with frontend developers to deliver exceptional user experiences."""),

    ("test_service_cleanup_on_success",
     """We are looking for a Senior Python Developer with experience in FastAPI to join
                  our innovative development team. The ideal candidate will have 5+ years of Python experience,
                  deep knowledge of FastAPI framework, and expertise in building high-performance RESTful APIs.
                  Experience with asynchronous programming, microservices architecture, Docker, Kubernetes, and
                  cloud platforms (AWS/Azure/GCP) is required. Strong problem-solving skills and ability to work
                  in an agile environment are essential."""),

    ("test_service_cleanup_on_error",
     """We need a Python developer with experience in building scalable web applications.
                  The successful candidate will have strong Python programming skills, experience with modern
                  web frameworks, and knowledge of software development best practices. Responsibilities include
                  developing new features, maintaining existing codebase, writing unit tests, and participating
                  in code reviews. Experience with agile methodologies and version control systems is required.""")
]

print("驗證擴充後的 job_description 長度\n")
print(f"{'測試函數':<50} {'新長度':<10} {'狀態':<10}")
print("-" * 80)

all_pass = True
for test_name, job_desc in updated_descriptions:
    # 移除多餘空白和換行以獲得實際長度
    clean_desc = ' '.join(job_desc.split())
    length = len(clean_desc)
    status = "✅ OK" if length >= 250 else "❌ 仍然太短"
    if length < 250:
        all_pass = False
    print(f"{test_name:<50} {length:<10} {status:<10}")

if all_pass:
    print("\n✅ 所有測試的 job_description 都已成功擴充到 250+ 字元！")
else:
    print("\n❌ 仍有測試的 job_description 未達到 250 字元要求")
