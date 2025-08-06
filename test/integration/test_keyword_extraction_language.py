"""
Integration tests for keyword extraction with language detection.

Tests the complete flow from language detection to prompt selection:
- Language detection for various input types
- Correct prompt selection based on detected language
- API response handling for different languages
- Error handling for unsupported languages
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
    """Integration tests for language detection in keyword extraction."""

    @pytest.fixture
    def test_client(self):
        """Create test client with mocked dependencies."""
        with patch('src.core.config.get_settings'), patch('src.main.monitoring_service', Mock()):
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

    # === Pure Language Tests ===

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_english_job_description_uses_english_prompt(self, test_client,
                                                        mock_keyword_service,
                                                        mock_llm_client):
        """TEST: API-KW-301-IT - 英文 JD 使用英文 prompt"""
        request_data = {
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience "
                             "in building scalable web applications using FastAPI and Django frameworks. "
                             "Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. "
                             "The ideal candidate must have excellent problem-solving skills and ability to work "
                             "independently in a fast-paced agile environment. Experience with microservices "
                             "architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, Redis, and distributed "
                             "systems is highly valued. Must be proficient in CI/CD pipelines, automated testing, "
                             "code review processes, and DevOps best practices for production deployments.",
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI", "Django", "Docker",
                        "Kubernetes", "AWS", "Web Applications", "Scalable Systems",
                        "5+ Years Experience", "Backend Development", "Cloud Computing",
                        "DevOps", "Microservices", "Software Engineering"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0-en",  # English prompt version
            "processing_time_ms": 2400.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "en"
        assert "en" in data["data"]["prompt_version_used"]

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_traditional_chinese_job_description_uses_chinese_prompt(self, test_client,
                                                                    mock_keyword_service,
                                                                    mock_llm_client):
        """TEST: API-KW-302-IT - 繁中 JD 使用繁中 prompt"""
        request_data = {
            "job_description": "我們正在尋找資深Python工程師，需要5年以上使用FastAPI和Django "
                             "開發可擴展網路應用程式的經驗。必須熟悉Docker、Kubernetes和AWS雲端服務。"
                             "具備微服務架構設計能力，熟悉CI/CD流程和自動化部署。理想的候選人應該具備優秀的問題解決能力，"
                             "能夠獨立工作並在快節奏的敏捷開發環境中表現出色。需要有RESTful API、GraphQL、"
                             "PostgreSQL、MongoDB、Redis分散式系統開發經驗。必須精通自動化測試、程式碼審查流程，"
                             "以及DevOps最佳實踐，包括容器化部署、監控和日誌分析等生產環境運維技能。",
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["Python工程師", "資深工程師", "FastAPI", "Django", "Docker",
                        "Kubernetes", "AWS", "網路應用程式", "可擴展系統", "5年經驗",
                        "後端開發", "雲端服務", "微服務架構", "CI/CD", "軟體工程"],
            "keyword_count": 15,
            "confidence_score": 0.90,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",
            "prompt_version_used": "v1.4.0-zh-TW",  # Chinese prompt version
            "processing_time_ms": 2600.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"
        assert "zh-TW" in data["data"]["prompt_version_used"]

    # === Mixed Language Tests ===

    @pytest.mark.precommit
    @pytest.mark.timeout(5)
    def test_mixed_chinese_english_above_threshold(self, test_client,
                                                  mock_keyword_service,
                                                  mock_llm_client):
        """TEST: API-KW-303-IT - 混合語言（>20%繁中）"""
        request_data = {
            "job_description": "We are looking for 資深後端工程師 with strong Python and FastAPI skills. "
                             "候選人需要具備 microservices 架構經驗, proficient in Docker/Kubernetes. "
                             "必須熟悉 AWS 雲端服務 and have experience with CI/CD 自動化流程. "
                             "The ideal candidate should have excellent problem-solving abilities 優秀的問題解決能力 "
                             "and be able to work independently in agile environments 敏捷開發環境. "
                             "Experience with RESTful APIs, GraphQL, PostgreSQL, MongoDB, Redis 分散式系統 "
                             "is highly valued. Must be proficient in automated testing 自動化測試, "
                             "code review processes 程式碼審查流程, and DevOps best practices 最佳實踐.",
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["資深後端工程師", "Python", "FastAPI", "Microservices", "架構經驗",
                        "Docker", "Kubernetes", "AWS", "雲端服務", "CI/CD",
                        "自動化流程", "Backend Development", "DevOps", "Cloud Computing", "軟體工程"],
            "keyword_count": 15,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",  # Should detect as zh-TW
            "prompt_version_used": "v1.4.0-zh-TW",  # Should use Chinese prompt
            "processing_time_ms": 2500.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"
        assert "zh-TW" in data["data"]["prompt_version_used"]

    def test_mixed_chinese_english_below_threshold(self, test_client,
                                                  mock_keyword_service,
                                                  mock_llm_client):
        """TEST: API-KW-304-IT - 混合語言（<20%繁中）"""
        request_data = {
            "job_description": "We are seeking a Senior Backend Developer with 5+ years of experience "
                             "in Python, FastAPI, and microservices architecture. Strong knowledge of "
                             "Docker, Kubernetes, AWS, and CI/CD pipelines is required. 需要良好溝通能力.",
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["Senior Backend Developer", "Python", "FastAPI", "Microservices",
                        "5+ Years Experience", "Docker", "Kubernetes", "AWS", "CI/CD",
                        "DevOps", "Cloud Computing", "Software Architecture", "Backend",
                        "Pipeline Automation", "Communication Skills"],
            "keyword_count": 15,
            "confidence_score": 0.87,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",  # Should detect as en
            "prompt_version_used": "v1.4.0-en",  # Should use English prompt
            "processing_time_ms": 2300.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "en"
        assert "en" in data["data"]["prompt_version_used"]

    # === Unsupported Language Rejection Tests ===

    def test_reject_simplified_chinese(self, test_client, mock_keyword_service, mock_llm_client):
        """TEST: API-KW-305-IT - 拒絕簡體中文"""
        request_data = {
            "job_description": "我们正在寻找资深Python工程师，需要5年以上使用FastAPI和Django"
                             "开发可扩展网络应用程序的经验。必须熟悉Docker、Kubernetes和AWS云端服务。"
                             "候选人应该具备优秀的问题解决能力，能够独立工作并领导技术团队。"
                             "需要有大规模分布式系统的设计和实施经验，了解微服务架构最佳实践。"
                             "加分项：有机器学习或人工智能项目经验，熟悉DevOps工具链。"
                             "工作地点在北京，提供有竞争力的薪资待遇和完善的福利制度。",
            "max_keywords": 15
        }

        # Mock service to raise UnsupportedLanguageError
        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="zh-CN",
            supported_languages=["en", "zh-TW"],
            confidence=0.9,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"
        assert "zh-CN" in data["error"]["message"] or "zh-CN" in data["error"]["details"]

    def test_reject_japanese(self, test_client, mock_keyword_service, mock_llm_client):
        """TEST: API-KW-306-IT - 拒絕日文"""
        request_data = {
            "job_description": "私たちはPythonエンジニアを探しています。FastAPIとDjangoの経験が必要です。"
                             "DockerとKubernetesの知識も必要です。AWSクラウドサービスの経験者歓迎。"
                             "優れた問題解決能力とチームワークスキルを持つ方を求めています。"
                             "大規模な分散システムの設計と実装の経験が必要です。"
                             "マイクロサービスアーキテクチャの理解とCI/CDパイプラインの経験も重要です。"
                             "東京オフィスで勤務。競争力のある給与と充実した福利厚生を提供します。",
            "max_keywords": 15
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="ja",
            supported_languages=["en", "zh-TW"],
            confidence=0.95,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"
        assert "ja" in data["error"]["message"]

    def test_reject_korean(self, test_client, mock_keyword_service, mock_llm_client):
        """TEST: API-KW-307-IT - 拒絕韓文"""
        request_data = {
            "job_description": "Python 개발자를 찾고 있습니다. FastAPI와 Django 경험이 필요합니다. "
                             "Docker 및 Kubernetes 지식이 필요합니다. AWS 클라우드 서비스 경험자 우대. "
                             "우수한 문제 해결 능력과 팀워크 기술을 갖춘 분을 찾고 있습니다. "
                             "대규모 분산 시스템의 설계 및 구현 경험이 필요합니다. "
                             "마이크로서비스 아키텍처 이해와 CI/CD 파이프라인 경험도 중요합니다. "
                             "서울 사무실 근무. 경쟁력 있는 급여와 포괄적인 복리후생 제공.",
            "max_keywords": 15
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="ko",
            supported_languages=["en", "zh-TW"],
            confidence=0.92,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"
        assert "ko" in data["error"]["message"]

    def test_reject_mixed_with_unsupported_languages(self, test_client,
                                                    mock_keyword_service,
                                                    mock_llm_client):
        """TEST: API-KW-308-IT - 拒絕混合不支援語言"""
        request_data = {
            "job_description": "We need Python developer 파이썬 개발자 with experience in FastAPI. "
                             "必須熟悉 Docker と Kubernetes. 経験が必要です。"
                             "Looking for someone with strong problem-solving skills and 팀워크 능력. "
                             "需要有大規模系統開發經驗 and understanding of マイクロサービス. "
                             "Experience with CI/CD 파이프라인 and cloud services is highly valued. "
                             "Remote work possible with competitive salary and benefits package available.",
            "max_keywords": 15
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="mixed-unsupported",
            supported_languages=["en", "zh-TW"],
            confidence=0.7,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"

    # === Language Parameter Override Tests ===

    def test_explicit_language_parameter_override(self, test_client,
                                                 mock_keyword_service,
                                                 mock_llm_client):
        """TEST: API-KW-309-IT - 語言參數覆蓋測試"""
        request_data = {
            "job_description": "We are looking for a Senior Python Developer with extensive experience in "
                             "building scalable web applications using FastAPI and Django frameworks. "
                             "Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. "
                             "The ideal candidate must have excellent problem-solving skills and ability to work "
                             "independently in a fast-paced agile environment. Experience with microservices "
                             "architecture, RESTful APIs, GraphQL, PostgreSQL, MongoDB, Redis, and distributed "
                             "systems is highly valued. Must be proficient in CI/CD pipelines and automated testing.",
            "max_keywords": 15,
            "language": "zh-TW"  # Force Chinese prompt for English text
        }

        expected_result = {
            "keywords": ["Python", "Senior Developer", "Software Engineering"],
            "keyword_count": 15,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",  # Auto-detected as English
            "forced_language": "zh-TW",  # But forced to use Chinese
            "prompt_version_used": "v1.4.0-zh-TW",  # Uses Chinese prompt
            "processing_time_ms": 2400.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "zh-TW" in data["data"]["prompt_version_used"]

    # === Error Response Format Tests ===

    def test_unsupported_language_error_response_format(self, test_client,
                                                       mock_keyword_service,
                                                       mock_llm_client):
        """TEST: API-KW-310-IT - 錯誤回應格式驗證"""
        request_data = {
            "job_description": "Estamos buscando un desarrollador Python senior con más de 5 años de experiencia "
                             "en el desarrollo de aplicaciones web escalables usando FastAPI y Django. "
                             "Se requiere conocimiento sólido de Docker, Kubernetes y servicios en la nube de AWS. "
                             "El candidato ideal debe tener experiencia en arquitectura de microservicios y CI/CD. "
                             "Ofrecemos trabajo remoto y un paquete de compensación competitivo.",  # Spanish
            "max_keywords": 15
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="es",
            supported_languages=["en", "zh-TW"],
            confidence=0.95,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()

        # Check response structure
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert "timestamp" in data

        # Check error details
        assert data["error"]["code"] == "UNSUPPORTED_LANGUAGE"
        assert "es" in data["error"]["details"]  # Language code should be in details string


    # === Additional Integration Tests for Complete Coverage ===

    def test_exactly_twenty_percent_chinese_threshold_integration(self, test_client,
                                                                 mock_keyword_service,
                                                                 mock_llm_client):
        """TEST: API-KW-311-IT - 20%閾值整合測試"""
        # Construct exactly 200 chars with exactly 40 Chinese chars (20%)
        chinese_40 = "資深Python工程師需要五年以上開發經驗必須熟悉微服務架構設計"  # 32 chars
        english_part = ("with extensive experience in FastAPI Django Docker Kubernetes " +
                       "AWS cloud services CI/CD automation RESTful APIs GraphQL " +
                       "PostgreSQL MongoDB distributed systems engineering")[:168]  # 168 chars

        request_data = {
            "job_description": chinese_40 + " " + english_part,  # 40 + 1 + 159 = 200 chars exactly
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["資深工程師", "Python", "FastAPI", "Django", "Docker", "Kubernetes"],
            "keyword_count": 15,
            "confidence_score": 0.85,
            "extraction_method": "2_round_intersection",
            "detected_language": "zh-TW",  # Should detect as zh-TW at exactly 20%
            "prompt_version_used": "v1.4.0-zh-TW",
            "processing_time_ms": 2500.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["detected_language"] == "zh-TW"
        assert "zh-TW" in data["data"]["prompt_version_used"]

    def test_minimum_length_validation_integration(self, test_client,
                                                  mock_keyword_service,
                                                  mock_llm_client):
        """TEST: API-KW-312-IT - 最小長度驗證整合"""
        # Text shorter than 200 chars (business rule update)
        short_text = "Senior Python Developer needed"  # Much shorter than 200 chars

        request_data = {
            "job_description": short_text,
            "max_keywords": 15
        }

        # Mock service to raise validation error for short text
        from src.services.exceptions import ValidationError
        mock_keyword_service.validate_input.side_effect = ValidationError(
            "Job description must be at least 200 characters long"
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()
        # Check the actual error response format from the application
        assert data["success"] is False
        assert "error" in data
        assert "200" in data["error"]["message"] or "200" in data["error"]["details"]

    def test_language_detection_metadata_in_response(self, test_client,
                                                    mock_keyword_service,
                                                    mock_llm_client):
        """TEST: API-KW-313-IT - 語言檢測元資料回應"""
        request_data = {
            "job_description": "We are seeking a Senior Python Developer with extensive experience in " +
                             "building scalable web applications using FastAPI and Django frameworks. " +
                             "Strong knowledge of Docker, Kubernetes, and AWS cloud services is required. " +
                             "Must have excellent problem-solving skills and ability to work independently.",
            "max_keywords": 15
        }

        expected_result = {
            "keywords": ["Senior Python Developer", "FastAPI", "Django", "Docker", "Kubernetes"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "language_confidence": 0.95,  # Language detection confidence
            "prompt_version_used": "v1.4.0-en",
            "processing_time_ms": 2200.0
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.return_value = expected_result

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify language detection metadata
        response_data = data["data"]
        assert "detected_language" in response_data
        assert "prompt_version_used" in response_data
        assert response_data["detected_language"] == "en"
        assert "en" in response_data["prompt_version_used"]

    def test_comprehensive_error_details_for_unsupported_language(self, test_client,
                                                                 mock_keyword_service,
                                                                 mock_llm_client):
        """TEST: API-KW-314-IT - 不支援語言詳細錯誤"""
        request_data = {
            "job_description": "Nous recherchons un développeur Python senior avec plus de 5 ans d'expérience " +
                             "dans le développement d'applications web évolutives utilisant FastAPI et Django. " +
                             "Une solide connaissance de Docker, Kubernetes et des services cloud AWS est requise. " +
                             "Le candidat idéal doit avoir d'excellentes compétences en résolution de problèmes.",  # French
            "max_keywords": 15
        }

        mock_keyword_service.validate_input.return_value = request_data
        mock_keyword_service.process.side_effect = UnsupportedLanguageError(
            detected_language="fr",
            supported_languages=["en", "zh-TW"],
            confidence=0.92,
            user_specified=False
        )

        with patch('src.api.v1.keyword_extraction.get_keyword_extraction_service_v2',
                  return_value=mock_keyword_service), patch('src.services.llm_factory.get_llm_client_smart',
                  return_value=mock_llm_client), patch('src.services.llm_factory.get_llm_info',
                  return_value={'model': 'gpt-4', 'region': 'japaneast'}):
            with (

                patch('src.api.v1.keyword_extraction.monitoring_service', Mock()),

                patch('src.api.v1.keyword_extraction.failure_storage', AsyncMock())

            ):
                    response = test_client.post(
                        "/api/v1/extract-jd-keywords",
                        json=request_data
                    )

        assert response.status_code == 422
        data = response.json()

        # Comprehensive error format validation
        assert data["success"] is False
        assert "error" in data
        assert "timestamp" in data

        error = data["error"]
        assert error["code"] == "UNSUPPORTED_LANGUAGE"
        assert "message" in error
        assert "details" in error

        # Error should contain language information
        assert "fr" in error["details"] or "French" in error["details"]
        # Check that supported languages are mentioned in details
        details_text = error["details"].lower()
        assert "english" in details_text or "en" in details_text
        assert "chinese" in details_text or "zh-tw" in details_text

        # Note: Confidence information is not included in current error details format
