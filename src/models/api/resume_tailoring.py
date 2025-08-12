"""
API models for Resume Tailoring service.
Provides request/response models for resume optimization.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TailoringOptions(BaseModel):
    """Options for resume tailoring"""
    include_visual_markers: bool = Field(
        default=True,
        description="Include visual markers (CSS classes) for optimizations"
    )
    language: Literal["en", "zh-TW"] = Field(
        default="en",
        description="Output language for the tailored resume"
    )


class GapAnalysisInput(BaseModel):
    """Gap analysis results to be used for tailoring"""
    core_strengths: list[str] = Field(
        description="3-5 identified strengths from gap analysis (supports multiple formats)"
    )
    key_gaps: list[str] = Field(
        description="3-5 identified gaps from gap analysis (supports multiple formats)"
    )
    quick_improvements: list[str] = Field(
        description="3-5 actionable improvements from gap analysis (supports multiple formats)"
    )
    covered_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords already present in resume (comma-separated or list)"
    )
    missing_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that need to be added (comma-separated or list)"
    )
    coverage_percentage: int = Field(
        default=0,
        description="Keyword coverage percentage (0-100) from gap analysis",
        ge=0,
        le=100
    )
    similarity_percentage: int = Field(
        default=0,
        description="Resume similarity percentage (0-100) from gap analysis",
        ge=0,
        le=100
    )

    @model_validator(mode='before')
    @classmethod
    def parse_flexible_inputs(cls, data):
        """Parse various input formats before validation"""
        if not isinstance(data, dict):
            return data

        from ...utils.input_parsers import (
            parse_flexible_keywords,
            parse_multiline_items,
        )

        # Parse multi-line fields
        for field in ['core_strengths', 'key_gaps', 'quick_improvements']:
            if field in data and isinstance(data[field], str):
                data[field] = parse_multiline_items(data[field])

        # Parse keyword fields
        for field in ['covered_keywords', 'missing_keywords']:
            if field in data and isinstance(data[field], str):
                data[field] = parse_flexible_keywords(data[field])

        return data


class TailorResumeRequest(BaseModel):
    """Request model for resume tailoring"""
    job_description: str = Field(
        description="Target job description",
        min_length=50,
        max_length=10000
    )
    original_resume: str = Field(
        description="Original resume in HTML format",
        min_length=100,
        max_length=50000
    )
    gap_analysis: GapAnalysisInput = Field(
        description="Gap analysis results"
    )
    options: TailoringOptions = Field(
        default_factory=TailoringOptions,
        description="Tailoring options"
    )


# OptimizationStats removed in v2.1 - merged with VisualMarkerStats


class VisualMarkerStats(BaseModel):
    """Statistics about visual markers applied"""
    keyword_new: int = Field(
        default=0,
        description="Number of new keyword markers (opt-keyword)"
    )
    keyword_existing: int = Field(
        default=0,
        description="Number of existing keyword markers (opt-keyword-existing)"
    )
    placeholder: int = Field(
        default=0,
        description="Number of placeholder markers"
    )
    new_section: int = Field(
        default=0,
        description="Number of new section markers (opt-new)"
    )
    modified: int = Field(
        default=0,
        description="Number of modified content markers (opt-modified)"
    )


class SimilarityStats(BaseModel):
    """Similarity statistics"""
    before: int = Field(
        description="Original resume similarity percentage (0-100)"
    )
    after: int = Field(
        description="Optimized resume similarity percentage (0-100)"
    )
    improvement: int = Field(
        description="Percentage point improvement in similarity"
    )


class CoverageDetails(BaseModel):
    """Keyword coverage details"""
    percentage: int = Field(
        description="Keyword coverage percentage (0-100)"
    )
    covered: list[str] = Field(
        default_factory=list,
        description="List of keywords covered"
    )
    missed: list[str] = Field(
        default_factory=list,
        description="List of keywords not covered"
    )


class CoverageStats(BaseModel):
    """Keyword coverage statistics"""
    before: CoverageDetails = Field(
        description="Coverage before optimization"
    )
    after: CoverageDetails = Field(
        description="Coverage after optimization"
    )
    improvement: int = Field(
        description="Percentage point improvement in coverage"
    )
    newly_added: list[str] = Field(
        default_factory=list,
        description="List of new keywords successfully integrated"
    )
    removed: list[str] = Field(
        default_factory=list,
        description="List of keywords that were removed during optimization"
    )


# KeywordsAnalysis removed in v2.1 - redundant with CoverageStats


class KeywordTracking(BaseModel):
    """Keyword tracking information for resume optimization"""
    still_covered: list[str] = Field(
        default_factory=list,
        description="Keywords that were originally covered and remain in the optimized resume"
    )
    removed: list[str] = Field(
        default_factory=list,
        description="Keywords that were originally covered but removed during optimization"
    )
    newly_added: list[str] = Field(
        default_factory=list,
        description="Keywords that were originally missing and successfully added"
    )
    still_missing: list[str] = Field(
        default_factory=list,
        description="Keywords that were originally missing and remain missing"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages related to keyword changes"
    )


class ErrorInfo(BaseModel):
    """Standard error information structure"""
    has_error: bool = Field(
        default=False,
        description="Whether an error occurred"
    )
    code: str = Field(
        default="",
        description="Error code (e.g., VALIDATION_TOO_SHORT, EXTERNAL_RATE_LIMIT_EXCEEDED)"
    )
    message: str = Field(
        default="",
        description="Error message"
    )
    details: str = Field(
        default="",
        description="Additional error details"
    )
    field_errors: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Field-specific validation errors"
    )


class WarningInfo(BaseModel):
    """Warning information structure"""
    has_warning: bool = Field(
        default=False,
        description="Whether a warning exists"
    )
    message: str = Field(
        default="",
        description="Warning message"
    )
    details: list[str] = Field(
        default_factory=list,
        description="Detailed warning information (e.g., removed keywords)"
    )

class TailoringStatistics(BaseModel):
    """Additional statistics for resume tailoring (optional)"""
    markers: VisualMarkerStats = Field(
        description="Statistics about visual markers"
    )
    similarity: SimilarityStats = Field(
        description="Similarity statistics"
    )


class TailoringResult(BaseModel):
    """Result of resume tailoring - Bubble.io compatible format"""
    # Core fields required by Bubble.io
    optimized_resume: str = Field(
        description="Optimized resume HTML with visual markers"
    )
    applied_improvements: str = Field(
        default="",
        description="HTML formatted list of improvements for direct display"
    )
    improvement_count: int = Field(
        default=0,
        description="Number of improvements applied"
    )
    keyword_tracking: KeywordTracking = Field(
        default_factory=KeywordTracking,
        description="Detailed keyword tracking information"
    )
    coverage: CoverageStats = Field(
        description="Keyword coverage statistics"
    )
    processing_time_ms: int = Field(
        default=0,
        description="Total processing time in milliseconds"
    )
    stage_timings: dict[str, int] = Field(
        default_factory=lambda: {
            "instruction_compilation_ms": 0,
            "resume_writing_ms": 0
        },
        description="Timing breakdown by processing stage (milliseconds)"
    )

    # Keep these at root level for backward compatibility
    markers: VisualMarkerStats = Field(
        default_factory=VisualMarkerStats,
        description="Statistics about visual markers"
    )
    similarity: SimilarityStats = Field(
        default_factory=lambda: SimilarityStats(before=0, after=0, improvement=0),
        description="Similarity statistics"
    )


class TailoringResponse(BaseModel):
    """Response model for resume tailoring - Bubble.io compatible"""
    success: bool = Field(
        description="Whether the request was successful"
    )
    data: TailoringResult | None = Field(
        default=None,
        description="Tailoring result when successful"
    )
    warning: WarningInfo = Field(
        default_factory=WarningInfo,
        description="Warning information (e.g., keywords removed)"
    )
    # Error field only included when success=False
    error: ErrorInfo | None = Field(
        default=None,
        description="Error information if request failed",
        exclude_none=True  # Don't include in response when None
    )

    class Config:
        # Ensure empty arrays are preserved, not converted to null
        json_encoders = {
            list: lambda v: v if v is not None else []
        }


class TailoringError(BaseModel):
    """Error details for tailoring failures"""
    error_type: str = Field(
        description="Type of error that occurred"
    )
    details: str = Field(
        description="Detailed error message"
    )
    suggestion: str | None = Field(
        default=None,
        description="Suggestion for fixing the error"
    )
