"""
Resume Tailoring Service for optimizing resumes based on gap analysis.
"""

import asyncio
import json
import logging
import re
import time

from ..core.config import get_settings
from ..core.html_processor import HTMLProcessor
from ..core.language_handler import LanguageHandler
from ..core.marker_fixer import MarkerFixer
from ..core.monitoring_service import monitoring_service
from ..core.star_formatter import STARFormatter
from ..models.api.resume_tailoring import (
    CoverageDetails,
    CoverageStats,
    GapAnalysisInput,
    SimilarityStats,
    TailoringResult,
    VisualMarkerStats,
)
from ..models.domain.tailoring import (
    TailoringContext,
)
from ..services.index_calculation import (
    IndexCalculationService,
    analyze_keyword_coverage,
)
from ..services.llm_factory import get_llm_client
from ..services.resume_sections import SectionProcessor
from ..services.standardization import (
    EnglishStandardizer,
    TraditionalChineseStandardizer,
)
from ..services.unified_prompt_service import UnifiedPromptService

logger = logging.getLogger(__name__)


class ResumeTailoringService:
    """Service for tailoring resumes based on gap analysis results"""

    def __init__(self):
        self.settings = get_settings()
        self.llm_client = get_llm_client(api_name="resume_tailor")
        self.monitoring = monitoring_service
        self.prompt_service = UnifiedPromptService(task_path="resume_tailoring")

        # Initialize components
        self.html_processor = HTMLProcessor()
        self.language_handler = LanguageHandler()
        self.star_formatter = STARFormatter()
        self.marker_fixer = MarkerFixer()
        self.section_processor = SectionProcessor()

        # Initialize standardizers
        self.en_standardizer = EnglishStandardizer()
        self.zh_tw_standardizer = TraditionalChineseStandardizer()

        logger.info("ResumeTailoringService initialized")

    async def tailor_resume(
        self,
        job_description: str,
        original_resume: str,
        gap_analysis: GapAnalysisInput,
        language: str = "en",
        include_markers: bool = True
    ) -> TailoringResult:
        """
        Main method to tailor a resume based on gap analysis results.

        Args:
            job_description: Target job description
            original_resume: Original resume in HTML format
            gap_analysis: Gap analysis results
            language: Output language (en or zh-TW)
            include_markers: Whether to include visual markers

        Returns:
            TailoringResult with optimized resume and statistics
        """
        start_time = time.time()

        # Track start
        self.monitoring.track_event("ResumeTailoringStarted", {
            "language": language,
            "resume_length": len(original_resume),
            "strengths_count": len(gap_analysis.core_strengths),
            "improvements_count": len(gap_analysis.quick_improvements)
        })

        try:
            # Validate inputs
            self._validate_inputs(job_description, original_resume, language)

            # Build tailoring context
            context = self._build_context(
                job_description,
                original_resume,
                gap_analysis,
                language,
                include_markers
            )

            # Call LLM to optimize resume
            optimized_data = await self._optimize_with_llm(context)

            # Process the result
            result = await self._process_optimization_result(
                optimized_data,
                original_resume,
                include_markers,
                gap_analysis,
                job_description,
                language
            )

            # Track metrics
            duration = time.time() - start_time
            self._track_metrics(result, duration, language)

            return result

        except Exception as e:
            logger.error(f"Resume tailoring failed: {e!s}")
            self.monitoring.track_event("ResumeTailoringFailed", {
                "language": language,
                "error": str(e)
            })
            raise

    def _validate_inputs(self, job_description: str, original_resume: str, language: str):
        """Validate input parameters"""
        if not job_description or len(job_description) < 50:
            raise ValueError("Job description too short")

        if not original_resume or len(original_resume) < 100:
            raise ValueError("Resume too short")

        if not self.language_handler.is_supported_language(language):
            raise ValueError(f"Unsupported language: {language}")

        # Validate both inputs can be processed as HTML/text
        is_valid_jd, error_jd = self.html_processor.validate_html_structure(job_description)
        if not is_valid_jd:
            raise ValueError(f"Invalid job description: {error_jd}")

        is_valid_resume, error_resume = self.html_processor.validate_html_structure(original_resume)
        if not is_valid_resume:
            raise ValueError(f"Invalid resume: {error_resume}")

    def _build_context(
        self,
        job_description: str,
        original_resume: str,
        gap_analysis: GapAnalysisInput,
        language: str,
        include_markers: bool
    ) -> TailoringContext:
        """Build context for tailoring"""
        # Normalize inputs to HTML format
        job_description_html = self.html_processor.normalize_to_html(job_description)
        original_resume_html = self.html_processor.normalize_to_html(original_resume)

        # Standardize section titles to avoid duplication
        original_resume_html = self.html_processor.standardize_section_titles(original_resume_html)
        logger.info("Standardized section titles in original resume to avoid duplication")

        # Standardize keywords based on language
        standardizer = self.en_standardizer if language == "en" else self.zh_tw_standardizer

        # Standardize covered keywords
        covered_result = standardizer.standardize_keywords(gap_analysis.covered_keywords)
        covered_keywords = covered_result.standardized_keywords

        # Standardize missing keywords
        missing_result = standardizer.standardize_keywords(gap_analysis.missing_keywords)
        missing_keywords = missing_result.standardized_keywords

        return TailoringContext(
            job_description=job_description_html,
            original_resume=original_resume_html,
            core_strengths=gap_analysis.core_strengths if isinstance(gap_analysis.core_strengths, list) else [],
            key_gaps=gap_analysis.key_gaps if isinstance(gap_analysis.key_gaps, list) else [],
            quick_improvements=(
                gap_analysis.quick_improvements
                if isinstance(gap_analysis.quick_improvements, list) else []
            ),
            covered_keywords=covered_keywords,
            missing_keywords=missing_keywords,
            language=language,
            include_markers=include_markers
        )

    async def _optimize_with_llm(self, context: TailoringContext) -> dict:
        """Call LLM to optimize resume"""
        # Get prompt template - we use the same prompt for all languages
        # The prompt itself contains language output instructions
        try:
            # First try to load language-specific prompt with v1.1.0
            prompt_config = self.prompt_service.get_prompt_config(context.language, "1.1.0")
        except FileNotFoundError:
            # Fall back to language-agnostic prompt
            # Load the v1.1.0.yaml file directly
            prompt_config = self.prompt_service.simple_prompt_manager.load_prompt_config_by_filename(
                "resume_tailoring", "v1.1.0.yaml"
            )

        # Build prompt with context
        system_prompt = prompt_config.get_system_prompt()

        # Prepare prompt variables
        output_language = self.language_handler.get_output_language(context.language)

        prompt_vars = {
            "output_language": output_language,
            "job_description": context.job_description,
            "original_resume": context.original_resume,
            "core_strengths": "\n".join(f"- {s}" for s in context.core_strengths),
            "key_gaps": "\n".join(f"- {g}" for g in context.key_gaps),
            "quick_improvements": "\n".join(f"- {i}" for i in context.quick_improvements),
            "covered_keywords": ", ".join(context.covered_keywords),
            "missing_keywords": ", ".join(context.missing_keywords)
        }

        # Format prompts
        user_prompt = prompt_config.format_user_prompt(**prompt_vars)

        # Call LLM with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Calling LLM for resume optimization (attempt {attempt + 1})")

                response = await self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=prompt_config.llm_config.temperature,
                    max_tokens=prompt_config.llm_config.max_tokens,
                    top_p=prompt_config.llm_config.top_p
                )

                # Track token usage
                if 'usage' in response:
                    usage = response['usage']
                    self.monitoring.track_event("LLMTokenUsage", {
                        "service": "resume_tailoring",
                        "input_tokens": usage.get('prompt_tokens', 0),
                        "output_tokens": usage.get('completion_tokens', 0),
                        "total_tokens": usage.get('total_tokens', 0),
                        "model": "gpt-4o-2"
                    })

                # Parse response
                choices = response.get('choices', [])
                if choices:
                    content = choices[0].get('message', {}).get('content', '')
                    logger.info(f"LLM raw response length: {len(content)} chars")
                    logger.info(f"LLM raw response preview: {content[:200]}...")
                    return self._parse_llm_response(content)
                else:
                    raise ValueError("No response content from LLM")

            except Exception as e:
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e!s}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

    def _parse_llm_response(self, content: str) -> dict:
        """Parse LLM response to extract optimized resume and improvements"""
        result = None

        # First check if the content is wrapped in markdown code blocks
        if content.strip().startswith('```json') and content.strip().endswith('```'):
            # Extract JSON from markdown code block
            json_str = content.strip()[7:-3].strip()  # Remove ```json and ```
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from markdown block")

        if not result:
            try:
                # Try to parse as JSON directly
                result = json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract from text
                logger.warning("LLM response is not valid JSON, attempting text extraction")

                # Extract optimized resume
                resume_match = re.search(
                    r'"optimized_resume":\s*"([^"]+)"',
                    content,
                    re.DOTALL
                )

                # Extract improvements
                improvements_match = re.search(
                    r'"applied_improvements":\s*\[(.*?)\]',
                    content,
                    re.DOTALL
                )

                if resume_match:
                    optimized_resume = resume_match.group(1)
                    improvements = []

                    if improvements_match:
                        improvements_text = improvements_match.group(1)
                        # Extract individual improvements
                        improvements = re.findall(r'"([^"]+)"', improvements_text)

                    result = {
                        "optimized_resume": optimized_resume,
                        "applied_improvements": improvements
                    }

        # Validate extraction result
        if not result:
            logger.error(f"Failed to extract any data from LLM response: {content[:500]}...")
            self.monitoring.track_event("ResumeTailoringExtractionFailed", {
                "response_preview": content[:500],
                "response_length": len(content)
            })
            raise ValueError("Could not parse LLM response")

        if not result.get("optimized_resume"):
            logger.error(f"Failed to extract optimized_resume from LLM response: {content[:500]}...")
            self.monitoring.track_event("ResumeTailoringMissingField", {
                "missing_field": "optimized_resume",
                "response_preview": content[:500],
                "extracted_fields": list(result.keys())
            })
            raise ValueError("Extracted data missing optimized_resume field")

        # Log successful extraction
        if not result.get("applied_improvements"):
            logger.warning("No applied_improvements found in LLM response, using empty list")
            result["applied_improvements"] = []

        return result

    async def _process_optimization_result(
        self,
        optimized_data: dict,
        original_resume: str,
        include_markers: bool,
        gap_analysis: GapAnalysisInput,
        job_description: str,
        language: str
    ) -> TailoringResult:
        """Process optimization result from LLM"""
        optimized_resume = optimized_data.get("optimized_resume", "")
        applied_improvements = optimized_data.get("applied_improvements", [])

        # Remove format markers
        optimized_resume = self.star_formatter.remove_format_markers(optimized_resume)

        # Calculate original keyword coverage before optimization
        all_keywords = gap_analysis.covered_keywords + gap_analysis.missing_keywords
        original_coverage = analyze_keyword_coverage(original_resume, all_keywords)

        # Fix incorrectly placed markers and apply keyword markers properly
        if include_markers:
            # Fix markers and apply keyword marking
            optimized_resume = self.marker_fixer.fix_and_enhance_markers(
                optimized_resume,
                keywords=gap_analysis.missing_keywords,
                original_keywords=gap_analysis.covered_keywords
            )

        # Count markers if included
        marker_counts = self.html_processor.count_markers(optimized_resume)

        # Statistics are now calculated via visual markers and coverage

        visual_markers = VisualMarkerStats(
            keyword_new=marker_counts.get("keyword", 0),
            keyword_existing=marker_counts.get("keyword-existing", 0),
            placeholder=marker_counts.get("placeholder", 0),
            new_section=marker_counts.get("new", 0),
            modified=marker_counts.get("modified", 0)
        )

        # Generate HTML formatted improvements list
        applied_improvements_html = self._format_improvements_as_html(applied_improvements)

        # Calculate index and similarity
        index_calc_service = IndexCalculationService()

        # Calculate similarity for original resume
        from ..services.index_calculation import compute_similarity

        original_raw, original_similarity = await compute_similarity(
            original_resume,
            job_description
        )

        # Calculate full index for optimized resume
        optimized_index = await index_calc_service.calculate_index(
            optimized_resume,
            job_description,
            all_keywords
        )

        # Build similarity stats
        similarity = SimilarityStats(
            before=original_similarity,
            after=optimized_index["similarity_percentage"],
            improvement=optimized_index["similarity_percentage"] - original_similarity
        )

        # Build coverage stats
        coverage_before = CoverageDetails(
            percentage=original_coverage["coverage_percentage"],
            covered=original_coverage["covered_keywords"],
            missed=[kw for kw in all_keywords if kw not in original_coverage["covered_keywords"]]
        )

        coverage_after = CoverageDetails(
            percentage=optimized_index["keyword_coverage"]["coverage_percentage"],
            covered=optimized_index["keyword_coverage"]["covered_keywords"],
            missed=[kw for kw in all_keywords if kw not in optimized_index["keyword_coverage"]["covered_keywords"]]
        )

        coverage = CoverageStats(
            before=coverage_before,
            after=coverage_after,
            improvement=(
                optimized_index["keyword_coverage"]["coverage_percentage"] -
                original_coverage["coverage_percentage"]
            ),
            newly_added=list(
                set(optimized_index["keyword_coverage"]["covered_keywords"]) -
                set(original_coverage["covered_keywords"])
            )
        )

        # Remove markers if not requested
        if not include_markers:
            optimized_resume = self.html_processor.remove_markers(optimized_resume)

        return TailoringResult(
            resume=optimized_resume,
            improvements=applied_improvements_html,
            markers=visual_markers,
            similarity=similarity,
            coverage=coverage
        )

    def _format_improvements_as_html(self, improvements: list[str]) -> str:
        """Format improvements list as HTML for direct display"""
        if not improvements:
            return "<p>No improvements applied.</p>"

        # Create HTML list
        html_parts = ["<ul>"]
        for improvement in improvements:
            # Escape any HTML in the improvement text
            escaped_improvement = improvement.replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(f"  <li>{escaped_improvement}</li>")
        html_parts.append("</ul>")

        return "\n".join(html_parts)

    # Removed _calculate_optimization_stats - no longer needed in v2.1

    def _track_metrics(self, result: TailoringResult, duration: float, language: str):
        """Track optimization metrics"""
        self.monitoring.track_event("ResumeTailoringCompleted", {
            "duration_ms": duration * 1000,
            "language": language,
            "keywords_new": result.markers.keyword_new,
            "keywords_existing": result.markers.keyword_existing,
            "placeholders": result.markers.placeholder,
            "new_sections": result.markers.new_section,
            "modified_content": result.markers.modified,
            "similarity_improvement": result.similarity.improvement,
            "coverage_improvement": result.coverage.improvement
        })
