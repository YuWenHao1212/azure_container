"""
Data models for keyword extraction functionality.
Following Bubble.io compatibility - no Optional types.
"""
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field, validator

from src.models.response import IntersectionStats, StandardizedTerm, WarningInfo


class KeywordExtractionRequest(BaseModel):
    """Request model for keyword extraction."""
    job_description: str = Field(
        description="Job description text to extract keywords from",
        max_length=20000
    )
    max_keywords: int = Field(
        default=16,
        description="Maximum number of keywords to extract",
        ge=5,
        le=25
    )
    include_standardization: bool = Field(
        default=True,
        description="Whether to apply keyword standardization"
    )
    use_multi_round_validation: bool = Field(
        default=True,
        description="Whether to use 2-round intersection strategy"
    )
    prompt_version: str = Field(
        default="1.4.0",
        description=(
            "Prompt version to use (e.g., '1.0.0', '1.1.0', '1.3.0', '1.4.0', "
            "'latest')"
        )
    )
    language: str = Field(
        default="auto",
        description=(
            "Language preference: 'auto' for detection, 'en' for English, "
            "'zh-TW' for Traditional Chinese"
        )
    )

    @validator('job_description')
    def validate_job_description(cls, v):
        """驗證職位描述內容"""
        if len(v.strip()) < 200:
            raise ValueError("Job description must be at least 200 characters")
        return v.strip()

    @validator('language')
    def validate_language(cls, v):
        """驗證語言參數"""
        allowed = ["auto", "en", "zh-TW"]
        if v not in allowed:
            raise ValueError(f"Language must be one of {allowed}")
        return v

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "job_description": "We are seeking a Senior Python Developer...",
                "max_keywords": 16,
                "include_standardization": True,
                "use_multi_round_validation": True,
                "prompt_version": "1.3.0",
                "language": "auto"
            }
        }


class KeywordExtractionData(BaseModel):
    """Data model for keyword extraction results."""
    keywords: list[str] = Field(
        default_factory=list,
        description="Extracted keywords"
    )
    keyword_count: int = Field(
        default=0,
        description="Number of keywords extracted"
    )
    standardized_terms: list[StandardizedTerm] = Field(
        default_factory=list,
        description="Standardization mappings applied"
    )
    confidence_score: float = Field(
        default=0.0,
        description="Confidence score of extraction",
        ge=0.0,
        le=1.0
    )
    processing_time_ms: int = Field(
        default=0,
        description="Processing time in milliseconds"
    )
    extraction_method: str = Field(
        default="",
        description="Method used for extraction"
    )
    intersection_stats: IntersectionStats = Field(
        default_factory=IntersectionStats,
        description="Statistics for intersection-based extraction"
    )
    warning: WarningInfo = Field(
        default_factory=WarningInfo,
        description="Warning information if any"
    )
    prompt_version: str = Field(
        default="",
        description="Prompt version used for extraction"
    )
    detected_language: str = Field(
        default="",
        description="Language detected from input text"
    )
    input_language: str = Field(
        default="",
        description="Language parameter provided in request"
    )
    language_detection_time_ms: int = Field(
        default=0,
        description="Time spent on language detection in milliseconds"
    )

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "keywords": ["Python", "AWS", "Machine Learning"],
                "keyword_count": 3,
                "standardized_terms": [
                    {
                        "original": "Python programming",
                        "standardized": "Python",
                        "method": "dictionary"
                    }
                ],
                "confidence_score": 0.95,
                "processing_time_ms": 1250,
                "extraction_method": "2-round_intersection",
                "intersection_stats": {
                    "intersection_count": 18,
                    "round1_count": 22,
                    "round2_count": 21,
                    "total_available": 25,
                    "final_count": 18,
                    "supplement_count": 0,
                    "strategy_used": "pure_intersection",
                    "warning": False,
                    "warning_message": ""
                },
                "warning": {
                    "has_warning": False,
                    "message": "",
                    "expected_minimum": 12,
                    "actual_extracted": 18,
                    "suggestion": ""
                },
                "prompt_version": "1.0.0",
                "detected_language": "en",
                "input_language": "auto",
                "language_detection_time_ms": 85
            }
        }


class KeywordExtractionResponse(BaseModel):
    """
    Standard API response for keyword extraction.
    Bubble.io compatible - all fields always present.
    """
    success: bool = Field(
        description="Whether the operation was successful"
    )
    data: KeywordExtractionData = Field(
        default_factory=KeywordExtractionData,
        description="Extraction results data"
    )
    error: dict[str, str] = Field(
        default_factory=lambda: {"code": "", "message": "", "details": ""},
        description="Error information if any"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp"
    )

    class Config:
        json_schema_extra: ClassVar = {
            "example": {
                "success": True,
                "data": {
                    "keywords": ["Python", "AWS", "Machine Learning"],
                    "keyword_count": 3,
                    "standardized_terms": [],
                    "confidence_score": 0.95,
                    "processing_time_ms": 1250,
                    "extraction_method": "2-round_intersection",
                    "intersection_stats": {
                        "intersection_count": 18,
                        "round1_count": 22,
                        "round2_count": 21,
                        "total_available": 25,
                        "final_count": 18,
                        "supplement_count": 0,
                        "strategy_used": "pure_intersection",
                        "warning": False,
                        "warning_message": ""
                    },
                    "warning": {
                        "has_warning": False,
                        "message": "",
                        "expected_minimum": 12,
                        "actual_extracted": 18,
                        "suggestion": ""
                    },
                    "prompt_version": "1.0.0",
                    "detected_language": "en",
                    "input_language": "auto",
                    "language_detection_time_ms": 85
                },
                "error": {
                    "code": "",
                    "message": "",
                    "details": ""
                },
                "timestamp": "2025-07-01T00:48:30.000Z"
            }
        }
