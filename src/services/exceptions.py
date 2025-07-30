"""
Custom exceptions for bilingual keyword extraction service.
Provides specialized error handling for language detection and extraction.
"""

from typing import Any


class ServiceError(Exception):
    """Base exception for all service errors."""
    pass


class BilingualServiceError(Exception):
    """Base exception for bilingual service errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "BILINGUAL_SERVICE_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class UnsupportedLanguageError(BilingualServiceError):
    """
    Exception raised when an unsupported language is detected or specified.
    
    This error should be returned to the user with clear guidance about
    supported languages and alternatives.
    """
    
    def __init__(self, 
                 detected_language: str, 
                 supported_languages: list[str],
                 confidence: float = None,
                 user_specified: bool = False):
        """
        Initialize unsupported language error.
        
        Args:
            detected_language: The language that was detected/specified
            supported_languages: List of supported language codes
            confidence: Detection confidence (if detected)
            user_specified: Whether language was explicitly specified by user
        """
        if user_specified:
            message = (
                f"Language '{detected_language}' is not supported. "
                f"Please use one of the supported languages: {', '.join(supported_languages)}"
            )
        else:
            confidence_text = f" (confidence: {confidence:.2f})" if confidence else ""
            message = (
                f"Detected language '{detected_language}'{confidence_text} is not supported. "
                f"This service only supports: {', '.join(supported_languages)}. "
                f"Please provide job descriptions in English or Traditional Chinese (Taiwan)."
            )
        
        details = {
            "detected_language": detected_language,
            "supported_languages": supported_languages,
            "confidence": confidence,
            "user_specified": user_specified,
            "suggestion": "Please provide the job description in English or Traditional Chinese (Taiwan)"
        }
        
        super().__init__(
            message=message,
            error_code="UNSUPPORTED_LANGUAGE",
            details=details
        )
        
        self.detected_language = detected_language
        self.supported_languages = supported_languages
        self.confidence = confidence
        self.user_specified = user_specified


class LanguageDetectionError(BilingualServiceError):
    """
    Exception raised when language detection fails.
    
    This typically happens with very short text, mixed languages,
    or text that doesn't contain enough linguistic markers.
    """
    
    def __init__(self, 
                 text_length: int = None,
                 reason: str = None,
                 fallback_language: str = "en"):
        """
        Initialize language detection error.
        
        Args:
            text_length: Length of text that failed detection
            reason: Specific reason for detection failure
            fallback_language: Language to fall back to
        """
        reason = reason or "Unable to reliably detect language"
        
        if text_length and text_length < 10:
            message = (
                f"Text too short for language detection ({text_length} characters). "
                f"Minimum 10 characters required. Using {fallback_language} as fallback."
            )
        else:
            message = (
                f"Language detection failed: {reason}. "
                f"Using {fallback_language} as fallback language."
            )
        
        details = {
            "text_length": text_length,
            "reason": reason,
            "fallback_language": fallback_language,
            "suggestion": "Please provide a longer, clearer job description for better language detection"
        }
        
        super().__init__(
            message=message,
            error_code="LANGUAGE_DETECTION_FAILED",
            details=details
        )
        
        self.text_length = text_length
        self.reason = reason
        self.fallback_language = fallback_language


class LowConfidenceDetectionError(BilingualServiceError):
    """
    Exception raised when language detection confidence is too low.
    
    This indicates the text might be mixed language, ambiguous,
    or contain insufficient linguistic markers.
    """
    
    def __init__(self, 
                 detected_language: str,
                 confidence: float,
                 threshold: float,
                 fallback_language: str = "en"):
        """
        Initialize low confidence detection error.
        
        Args:
            detected_language: Language detected with low confidence
            confidence: Actual confidence score
            threshold: Required confidence threshold
            fallback_language: Language to fall back to
        """
        message = (
            f"Language detection confidence too low: {confidence:.2f} < {threshold:.2f} "
            f"for '{detected_language}'. This might indicate mixed languages or ambiguous text. "
            f"Using {fallback_language} as fallback."
        )
        
        details = {
            "detected_language": detected_language,
            "confidence": confidence,
            "threshold": threshold,
            "fallback_language": fallback_language,
            "suggestion": "Please ensure the job description is written primarily in one language"
        }
        
        super().__init__(
            message=message,
            error_code="LOW_CONFIDENCE_DETECTION",
            details=details
        )
        
        self.detected_language = detected_language
        self.confidence = confidence
        self.threshold = threshold
        self.fallback_language = fallback_language


class PromptNotAvailableError(BilingualServiceError):
    """
    Exception raised when prompt is not available for a language.
    
    This indicates a configuration issue where language detection
    succeeded but no prompt template exists for that language.
    """
    
    def __init__(self, 
                 language: str,
                 version: str = None,
                 available_languages: list[str] = None):
        """
        Initialize prompt not available error.
        
        Args:
            language: Language for which prompt is not available
            version: Requested prompt version
            available_languages: List of available languages
        """
        version_text = f" (version: {version})" if version else ""
        available_text = f". Available: {available_languages}" if available_languages else ""
        
        message = (
            f"Prompt not available for language '{language}'{version_text}{available_text}. "
            f"This is a configuration issue."
        )
        
        details = {
            "language": language,
            "version": version,
            "available_languages": available_languages or [],
            "suggestion": "Contact system administrator or use a supported language"
        }
        
        super().__init__(
            message=message,
            error_code="PROMPT_NOT_AVAILABLE",
            details=details
        )
        
        self.language = language
        self.version = version
        self.available_languages = available_languages


class StandardizationError(BilingualServiceError):
    """
    Exception raised when keyword standardization fails.
    
    This typically happens when standardization dictionaries
    are not available or corrupted for a specific language.
    """
    
    def __init__(self, 
                 language: str,
                 reason: str = None,
                 keywords_count: int = None):
        """
        Initialize standardization error.
        
        Args:
            language: Language for which standardization failed
            reason: Specific reason for failure
            keywords_count: Number of keywords that failed standardization
        """
        reason = reason or "Standardization dictionary not available"
        keywords_text = f" for {keywords_count} keywords" if keywords_count else ""
        
        message = (
            f"Keyword standardization failed for language '{language}'{keywords_text}: {reason}. "
            f"Keywords will be returned without standardization."
        )
        
        details = {
            "language": language,
            "reason": reason,
            "keywords_count": keywords_count,
            "fallback_action": "returning unstandardized keywords"
        }
        
        super().__init__(
            message=message,
            error_code="STANDARDIZATION_FAILED",
            details=details
        )
        
        self.language = language
        self.reason = reason
        self.keywords_count = keywords_count


class BilingualValidationError(BilingualServiceError):
    """
    Exception raised when bilingual validation fails.
    
    This covers various validation issues like language parameter
    validation, text quality validation, etc.
    """
    
    def __init__(self, 
                 validation_type: str,
                 errors: list[str],
                 suggestions: list[str] = None):
        """
        Initialize bilingual validation error.
        
        Args:
            validation_type: Type of validation that failed
            errors: List of validation errors
            suggestions: List of suggestions to fix errors
        """
        errors_text = "; ".join(errors)
        message = f"Bilingual validation failed ({validation_type}): {errors_text}"
        
        details = {
            "validation_type": validation_type,
            "errors": errors,
            "suggestions": suggestions or []
        }
        
        super().__init__(
            message=message,
            error_code="BILINGUAL_VALIDATION_FAILED",
            details=details
        )
        
        self.validation_type = validation_type
        self.errors = errors
        self.suggestions = suggestions


def create_unsupported_language_response(error: UnsupportedLanguageError) -> dict[str, Any]:
    """
    Create a standardized API response for unsupported language errors.
    
    Args:
        error: UnsupportedLanguageError instance
        
    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "data": {
            "keywords": [],
            "keyword_count": 0,
            "standardized_terms": [],
            "confidence_score": 0.0,
            "processing_time_ms": 0,
            "extraction_method": "none",
            "intersection_stats": {
                "intersection_count": 0,
                "round1_count": 0,
                "round2_count": 0,
                "total_available": 0,
                "final_count": 0,
                "supplement_count": 0,
                "strategy_used": "none",
                "warning": True,
                "warning_message": "Language not supported"
            },
            "warning": {
                "has_warning": True,
                "message": error.message,
                "expected_minimum": 12,
                "actual_extracted": 0,
                "suggestion": error.details.get("suggestion", "")
            },
            "prompt_version": "",
            "detected_language": error.detected_language,
            "input_language": error.detected_language if error.user_specified else "auto",
            "language_detection_time_ms": 0
        },
        "error": error.to_dict(),
        "timestamp": ""  # Will be filled by response handler
    }


class LLMServiceError(ServiceError):
    """Exception raised when LLM service fails."""
    pass


class ValidationError(ServiceError):
    """Exception raised when input validation fails."""
    pass


class ProcessingError(ServiceError):
    """Exception raised when processing fails."""
    pass


def create_language_detection_error_response(error: LanguageDetectionError) -> dict[str, Any]:
    """
    Create a standardized API response for language detection errors.
    
    Args:
        error: LanguageDetectionError instance
        
    Returns:
        Standardized error response dictionary with fallback processing
    """
    return {
        "success": True,  # Continue processing with fallback
        "data": {
            "keywords": [],  # Will be filled by fallback processing
            "keyword_count": 0,
            "standardized_terms": [],
            "confidence_score": 0.0,
            "processing_time_ms": 0,
            "extraction_method": "fallback",
            "intersection_stats": {
                "intersection_count": 0,
                "round1_count": 0,
                "round2_count": 0,
                "total_available": 0,
                "final_count": 0,
                "supplement_count": 0,
                "strategy_used": "fallback",
                "warning": True,
                "warning_message": "Language detection failed, using fallback"
            },
            "warning": {
                "has_warning": True,
                "message": error.message,
                "expected_minimum": 12,
                "actual_extracted": 0,
                "suggestion": error.details.get("suggestion", "")
            },
            "prompt_version": "",
            "detected_language": error.fallback_language,
            "input_language": "auto",
            "language_detection_time_ms": 0
        },
        "error": {
            "code": "",
            "message": "",
            "details": ""
        },
        "timestamp": ""
    }