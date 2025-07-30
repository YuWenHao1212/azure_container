"""
Simplified language detector for Taiwan job descriptions.
Only accepts: Pure Traditional Chinese, Pure English, or Traditional Chinese + English mix.
Rejects all other cases including Simplified Chinese, Japanese, Korean, etc.
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


class SimpleLanguageStats(NamedTuple):
    """Language composition statistics."""
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


class SimplifiedLanguageDetector(LanguageDetectionService):
    """
    Simplified language detection that only accepts:
    1. Pure Traditional Chinese
    2. Pure English  
    3. Traditional Chinese + English mix
    
    Rejects everything else including Simplified Chinese, Japanese, Korean, etc.
    """
    
    # Threshold for mixed content
    TRADITIONAL_CHINESE_THRESHOLD = 0.20  # 20% threshold
    
    # Common Japanese/Korean characters to detect and reject
    JAPANESE_HIRAGANA_RANGE = ('\u3040', '\u309f')
    JAPANESE_KATAKANA_RANGE = ('\u30a0', '\u30ff')
    KOREAN_HANGUL_RANGE = ('\uac00', '\ud7af')
    
    def analyze_language_composition(self, text: str) -> SimpleLanguageStats:
        """
        Analyze text to determine language composition.
        Focus on detecting Traditional Chinese, English, and unwanted languages.
        """
        if not text:
            return SimpleLanguageStats(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, False, False)
        
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
        
        return SimpleLanguageStats(
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
        Detect language with new two-step logic:
        Step 1: Reject if unsupported languages > 10% of total
        Step 2: Use zh-TW if zh-TW >= 20% of (EN + zh-TW + numbers/symbols)
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
                f"Language composition: "
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
                    f"Rejected: Unsupported content {unsupported_ratio:.1%} > 10% "
                    f"(Simplified: {stats.simplified_chinese_chars}, Other: {stats.other_chars})"
                )
                
                # Determine specific unsupported language for tracking
                detected_lang = "other"
                if stats.simplified_chinese_chars > stats.other_chars:
                    detected_lang = "zh-CN"
                else:
                    # Try to identify specific language
                    for char in text:
                        if self.JAPANESE_HIRAGANA_RANGE[0] <= char <= self.JAPANESE_HIRAGANA_RANGE[1] or \
                           self.JAPANESE_KATAKANA_RANGE[0] <= char <= self.JAPANESE_KATAKANA_RANGE[1]:
                            detected_lang = "ja"
                            break
                        elif self.KOREAN_HANGUL_RANGE[0] <= char <= self.KOREAN_HANGUL_RANGE[1]:
                            detected_lang = "ko"
                            break
                        elif char in 'ñÑáéíóúÁÉÍÓÚüÜ¿¡':
                            detected_lang = "es"
                            break
                
                raise UnsupportedLanguageError(
                    detected_language=detected_lang,
                    supported_languages=["en", "zh-TW"],
                    confidence=0.9,
                    user_specified=False
                )
            
            # 4. Step 2: Determine language from supported content
            # Calculate supported content (EN + zh-TW + numbers/symbols)
            # Since we already excluded unsupported chars, supported = total - unsupported
            supported_chars = stats.total_chars - unsupported_chars
            
            if supported_chars == 0:
                # No valid content
                raise LanguageDetectionError(
                    text_length=len(text),
                    reason="No valid Traditional Chinese or English content found"
                )
            
            # Calculate zh-TW percentage of supported content
            # Note: supported_chars = english_chars + traditional_chinese_chars + (numbers/symbols)
            # Since numbers/symbols are not counted in stats, supported_chars here is just EN + zh-TW
            trad_chinese_ratio_of_supported = stats.traditional_chinese_chars / supported_chars
            
            # 5. Apply 20% threshold rule
            if trad_chinese_ratio_of_supported >= self.TRADITIONAL_CHINESE_THRESHOLD:
                # Traditional Chinese >= 20% of supported content
                detected_lang = 'zh-TW'
                confidence = 0.9
                logger.info(
                    f"Detected: zh-TW (Traditional Chinese {trad_chinese_ratio_of_supported:.1%} "
                    f"of supported content >= 20%)"
                )
            else:
                # Traditional Chinese < 20%, use English as default
                detected_lang = 'en'
                confidence = 0.9
                logger.info(
                    f"Detected: en (Traditional Chinese {trad_chinese_ratio_of_supported:.1%} "
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
            logger.error(f"Unexpected error in language detection: {str(e)}")
            raise LanguageDetectionError(
                text_length=len(text) if text else 0,
                reason=f"Unexpected detection error: {str(e)}"
            )