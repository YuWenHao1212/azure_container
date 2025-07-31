"""
Domain models for resume tailoring logic.
"""

from dataclasses import dataclass
from enum import Enum


class OptimizationType(str, Enum):
    """Types of optimizations that can be applied"""
    STRENGTH = "strength"
    KEYWORD = "keyword"
    PLACEHOLDER = "placeholder"
    NEW = "new"
    IMPROVEMENT = "improvement"


@dataclass
class OptimizationMarker:
    """Represents a single optimization marker"""
    type: OptimizationType
    content: str
    css_class: str
    section: str
    description: str | None = None


@dataclass
class SectionOptimization:
    """Optimization details for a resume section"""
    section_name: str
    original_content: str
    optimized_content: str
    markers: list[OptimizationMarker]
    improvements: list[str]
    keywords_added: list[str]
    strengths_highlighted: list[str]


@dataclass
class TailoringContext:
    """Context for resume tailoring"""
    job_description: str
    original_resume: str
    core_strengths: list[str]
    key_gaps: list[str]
    quick_improvements: list[str]
    covered_keywords: list[str]
    missing_keywords: list[str]
    language: str
    include_markers: bool


@dataclass
class ResumeSection:
    """Represents a section in the resume"""
    name: str
    content: str
    html_element: str
    order: int
    is_required: bool = False


@dataclass
class ResumeStructure:
    """Parsed resume structure"""
    sections: dict[str, ResumeSection]
    has_summary: bool
    total_sections: int

    def get_section(self, name: str) -> ResumeSection | None:
        """Get section by name (case-insensitive)"""
        name_lower = name.lower()
        for section_name, section in self.sections.items():
            if section_name.lower() == name_lower:
                return section
        return None

    def add_section(self, name: str, content: str, order: int = 0):
        """Add a new section"""
        self.sections[name] = ResumeSection(
            name=name,
            content=content,
            html_element="",
            order=order
        )
        self.total_sections = len(self.sections)


@dataclass
class TailoringMetrics:
    """Metrics for monitoring and cost tracking"""
    optimization_duration: float
    sections_processed: int
    keywords_added: int
    strengths_highlighted: int
    placeholders_added: int
    llm_retry_count: int
    input_tokens: int
    output_tokens: int
    total_cost: float
    language: str
    model_used: str
