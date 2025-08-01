"""
Rule-based language detector for thread-safe language detection.
Implements the same detection logic as SimplifiedLanguageDetector but without external dependencies.
Ensures thread safety for concurrent environments.
"""

import logging
import time
from typing import NamedTuple

from src.services.exceptions import LanguageDetectionError, UnsupportedLanguageError
from src.services.language_detection.detector import (
    LanguageDetectionResult,
    LanguageDetectionService,
)

logger = logging.getLogger(__name__)


class RuleBasedLanguageStats(NamedTuple):
    """Language composition statistics for rule-based detection."""
    total_chars: int
    traditional_chinese_chars: int
    simplified_chinese_chars: int
    english_chars: int
    japanese_chars: int
    korean_chars: int
    spanish_chars: int
    other_chars: int
    traditional_chinese_ratio: float
    english_ratio: float
    has_simplified: bool
    has_other_languages: bool


class RuleBasedLanguageDetector(LanguageDetectionService):
    """
    Thread-safe rule-based language detection.

    Implements the same detection rules as SimplifiedLanguageDetector:
    1. Pure Traditional Chinese
    2. Pure English
    3. Traditional Chinese + English mix

    Rejects everything else including Simplified Chinese, Japanese, Korean, etc.

    Key differences from SimplifiedLanguageDetector:
    - No dependency on langdetect library
    - Completely stateless and thread-safe
    - Deterministic results
    """

    # Threshold for mixed content (same as SimplifiedLanguageDetector)
    TRADITIONAL_CHINESE_THRESHOLD = 0.20  # 20% threshold

    # Common Japanese/Korean characters to detect and reject
    JAPANESE_HIRAGANA_RANGE = ('\u3040', '\u309f')
    JAPANESE_KATAKANA_RANGE = ('\u30a0', '\u30ff')
    KOREAN_HANGUL_RANGE = ('\uac00', '\ud7af')

    def analyze_language_composition(self, text: str) -> RuleBasedLanguageStats:
        """
        Analyze text to determine language composition.
        Focus on detecting Traditional Chinese, English, and unwanted languages.

        This method is identical to SimplifiedLanguageDetector.analyze_language_composition
        to ensure consistent behavior.
        """
        if not text:
            return RuleBasedLanguageStats(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, False, False)

        total_chars = 0
        traditional_chinese_chars = 0
        simplified_chinese_chars = 0
        english_chars = 0
        japanese_chars = 0
        korean_chars = 0
        spanish_chars = 0
        other_chars = 0

        # Spanish special characters
        spanish_special = set('ñÑáéíóúÁÉÍÓÚüÜ¿¡')

        # Character-by-character analysis
        for char in text:
            # Skip whitespace and common punctuation
            if char.isspace() or char in '.,;:!?"\'()-[]{}/@#$%^&*+=<>|\\~`_':
                continue

            total_chars += 1

            # Check for Chinese characters
            if '\u4e00' <= char <= '\u9fff':
                # Determine if it's traditional or simplified
                if char in self.SIMPLIFIED_CHARS and char not in self.TRADITIONAL_CHARS:
                    # Exclusively simplified character
                    simplified_chinese_chars += 1
                elif char in self.TRADITIONAL_CHARS:
                    # Traditional character (including shared characters)
                    traditional_chinese_chars += 1
                else:
                    # Shared character - count as traditional
                    traditional_chinese_chars += 1

            # Check for English
            elif char.isalpha() and ord(char) < 128:
                english_chars += 1

            # Check for Japanese (including Kanji range that overlaps with Chinese)
            elif (self.JAPANESE_HIRAGANA_RANGE[0] <= char <= self.JAPANESE_HIRAGANA_RANGE[1] or
                  self.JAPANESE_KATAKANA_RANGE[0] <= char <= self.JAPANESE_KATAKANA_RANGE[1]):
                japanese_chars += 1

            # Check for Korean
            elif self.KOREAN_HANGUL_RANGE[0] <= char <= self.KOREAN_HANGUL_RANGE[1]:
                korean_chars += 1

            # Check for Spanish special characters
            elif char in spanish_special:
                spanish_chars += 1

            # Check for numbers (allowed, not counted as "other")
            elif char.isdigit():
                continue  # Numbers are OK, don't count them

            # Other alphabetic characters
            elif char.isalpha():
                other_chars += 1

        # Calculate ratios based on total characters
        trad_chinese_ratio = traditional_chinese_chars / total_chars if total_chars > 0 else 0.0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0.0

        # Determine if we have unwanted content
        # Has simplified Chinese if there are any simplified chars detected
        has_simplified = simplified_chinese_chars > 0
        # Has other languages if any non-English, non-Traditional Chinese detected
        has_other_languages = (japanese_chars + korean_chars + spanish_chars + other_chars) > 0

        return RuleBasedLanguageStats(
            total_chars=total_chars,
            traditional_chinese_chars=traditional_chinese_chars,
            simplified_chinese_chars=simplified_chinese_chars,
            english_chars=english_chars,
            japanese_chars=japanese_chars,
            korean_chars=korean_chars,
            spanish_chars=spanish_chars,
            other_chars=other_chars,
            traditional_chinese_ratio=trad_chinese_ratio,
            english_ratio=english_ratio,
            has_simplified=has_simplified,
            has_other_languages=has_other_languages
        )

    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect language using rule-based approach.

        Implements the same two-step logic as SimplifiedLanguageDetector:
        Step 1: Reject if unsupported languages > 10% of total
        Step 2: Use zh-TW if zh-TW >= 20% of (EN + zh-TW + numbers/symbols)

        This method is thread-safe and deterministic.
        """
        start_time = time.time()

        try:
            # 1. Text length validation
            if len(text.strip()) < self.MIN_TEXT_LENGTH:
                raise LanguageDetectionError(
                    text_length=len(text.strip()),
                    reason=f"Text too short (minimum {self.MIN_TEXT_LENGTH} characters required)"
                )

            # 2. Analyze language composition
            stats = self.analyze_language_composition(text)

            logger.info(
                f"[RuleBasedDetector] Language composition: "
                f"Trad Chinese={stats.traditional_chinese_ratio:.1%} ({stats.traditional_chinese_chars}), "
                f"English={stats.english_ratio:.1%} ({stats.english_chars}), "
                f"Simplified={stats.simplified_chinese_chars}, "
                f"Other={stats.other_chars}"
            )

            # 3. Step 1: Check unsupported language threshold (10% of total)
            unsupported_chars = (stats.simplified_chinese_chars + stats.japanese_chars +
                               stats.korean_chars + stats.spanish_chars + stats.other_chars)
            unsupported_ratio = unsupported_chars / stats.total_chars if stats.total_chars > 0 else 0.0

            if unsupported_ratio > 0.10:  # More than 10% unsupported content
                logger.warning(
                    f"[RuleBasedDetector] Rejected: Unsupported content {unsupported_ratio:.1%} > 10% "
                    f"(Simplified: {stats.simplified_chinese_chars}, Other: {stats.other_chars})"
                )

                # Determine specific unsupported language for tracking
                detected_lang = "other"
                if stats.simplified_chinese_chars > stats.other_chars:
                    detected_lang = "zh-CN"
                elif stats.japanese_chars > 0:
                    detected_lang = "ja"
                elif stats.korean_chars > 0:
                    detected_lang = "ko"
                elif stats.spanish_chars > 0:
                    detected_lang = "es"

                raise UnsupportedLanguageError(
                    detected_language=detected_lang,
                    supported_languages=["en", "zh-TW"],
                    confidence=0.9,
                    user_specified=False
                )

            # 4. Step 2: Determine language from supported content
            # Calculate supported content (EN + zh-TW + numbers/symbols)
            supported_chars = stats.total_chars - unsupported_chars

            if supported_chars == 0:
                # No valid content
                raise LanguageDetectionError(
                    text_length=len(text),
                    reason="No valid Traditional Chinese or English content found"
                )

            # Calculate zh-TW percentage of supported content
            trad_chinese_ratio_of_supported = stats.traditional_chinese_chars / supported_chars

            # 5. Apply 20% threshold rule
            if trad_chinese_ratio_of_supported >= self.TRADITIONAL_CHINESE_THRESHOLD:
                # Traditional Chinese >= 20% of supported content
                detected_lang = 'zh-TW'
                confidence = 0.95  # High confidence for rule-based detection
                logger.info(
                    f"[RuleBasedDetector] Detected: zh-TW (Traditional Chinese {trad_chinese_ratio_of_supported:.1%} "
                    f"of supported content >= 20%)"
                )
            else:
                # Traditional Chinese < 20%, use English as default
                detected_lang = 'en'
                confidence = 0.95  # High confidence for rule-based detection
                logger.info(
                    f"[RuleBasedDetector] Detected: en (Traditional Chinese {trad_chinese_ratio_of_supported:.1%} "
                    f"of supported content < 20%)"
                )

            detection_time_ms = int((time.time() - start_time) * 1000)

            return LanguageDetectionResult(
                language=detected_lang,
                confidence=confidence,
                is_supported=True,
                detection_time_ms=detection_time_ms
            )

        except (LanguageDetectionError, UnsupportedLanguageError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"[RuleBasedDetector] Unexpected error in language detection: {e!s}")
            raise LanguageDetectionError(
                text_length=len(text) if text else 0,
                reason=f"Unexpected detection error: {e!s}"
            ) from e
