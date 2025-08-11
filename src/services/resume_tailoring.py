"""
Resume Tailoring Service for optimizing resumes based on gap analysis.
"""

import json
import logging
import time
from typing import Any

from fastapi import HTTPException

from ..core.config import get_settings
from ..core.html_processor import HTMLProcessor
from ..core.language_handler import LanguageHandler
from ..core.marker_fixer import MarkerFixer
from ..core.monitoring_service import MonitoringService
from ..core.star_formatter import STARFormatter

# ResumeTailoringResponse will be a dict type for now
from ..services.llm_factory import get_llm_client
from ..services.resume_sections import SectionProcessor
from ..services.standardization import (
    EnglishStandardizer,
)
from ..services.standardization import (
    TraditionalChineseStandardizer as ChineseStandardizer,
)
from ..services.unified_prompt_service import UnifiedPromptService

logger = logging.getLogger(__name__)


class ResumeTailoringService:
    """
    Resume Tailoring Service v2.0.0 - Two-Stage Pipeline Architecture.

    This service implements a simplified, high-performance approach:
    1. Instruction Compiler - Converts gap analysis to structured instructions (GPT-4.1 mini)
    2. Resume Writer - Executes instructions with simplified prompt (v2.0.0)

    Note: Gap Analysis results are provided as input parameters, not computed internally.
    """

    def __init__(self):
        """Initialize the Resume Tailoring v2.0.0 service."""
        self.settings = get_settings()

        # LLM client for resume tailoring (GPT-4)
        self.llm_client = get_llm_client(api_name="resume_tailor")

        # Initialize monitoring
        self.monitoring = MonitoringService()

        # Initialize services
        self.prompt_service = UnifiedPromptService()
        self.html_processor = HTMLProcessor()
        self.language_handler = LanguageHandler()
        self.star_formatter = STARFormatter()
        self.marker_fixer = MarkerFixer()
        self.section_processor = SectionProcessor()

        # Initialize standardizers for different languages
        self.en_standardizer = EnglishStandardizer()
        self.zh_tw_standardizer = ChineseStandardizer()

        # Initialize Instruction Compiler for v2.0.0
        from src.services.instruction_compiler import InstructionCompiler
        self.instruction_compiler = InstructionCompiler()

        logger.info("ResumeTailoringService v2.0.0 initialized with two-stage pipeline")

    async def tailor_resume(
        self,
        original_resume: str,
        job_description: str,
        gap_analysis: dict[str, Any] | None = None,
        covered_keywords: list[str] | None = None,
        missing_keywords: list[str] | None = None,
        output_language: str = "English",
    ) -> dict[str, Any]:
        """
        Tailor a resume using the two-stage pipeline architecture.

        Stage 1: Instruction Compilation with GPT-4.1 mini
        Stage 2: Resume Writing with simplified prompt

        Args:
            original_resume: HTML content of the original resume
            job_description: Target job description
            gap_analysis: Gap analysis results (required) containing:
                - core_strengths or CoreStrengths
                - key_gaps or KeyGaps (with [Skill Gap] and [Presentation Gap] markers)
                - quick_improvements or QuickImprovements
            covered_keywords: Keywords already covered in resume
            missing_keywords: Keywords missing from resume
            output_language: Output language for the tailored resume

        Returns:
            ResumeTailoringResponse with optimized resume and metrics
        """

        start_time = time.time()
        stage_timings = {}

        try:
            # Validate inputs
            original_resume, job_description, gap_analysis = self._validate_inputs(
                original_resume, job_description, gap_analysis
            )

            # Clean up HTML whitespace
            original_resume = original_resume.strip()

            # Default keyword lists
            covered_keywords = covered_keywords or []
            missing_keywords = missing_keywords or []

            # Normalize gap analysis data format
            gap_analysis_data = self._normalize_gap_analysis(gap_analysis)

            # Stage 1: Compile Instructions using GPT-4.1 mini
            stage1_start = time.time()
            logger.info("Stage 1: Compiling instructions with GPT-4.1 mini")

            instructions = await self.instruction_compiler.compile_instructions(
                resume_html=original_resume,
                job_description=job_description,
                gap_analysis=gap_analysis_data,
                covered_keywords=covered_keywords,
                missing_keywords=missing_keywords,
            )

            stage_timings["instruction_compilation_ms"] = int((time.time() - stage1_start) * 1000)

            # Extract structure info for logging
            analysis = instructions.get('analysis', {})
            sections_found = sum(1 for v in analysis.get('resume_sections', {}).values() if v is not None)

            logger.info(
                f"Stage 1 completed in {stage_timings['instruction_compilation_ms']}ms. "
                f"Found {sections_found} existing sections in resume"
            )

            # Stage 2: Execute Instructions with Simplified Prompt
            stage2_start = time.time()
            logger.info("Stage 2: Executing resume optimization with simplified prompt")

            # Convert instructions to JSON string for the prompt
            import json
            instructions_json = json.dumps(instructions, indent=2)

            # Build context with simplified prompt and all necessary data
            context = self._build_context_v2(
                original_resume=original_resume,
                instructions_json=instructions_json,
                output_language=output_language,
                job_description=job_description,
                covered_keywords=covered_keywords,
                missing_keywords=missing_keywords,
                gap_analysis_data=gap_analysis_data,
                prompt_version="v2.1.0-simplified",  # Use simplified version
            )

            # Execute optimization with LLM
            optimized_result = await self._optimize_with_llm_v2(context, output_language)

            stage_timings["resume_writing_ms"] = int((time.time() - stage2_start) * 1000)
            logger.info(f"Stage 2 completed in {stage_timings['resume_writing_ms']}ms")

            # Process and validate the result
            final_result = await self._process_optimization_result_v2(
                optimized_result,
                original_resume,
                output_language,
                stage_timings,
                instructions,
            )

            # Calculate total time
            total_time_ms = int((time.time() - start_time) * 1000)

            # Update response with timing metrics
            final_result["processing_time_ms"] = total_time_ms
            final_result["stage_timings"] = stage_timings

            # Add gap analysis insights from simplified format
            analysis = instructions.get('analysis', {})
            section_metadata = analysis.get('section_metadata', {})

            final_result["gap_analysis_insights"] = {
                "structure_found": {
                    "sections": analysis.get('resume_sections', {}),
                    "metadata": section_metadata
                },
                "improvements_needed": len(final_result.get("applied_improvements", [])),
            }

            logger.info(
                f"Resume tailoring v2.1.0-simplified completed in {total_time_ms}ms "
                f"(Compile: {stage_timings['instruction_compilation_ms']}ms, "
                f"Write: {stage_timings['resume_writing_ms']}ms)"
            )

            # Track metrics
            self._track_metrics_v2(final_result, total_time_ms, stage_timings)

            return final_result

        except Exception as e:
            logger.error(f"Error in resume tailoring v2.1.0-simplified: {e!s}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Resume tailoring failed: {e!s}"
            ) from e

    def _validate_inputs(
        self,
        original_resume: str,
        job_description: str,
        gap_analysis: dict[str, Any] | None
    ) -> tuple[str, str, dict[str, Any]]:
        """Validate and clean input data."""
        if not original_resume or not original_resume.strip():
            raise HTTPException(
                status_code=400,
                detail="Original resume content is required"
            )

        if not job_description or not job_description.strip():
            raise HTTPException(
                status_code=400,
                detail="Job description is required"
            )

        if not gap_analysis:
            raise HTTPException(
                status_code=400,
                detail="Gap analysis results are required for Resume Tailoring v2.0.0"
            )

        # Clean inputs
        original_resume = original_resume.strip()
        job_description = job_description.strip()

        # Check minimum length
        if len(job_description) < 200:
            raise HTTPException(
                status_code=400,
                detail="Job description must be at least 200 characters"
            )

        if len(original_resume) < 200:
            raise HTTPException(
                status_code=400,
                detail="Resume must be at least 200 characters"
            )

        return original_resume, job_description, gap_analysis

    def _normalize_gap_analysis(self, gap_analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize gap analysis data to handle different formats.

        Accepts both formats:
        - API format: {"core_strengths", "key_gaps", "quick_improvements"}
        - Direct format: {"CoreStrengths", "KeyGaps", "QuickImprovements"}

        Returns:
        Normalized format with capitalized keys for backward compatibility
        """
        if not gap_analysis:
            raise ValueError("Gap analysis data is required")

        # Check which format we have and normalize
        normalized = {}

        # Handle core strengths
        if "core_strengths" in gap_analysis:
            normalized["CoreStrengths"] = gap_analysis["core_strengths"]
        elif "CoreStrengths" in gap_analysis:
            normalized["CoreStrengths"] = gap_analysis["CoreStrengths"]
        else:
            normalized["CoreStrengths"] = ""

        # Handle key gaps (must contain classification markers)
        if "key_gaps" in gap_analysis:
            normalized["KeyGaps"] = gap_analysis["key_gaps"]
        elif "KeyGaps" in gap_analysis:
            normalized["KeyGaps"] = gap_analysis["KeyGaps"]
        else:
            normalized["KeyGaps"] = ""

        # Handle quick improvements
        if "quick_improvements" in gap_analysis:
            normalized["QuickImprovements"] = gap_analysis["quick_improvements"]
        elif "QuickImprovements" in gap_analysis:
            normalized["QuickImprovements"] = gap_analysis["QuickImprovements"]
        else:
            normalized["QuickImprovements"] = ""

        # Also preserve other fields if present
        if "covered_keywords" in gap_analysis:
            normalized["covered_keywords"] = gap_analysis["covered_keywords"]
        if "missing_keywords" in gap_analysis:
            normalized["missing_keywords"] = gap_analysis["missing_keywords"]
        if "coverage_percentage" in gap_analysis:
            normalized["coverage_percentage"] = gap_analysis["coverage_percentage"]
        if "similarity_percentage" in gap_analysis:
            normalized["similarity_percentage"] = gap_analysis["similarity_percentage"]

        # Validate that we have the required gap classification markers
        key_gaps = normalized.get("KeyGaps", "")
        if key_gaps and not ("[Skill Gap]" in key_gaps or "[Presentation Gap]" in key_gaps):
            logger.warning(
                "Gap analysis KeyGaps does not contain classification markers "
                "([Skill Gap] or [Presentation Gap]). This may affect optimization quality."
            )

        return normalized

    def _build_context_v2(
        self,
        original_resume: str,
        instructions_json: str,
        output_language: str,
        job_description: str = "",
        covered_keywords: list[str] | None = None,
        missing_keywords: list[str] | None = None,
        gap_analysis_data: dict[str, Any] | None = None,
        prompt_version: str = "v2.1.0-simplified",  # Updated default to simplified version
    ) -> dict[str, Any]:
        """
        Build context for the v2.x prompt versions.

        Args:
            original_resume: Original resume HTML
            instructions_json: Structured instructions from Instruction Compiler
            output_language: Target language for output
            job_description: Target job description
            covered_keywords: Keywords already covered
            missing_keywords: Keywords missing
            gap_analysis_data: Original gap analysis data
            prompt_version: Prompt version to use (default: v2.1.0-simplified)

        Returns:
            Context dictionary for the prompt
        """
        # Extract gap analysis components for the main prompt
        core_strengths = ""
        key_gaps = ""
        quick_improvements = ""

        if gap_analysis_data:
            core_strengths = gap_analysis_data.get("CoreStrengths", "")
            key_gaps = gap_analysis_data.get("KeyGaps", "")
            quick_improvements = gap_analysis_data.get("QuickImprovements", "")

        covered_keywords_str = ", ".join(covered_keywords) if covered_keywords else "None"
        missing_keywords_str = ", ".join(missing_keywords) if missing_keywords else "None"

        # Load prompt from YAML using UnifiedPromptService
        # Support both v2.0.0 and v2.1.0-simplified versions
        prompt_template = self.prompt_service.load_prompt(
            feature="resume_tailoring",
            version=prompt_version
        )

        # Build the context with all necessary information
        context = {
            "system_prompt": prompt_template["prompts"]["system"].format(
                output_language=output_language
            ),
            "user_prompt": prompt_template["prompts"]["user"].format(
                original_resume=original_resume,
                job_description=job_description,
                instructions_json=instructions_json,
                covered_keywords=covered_keywords_str,
                missing_keywords=missing_keywords_str,
                core_strengths=core_strengths,
                key_gaps=key_gaps,
                quick_improvements=quick_improvements,
                output_language=output_language,
            ),
            "llm_config": prompt_template.get("llm_config", {})
        }

        return context

    async def _optimize_with_llm_v2(
        self,
        context: dict[str, Any],
        output_language: str,
    ) -> dict[str, Any]:
        """
        Execute the resume optimization using the simplified v2.0.0 prompt.

        Args:
            context: Prompt context with instructions
            output_language: Target language

        Returns:
            Optimized resume with improvements list
        """

        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": context["system_prompt"]},
                {"role": "user", "content": context["user_prompt"]}
            ]

            # Get LLM config
            llm_config = context.get("llm_config", {})

            # Track LLM processing time
            llm_start = time.time()

            # Call LLM with simplified prompt - use proper method name
            response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=llm_config.get("temperature", 0.3),
                max_tokens=llm_config.get("max_tokens", 6000),
                top_p=llm_config.get("top_p", 0.2),
                frequency_penalty=llm_config.get("frequency_penalty", 0.0),
                presence_penalty=llm_config.get("presence_penalty", 0.0),
            )

            llm_time_ms = int((time.time() - llm_start) * 1000)

            # Parse response - AzureOpenAIClient returns dict format
            content = response["choices"][0]["message"]["content"].strip()

            # Parse JSON response
            result = self._parse_llm_response(content)

            # Add timing metadata
            result["llm_processing_time_ms"] = llm_time_ms

            logger.info(f"LLM optimization completed in {llm_time_ms}ms")

            return result

        except Exception as e:
            logger.error(f"LLM optimization failed: {e!s}")
            raise

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """Parse the LLM response containing optimized resume."""

        try:
            # Try to extract JSON from the response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content and "}" in content:
                # Find the JSON object
                start_idx = content.index("{")
                end_idx = content.rindex("}") + 1
                json_str = content[start_idx:end_idx]
            else:
                raise ValueError("No JSON found in response")

            # Parse the JSON
            result = json.loads(json_str)

            # Validate required fields
            if "optimized_resume" not in result:
                raise ValueError("Missing 'optimized_resume' field in response")

            # Ensure applied_improvements exists
            if "applied_improvements" not in result:
                result["applied_improvements"] = []

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {content[:500]}...")

            # Return a fallback response
            return {
                "optimized_resume": content,
                "applied_improvements": ["Failed to parse structured response"],
                "parse_error": str(e)
            }

    async def _process_optimization_result_v2(
        self,
        optimized_result: dict[str, Any],
        original_resume: str,
        output_language: str,
        stage_timings: dict[str, int],
        instructions: dict[str, Any],
        covered_keywords: list[str] | None = None,
        missing_keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Process the optimization result and prepare the final response.
        Implements hybrid CSS class approach:
        1. LLM marks semantic changes (opt-modified, opt-new, opt-placeholder)
        2. Python post-processing adds keyword markers (opt-keyword, opt-keyword-existing)

        Args:
            optimized_result: Result from LLM optimization
            original_resume: Original resume for comparison
            output_language: Target language
            stage_timings: Timing metrics from each stage
            instructions: Instructions from the compiler
            covered_keywords: Keywords covered in original resume
            missing_keywords: Keywords missing from original resume

        Returns:
            Final response with all metrics and improvements
        """
        try:
            optimized_html = optimized_result.get("optimized_resume", "")
            applied_improvements = optimized_result.get("applied_improvements", [])

            # Initialize keyword lists
            covered_keywords = covered_keywords or []
            missing_keywords = missing_keywords or []

            # Phase 1: Detect which keywords are present in original and optimized resumes
            # Detect keywords in original resume
            originally_covered = self._detect_keywords_presence(
                original_resume,
                covered_keywords
            )

            # Detect all keywords in optimized resume
            all_keywords_to_check = list(set(covered_keywords + missing_keywords))
            currently_covered = self._detect_keywords_presence(
                optimized_html,
                all_keywords_to_check
            )

            # Phase 2: Categorize keywords into 4 states
            keyword_tracking = self._categorize_keywords(
                originally_covered,
                currently_covered,
                covered_keywords,
                missing_keywords
            )

            # Phase 3: Apply keyword marking using EnhancedMarker
            if keyword_tracking["newly_added"] or keyword_tracking["still_covered"]:
                from src.core.enhanced_marker import EnhancedMarker
                marker = EnhancedMarker()

                # Mark keywords in the optimized HTML
                # still_covered → opt-keyword-existing (blue background)
                # newly_added → opt-keyword (transparent bg, purple text)
                optimized_html = marker.mark_keywords(
                    html=optimized_html,
                    original_keywords=keyword_tracking["still_covered"],
                    new_keywords=keyword_tracking["newly_added"]
                )

                logger.info(
                    f"Keyword marking applied - Still covered: {len(keyword_tracking['still_covered'])}, "
                    f"Newly added: {len(keyword_tracking['newly_added'])}"
                )

            # Phase 4: Generate warnings for removed keywords
            warnings = []
            if keyword_tracking["removed"]:
                warnings.append(
                    f"Warning: {len(keyword_tracking['removed'])} originally covered keywords "
                    f"were removed during optimization: {', '.join(keyword_tracking['removed'])}"
                )
                logger.warning(f"Keywords removed during optimization: {keyword_tracking['removed']}")

            # Calculate improvements count
            total_improvements = len(applied_improvements)

            # Format improvements as HTML list
            improvements_html = self._format_improvements_as_html(applied_improvements)

            # Build response
            response = dict(
                optimized_resume=optimized_html,
                applied_improvements=improvements_html,
                improvement_count=total_improvements,
                output_language=output_language,
                success=True,
                message=f"Resume optimized successfully with {total_improvements} improvements using v2.1.0-simplified pipeline",
                processing_time_ms=sum(stage_timings.values()),
                stage_timings=stage_timings,
                # Add warning field if there are warnings
                warning=warnings[0] if warnings else None,
                # Enhanced keyword tracking information
                keyword_tracking={
                    "still_covered": keyword_tracking["still_covered"],
                    "removed": keyword_tracking["removed"],
                    "newly_added": keyword_tracking["newly_added"],
                    "still_missing": keyword_tracking["still_missing"],
                    "warnings": warnings
                },
                gap_analysis_insights={
                    "structure_found": {
                        "sections": instructions.get('analysis', {}).get('resume_sections', {}),
                        "metadata": instructions.get('analysis', {}).get('section_metadata', {})
                    },
                    "improvements_applied": total_improvements,
                },
                metadata={
                    "version": "v2.1.0-simplified",
                    "pipeline": "two-stage-hybrid",
                    "models": {
                        "instruction_compiler": "gpt-4.1-mini",
                        "resume_writer": "gpt-4.1",
                    },
                    "llm_processing_time_ms": optimized_result.get("llm_processing_time_ms", 0),
                    "gap_analysis_external": True,
                    "css_marking": {
                        "semantic": ["opt-modified", "opt-new", "opt-placeholder"],
                        "keywords": ["opt-keyword", "opt-keyword-existing"]
                    }
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error processing optimization result: {e!s}")
            raise

    def _format_improvements_as_html(self, improvements: list[str]) -> str:
        """Format improvements list as HTML."""
        if not improvements:
            return "<p>No specific improvements listed</p>"

        html_items = []
        for improvement in improvements:
            # Escape HTML characters
            improvement = improvement.replace("<", "&lt;").replace(">", "&gt;")
            html_items.append(f"<li>{improvement}</li>")

        return f"<ul>{''.join(html_items)}</ul>"

    def _track_metrics_v2(
        self,
        result: dict[str, Any],
        total_time_ms: int,
        stage_timings: dict[str, int],
    ) -> None:
        """Track performance metrics for the v2.0.0 pipeline."""
        try:
            # Track overall metrics
            self.monitoring.track_event(
                "resume_tailoring_v2_completed",
                {
                    "total_time_ms": total_time_ms,
                    "improvement_count": result.get("improvement_count", 0),
                    "output_language": result.get("output_language", "unknown"),
                    "success": result.get("success", False),
                    "sections_found": len(
                        result.get("gap_analysis_insights", {})
                        .get("structure_found", {})
                        .get("sections", {})
                    ),
                    "improvements_applied": result.get("gap_analysis_insights", {}).get("improvements_applied", 0),
                }
            )

            # Track stage-specific metrics
            for stage, timing in stage_timings.items():
                self.monitoring.track_metric(f"resume_tailoring_v2_{stage}", timing)

            # Log performance summary
            logger.info(
                f"Resume Tailoring v2.0.0 Performance: "
                f"Total={total_time_ms}ms, "
                f"Gap Analysis={stage_timings.get('gap_analysis_ms', 0)}ms, "
                f"Instruction Compilation={stage_timings.get('instruction_compilation_ms', 0)}ms, "
                f"Resume Writing={stage_timings.get('resume_writing_ms', 0)}ms"
            )

        except Exception as e:
            logger.error(f"Error tracking metrics: {e!s}")
