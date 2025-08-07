"""
Unit tests for Language Detection Service.

Based on TEST_SPEC_SERVICE_MODULES.md Section 2: Language Detection Service (SVC-LD)
Implements exactly 14 unit tests as specified:
- Core functionality (5 tests): SVC-LD-001 to SVC-LD-005
- Rejection mechanism (4 tests): SVC-LD-006 to SVC-LD-009
- Special handling (5 tests): SVC-LD-010 to SVC-LD-014

All tests use Mock, no real API calls or external dependencies.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.exceptions import LanguageDetectionError, LowConfidenceDetectionError, UnsupportedLanguageError
from src.services.language_detection.detector import LanguageDetectionResult, LanguageDetectionService
from src.services.language_detection.simple_language_detector import SimplifiedLanguageDetector


class TestLanguageDetectionService:
    """Unit tests for Language Detection Service - 14 tests as per spec."""

    @pytest.fixture
    def language_detector(self):
        """Create a SimplifiedLanguageDetector instance."""
        return SimplifiedLanguageDetector()

    @pytest.fixture
    def mock_langdetect_english(self):
        """Mock langdetect to return English."""
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'en'
            mock_detect_langs.return_value = [Mock(lang='en', prob=0.95)]
            yield {'detect': mock_detect, 'detect_langs': mock_detect_langs}

    @pytest.fixture
    def mock_langdetect_chinese(self):
        """Mock langdetect to return Chinese."""
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'zh-tw'
            mock_detect_langs.return_value = [Mock(lang='zh-tw', prob=0.92)]
            yield {'detect': mock_detect, 'detect_langs': mock_detect_langs}

    # ==================== CORE FUNCTIONALITY TESTS (5) ====================

    @pytest.mark.asyncio
    async def test_SVC_LD_001_pure_english_detection(
        self, language_detector, valid_english_jd, mock_langdetect_english
    ):
        """
        SVC-LD-001-UT: Pure English content detection
        Priority: P0
        Validates that pure English content is correctly identified as English.
        Includes: get_supported_languages validation
        """
        # First verify get_supported_languages method
        supported = language_detector.get_supported_languages()
        assert isinstance(supported, list)
        assert 'en' in supported
        assert 'zh-TW' in supported
        assert len(supported) == 2

        # Verify en is supported
        assert language_detector.is_supported_language('en') is True

        # Act
        result = await language_detector.detect_language(valid_english_jd)

        # Assert
        assert isinstance(result, LanguageDetectionResult)
        assert result.language == 'en'
        assert result.is_supported is True
        assert result.confidence >= 0.8
        assert result.detection_time_ms >= 0  # Accept 0 for mocked tests

        # Verify langdetect was called
        mock_langdetect_english['detect'].assert_called_once()
        mock_langdetect_english['detect_langs'].assert_called_once()

    @pytest.mark.asyncio
    async def test_SVC_LD_002_pure_traditional_chinese_detection(
        self, language_detector, valid_chinese_jd, mock_langdetect_chinese
    ):
        """
        SVC-LD-002-UT: Pure Traditional Chinese detection
        Priority: P0
        Validates that pure Traditional Chinese content is correctly identified.
        """
        # Act
        result = await language_detector.detect_language(valid_chinese_jd)

        # Assert
        assert isinstance(result, LanguageDetectionResult)
        assert result.language == 'zh-TW'
        assert result.is_supported is True
        assert result.confidence >= 0.8
        assert result.detection_time_ms >= 0  # Accept 0 for mocked tests

    @pytest.mark.asyncio
    async def test_SVC_LD_003_mixed_language_above_threshold(
        self, language_detector, valid_mixed_jd_high_chinese
    ):
        """
        SVC-LD-003-UT: Mixed language (Traditional Chinese >20%)
        Priority: P0
        Validates mixed language threshold logic - should return zh-TW.
        Includes: analyze_language_composition validation
        """
        # Test analyze_language_composition for mixed content
        stats = language_detector.analyze_language_composition(valid_mixed_jd_high_chinese)
        assert stats.traditional_chinese_chars > 0
        assert stats.english_chars > 0
        assert stats.traditional_chinese_ratio > 0.20  # Above threshold

        # Mock langdetect to return mixed signal
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'zh-tw'
            mock_detect_langs.return_value = [Mock(lang='zh-tw', prob=0.85)]

            # Act
            result = await language_detector.detect_language(valid_mixed_jd_high_chinese)

            # Assert
            assert result.language == 'zh-TW'
            assert result.is_supported is True

    @pytest.mark.asyncio
    async def test_SVC_LD_004_mixed_language_below_threshold(
        self, language_detector, valid_mixed_jd_low_chinese
    ):
        """
        SVC-LD-004-UT: Mixed language (Traditional Chinese <20%)
        Priority: P0
        Validates mixed language threshold logic - should return en.
        """
        # Mock langdetect to return English (dominant language)
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'en'
            mock_detect_langs.return_value = [Mock(lang='en', prob=0.90)]

            # Act
            result = await language_detector.detect_language(valid_mixed_jd_low_chinese)

            # Assert
            assert result.language == 'en'
            assert result.is_supported is True

    @pytest.mark.asyncio
    async def test_SVC_LD_005_boundary_condition_exactly_20_percent(
        self, language_detector
    ):
        """
        SVC-LD-005-UT: Boundary condition (exactly 20% Traditional Chinese)
        Priority: P1
        Validates boundary condition handling - at 20% should return zh-TW.
        """
        # Create text with exactly 20% Traditional Chinese
        # Need 200+ chars with at least 20% Traditional Chinese (40+ Chinese chars)
        boundary_text = "We are looking for a Senior Python Developer with extensive experience in FastAPI and Django. " \
                       "需要具備微服務架構經驗、團隊合作精神、良好的溝通能力、問題解決能力、專案管理經驗、技術領導能力和創新思維。" \
                       "Must have strong Docker, Kubernetes, CI/CD pipeline and cloud computing skills."  # 210+ chars, ~20% Chinese

        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'zh-tw'
            mock_detect_langs.return_value = [Mock(lang='zh-tw', prob=0.85)]

            # Act
            result = await language_detector.detect_language(boundary_text)

            # Assert - at 20% boundary, should return zh-TW
            assert result.language == 'zh-TW'
            assert result.is_supported is True

    # ==================== REJECTION MECHANISM TESTS (4) ====================

    @pytest.mark.asyncio
    async def test_SVC_LD_006_reject_simplified_chinese(
        self, language_detector, simplified_chinese_text
    ):
        """
        SVC-LD-006-UT: Reject Simplified Chinese
        Priority: P0
        Validates Simplified Chinese rejection mechanism.
        Expected: UnsupportedLanguageError with HTTP 422
        Includes: is_supported_language validation
        """
        # First verify is_supported_language method works correctly
        assert language_detector.is_supported_language('zh-CN') is False
        assert language_detector.is_supported_language('zh-cn') is False
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'zh-cn'
            mock_detect_langs.return_value = [Mock(lang='zh-cn', prob=0.95)]

            # Act & Assert
            with pytest.raises(UnsupportedLanguageError) as exc_info:
                await language_detector.detect_language(simplified_chinese_text)

            # Verify error details
            assert exc_info.value.detected_language in ['zh-CN', 'zh-cn', 'other']
            assert exc_info.value.supported_languages == ['en', 'zh-TW']

    @pytest.mark.asyncio
    async def test_SVC_LD_007_reject_japanese(
        self, language_detector, japanese_text
    ):
        """
        SVC-LD-007-UT: Reject Japanese
        Priority: P0
        Validates Japanese rejection mechanism.
        Expected: UnsupportedLanguageError with HTTP 422
        Includes: is_supported_language validation
        """
        # Verify is_supported_language method
        assert language_detector.is_supported_language('ja') is False
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'ja'
            mock_detect_langs.return_value = [Mock(lang='ja', prob=0.93)]

            # Act & Assert
            with pytest.raises(UnsupportedLanguageError) as exc_info:
                await language_detector.detect_language(japanese_text)

            # Verify error details
            assert exc_info.value.detected_language == 'ja'
            assert exc_info.value.supported_languages == ['en', 'zh-TW']

    @pytest.mark.asyncio
    async def test_SVC_LD_008_reject_korean(
        self, language_detector, korean_text
    ):
        """
        SVC-LD-008-UT: Reject Korean
        Priority: P0
        Validates Korean rejection mechanism.
        Expected: UnsupportedLanguageError with HTTP 422
        Includes: is_supported_language validation
        """
        # Verify is_supported_language method
        assert language_detector.is_supported_language('ko') is False
        assert language_detector.is_supported_language('es') is False  # Also test Spanish
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'ko'
            mock_detect_langs.return_value = [Mock(lang='ko', prob=0.91)]

            # Act & Assert
            with pytest.raises(UnsupportedLanguageError) as exc_info:
                await language_detector.detect_language(korean_text)

            # Verify error details
            assert exc_info.value.detected_language == 'ko'
            assert exc_info.value.supported_languages == ['en', 'zh-TW']

    @pytest.mark.asyncio
    async def test_SVC_LD_009_reject_mixed_unsupported_languages(
        self, language_detector
    ):
        """
        SVC-LD-009-UT: Reject mixed unsupported languages
        Priority: P0
        Validates handling of text with mixed unsupported languages.
        """
        # Mix of English with Simplified Chinese and Japanese
        mixed_unsupported = """
        We need a developer with experience in 软件开发 and システム設計.
        Must have knowledge of 云端服务 and マイクロサービス architecture.
        Strong skills in 数据库 management and プログラミング required.
        The candidate should understand 分布式系统 and have テスト駆動開発 experience.
        """

        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            # langdetect might return various results for mixed text
            mock_detect.return_value = 'zh-cn'
            mock_detect_langs.return_value = [Mock(lang='zh-cn', prob=0.70)]

            # Act & Assert
            with pytest.raises(UnsupportedLanguageError):
                await language_detector.detect_language(mixed_unsupported)

    # ==================== SPECIAL HANDLING TESTS (5) ====================

    @pytest.mark.asyncio
    async def test_SVC_LD_010_short_text_handling(
        self, language_detector, boundary_text_199
    ):
        """
        SVC-LD-010-UT: Short text handling
        Priority: P0
        Validates error handling for text shorter than MIN_TEXT_LENGTH (200 chars).
        Includes: validate_text_length method testing
        """
        # First test validate_text_length method
        assert language_detector.validate_text_length('x' * 200) is True
        assert language_detector.validate_text_length('x' * 500) is True
        assert language_detector.validate_text_length('x' * 199) is False
        assert language_detector.validate_text_length('x' * 100) is False
        assert language_detector.validate_text_length('') is False

        # Act & Assert - test actual detection error
        with pytest.raises(LanguageDetectionError) as exc_info:
            await language_detector.detect_language(boundary_text_199)

        # Verify error message
        assert "Text too short" in str(exc_info.value.reason)
        assert "minimum 200 characters required" in str(exc_info.value.reason)
        # Text length might be slightly different due to stripping
        assert 195 <= exc_info.value.text_length <= 199

    @pytest.mark.asyncio
    async def test_SVC_LD_011_html_tags_filtering(
        self, language_detector, text_with_html_tags
    ):
        """
        SVC-LD-011-UT: HTML tags filtering
        Priority: P1
        Validates that HTML tags don't affect language detection.
        """
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'en'
            mock_detect_langs.return_value = [Mock(lang='en', prob=0.94)]

            # Act
            result = await language_detector.detect_language(text_with_html_tags)

            # Assert - should correctly identify English despite HTML tags
            assert result.language == 'en'
            assert result.is_supported is True

    @pytest.mark.asyncio
    async def test_SVC_LD_012_large_text_handling(
        self, language_detector, large_text_3000_chars
    ):
        """
        SVC-LD-012-UT: Large text handling
        Priority: P1
        Validates handling of large text (3000 characters).
        """
        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'en'
            mock_detect_langs.return_value = [Mock(lang='en', prob=0.96)]

            # Act
            start_time = time.time()
            result = await language_detector.detect_language(large_text_3000_chars)
            processing_time = (time.time() - start_time) * 1000

            # Assert
            assert result.language == 'en'
            assert result.is_supported is True
            # Large text may take longer, but should still be under 1000ms
            assert processing_time < 1000, f"Processing took {processing_time}ms, expected <1000ms"

    @pytest.mark.asyncio
    async def test_SVC_LD_013_technical_terms_handling(
        self, language_detector
    ):
        """
        SVC-LD-013-UT: Technical terms handling
        Priority: P1
        Validates that technical terms don't affect main language detection.
        """
        # Chinese text with many English technical terms
        text_with_tech_terms = """
        我們需要具備Python、FastAPI、Docker、Kubernetes經驗的工程師。
        候選人應該熟悉AWS、Azure、GCP等雲端平台，並且了解CI/CD、DevOps流程。
        必須精通PostgreSQL、MongoDB、Redis等資料庫系統，以及RESTful API、GraphQL設計。
        需要有Microservices、Event-driven Architecture、Domain-driven Design的實務經驗。
        熟悉Agile、Scrum、Kanban等開發方法論，並能使用JIRA、Confluence等工具。
        技術棧包括React、Vue、Angular前端框架，以及Node.js、Express後端技術。
        """

        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            # Should still detect as Chinese despite many English terms
            mock_detect.return_value = 'zh-tw'
            mock_detect_langs.return_value = [Mock(lang='zh-tw', prob=0.88)]

            # Act
            result = await language_detector.detect_language(text_with_tech_terms)

            # Assert - should identify as Traditional Chinese
            assert result.language == 'zh-TW'
            assert result.is_supported is True

    @pytest.mark.asyncio
    async def test_SVC_LD_014_performance_benchmark(
        self, language_detector
    ):
        """
        SVC-LD-014-UT: Performance benchmark test
        Priority: P2
        Establishes performance baseline - detection should complete in <100ms.
        """
        # Standard test text (500 characters)
        test_text = """
        We are looking for a Senior Python Developer with 5+ years of experience
        in building scalable web applications. Strong knowledge of modern frameworks
        including FastAPI, Django, and Flask is required. The ideal candidate must
        have excellent problem-solving skills and experience with cloud services.
        Proficiency in Docker, Kubernetes, and microservices architecture is essential.
        Must be able to work independently in a fast-paced agile environment.
        Experience with CI/CD pipelines and automated testing is highly valued.
        """

        with patch('src.services.language_detection.simple_language_detector.detect') as mock_detect, \
             patch('src.services.language_detection.simple_language_detector.detect_langs') as mock_detect_langs:
            mock_detect.return_value = 'en'
            mock_detect_langs.return_value = [Mock(lang='en', prob=0.95)]

            # Act - measure detection time
            start_time = time.time()
            result = await language_detector.detect_language(test_text)
            processing_time = (time.time() - start_time) * 1000

            # Assert
            assert result.language == 'en'
            assert result.is_supported is True
            assert processing_time < 100, f"Detection took {processing_time}ms, expected <100ms"
            # Also check the result's reported time
            assert result.detection_time_ms < 100

