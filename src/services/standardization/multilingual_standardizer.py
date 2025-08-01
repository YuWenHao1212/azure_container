"""
Multilingual keyword standardizer.
Coordinates standardization across multiple languages.
"""

import logging
from typing import ClassVar

from .base_standardizer import BaseStandardizer, StandardizationResult
from .en_standardizer import EnglishStandardizer
from .zh_tw_standardizer import TraditionalChineseStandardizer

logger = logging.getLogger(__name__)


class MultilingualStandardizer:
    """
    Multilingual keyword standardizer that coordinates language-specific standardizers.

    Supports:
    - English (en): No standardization (preserve original terms)
    - Traditional Chinese (zh-TW): Taiwan-specific professional terminology
    """

    SUPPORTED_LANGUAGES: ClassVar[list] = ["en", "zh-TW"]

    def __init__(self):
        """Initialize multilingual standardizer with language-specific standardizers."""
        self.standardizers: dict[str, BaseStandardizer | None] = {}
        self._initialize_standardizers()

    def _initialize_standardizers(self):
        """Initialize all language-specific standardizers."""
        # English: Use EnglishStandardizer with 581 mappings
        try:
            self.standardizers["en"] = EnglishStandardizer()
            logger.info("English standardizer initialized with legacy dictionary")
        except Exception as e:
            logger.error(f"Failed to initialize English standardizer: {e!s}")
            self.standardizers["en"] = None

        # Traditional Chinese: Use specialized standardizer
        try:
            self.standardizers["zh-TW"] = TraditionalChineseStandardizer()
            logger.info("Traditional Chinese standardizer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Traditional Chinese standardizer: {e!s}")
            self.standardizers["zh-TW"] = None

    def standardize_keywords(self, keywords: list[str], language: str) -> StandardizationResult:
        """
        Standardize keywords for the specified language.

        Args:
            keywords: List of keywords to standardize
            language: Language code ("en" or "zh-TW")

        Returns:
            StandardizationResult with standardized keywords
        """
        if not keywords:
            return StandardizationResult([], [])

        if language not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language for standardization: {language}")
            # Return original keywords without standardization
            return StandardizationResult(keywords, keywords)

        logger.info(f"Standardizing {len(keywords)} keywords for language: {language}")

        # Get language-specific standardizer
        standardizer = self.standardizers.get(language)

        if standardizer is None:
            # No standardization for this language (e.g., English)
            logger.debug(f"No standardization applied for language: {language}")
            return StandardizationResult(keywords, keywords)

        if not standardizer.is_standardization_available():
            logger.warning(f"Standardization not available for language: {language}")
            return StandardizationResult(keywords, keywords)

        # Apply language-specific standardization
        try:
            result = standardizer.standardize_keywords(keywords)
            logger.info(
                f"Standardization complete for {language}: {len(keywords)} -> "
                f"{len(result.standardized_keywords)}"
            )
            return result

        except Exception as e:
            logger.error(f"Standardization failed for language {language}: {e!s}")
            # Return original keywords on error
            return StandardizationResult(keywords, keywords)

    def is_standardization_supported(self, language: str) -> bool:
        """
        Check if standardization is supported for a language.

        Args:
            language: Language code to check

        Returns:
            True if standardization is supported and available
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return False

        standardizer = self.standardizers.get(language)

        # English has no standardizer (by design)
        if language == "en":
            return True

        # Other languages need working standardizer
        return standardizer is not None and standardizer.is_standardization_available()

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported languages.

        Returns:
            List of supported language codes
        """
        return self.SUPPORTED_LANGUAGES.copy()

    def get_standardizer_for_language(self, language: str) -> BaseStandardizer | None:
        """
        Get the standardizer instance for a specific language.

        Args:
            language: Language code

        Returns:
            Standardizer instance or None if not available
        """
        return self.standardizers.get(language)

    def get_standardization_stats(self, language: str) -> dict:
        """
        Get standardization statistics for a language.

        Args:
            language: Language code

        Returns:
            Dictionary with standardization statistics
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return {
                "language": language,
                "supported": False,
                "reason": "Language not supported"
            }

        standardizer = self.standardizers.get(language)

        if language == "en":
            if standardizer and standardizer.is_standardization_available():
                stats = standardizer.get_standardization_stats()
                stats["language"] = language
                stats["supported"] = True
                stats["standardization_applied"] = True
                return stats
            else:
                return {
                    "language": language,
                    "supported": True,
                    "standardization_applied": False,
                    "reason": "English standardizer not available"
                }

        if standardizer is None:
            return {
                "language": language,
                "supported": True,
                "available": False,
                "reason": "Standardizer not initialized"
            }

        stats = standardizer.get_standardization_stats()
        stats["language"] = language
        stats["supported"] = True
        stats["standardization_applied"] = stats.get("available", False)

        return stats

    def get_all_standardization_stats(self) -> dict[str, dict]:
        """
        Get standardization statistics for all supported languages.

        Returns:
            Dictionary mapping language codes to their statistics
        """
        all_stats = {}

        for language in self.SUPPORTED_LANGUAGES:
            all_stats[language] = self.get_standardization_stats(language)

        return all_stats

    def validate_language_support(self, language: str) -> dict[str, any]:
        """
        Validate language support and return detailed status.

        Args:
            language: Language code to validate

        Returns:
            Dictionary with validation results
        """
        validation = {
            "language": language,
            "is_supported": language in self.SUPPORTED_LANGUAGES,
            "has_standardizer": False,
            "standardizer_ready": False,
            "errors": []
        }

        if not validation["is_supported"]:
            validation["errors"].append(f"Language '{language}' is not supported")
            return validation

        standardizer = self.standardizers.get(language)

        if language == "en":
            # English uses EnglishStandardizer with legacy dictionary
            if standardizer and standardizer.is_standardization_available():
                validation.update({
                    "has_standardizer": True,
                    "standardizer_ready": True,
                    "standardization_method": "dictionary_and_patterns"
                })
            else:
                validation["has_standardizer"] = bool(standardizer)
                validation["errors"].append("English standardizer not ready")
            return validation

        if standardizer is None:
            validation["errors"].append(f"No standardizer available for '{language}'")
            return validation

        validation["has_standardizer"] = True

        if not standardizer.is_standardization_available():
            validation["errors"].append(f"Standardizer for '{language}' is not ready")
            return validation

        validation["standardizer_ready"] = True
        validation["standardization_method"] = "dictionary_and_patterns"

        return validation

    def get_multilingual_summary(self) -> dict:
        """
        Get summary of multilingual standardization capabilities.

        Returns:
            Summary dictionary
        """
        summary = {
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "total_languages": len(self.SUPPORTED_LANGUAGES),
            "standardizers_ready": 0,
            "standardizers_with_errors": 0,
            "language_details": {}
        }

        for language in self.SUPPORTED_LANGUAGES:
            validation = self.validate_language_support(language)
            summary["language_details"][language] = validation

            if validation["standardizer_ready"]:
                summary["standardizers_ready"] += 1

            if validation["errors"]:
                summary["standardizers_with_errors"] += 1

        summary["system_ready"] = (summary["standardizers_with_errors"] == 0)

        return summary
