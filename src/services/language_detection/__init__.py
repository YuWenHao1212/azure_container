"""
Language detection services for bilingual keyword extraction.
Supports English (en) and Traditional Chinese (zh-TW) only.
"""

from .bilingual_prompt_manager import BilingualPromptManager
from .detector import LanguageDetectionService
from .mixed_language_detector import MixedLanguageDetectionService
from .validator import LanguageValidator

__all__ = [
    "BilingualPromptManager",
    "LanguageDetectionService",
    "LanguageValidator",
    "MixedLanguageDetectionService"
]
