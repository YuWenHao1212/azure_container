"""
Language validation service for bilingual keyword extraction.
Provides validation utilities for language detection and processing.
"""

import logging
from typing import Any, Optional

from ..exceptions import (
    LanguageDetectionError,
    LowConfidenceDetectionError,
    UnsupportedLanguageError,
)
from .detector import LanguageDetectionService

logger = logging.getLogger(__name__)


class LanguageValidationResult:
    """Result of language validation."""

    def __init__(self, is_valid: bool, language: str = "", errors: Optional[list[str]] = None, confidence: float = 0.0):
        self.is_valid = is_valid
        self.language = language
        self.errors = errors or []
        self.confidence = confidence

    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "is_valid": self.is_valid,
            "language": self.language,
            "errors": self.errors,
            "confidence": self.confidence
        }


class LanguageValidator:
    """
    Language validation service for bilingual keyword extraction.

    Provides validation utilities for:
    - Language parameter validation
    - Text content validation
    - Language detection result validation
    """

    def __init__(self, detection_service: LanguageDetectionService | None = None):
        """
        Initialize validator with optional detection service.

        Args:
            detection_service: LanguageDetectionService instance for validation
        """
        self.detection_service = detection_service or LanguageDetectionService()

    def validate_language_parameter(self, language: str) -> LanguageValidationResult:
        """
        Validate language parameter from API request.

        Args:
            language: Language parameter ("auto", "en", "zh-TW")

        Returns:
            LanguageValidationResult with validation status
        """
        allowed_languages = ["auto", *self.detection_service.get_supported_languages()]

        if not language:
            return LanguageValidationResult(
                is_valid=False,
                errors=["Language parameter is required"]
            )

        if language not in allowed_languages:
            return LanguageValidationResult(
                is_valid=False,
                language=language,
                errors=[f"Language '{language}' not supported. Allowed: {allowed_languages}"]
            )

        logger.debug(f"Language parameter '{language}' validation passed")
        return LanguageValidationResult(is_valid=True, language=language)

    def validate_text_for_detection(self, text: str) -> LanguageValidationResult:
        """
        Validate text content for language detection.

        Args:
            text: Input text to validate

        Returns:
            LanguageValidationResult with validation status
        """
        if not text:
            return LanguageValidationResult(
                is_valid=False,
                errors=["Text content is required"]
            )

        text = text.strip()

        if not text:
            return LanguageValidationResult(
                is_valid=False,
                errors=["Text content is empty after trimming"]
            )

        if not self.detection_service.validate_text_length(text):
            min_length = self.detection_service.MIN_TEXT_LENGTH
            return LanguageValidationResult(
                is_valid=False,
                errors=[f"Text too short for detection. Minimum length: {min_length} characters"]
            )

        # Check for suspicious content patterns
        if self._contains_suspicious_patterns(text):
            return LanguageValidationResult(
                is_valid=False,
                errors=["Text contains suspicious patterns"]
            )

        logger.debug(f"Text validation passed for {len(text)} characters")
        return LanguageValidationResult(is_valid=True)

    async def validate_with_detection(
        self, text: str, expected_language: Optional[str] = None
    ) -> LanguageValidationResult:
        """
        Validate text with actual language detection.

        Args:
            text: Input text to detect and validate
            expected_language: Expected language code for comparison

        Returns:
            LanguageValidationResult with detection results
        """
        # First validate text content
        text_validation = self.validate_text_for_detection(text)
        if not text_validation.is_valid:
            return text_validation

        try:
            # Perform language detection
            detection_result = await self.detection_service.detect_language(text)

            result = LanguageValidationResult(
                is_valid=True,
                language=detection_result.language,
                confidence=detection_result.confidence
            )

            # Validate against expected language if provided
            # SIM102: Combine nested if statements using 'and'
            if (expected_language and expected_language != "auto" and
                detection_result.language != expected_language):
                    result.add_error(
                        f"Detected language '{detection_result.language}' does not match expected '{expected_language}'"
                    )

            logger.info(f"Language detection validation completed: {detection_result.language}")
            return result

        except UnsupportedLanguageError as e:
            return LanguageValidationResult(
                is_valid=False,
                language=e.detected_language,
                confidence=e.confidence,
                errors=[f"Unsupported language detected: {e.detected_language}"]
            )

        except LowConfidenceDetectionError as e:
            return LanguageValidationResult(
                is_valid=False,
                language=e.detected_language,
                confidence=e.confidence,
                errors=[f"Low confidence detection: {e.confidence:.2f} < {e.threshold}"]
            )

        except LanguageDetectionError as e:
            return LanguageValidationResult(
                is_valid=False,
                errors=[str(e)]
            )

        except Exception as e:
            logger.error(f"Unexpected error in language validation: {e!s}")
            return LanguageValidationResult(
                is_valid=False,
                errors=[f"Language detection failed: {e!s}"]
            )

    def _contains_suspicious_patterns(self, text: str) -> bool:
        """
        Check for suspicious patterns in text content.

        Args:
            text: Text to check

        Returns:
            True if suspicious patterns found
        """
        suspicious_patterns = [
            # Excessive repetition
            lambda t: len(set(t.split())) < len(t.split()) * 0.3,
            # Too many special characters
            lambda t: sum(1 for c in t if not c.isalnum() and not c.isspace()) > len(t) * 0.5,
            # Excessive whitespace
            lambda t: t.count(' ') > len(t) * 0.7
        ]

        for pattern_check in suspicious_patterns:
            try:
                if pattern_check(text):
                    logger.warning("Suspicious pattern detected in text")
                    return True
            except Exception as e:
                # Skip pattern check if it fails
                logger.debug(f"Pattern check failed for suspicious content detection: {e}")
                continue

        return False

    def validate_language_consistency(self,
                                     input_language: str,
                                     detected_language: str,
                                     extracted_keywords: list[str]) -> LanguageValidationResult:
        """
        Validate language consistency between input, detection, and output.

        Args:
            input_language: Language parameter from request
            detected_language: Language detected from text
            extracted_keywords: Keywords extracted from text

        Returns:
            LanguageValidationResult with consistency validation
        """
        result = LanguageValidationResult(is_valid=True)

        # If explicit language was specified, it should match detection
        if input_language != "auto" and input_language != detected_language:
            result.add_error(
                f"Language mismatch: requested '{input_language}', detected '{detected_language}'"
            )

        # Basic keyword language consistency check
        # SIM102: Combine nested if statements using 'and'
        if (extracted_keywords and detected_language and
            not self._validate_keyword_language_consistency(extracted_keywords, detected_language)):
                result.add_error(
                    f"Keywords language inconsistent with detected language '{detected_language}'"
                )

        logger.debug(f"Language consistency validation: {result.is_valid}")
        return result

    def _validate_keyword_language_consistency(self, keywords: list[str], language: str) -> bool:
        """
        Basic validation of keyword language consistency.

        Args:
            keywords: List of extracted keywords
            language: Expected language

        Returns:
            True if keywords appear consistent with expected language
        """
        if not keywords or not language:
            return True

        # Simple heuristic checks
        if language == "en":
            # English keywords should primarily use ASCII characters
            ascii_ratio = sum(1 for kw in keywords if kw.isascii()) / len(keywords)
            return ascii_ratio > 0.7

        elif language == "zh-TW":
            # Traditional Chinese keywords should contain Chinese characters
            chinese_keywords = 0
            for keyword in keywords:
                if any('\u4e00' <= char <= '\u9fff' for char in keyword):
                    chinese_keywords += 1
            chinese_ratio = chinese_keywords / len(keywords)
            return chinese_ratio > 0.5

        # Default: assume consistent
        return True

    def get_validation_summary(self, validations: list[LanguageValidationResult]) -> dict[str, Any]:
        """
        Generate summary of multiple validation results.

        Args:
            validations: List of validation results

        Returns:
            Summary dictionary with overall status and details
        """
        total_validations = len(validations)
        passed_validations = sum(1 for v in validations if v.is_valid)

        all_errors = []
        for validation in validations:
            all_errors.extend(validation.errors)

        return {
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "failed_validations": total_validations - passed_validations,
            "success_rate": passed_validations / total_validations if total_validations > 0 else 0.0,
            "overall_status": "PASS" if passed_validations == total_validations else "FAIL",
            "errors": all_errors,
            "error_count": len(all_errors)
        }
