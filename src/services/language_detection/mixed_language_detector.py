"""
Enhanced language detector with mixed language support for Taiwan job descriptions.
When Traditional Chinese ratio > 40%, use Traditional Chinese prompt.
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
from src.services.language_detection.detector import (
    LanguageDetectionResult,
    LanguageDetectionService,
)

logger = logging.getLogger(__name__)


class MixedLanguageStats(NamedTuple):
    """Statistics for mixed language content."""
    total_chars: int
    chinese_chars: int
    english_chars: int
    chinese_ratio: float
    english_ratio: float
    traditional_chars: int
    simplified_chars: int


class MixedLanguageDetectionService(LanguageDetectionService):
    """
    Enhanced language detection service for Taiwan job descriptions.
    
    Key enhancement:
    - If Traditional Chinese ratio > 20%, use Traditional Chinese prompt
    - Better handling of mixed Chinese-English content common in Taiwan
    """
    
    # Taiwan JD specific threshold
    TRADITIONAL_CHINESE_THRESHOLD = 0.20  # 20% threshold for Taiwan JDs
    
    def analyze_language_mix(self, text: str) -> MixedLanguageStats:
        """
        Analyze the language composition of the text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            MixedLanguageStats with detailed language composition
        """
        total_chars = len(text)
        if total_chars == 0:
            return MixedLanguageStats(0, 0, 0, 0.0, 0.0, 0, 0)
        
        # Count Chinese characters
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        
        # Count English letters
        english_chars = sum(1 for char in text if char.isalpha() and ord(char) < 128)
        
        # Count Traditional vs Simplified
        text_chars = set(text)
        traditional_chars = len(text_chars.intersection(self.TRADITIONAL_CHARS))
        simplified_chars = len(text_chars.intersection(self.SIMPLIFIED_CHARS))
        
        # Calculate ratios
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        
        return MixedLanguageStats(
            total_chars=total_chars,
            chinese_chars=chinese_chars,
            english_chars=english_chars,
            chinese_ratio=chinese_ratio,
            english_ratio=english_ratio,
            traditional_chars=traditional_chars,
            simplified_chars=simplified_chars
        )
    
    async def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Enhanced language detection for Taiwan job descriptions.
        
        Key logic:
        1. Analyze language composition first
        2. If Traditional Chinese ratio > 20%, use zh-TW
        3. Otherwise, use standard detection logic
        
        Args:
            text: Input text for language detection
            
        Returns:
            LanguageDetectionResult with detected language and metadata
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
            lang_stats = self.analyze_language_mix(text)
            
            logger.info(
                f"Language mix analysis: "
                f"Chinese={lang_stats.chinese_ratio:.1%} ({lang_stats.chinese_chars} chars), "
                f"English={lang_stats.english_ratio:.1%} ({lang_stats.english_chars} chars), "
                f"Traditional={lang_stats.traditional_chars}, "
                f"Simplified={lang_stats.simplified_chars}"
            )
            
            # 3. First use langdetect for initial detection
            # This is important to identify Japanese, Korean, etc. correctly
            
            # 4. Use langdetect for standard detection
            try:
                detected_lang = detect(text)
                lang_probs = detect_langs(text)
                confidence = lang_probs[0].prob if lang_probs else 0.0
            except LangDetectException as e:
                raise LanguageDetectionError(
                    text_length=len(text),
                    reason=f"langdetect library error: {str(e)}"
                )
            
            # 5. Special handling for Japanese before applying Taiwan JD rules
            if detected_lang == 'ja':
                # Count Japanese-specific characters
                hiragana_count = sum(1 for char in text if '\u3040' <= char <= '\u309f')
                katakana_count = sum(1 for char in text if '\u30a0' <= char <= '\u30ff')
                kana_count = hiragana_count + katakana_count
                
                if kana_count > 10 or (kana_count / len(text) > 0.1):
                    logger.info(
                        f"Confirmed Japanese text with {kana_count} kana characters "
                        f"({kana_count/len(text):.1%} of text). Will not override."
                    )
                    # This is genuine Japanese, skip Taiwan JD rules
                else:
                    # No kana found, might be misdetected Chinese
                    logger.info("Japanese detected but no kana found, checking if it's actually Chinese")
                    if lang_stats.chinese_ratio >= self.TRADITIONAL_CHINESE_THRESHOLD and lang_stats.traditional_chars >= lang_stats.simplified_chars:
                        detected_lang = 'zh-TW'
                        confidence = max(confidence, 0.85)
                        logger.info(f"Corrected ja -> zh-TW (Chinese ratio: {lang_stats.chinese_ratio:.1%})")
            
            # 6. Apply Taiwan JD rules for non-Japanese content
            elif lang_stats.chinese_ratio >= self.TRADITIONAL_CHINESE_THRESHOLD and lang_stats.chinese_chars >= 10:
                # Check if Traditional Chinese should be used
                if lang_stats.traditional_chars >= lang_stats.simplified_chars:
                    if detected_lang == 'en':
                        # Mixed English-Chinese content
                        logger.info(
                            f"Taiwan JD rule: English with {lang_stats.chinese_ratio:.1%} Traditional Chinese, "
                            f"switching to zh-TW"
                        )
                        detected_lang = 'zh-TW'
                        confidence = min(0.95, 0.8 + lang_stats.chinese_ratio * 0.3)
                    elif detected_lang in ['zh', 'zh-cn', 'zh-tw']:
                        # Refine Chinese variant
                        detected_lang = self._refine_chinese_variant(text)
                    elif detected_lang in ['ko', 'vi']:
                        # Korean or Vietnamese detected but has significant Traditional Chinese
                        logger.info(
                            f"Taiwan JD rule: {detected_lang} with {lang_stats.chinese_ratio:.1%} Traditional Chinese, "
                            f"switching to zh-TW"
                        )
                        detected_lang = 'zh-TW'
                        confidence = min(0.95, 0.8 + lang_stats.chinese_ratio * 0.3)
                elif lang_stats.simplified_chars > lang_stats.traditional_chars:
                    # Simplified Chinese
                    if detected_lang != 'zh-CN':
                        detected_lang = 'zh-CN'
                        confidence = 0.9
            
            # 7. Handle other Asian languages (Korean, Vietnamese) with less Chinese content
            elif detected_lang in ['ko', 'vi'] and lang_stats.chinese_chars >= 10 and lang_stats.chinese_ratio < self.TRADITIONAL_CHINESE_THRESHOLD:
                # For Korean and Vietnamese with Chinese content
                original_lang = detected_lang
                chinese_variant = self._refine_chinese_variant(text)
                
                if chinese_variant == 'zh-TW' and lang_stats.chinese_ratio >= 0.20:
                    detected_lang = 'zh-TW'
                    confidence = max(confidence, 0.85)
                    logger.info(
                        f"Corrected misdetection: {original_lang} -> {detected_lang} "
                        f"(Chinese ratio: {lang_stats.chinese_ratio:.1%})"
                    )
            
            # 8. Confidence check
            if confidence < self.CONFIDENCE_THRESHOLD:
                raise LowConfidenceDetectionError(
                    detected_language=detected_lang,
                    confidence=confidence,
                    threshold=self.CONFIDENCE_THRESHOLD
                )
            
            # 9. Support check
            is_supported = detected_lang in self.SUPPORTED_LANGUAGES
            if not is_supported:
                raise UnsupportedLanguageError(
                    detected_language=detected_lang,
                    supported_languages=self.SUPPORTED_LANGUAGES,
                    confidence=confidence,
                    user_specified=False
                )
            
            detection_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Language detected: {detected_lang}, confidence: {confidence:.3f}, "
                f"time: {detection_time_ms}ms"
            )
            
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
            logger.error(f"Unexpected error in language detection: {str(e)}")
            raise LanguageDetectionError(
                text_length=len(text) if text else 0,
                reason=f"Unexpected detection error: {str(e)}"
            )