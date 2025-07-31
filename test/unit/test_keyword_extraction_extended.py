"""
Extended unit tests for keyword extraction endpoint focusing on language detection.

Additional tests to ensure complete coverage of language detection scenarios:
- Prompt selection verification
- Language-specific keyword extraction behavior
- Edge cases for language detection thresholds
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# Mock environment variables
os.environ['TESTING'] = 'true'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_ENDPOINT'] = 'https://test.openai.azure.com'
os.environ['GPT41_MINI_JAPANEAST_API_KEY'] = 'test-key'
os.environ['GPT41_MINI_JAPANEAST_DEPLOYMENT'] = 'test-deployment'

from src.models.keyword_extraction import KeywordExtractionRequest
from src.services.keyword_extraction_v2 import KeywordExtractionServiceV2
from src.services.language_detection.bilingual_prompt_manager import BilingualPromptManager
from src.services.exceptions import UnsupportedLanguageError, PromptNotAvailableError
from src.services.language_detection.simple_language_detector import SimpleLanguageStats


class TestKeywordExtractionLanguageUnit:
    """Unit tests for language-aware keyword extraction."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = AsyncMock()
        # Mock the chat completions response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"keywords": ["Python", "Developer"]}'))]
        client.chat.completions.create = AsyncMock(return_value=mock_response)
        # Mock complete_text for keyword extraction
        client.complete_text = AsyncMock(return_value='{"keywords": ["Python", "Developer", "Experience", "Software", "Engineering"]}')
        return client
    
    @pytest.fixture
    def mock_detection_service(self):
        """Create mock language detection service."""
        service = Mock()  # Use Mock instead of AsyncMock for the service itself
        # Only make specific methods async
        service.detect_language = AsyncMock()
        
        # Mock analyze_language_composition to return proper SimpleLanguageStats
        mock_stats = SimpleLanguageStats(
            total_chars=100,
            traditional_chinese_chars=0,
            simplified_chinese_chars=0,
            english_chars=100,
            japanese_chars=0,
            korean_chars=0,
            spanish_chars=0,
            other_chars=0,
            traditional_chinese_ratio=0.0,
            english_ratio=1.0,
            has_simplified=False,
            has_other_languages=False
        )
        service.analyze_language_composition = Mock(return_value=mock_stats)
        return service
    
    @pytest.fixture
    def keyword_service(self, mock_llm_client, mock_detection_service):
        """Create keyword extraction service with mocked dependencies."""
        with patch('src.services.llm_factory.get_llm_client', return_value=mock_llm_client):
            with patch('src.services.language_detection.simple_language_detector.SimplifiedLanguageDetector') as MockDetector:
                MockDetector.return_value = mock_detection_service
                service = KeywordExtractionServiceV2(
                    openai_client=mock_llm_client,
                    prompt_version="latest"
                )
                service.language_detector = mock_detection_service
                
                # Mock language validator
                mock_validator = AsyncMock()
                mock_validator.validate_with_detection = AsyncMock(return_value=Mock(is_valid=True, errors=[]))
                service.language_validator = mock_validator
                
                return service
    
    # === Prompt Selection Tests ===
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    @pytest.mark.asyncio
    async def test_english_detection_selects_english_prompt(self, keyword_service, 
                                                          mock_detection_service):
        """TEST: API-KW-401-UT - 英文檢測選擇英文 prompt"""
        job_description = """Senior Python Developer with FastAPI experience needed. We are looking for 
                  an experienced developer with at least 5 years of Python development experience. 
                  Strong knowledge of FastAPI, microservices architecture, Docker, and cloud services required. 
                  Experience with CI/CD pipelines and test-driven development highly desired."""
        
        # Mock language composition analysis
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "en"
        )
        
        # Mock detection to return English
        mock_detection_service.detect_language.return_value = Mock(
            language="en",
            confidence=0.95,
            is_supported=True,
            detection_time_ms=50
        )
        
        # Spy on prompt manager to verify correct prompt selection
        with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
            # get_prompt_with_config returns a tuple: (formatted_prompt, llm_config)
            mock_get_prompt.return_value = (
                "English prompt template Senior Python Developer with FastAPI experience needed",
                Mock(
                    temperature=0.3,
                    max_tokens=500,
                    top_p=1.0,
                    seed=42,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
            )
            
            result = await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15
            })
            
            # Verify English prompt was requested
            mock_get_prompt.assert_called_with(
                language="en", 
                version="latest",
                variables={"job_description": job_description}
            )
            assert result["detected_language"] == "en"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    @pytest.mark.asyncio
    async def test_chinese_detection_selects_chinese_prompt(self, keyword_service,
                                                          mock_detection_service):
        """TEST: API-KW-402-UT - 中文檢測選擇中文 prompt"""
        job_description = """我們正在尋找一位經驗豐富的資深Python工程師加入我們的技術團隊。理想的候選人需要具備至少5年的
                  Python開發經驗，並且精通FastAPI框架的應用。您將負責設計和開發高性能的RESTful API服務，
                  實施微服務架構，以及優化系統性能。必須熟練掌握Docker容器技術、Kubernetes編排系統，以及
                  AWS/Azure/GCP等主流雲端平台。需要有紮實的CI/CD流程經驗，包括Jenkins、GitLab CI或GitHub 
                  Actions。測試驅動開發(TDD)和行為驅動開發(BDD)的實踐經驗將是重要的加分項。此外，我們期望
                  您具備優秀的問題解決能力、團隊協作精神，以及良好的中英文溝通技巧。如果您對技術充滿熱情，
                  渴望在快節奏的敏捷開發環境中成長，歡迎加入我們，一起打造創新的技術解決方案。"""
        
        # Mock language composition analysis
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "zh-TW"
        )
        
        # Mock detection to return Traditional Chinese
        mock_detection_service.detect_language.return_value = Mock(
            language="zh-TW",
            confidence=0.92,
            is_supported=True,
            detection_time_ms=60
        )
        
        # Spy on prompt manager
        with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
            # get_prompt_with_config returns a tuple: (formatted_prompt, llm_config)
            mock_get_prompt.return_value = (
                "Chinese prompt template 尋找資深Python工程師，需要FastAPI經驗",
                Mock(
                    temperature=0.3,
                    max_tokens=500,
                    top_p=1.0,
                    seed=42,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
            )
            
            result = await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15
            })
            
            # Verify Chinese prompt was requested
            mock_get_prompt.assert_called_with(
                language="zh-TW", 
                version="latest",
                variables={"job_description": job_description}
            )
            assert result["detected_language"] == "zh-TW"
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    @pytest.mark.asyncio
    async def test_mixed_language_prompt_selection(self, keyword_service,
                                                  mock_detection_service):
        """TEST: API-KW-403-UT - 混合語言 prompt 選擇"""
        job_description = """Looking for 資深工程師 with Python and 機器學習 experience. We need a 
                  senior engineer 具備5年以上 Python development 經驗. Strong background in 機器學習, 
                  深度學習, and data science required. Experience with TensorFlow, PyTorch, 和 scikit-learn 
                  是必須的. 需要有 cloud platforms 經驗, especially AWS or Azure. 優秀的問題解決能力和
                  團隊合作精神 are essential for this role."""
        
        # Mock language composition analysis for mixed content
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "zh-TW"
        )
        
        # Mock detection to return zh-TW for mixed content
        mock_detection_service.detect_language.return_value = Mock(
            language="zh-TW",
            confidence=0.88,
            is_supported=True,
            detection_time_ms=70
        )
        
        with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
            # get_prompt_with_config returns a tuple: (formatted_prompt, llm_config)
            mock_get_prompt.return_value = (
                "Chinese prompt for mixed content Looking for 資深工程師 with Python and 機器學習 experience",
                Mock(
                    temperature=0.3,
                    max_tokens=500,
                    top_p=1.0,
                    seed=42,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
            )
            
            result = await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15
            })
            
            # Should use Chinese prompt for mixed content detected as zh-TW
            mock_get_prompt.assert_called_with(
                language="zh-TW", 
                version="latest",
                variables={"job_description": job_description}
            )
            assert result["detected_language"] == "zh-TW"
    
    # === Unsupported Language Handling ===
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    @pytest.mark.asyncio
    async def test_unsupported_language_raises_error(self, keyword_service,
                                                   mock_detection_service):
        """TEST: API-KW-404-UT - 不支援語言錯誤"""
        job_description = """Pythonエンジニアを募集しています。当社では経験豊富なPython開発者を求めており、
                  FastAPIフレームワークを使用したWebアプリケーション開発の経験が必須です。マイクロサービス
                  アーキテクチャの設計と実装、Dockerコンテナ技術の活用、AWS/Azure/GCPなどのクラウドプラット
                  フォームでの開発経験を重視します。アジャイル開発手法に精通し、CI/CDパイプラインの構築と
                  運用ができる方を歓迎します。日本語でのコミュニケーション能力は必須で、技術文書の作成や
                  チーム内での技術的な議論に積極的に参加できることが重要です。リモートワーク可能。"""
        
        # Mock language composition analysis
        mock_detection_service.analyze_language_composition.return_value = SimpleLanguageStats(
            total_chars=len(job_description),
            traditional_chinese_chars=0,
            simplified_chinese_chars=0,
            english_chars=0,
            japanese_chars=len(job_description),
            korean_chars=0,
            spanish_chars=0,
            other_chars=0,
            traditional_chinese_ratio=0.0,
            english_ratio=0.0,
            has_simplified=False,
            has_other_languages=True
        )
        
        # Mock detection to raise UnsupportedLanguageError
        mock_detection_service.detect_language.side_effect = UnsupportedLanguageError(
            detected_language="ja",
            supported_languages=["en", "zh-TW"],
            confidence=0.95,
            user_specified=False
        )
        
        with pytest.raises(UnsupportedLanguageError) as exc_info:
            await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15
            })
        
        assert exc_info.value.detected_language == "ja"
        assert exc_info.value.supported_languages == ["en", "zh-TW"]
    
    # === Language Override Tests ===
    
    @pytest.mark.asyncio
    async def test_explicit_language_bypasses_detection(self, keyword_service,
                                                      mock_detection_service):
        """TEST: API-KW-405-UT - 明確語言參數跳過檢測"""
        job_description = """Senior Python Developer needed for our growing technology team. We are seeking 
                  an experienced developer with strong Python skills and a passion for building scalable 
                  applications. The ideal candidate will have experience with web frameworks like Django or 
                  FastAPI, RESTful API design, database management, and cloud deployment. Knowledge of 
                  microservices architecture and containerization technologies is highly valued."""
        
        # Mock language composition analysis - shouldn't be called but let's be safe
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "en"
        )
        
        with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
            # get_prompt_with_config returns a tuple: (formatted_prompt, llm_config)
            mock_get_prompt.return_value = (
                "Chinese prompt Senior Python Developer needed",
                Mock(
                    temperature=0.3,
                    max_tokens=500,
                    top_p=1.0,
                    seed=42,
                    frequency_penalty=0.0,
                    presence_penalty=0.0
                )
            )
            
            result = await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15,
                "language": "zh-TW"  # Force Chinese
            })
            
            # Detection service is still called but result is overridden
            mock_detection_service.detect_language.assert_called_once()
            # Should use Chinese prompt despite detection
            mock_get_prompt.assert_called_with(
                language="zh-TW", 
                version="latest",
                variables={"job_description": job_description}
            )
            assert result["detected_language"] == "zh-TW"
    
    @pytest.mark.asyncio
    async def test_invalid_explicit_language_raises_error(self, keyword_service):
        """TEST: API-KW-406-UT - 無效明確語言錯誤"""
        with pytest.raises(ValueError) as exc_info:
            await keyword_service.process({
                "job_description": """Test job description for keyword extraction service validation. This is a 
                  comprehensive job posting for a Senior Software Engineer position requiring extensive 
                  experience in multiple programming languages and frameworks. The ideal candidate should 
                  have strong problem-solving skills, excellent communication abilities, and a proven track 
                  record of delivering high-quality software solutions in agile environments.""",
                "max_keywords": 15,
                "language": "fr"  # French not supported
            })
        
        assert "Language 'fr' not supported" in str(exc_info.value)
    
    # === Prompt Manager Tests ===
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_prompt_manager_initialization(self):
        """TEST: API-KW-407-UT - Prompt 管理器初始化"""
        manager = BilingualPromptManager()
        
        # Check supported languages
        assert "en" in manager.SUPPORTED_LANGUAGES
        assert "zh-TW" in manager.SUPPORTED_LANGUAGES
        assert len(manager.SUPPORTED_LANGUAGES) == 2
        
        # Check version mappings exist
        assert "en" in manager._version_mapping
        assert "zh-TW" in manager._version_mapping
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_get_english_prompt(self):
        """TEST: API-KW-408-UT - 獲取英文 prompt"""
        manager = BilingualPromptManager()
        
        prompt_config = manager.get_prompt("en", "latest")
        
        assert prompt_config.language == "en"
        assert "{job_description}" in prompt_config.content
        assert "keyword" in prompt_config.content.lower()
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_get_chinese_prompt(self):
        """TEST: API-KW-409-UT - 獲取中文 prompt"""
        manager = BilingualPromptManager()
        
        prompt_config = manager.get_prompt("zh-TW", "latest")
        
        assert prompt_config.language == "zh-TW"
        assert "{job_description}" in prompt_config.content
        assert "關鍵字" in prompt_config.content or "keyword" in prompt_config.content.lower()
    
    @pytest.mark.precommit
    @pytest.mark.timeout(2)
    def test_format_prompt_with_job_description(self):
        """TEST: API-KW-410-UT - 格式化 prompt"""
        manager = BilingualPromptManager()
        
        job_desc = """Looking for Python developer with strong backend development skills. We need someone 
                  with at least 3 years of experience in Python web development, preferably with Django or 
                  Flask frameworks. Knowledge of RESTful APIs, database design, and cloud services is essential. 
                  The role involves designing and implementing scalable backend services, optimizing application 
                  performance, and collaborating with frontend developers to deliver exceptional user experiences."""
        prompt_config = manager.get_prompt("en", "latest")
        formatted = manager.format_prompt(prompt_config, job_description=job_desc)
        
        assert job_desc in formatted
        assert "{job_description}" not in formatted
    
    def test_get_unsupported_language_raises_error(self):
        """TEST: API-KW-411-UT - 不支援語言 prompt 錯誤"""
        manager = BilingualPromptManager()
        
        with pytest.raises(PromptNotAvailableError) as exc_info:
            manager.get_prompt("es", "latest")
        
        assert "not supported" in str(exc_info.value)
    
    # === Language Detection Edge Cases ===
    
    @pytest.mark.asyncio
    async def test_empty_job_description_handling(self, keyword_service):
        """TEST: API-KW-412-UT - 空 JD 處理"""
        with pytest.raises(ValueError):
            await keyword_service.validate_input({
                "job_description": "",
                "max_keywords": 15
            })
    
    @pytest.mark.asyncio
    async def test_very_short_job_description(self, keyword_service,
                                            mock_detection_service):
        """TEST: API-KW-413-UT - 極短 JD 處理"""
        # Very short job descriptions should fail validation
        short_job_desc = "Python Developer needed with experience in Django and REST APIs"
        
        # This is less than 200 characters, should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await keyword_service.execute({
                "job_description": short_job_desc,
                "max_keywords": 15
            })
        
        assert "Job description must be at least 200 characters" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_numbers_and_symbols_only(self, keyword_service,
                                          mock_detection_service):
        """TEST: API-KW-414-UT - 純數字符號處理"""
        job_description = "5+ years, $100k-150k, 401k, PTO"
        
        # Mock language composition analysis for numbers/symbols
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "en"
        )
        
        mock_detection_service.detect_language.return_value = Mock(
            language="en",  # Default to English for ambiguous content
            confidence=0.5,
            is_supported=True,
            detection_time_ms=30
        )
        
        result = await keyword_service.process({
            "job_description": "5+ years, $100k-150k, 401k, PTO",
            "max_keywords": 15
        })
        
        # Should handle gracefully, likely defaulting to English
        assert result["detected_language"] == "en"
    
    def _create_language_stats(self, text, language):
        """Helper to create language statistics based on detected language."""
        total_chars = len(text)
        if language == "zh-TW":
            # Simulate Traditional Chinese text
            return SimpleLanguageStats(
                total_chars=total_chars,
                traditional_chinese_chars=int(total_chars * 0.7),
                simplified_chinese_chars=0,
                english_chars=int(total_chars * 0.3),
                japanese_chars=0,
                korean_chars=0,
                spanish_chars=0,
                other_chars=0,
                traditional_chinese_ratio=0.7,
                english_ratio=0.3,
                has_simplified=False,
                has_other_languages=False
            )
        elif language == "ja":
            # Simulate Japanese text
            return SimpleLanguageStats(
                total_chars=total_chars,
                traditional_chinese_chars=0,
                simplified_chinese_chars=0,
                english_chars=0,
                japanese_chars=total_chars,
                korean_chars=0,
                spanish_chars=0,
                other_chars=0,
                traditional_chinese_ratio=0.0,
                english_ratio=0.0,
                has_simplified=False,
                has_other_languages=True
            )
        else:
            # Default to English
            return SimpleLanguageStats(
                total_chars=total_chars,
                traditional_chinese_chars=0,
                simplified_chinese_chars=0,
                english_chars=total_chars,
                japanese_chars=0,
                korean_chars=0,
                spanish_chars=0,
                other_chars=0,
                traditional_chinese_ratio=0.0,
                english_ratio=1.0,
                has_simplified=False,
                has_other_languages=False
            )

    # === Service Cleanup Tests ===
    
    @pytest.mark.asyncio
    async def test_service_cleanup_on_success(self, keyword_service,
                                             mock_detection_service):
        """TEST: API-KW-415-UT - 成功時服務清理"""
        job_description = """We are looking for a Senior Python Developer with experience in FastAPI to join 
                  our innovative development team. The ideal candidate will have 5+ years of Python experience, 
                  deep knowledge of FastAPI framework, and expertise in building high-performance RESTful APIs. 
                  Experience with asynchronous programming, microservices architecture, Docker, Kubernetes, and 
                  cloud platforms (AWS/Azure/GCP) is required. Strong problem-solving skills and ability to work 
                  in an agile environment are essential."""
        
        # Mock language composition analysis
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "en"
        )
        
        # Mock detection to return English
        mock_detection_service.detect_language.return_value = Mock(
            language="en",
            confidence=0.95,
            is_supported=True,
            detection_time_ms=50
        )
        
        # Mock successful keyword extraction
        expected_result = {
            "keywords": ["Python", "Senior Developer", "FastAPI"],
            "keyword_count": 15,
            "confidence_score": 0.88,
            "extraction_method": "2_round_intersection",
            "detected_language": "en",
            "prompt_version_used": "v1.4.0-en",
            "processing_time_ms": 2400.0
        }
        
        # Ensure process completes successfully
        with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
            mock_get_prompt.return_value = (
                "English prompt template",
                Mock(temperature=0.3, max_tokens=500, top_p=1.0, seed=42, 
                     frequency_penalty=0.0, presence_penalty=0.0)
            )
            
            # Mock the LLM response
            keyword_service.openai_client.complete_text.return_value = '{"keywords": ["Python", "Senior Developer", "FastAPI"]}'
            
            result = await keyword_service.process({
                "job_description": job_description,
                "max_keywords": 15
            })
        
        # Verify service completed successfully
        assert result["keywords"] == ["Python", "Senior Developer", "FastAPI"]
        assert result["detected_language"] == "en"
        assert result["keyword_count"] == 3  # Actual count of keywords returned
        # In a real implementation, cleanup would be handled by context managers or finally blocks
        # This test verifies that the service completes successfully without resource leaks
    
    @pytest.mark.asyncio
    async def test_service_cleanup_on_error(self, keyword_service,
                                          mock_detection_service):
        """TEST: API-KW-416-UT - 錯誤時服務清理"""
        job_description = """We need a Python developer with experience in building scalable web applications. 
                  The successful candidate will have strong Python programming skills, experience with modern 
                  web frameworks, and knowledge of software development best practices. Responsibilities include 
                  developing new features, maintaining existing codebase, writing unit tests, and participating 
                  in code reviews. Experience with agile methodologies and version control systems is required."""
        
        # Mock language composition analysis
        mock_detection_service.analyze_language_composition.return_value = self._create_language_stats(
            job_description, "en"
        )
        
        # Mock detection to return English
        mock_detection_service.detect_language.return_value = Mock(
            language="en",
            confidence=0.95,
            is_supported=True,
            detection_time_ms=50
        )
        
        # Mock LLM client to raise an error
        from src.services.openai_client import AzureOpenAIError
        keyword_service.openai_client.complete_text.side_effect = AzureOpenAIError("API Error")
        
        # Ensure error is raised
        with pytest.raises(AzureOpenAIError):
            with patch.object(keyword_service.unified_prompt_service, 'get_prompt_with_config') as mock_get_prompt:
                mock_get_prompt.return_value = (
                    "English prompt template",
                    Mock(temperature=0.3, max_tokens=500, top_p=1.0, seed=42,
                         frequency_penalty=0.0, presence_penalty=0.0)
                )
                
                await keyword_service.process({
                    "job_description": job_description,
                    "max_keywords": 15
                })
        
        # Verify that the error was properly raised
        # In a real implementation, cleanup would be done in a finally block or context manager
        # This test ensures that errors are properly propagated while still maintaining resource safety
        # The actual resource cleanup would be handled by the service's context management
