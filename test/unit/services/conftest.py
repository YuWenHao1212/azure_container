"""
Shared fixtures for service layer unit tests.

Based on TEST_SPEC_SERVICE_MODULES.md and MOCK_STRATEGY_GUIDE.md
Provides standard fixtures and test data for all service tests.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

# ==================== TEST DATA FIXTURES ====================

@pytest.fixture
def valid_english_jd():
    """Valid English job description (>200 chars)."""
    return """
We are looking for a Senior Python Developer with 5+ years of experience
in building scalable web applications using FastAPI and Django frameworks.
Strong knowledge of Docker, Kubernetes, and AWS cloud services is required.
The ideal candidate must have excellent problem-solving skills and ability
to work independently in a fast-paced agile environment. Experience with
microservices architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB,
Redis, and distributed systems is highly valued. Must be proficient in
CI/CD pipelines, automated testing, and modern development practices.
""".strip()  # 450+ characters


@pytest.fixture
def valid_chinese_jd():
    """Valid Traditional Chinese job description (>200 chars)."""
    return """
我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，
熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，
並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。
同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。
需要至少五年以上的後端開發經驗，能夠在快節奏環境中獨立工作。
必須具備良好的溝通能力和問題解決能力，並能在團隊中發揮領導作用。
熟悉敏捷開發流程，有Scrum或Kanban經驗者佳。
""".strip()  # 350+ characters


@pytest.fixture
def valid_mixed_jd_high_chinese():
    """Mixed language JD with >20% Traditional Chinese (>200 chars)."""
    return """
We are seeking a 資深Python開發工程師 with expertise in 微服務架構 and 雲端服務.
The candidate should have experience with FastAPI框架, Docker容器技術, and Azure服務.
Must be skilled in 分散式系統設計 and 測試驅動開發 methodologies.
Strong background in 後端開發 with 5+ years experience in 軟體工程 is required.
Knowledge of CI/CD流程, PostgreSQL資料庫, and 系統架構規劃 is essential.
Must have excellent 溝通能力 and 問題解決能力 to work effectively in our 敏捷團隊.
The ideal candidate will lead 技術創新 and mentor 初級工程師 in best practices.
""".strip()  # 400+ characters, >25% Traditional Chinese


@pytest.fixture
def valid_mixed_jd_low_chinese():
    """Mixed language JD with <20% Traditional Chinese (>200 chars)."""
    return """
We are looking for a Senior Python Developer with extensive experience in building
scalable web applications using FastAPI and Django frameworks. The ideal candidate
should have strong knowledge of Docker, Kubernetes, and AWS cloud services.
Experience with microservices architecture, RESTful APIs, GraphQL, PostgreSQL,
MongoDB, Redis, and distributed systems is highly valued. Must be proficient in
CI/CD pipelines, automated testing, and 軟體工程 best practices. 資深工程師 preferred.
Strong problem-solving skills and ability to work in fast-paced environment required.
""".strip()  # 400+ characters, <10% Traditional Chinese


@pytest.fixture
def invalid_short_text():
    """Text that is too short (<200 chars)."""
    return "Python Developer with FastAPI experience needed. Must have Docker and Kubernetes knowledge."  # <200 chars


@pytest.fixture
def boundary_text_199():
    """Text with exactly 199 characters (should fail)."""
    # Create text that is exactly 199 characters
    text = "We are looking for a Python Developer with experience in FastAPI and Django frameworks. " \
           "Must have Docker and Kubernetes knowledge. AWS cloud experience required. " \
           "Strong problem-solving skills needed now."
    return text[:199]  # Exactly 199 characters


@pytest.fixture
def boundary_text_200():
    """Text with exactly 200 characters (should pass)."""
    text = "We are looking for a Python Developer with experience in FastAPI and Django. " \
           "Must have Docker and Kubernetes knowledge. AWS experience required. " \
           "Strong problem-solving skills needed. Join us!"
    return text[:200]  # Exactly 200 characters


@pytest.fixture
def simplified_chinese_text():
    """Simplified Chinese text (should be rejected)."""
    return """
我们正在寻找一位高级Python开发工程师，需要具备FastAPI框架经验，
熟悉Docker容器技术和Azure云端服务。理想的候选人应该对微服务架构有深入理解，
并且有RESTful API开发经验。具备CI/CD流程和测试驱动开发经验者优先。
同时需要熟悉分布式系统设计，具备系统架构规划能力和团队合作精神。
需要至少五年以上的后端开发经验，能够在快节奏环境中独立工作。
具备良好的沟通能力和问题解决能力，有金融科技或电子商务经验优先考虑。
""".strip()  # 220+ characters, Simplified Chinese


@pytest.fixture
def japanese_text():
    """Japanese text (should be rejected)."""
    return """
私たちは、FastAPIフレームワークの経験を持つシニアPython開発エンジニアを探しています。
Dockerコンテナ技術とAzureクラウドサービスに精通していることが求められます。
理想的な候補者は、マイクロサービスアーキテクチャについて深い理解を持ち、
RESTful API開発の経験があることが必要です。CI/CDプロセスとテスト駆動開発の経験がある方を優先します。
分散システム設計に精通し、システムアーキテクチャの計画能力とチームワーク精神を持っていることが必要です。
""".strip()  # 250+ characters, Japanese


@pytest.fixture
def korean_text():
    """Korean text (should be rejected)."""
    return """
FastAPI 프레임워크 경험을 가진 시니어 Python 개발 엔지니어를 찾고 있습니다.
Docker 컨테이너 기술과 Azure 클라우드 서비스에 능숙해야 합니다.
이상적인 후보자는 마이크로서비스 아키텍처에 대한 깊은 이해와
RESTful API 개발 경험이 있어야 합니다. CI/CD 프로세스와 테스트 주도 개발 경험을 우선시합니다.
분산 시스템 설계에 익숙하고 시스템 아키텍처 계획 능력과 팀워크 정신이 필요합니다.
""".strip()  # 250+ characters, Korean


@pytest.fixture
def text_with_html_tags():
    """Text with HTML tags that should be handled properly."""
    return """
<p>We are looking for a <strong>Senior Python Developer</strong> with 5+ years of experience
in building scalable web applications using <em>FastAPI</em> and Django frameworks.</p>
<ul>
<li>Strong knowledge of Docker, Kubernetes, and AWS cloud services</li>
<li>Experience with microservices architecture and RESTful APIs</li>
<li>Proficient in CI/CD pipelines and automated testing</li>
</ul>
Must have excellent problem-solving skills and ability to work independently.
""".strip()  # 350+ characters with HTML


@pytest.fixture
def large_text_3000_chars():
    """Large text with 3000+ characters for performance testing."""
    base_text = """
We are looking for a Senior Python Developer with extensive experience in building
scalable web applications using modern frameworks and technologies.
"""
    # Repeat and expand to reach 3000+ characters
    return (base_text * 15)[:3000] + " Join our innovative team today!"


# ==================== MOCK FIXTURES ====================

@pytest.fixture
def mock_azure_openai_client():
    """Mock Azure OpenAI client for service tests."""
    client = Mock()

    # Chat completions structure
    client.chat = Mock()
    client.chat.completions = Mock()

    # Default successful response
    client.chat.completions.create = AsyncMock(
        return_value=Mock(
            id="chatcmpl-test",
            object="chat.completion",
            created=1234567890,
            model="gpt-4",
            choices=[
                Mock(
                    index=0,
                    message=Mock(
                        role="assistant",
                        content='{"keywords": ["Python", "FastAPI", "Docker", "Azure", "Microservices"]}'
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Mock(
                prompt_tokens=150,
                completion_tokens=50,
                total_tokens=200
            )
        )
    )

    return client


@pytest.fixture
def mock_llm_factory():
    """Mock LLM Factory for dynamic model selection."""
    with patch('src.services.llm_factory.get_llm_client') as mock_get_client, \
         patch('src.services.llm_factory.get_llm_client_smart') as mock_get_smart, \
         patch('src.services.llm_factory.get_llm_info') as mock_get_info:

        # Set default return values
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_get_smart.return_value = mock_client
        mock_get_info.return_value = {
            'model': 'gpt-4.1-mini',
            'region': 'japaneast',
            'deployment': 'gpt-41-mini-japaneast'
        }

        yield {
            'get_client': mock_get_client,
            'get_smart': mock_get_smart,
            'get_info': mock_get_info,
            'client': mock_client
        }


@pytest.fixture
def mock_langdetect():
    """Mock langdetect library functions."""
    with patch('src.services.language_detection.detector.detect') as mock_detect, \
         patch('src.services.language_detection.detector.detect_langs') as mock_detect_langs:

        # Default to English detection
        mock_detect.return_value = 'en'
        mock_detect_langs.return_value = [Mock(lang='en', prob=0.95)]

        yield {
            'detect': mock_detect,
            'detect_langs': mock_detect_langs
        }


@pytest.fixture
def mock_prompt_service():
    """Mock Unified Prompt Service."""
    with patch('src.services.unified_prompt_service.UnifiedPromptService') as MockClass:
        instance = Mock()
        MockClass.return_value = instance

        # Default methods
        instance.get_prompt = Mock(return_value={
            'content': 'Test prompt content',
            'version': '1.4.0',
            'language': 'en'
        })
        instance.get_active_version = Mock(return_value='1.4.0')
        instance.list_versions = Mock(return_value=['1.0.0', '1.2.0', '1.3.0', '1.4.0'])

        yield instance


@pytest.fixture
def mock_monitoring_service():
    """Mock monitoring service."""
    with patch('src.core.monitoring_service.monitoring_service') as mock_service:
        mock_service.track_metric = Mock()
        mock_service.track_event = Mock()
        mock_service.log_error = Mock()
        yield mock_service


# ==================== HELPER FUNCTIONS ====================

def create_language_detection_result(language='en', confidence=0.95, is_supported=True, detection_time_ms=50):
    """Helper to create LanguageDetectionResult."""
    from src.services.language_detection.detector import LanguageDetectionResult
    return LanguageDetectionResult(
        language=language,
        confidence=confidence,
        is_supported=is_supported,
        detection_time_ms=detection_time_ms
    )


def create_mock_prompt_config(version='1.4.0', language='en'):
    """Helper to create mock prompt configuration."""
    return Mock(
        version=version,
        metadata=Mock(
            status='active',
            author='test',
            description='Test prompt',
            created_at='2025-01-01'
        ),
        llm_config=Mock(
            temperature=0.3,
            max_tokens=500,
            seed=42,
            top_p=0.95
        ),
        multi_round_config={'enabled': True}
    )
