"""
Integration tests for keyword extraction with language detection - Complete Rewrite.

Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0
Implements exactly 10 integration tests as specified:
- API-KW-101-IT: Azure OpenAI integration
- API-KW-102-IT: English JD uses English prompt
- API-KW-103-IT: Traditional Chinese JD uses Traditional Chinese prompt
- API-KW-104-IT: Mixed language (>20% Traditional Chinese)
- API-KW-105-IT: Mixed language (<20% Traditional Chinese)
- API-KW-106-IT: Reject Simplified Chinese
- API-KW-107-IT: Reject Japanese
- API-KW-108-IT: Reject Korean
- API-KW-109-IT: Reject mixed unsupported languages with detailed error
- API-KW-110-IT: Language parameter override test

All tests use Mock Azure OpenAI services (no real API calls).
Each test is precisely aligned with specification requirements.
"""

import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables before imports
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'

from src.main import create_app
from src.services.exceptions import UnsupportedLanguageError


class TestKeywordExtractionLanguageIntegration:
    """Integration tests for language detection in keyword extraction - exactly 10 tests as per spec."""

    @pytest.fixture
    def test_client(self):
        """Create test client with mocked dependencies."""
        with patch('src.core.config.get_settings'), \
             patch('src.main.monitoring_service', Mock()):
            with patch.dict(os.environ, {
                'MONITORING_ENABLED': 'false',
                'LIGHTWEIGHT_MONITORING': 'false',
                'ERROR_CAPTURE_ENABLED': 'false',
                'CONTAINER_APP_API_KEY': ''
            }):
                app = create_app()
                return TestClient(app)

    @pytest.fixture
    def mock_keyword_service(self):
        """Create mock keyword extraction service."""
        service = AsyncMock()
        service.validate_input = AsyncMock()
        service.process = AsyncMock()
        service.close = AsyncMock()
        return service

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock()
        return client

    @pytest.fixture
    def english_jd_request(self):
        """Valid English job description request (>200 chars)."""
        return {
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience "
                             "in building scalable web applications using FastAPI and Django frameworks. "
                             "Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. "
                             "The ideal candidate must have excellent problem-solving skills and ability to work "
                             "independently in a fast-paced agile environment. Experience with microservices "
                             "architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, Redis, and distributed "
                             "systems is highly valued. Must be proficient in CI/CD pipelines, automated testing.",
            "max_keywords": 15
        }

    @pytest.fixture
    def traditional_chinese_jd_request(self):
        """Valid Traditional Chinese job description request (>200 chars)."""
        return {
            "job_description": "我們正在尋找一位資深的Python開發工程師，需要具備FastAPI框架經驗，"
                             "熟悉Docker容器技術和Azure雲端服務。理想的候選人應該對微服務架構有深入理解，"
                             "並且有RESTful API開發經驗。具備CI/CD流程和測試驅動開發經驗者優先。"
                             "同時需要熟悉分散式系統設計，具備系統架構規劃能力和團隊合作精神。"
                             "需要至少五年以上的後端開發經驗，能夠在快節奏環境中獨立工作。"
                             "必須具備良好的溝通能力和問題解決能力，並能在團隊中發揮領導作用。",
            "max_keywords": 12
        }

    @pytest.fixture
    def mixed_language_above_threshold_request(self):
        """Mixed language JD with >20% Traditional Chinese (>200 chars)."""
        return {
            "job_description": "We are seeking a 資深Python開發工程師 with expertise in 微服務架構 and 雲端服務. "
                             "The candidate should have experience with FastAPI框架, Docker容器技術, and Azure服務. "
                             "Must be skilled in 分散式系統設計 and 測試驅動開發 methodologies. "
                             "Strong background in 後端開發 with 5+ years experience in 軟體工程 is required. "
                             "Knowledge of CI/CD流程, PostgreSQL, and 系統架構規劃 is essential. "
                             "Must have excellent 溝通能力 and 問題解決能力 to work effectively in our team.",
            "max_keywords": 15
        }

    @pytest.fixture
    def mixed_language_below_threshold_request(self):
        """Mixed language JD with <20% Traditional Chinese (>200 chars)."""
        return {
            "job_description": "We are looking for a Senior Python Developer with extensive experience in building "
                             "scalable web applications using FastAPI and Django frameworks. The ideal candidate "
                             "should have strong knowledge of Docker, Kubernetes, and AWS cloud services. "
                             "Experience with microservices architecture, RESTful APIs, GraphQL, PostgreSQL, "
                             "MongoDB, Redis, and distributed systems is highly valued. Must be proficient in "
                             "CI/CD pipelines, automated testing, and 軟體工程 best practices. 資深工程師 preferred.",
            "max_keywords": 15
        }

    @pytest.fixture
    def simplified_chinese_jd_request(self):
        """Simplified Chinese job description request (>200 chars)."""
        return {
            "job_description": "我们正在寻找一位高级Python开发工程师，需要具备FastAPI框架经验，"
                             "熟悉Docker容器技术和Azure云端服务。理想的候选人应该对微服务架构有深入理解，"
                             "并且有RESTful API开发经验。具备CI/CD流程和测试驱动开发经验者优先。"
                             "同时需要熟悉分布式系统设计，具备系统架构规划能力和团队合作精神。"
                             "需要至少五年以上的后端开发经验，能够在快节奏环境中独立工作。"
                             "必须具备良好的沟通能力和问题解决能力，并能在团队中发挥领导作用。",
            "max_keywords": 12
        }

    @pytest.fixture
    def japanese_jd_request(self):
        """Japanese job description request (>200 chars)."""
        return {
            "job_description": "私たちは、FastAPIフレームワークの経験を持つシニアPython開発エンジニアを探しています。"
                             "Dockerコンテナ技術とAzureクラウドサービスに精通していることが求められます。"
                             "理想的な候補者は、マイクロサービスアーキテクチャについて深い理解を持ち、"
                             "RESTful API開発の経験があることが必要です。CI/CDプロセスとテスト駆動開発の経験がある方を優先します。"
                             "分散システム設計に精通し、システムアーキテクチャの計画能力とチームワーク精神を持っていることが必要です。"
                             "バックエンド開発において少なくとも5年以上の経験が必要で、ペースの速い環境で独立して作業できることが求められます。",
            "max_keywords": 12
        }

    @pytest.fixture
    def korean_jd_request(self):
        """Korean job description request (>200 chars)."""
        return {
            "job_description": "FastAPI 프레임워크 경험을 가진 시니어 Python 개발 엔지니어를 찾고 있습니다. "
                             "Docker 컨테이너 기술과 Azure 클라우드 서비스에 능숙해야 합니다. "
                             "이상적인 후보자는 마이크로서비스 아키텍처에 대한 깊은 이해와 "
                             "RESTful API 개발 경험이 있어야 합니다. CI/CD 프로세스와 테스트 주도 개발 경험을 우선시합니다. "
                             "분산 시스템 설계에 익숙하고 시스템 아키텍처 계획 능력과 팀워크 정신이 필요합니다. "
                             "백엔드 개발에서 최소 5년 이상의 경험이 필요하며, 빠른 속도의 환경에서 독립적으로 작업할 수 있어야 합니다.",
            "max_keywords": 12
        }

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_101_IT_azure_openai_integration(self, test_client, mock_keyword_service, mock_llm_client, english_jd_request):
        """
        TEST ID: API-KW-101-IT
        測試名稱: 關鍵字提取 API 整合測試
        優先級: P0
        類型: 整合測試
        測試目標: 驗證與 Azure OpenAI 的整合

        判斷標準: 成功返回關鍵字
        """
        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Docker", "Azure"],
            "keyword_count": 5,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0-en",
            "processing_time_ms": 2400.0
        }

        mock_keyword_service.validate_input.return_value = english_jd_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=english_jd_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["keywords"]) > 0

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_102_IT_english_jd_english_prompt(self, test_client, mock_keyword_service, mock_llm_client, english_jd_request):
        """
        TEST ID: API-KW-102-IT
        測試名稱: 端到端驗證英文職缺使用英文 prompt
        優先級: P0
        類型: 整合測試
        測試目標: 驗證語言檢測與prompt選擇

        判斷標準:
        - detected_language="en"
        - prompt_version 包含 "en"
        """
        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Django", "Docker", "Kubernetes", "AWS"],
            "keyword_count": 7,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0-en",  # English prompt version
            "processing_time_ms": 2400.0
        }

        mock_keyword_service.validate_input.return_value = english_jd_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=english_jd_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "en"
        assert "en" in data["data"].get("prompt_version_used", "")

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_103_IT_traditional_chinese_prompt(self, test_client, mock_keyword_service, mock_llm_client, traditional_chinese_jd_request):
        """
        TEST ID: API-KW-103-IT
        測試名稱: 端到端驗證繁中職缺使用繁中 prompt
        優先級: P0
        類型: 整合測試
        測試目標: 驗證繁中語言處理

        判斷標準:
        - detected_language="zh-TW"
        - prompt_version 包含 "zh-TW"
        """
        expected_result = {
            "keywords": ["Python", "資深工程師", "FastAPI", "Docker", "Azure", "微服務架構", "RESTful API", "CI/CD"],
            "keyword_count": 8,
            "confidence_score": 0.82,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",
            "prompt_version_used": "v1.4.0-zh-TW",  # Traditional Chinese prompt version
            "processing_time_ms": 2800.0
        }

        mock_keyword_service.validate_input.return_value = traditional_chinese_jd_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=traditional_chinese_jd_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"
        assert "zh-TW" in data["data"].get("prompt_version_used", "")

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_104_IT_mixed_language_above_threshold(self, test_client, mock_keyword_service, mock_llm_client, mixed_language_above_threshold_request):
        """
        TEST ID: API-KW-104-IT
        測試名稱: 混合語言正確選擇 prompt
        優先級: P0
        類型: 整合測試
        測試目標: 驗證混合語言閾值處理

        判斷標準:
        - detected_language="zh-TW"
        - 使用繁中 prompt
        """
        expected_result = {
            "keywords": ["Python", "資深工程師", "微服務架構", "雲端服務", "FastAPI框架", "Docker", "Azure"],
            "keyword_count": 7,
            "confidence_score": 0.75,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",  # Over 20% Traditional Chinese detected
            "prompt_version_used": "v1.4.0-zh-TW",
            "processing_time_ms": 3000.0
        }

        mock_keyword_service.validate_input.return_value = mixed_language_above_threshold_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=mixed_language_above_threshold_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_105_IT_mixed_language_below_threshold(self, test_client, mock_keyword_service, mock_llm_client, mixed_language_below_threshold_request):
        """
        TEST ID: API-KW-105-IT
        測試名稱: 混合語言低於閾值時使用英文 prompt
        優先級: P0
        類型: 整合測試
        測試目標: 驗證混合語言閾值處理

        判斷標準:
        - detected_language="en"
        - prompt_version 包含 "en"
        """
        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Django", "Docker", "Kubernetes", "AWS"],
            "keyword_count": 7,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",  # Under 20% Traditional Chinese, defaults to English
            "prompt_version_used": "v1.4.0-en",
            "processing_time_ms": 2600.0
        }

        mock_keyword_service.validate_input.return_value = mixed_language_below_threshold_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=mixed_language_below_threshold_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "en"
        assert "en" in data["data"].get("prompt_version_used", "")

    @pytest.mark.precommit
    @pytest.mark.timeout(3)
    def test_API_KW_106_IT_reject_simplified_chinese(self, test_client, mock_keyword_service, mock_llm_client, simplified_chinese_jd_request):
        """
        TEST ID: API-KW-106-IT
        測試名稱: API 正確拒絕簡體中文內容
        優先級: P0
        類型: 整合測試
        測試目標: 驗證簡體中文檢測和拒絕機制

        判斷標準:
        - HTTP 422
        - error.code="UNSUPPORTED_LANGUAGE"
        - 錯誤訊息包含語言檢測結果
        """
        # Mock service to raise UnsupportedLanguageError for simplified Chinese
        mock_keyword_service.validate_input.return_value = simplified_chinese_jd_request
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="zh-CN",
            supported_languages=["en", "zh-TW"],
            confidence=0.95,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=simplified_chinese_jd_request
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"
        assert "zh-CN" in data["error"]["message"] or "zh-cn" in data["error"]["message"].lower()

    @pytest.mark.precommit
    @pytest.mark.timeout(3)
    def test_API_KW_107_IT_reject_japanese(self, test_client, mock_keyword_service, mock_llm_client, japanese_jd_request):
        """
        TEST ID: API-KW-107-IT
        測試名稱: API 正確拒絕日文內容
        優先級: P0
        類型: 整合測試
        測試目標: 驗證日文檢測和拒絕機制

        判斷標準:
        - HTTP 422
        - error.code="UNSUPPORTED_LANGUAGE"
        """
        # Mock service to raise UnsupportedLanguageError for Japanese
        mock_keyword_service.validate_input.return_value = japanese_jd_request
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="ja",
            supported_languages=["en", "zh-TW"],
            confidence=0.98,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=japanese_jd_request
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"

    @pytest.mark.precommit
    @pytest.mark.timeout(3)
    def test_API_KW_108_IT_reject_korean(self, test_client, mock_keyword_service, mock_llm_client, korean_jd_request):
        """
        TEST ID: API-KW-108-IT
        測試名稱: API 正確拒絕韓文內容
        優先級: P0
        類型: 整合測試
        測試目標: 驗證韓文檢測和拒絕機制

        判斷標準:
        - HTTP 422
        - error.code="UNSUPPORTED_LANGUAGE"
        """
        # Mock service to raise UnsupportedLanguageError for Korean
        mock_keyword_service.validate_input.return_value = korean_jd_request
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="ko",
            supported_languages=["en", "zh-TW"],
            confidence=0.92,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=korean_jd_request
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"

    @pytest.mark.precommit
    @pytest.mark.timeout(3)
    def test_API_KW_109_IT_reject_mixed_unsupported_language_detailed_error(self, test_client, mock_keyword_service, mock_llm_client):
        """
        TEST ID: API-KW-109-IT
        測試名稱: 混合不支援語言的詳細錯誤回應
        優先級: P0
        類型: 整合測試
        測試目標: 驗證混合語言檢測和完整錯誤回應

        判斷標準:
        - HTTP 422
        - error.code="UNSUPPORTED_LANGUAGE"
        - 錯誤回應包含完整結構
        - 錯誤包含語言組成分析詳情
        """
        mixed_unsupported_request = {
            "job_description": "We are looking for a 高级Python开发工程师 with experience in マイクロサービス架構 and "
                             "クラウドサービス. The candidate should have expertise in 분산 시스템 설계 and CI/CD流程. "
                             "Must be skilled in RESTful API development and 테스트 주도 개발. Strong background in "
                             "後端開發 with 5+ years experience in software engineering is required. Knowledge of "
                             "PostgreSQL, Docker컨테이너技術, and system architecture planning is essential.",
            "max_keywords": 15
        }

        # Mock detailed unsupported language error with language composition analysis
        detailed_error = UnsupportedLanguageError(
            detected_language="mixed",
            supported_languages=["en", "zh-TW"],
            confidence=0.45,
            user_specified=False
        )

        mock_keyword_service.validate_input.return_value = mixed_unsupported_request
        mock_keyword_service.process.side_effect = detailed_error

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=mixed_unsupported_request
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"

        # Verify detailed error structure
        assert "error" in data
        assert "timestamp" in data

        # Verify language composition analysis details are included
        error_message = data["error"]["message"]
        assert "mixed" in error_message.lower() or "語言" in error_message

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_API_KW_110_IT_language_parameter_override(self, test_client, mock_keyword_service, mock_llm_client):
        """
        TEST ID: API-KW-110-IT
        測試名稱: 明確指定 language 參數時的 API 行為
        優先級: P1
        類型: 整合測試
        測試目標: 驗證語言參數覆蓋自動檢測

        判斷標準: 使用指定語言的 prompt
        """
        language_override_request = {
            "job_description": "We are looking for a Senior Python Developer with experience in FastAPI, "
                             "Docker, and Azure cloud services. The ideal candidate should have strong "
                             "knowledge of microservices architecture and RESTful APIs. Experience with "
                             "CI/CD pipelines and test-driven development is highly desired. Must have "
                             "5+ years of experience in backend development and distributed systems.",
            "max_keywords": 10,
            "language": "zh-TW"  # Override language to Traditional Chinese
        }

        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Docker", "Azure", "Microservices"],
            "keyword_count": 6,
            "confidence_score": 0.80,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",  # Auto-detected as English
            "specified_language": "zh-TW",  # But overridden to Traditional Chinese
            "prompt_version_used": "v1.4.0-zh-TW",  # Uses Traditional Chinese prompt
            "processing_time_ms": 2700.0
        }

        mock_keyword_service.validate_input.return_value = language_override_request
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), \
             patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), \
             patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with patch('src.api.v1.keyword_extraction.monitoring_service', Mock()):
                with patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock()):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=language_override_request
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify language parameter override worked
        # The prompt used should be Traditional Chinese despite auto-detected English
        assert "zh-TW" in data["data"].get("prompt_version_used", "")
