"""
Language detection service for bilingual keyword extraction.
Uses langdetect library with Traditional Chinese support.
"""

import logging
import time
from typing import NamedTuple

from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException

from src.services.exceptions import (
    LanguageDetectionError,
    LowConfidenceDetectionError,
    UnsupportedLanguageError,
)

logger = logging.getLogger(__name__)


class LanguageDetectionResult(NamedTuple):
    """Result of language detection."""
    language: str
    confidence: float
    is_supported: bool
    detection_time_ms: int


# Exception classes are imported from src.services.exceptions to avoid duplication


class LanguageDetectionService:
    """
    Language detection service supporting English and Traditional Chinese.

    Supported languages:
    - English (en)
    - Traditional Chinese (zh-TW)

    Unsupported languages (will be rejected):
    - Simplified Chinese (zh-CN)
    - Japanese (ja)
    - Korean (ko)
    - And all other languages
    """

    SUPPORTED_LANGUAGES = ['en', 'zh-TW']
    CONFIDENCE_THRESHOLD = 0.8
    MIN_TEXT_LENGTH = 50

    # Comprehensive Traditional vs Simplified Chinese character sets for accurate differentiation
    # These sets focus on the most distinguishing characters commonly found in job descriptions
    TRADITIONAL_CHARS = set(
        # Core traditional technology terms
        '繁體語機業資訊軟體開發設計測試資料庫網路計劃團隊責任工作經驗技能專業證照學歷維護系統候選尋找精通熟悉需要具備負責'
        # Extended traditional-specific characters
        '學習專案管理執行運營營運數據資料分析處理優化協調溝通領導監督製造產品營銷銷售財務會計審計風險合規項目調研開拓擴展'
        '質量品質標準規範流程優勢競爭創新變革轉型數碼數位科技智慧雲端傳統現代先進前沿頂尖卓越績效評估測量指標關鍵重要核心'
        '進階高級初級中級資深首席總監經理主任主管助理實習生全職兼職遠程在線線上離線線下辦公室現場客戶服務支持技術諮詢顧問'
        '軟件硬件網絡安全防護保護隱私機密敏感關聯關係連接整合集成部署運維監控日誌記錄追蹤跟蹤診斷故障排除解決問題回饋反饋'
        '訓練培訓學習成長發展晉升升遷轉職跳槽招聘聘用錄用僱用雇用離職退休請假休假薪資薪酬報酬津貼補助福利保險醫療健康'
        '團隊合作協作配合默契溝通交流互動參與投入貢獻價值創造生產製作建設構建設計開發維護升級更新改進完善優化調整修改'
    )

    SIMPLIFIED_CHARS = set(
        # Core simplified technology terms
        '繁体语机业资讯软体开发设计测试资料库网络计划团队责任工作经验技能专业证照学历维护系统候选寻找精通熟悉需要具备负责'
        # Extended simplified-specific characters
        '学习专案管理执行运营营运数据资料分析处理优化协调沟通领导监督制造产品营销销售财务会计审计风险合规项目调研开拓扩展'
        '质量品质标准规范流程优势竞争创新变革转型数码数位科技智慧云端传统现代先进前沿顶尖卓越绩效评估测量指标关键重要核心'
        '进阶高级初级中级资深首席总监经理主任主管助理实习生全职兼职远程在线线上离线线下办公室现场客户服务支持技术咨询顾问'
        '软件硬件网络安全防护保护隐私机密敏感关联关系连接整合集成部署运维监控日志记录追踪跟踪诊断故障排除解决问题回馈反馈'
        '训练培训学习成长发展晋升升迁转职跳槽招聘聘用录用雇用雇用离职退休请假休假薪资薪酬报酬津贴补助福利保险医疗健康'
        '团队合作协作配合默契沟通交流互动参与投入贡献价值创造生产制作建设构建设计开发维护升级更新改进完善优化调整修改'
    )

    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect language from input text.

        Args:
            text: Input text for language detection

        Returns:
            LanguageDetectionResult with detected language and metadata

        Raises:
            TextTooShortError: If text is too short for reliable detection
            LowConfidenceError: If detection confidence is below threshold
            UnsupportedLanguageError: If detected language is not supported
            LanguageDetectionError: For other detection failures
        """
        start_time = time.time()

        try:
            # 1. Text length validation
            if len(text.strip()) < self.MIN_TEXT_LENGTH:
                raise LanguageDetectionError(
                    text_length=len(text.strip()),
                    reason=f"Text too short (minimum {self.MIN_TEXT_LENGTH} characters required)"
                )

            # 2. Use langdetect for initial detection
            try:
                detected_lang = detect(text)
                lang_probs = detect_langs(text)
                confidence = lang_probs[0].prob if lang_probs else 0.0
            except LangDetectException as e:
                raise LanguageDetectionError(
                    text_length=len(text),
                    reason=f"langdetect library error: {e!s}"
                )

            # 3. Refine Chinese variant detection
            has_chinese_chars = any('\u4e00' <= char <= '\u9fff' for char in text)
            chinese_char_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')

            # Special handling for Japanese before applying Chinese variant analysis
            if detected_lang == 'ja':
                # Count Japanese-specific characters
                hiragana_count = sum(1 for char in text if '\u3040' <= char <= '\u309f')
                katakana_count = sum(1 for char in text if '\u30a0' <= char <= '\u30ff')
                kana_count = hiragana_count + katakana_count

                if kana_count > 10 or (kana_count / len(text) > 0.1):
                    logger.info(
                        f"Confirmed Japanese text with {kana_count} kana characters "
                        f"({kana_count/len(text):.1%} of text). Keeping original detection."
                    )
                    # This is genuine Japanese, don't apply Chinese variant rules
                else:
                    # No significant kana found, might be misdetected Chinese
                    logger.info("Japanese detected but insufficient kana found, checking if it's actually Chinese")
                    if chinese_char_count >= 10:
                        detected_lang = self._refine_chinese_variant(text)
                        if detected_lang == 'zh-TW':
                            confidence = max(confidence, 0.85)
                            logger.info("Corrected ja -> zh-TW")
            elif detected_lang in ['zh', 'zh-cn', 'zh-tw']:
                detected_lang = self._refine_chinese_variant(text)
            elif has_chinese_chars and chinese_char_count >= 10:  # Lower threshold for Chinese detection
                # If text has significant Chinese content but misdetected as other language
                if detected_lang in ['ko', 'vi', 'ja', 'no', 'en'] or confidence < 0.9:
                    logger.info(f"Potential Chinese text misdetected as {detected_lang}, analyzing Chinese variant")
                    original_lang = detected_lang
                    detected_lang = self._refine_chinese_variant(text)

                    # For texts with substantial Chinese content, trust our Chinese variant analysis
                    if detected_lang == 'zh-TW':
                        confidence = max(confidence, 0.85)
                        logger.info(f"Corrected misdetection: {original_lang} -> {detected_lang}")
                    elif chinese_char_count >= 15:  # Lower threshold for Traditional Chinese preference
                        # For Chinese-heavy text, even if simplified, prefer zh-TW over other Asian languages
                        detected_lang = 'zh-TW'
                        confidence = max(confidence, 0.82)
                        logger.info(f"Chinese-heavy text corrected: {original_lang} -> {detected_lang}")
                    else:
                        # Revert to original detection for ambiguous cases
                        detected_lang = original_lang

            # 4. Confidence check - be more lenient for Chinese text
            effective_threshold = self.CONFIDENCE_THRESHOLD
            if detected_lang == 'zh-TW' and chinese_char_count >= 15:
                # Lower threshold for Chinese text with substantial content
                effective_threshold = 0.5

            if confidence < effective_threshold:
                raise LowConfidenceDetectionError(
                    detected_language=detected_lang,
                    confidence=confidence,
                    threshold=effective_threshold
                )

            # 5. Support check
            is_supported = detected_lang in self.SUPPORTED_LANGUAGES
            if not is_supported:
                raise UnsupportedLanguageError(
                    detected_language=detected_lang,
                    supported_languages=self.SUPPORTED_LANGUAGES,
                    confidence=confidence,
                    user_specified=False
                )

            detection_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Language detected: {detected_lang}, confidence: {confidence:.3f}, time: {detection_time_ms}ms")

            return LanguageDetectionResult(
                language=detected_lang,
                confidence=confidence,
                is_supported=is_supported,
                detection_time_ms=detection_time_ms
            )

        except (LanguageDetectionError, LowConfidenceDetectionError, UnsupportedLanguageError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            detection_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected error in language detection: {e!s}")
            raise LanguageDetectionError(
                text_length=len(text) if text else 0,
                reason=f"Unexpected detection error: {e!s}"
            )

    def _refine_chinese_variant(self, text: str) -> str:
        """
        Distinguish between Traditional Chinese (zh-TW) and Simplified Chinese (zh-CN).

        Args:
            text: Chinese text to analyze

        Returns:
            'zh-TW' for Traditional Chinese, 'zh-CN' for Simplified Chinese
        """
        text_chars = set(text)
        traditional_count = len(text_chars.intersection(self.TRADITIONAL_CHARS))
        simplified_count = len(text_chars.intersection(self.SIMPLIFIED_CHARS))

        # Count total Chinese characters
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')

        logger.debug(f"Chinese variant analysis - Traditional: {traditional_count}, Simplified: {simplified_count}, Total Chinese: {chinese_chars}")

        # More strict Traditional Chinese detection
        if traditional_count > 0 and traditional_count > simplified_count:
            return 'zh-TW'
        elif simplified_count > 0 and simplified_count > traditional_count:
            return 'zh-CN'
        elif chinese_chars > 5:
            # For ambiguous cases, check for common Traditional vs Simplified patterns
            # If no clear indicators, default to Simplified (will be rejected)
            return 'zh-CN'
        else:
            return 'zh-CN'

    def _has_strong_traditional_indicators(self, text: str) -> bool:
        """
        Check for strong Traditional Chinese indicators.

        Args:
            text: Text to analyze

        Returns:
            True if strong Traditional Chinese indicators found
        """
        text_chars = set(text)
        traditional_indicators = len(text_chars.intersection(self.TRADITIONAL_CHARS))
        # Require at least 2 traditional-specific characters for strong indication
        return traditional_indicators >= 2

    def is_supported_language(self, language_code: str) -> bool:
        """Check if a language code is supported."""
        return language_code in self.SUPPORTED_LANGUAGES

    def validate_text_length(self, text: str) -> bool:
        """Validate if text is long enough for detection."""
        return len(text.strip()) >= self.MIN_TEXT_LENGTH

    def get_supported_languages(self) -> list[str]:
        """Get list of supported language codes."""
        return self.SUPPORTED_LANGUAGES.copy()
