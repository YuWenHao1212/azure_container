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
    Resume Tailoring Service v2.0.0 - Three-Stage Pipeline Architecture.

    This service implements a simplified, high-performance approach:
    1. Gap Analysis (v2.1.0) - Identifies gaps with classification markers
    2. Instruction Compiler - Converts gaps to structured instructions (GPT-4.1 mini)
    3. Resume Writer - Executes instructions with simplified prompt (v2.0.0)
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

        # Initialize Gap Analysis service
        from src.services.gap_analysis_v2 import GapAnalysisServiceV2
        self.gap_analysis_service = GapAnalysisServiceV2()

        logger.info("ResumeTailoringService v2.0.0 initialized with three-stage pipeline")

    async def tailor_resume(
        self,
        original_resume: str,
        job_description: str,
        covered_keywords: list[str] | None = None,
        missing_keywords: list[str] | None = None,
        output_language: str = "English",
    ) -> dict[str, Any]:
        """
        Tailor a resume using the three-stage pipeline architecture.

        Stage 1: Gap Analysis with classification markers
        Stage 2: Instruction Compilation with GPT-4.1 mini
        Stage 3: Resume Writing with simplified prompt

        Args:
            original_resume: HTML content of the original resume
            job_description: Target job description
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
            original_resume, job_description = self._validate_inputs(
                original_resume, job_description
            )

            # Clean up HTML whitespace
            original_resume = original_resume.strip()

            # Default keyword lists
            covered_keywords = covered_keywords or []
            missing_keywords = missing_keywords or []

            # Stage 1: Run Gap Analysis (v2.1.0 with classification markers)
            stage1_start = time.time()
            logger.info("Stage 1: Running Gap Analysis with classification markers")

            gap_analysis_result = await self.gap_analysis_service.analyze_gap(
                resume=original_resume,
                job_description=job_description,
                covered_keywords=covered_keywords,
                missing_keywords=missing_keywords,
            )

            # Extract gap analysis data
            gap_analysis_data = {
                "CoreStrengths": gap_analysis_result.get("core_strengths", ""),
                "KeyGaps": gap_analysis_result.get("key_gaps", ""),
                "QuickImprovements": gap_analysis_result.get("quick_improvements", ""),
            }

            stage_timings["gap_analysis_ms"] = int((time.time() - stage1_start) * 1000)
            logger.info(f"Stage 1 completed in {stage_timings['gap_analysis_ms']}ms")

            # Stage 2: Compile Instructions using GPT-4.1 mini
            stage2_start = time.time()
            logger.info("Stage 2: Compiling instructions with GPT-4.1 mini")

            instructions = await self.instruction_compiler.compile_instructions(
                resume_html=original_resume,
                job_description=job_description,
                gap_analysis=gap_analysis_data,
                covered_keywords=covered_keywords,
                missing_keywords=missing_keywords,
            )

            stage_timings["instruction_compilation_ms"] = int((time.time() - stage2_start) * 1000)
            logger.info(
                f"Stage 2 completed in {stage_timings['instruction_compilation_ms']}ms. "
                f"Found {instructions['metadata']['presentation_gaps_found']} presentation gaps, "
                f"{instructions['metadata']['skill_gaps_found']} skill gaps"
            )

            # Stage 3: Execute Instructions with Simplified Prompt
            stage3_start = time.time()
            logger.info("Stage 3: Executing resume optimization with simplified prompt")

            # Convert instructions to JSON string for the prompt
            import json
            instructions_json = json.dumps(instructions, indent=2)

            # Build context with simplified prompt
            context = self._build_context_v2(
                original_resume=original_resume,
                instructions_json=instructions_json,
                output_language=output_language,
            )

            # Execute optimization with LLM
            optimized_result = await self._optimize_with_llm_v2(context, output_language)

            stage_timings["resume_writing_ms"] = int((time.time() - stage3_start) * 1000)
            logger.info(f"Stage 3 completed in {stage_timings['resume_writing_ms']}ms")

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

            # Add gap analysis insights
            final_result["gap_analysis_insights"] = {
                "presentation_gaps_found": instructions['metadata']['presentation_gaps_found'],
                "skill_gaps_found": instructions['metadata']['skill_gaps_found'],
                "priority_keywords": instructions['optimization_strategy'].get('priority_keywords', []),
                "overall_approach": instructions['optimization_strategy'].get('overall_approach', ''),
            }

            logger.info(
                f"Resume tailoring v2.0.0 completed in {total_time_ms}ms "
                f"(Gap: {stage_timings['gap_analysis_ms']}ms, "
                f"Compile: {stage_timings['instruction_compilation_ms']}ms, "
                f"Write: {stage_timings['resume_writing_ms']}ms)"
            )

            # Track metrics
            self._track_metrics_v2(final_result, total_time_ms, stage_timings)

            return final_result

        except Exception as e:
            logger.error(f"Error in resume tailoring v2.0.0: {e!s}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Resume tailoring failed: {e!s}"
            ) from e

    def _validate_inputs(self, original_resume: str, job_description: str) -> tuple[str, str]:
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

        # Clean inputs
        original_resume = original_resume.strip()
        job_description = job_description.strip()

        # Check minimum length
        if len(job_description) < 200:
            raise HTTPException(
                status_code=400,
                detail="Job description must be at least 200 characters"
            )

        return original_resume, job_description

    def _build_context_v2(
        self,
        original_resume: str,
        instructions_json: str,
        output_language: str,
    ) -> dict[str, Any]:
        """
        Build context for the simplified v2.0.0 prompt.

        Args:
            original_resume: Original resume HTML
            instructions_json: Structured instructions from Instruction Compiler
            output_language: Target language for output

        Returns:
            Context dictionary for the prompt
        """
        # Load the simplified v2.0.0 prompt directly
        # Since UnifiedPromptService doesn't support resume_tailoring directly,
        # we'll load the prompt inline for now
        prompt_template = {
            "prompts": {
                "system": """You are a Professional Resume Writer executing optimization instructions
with precision and creativity.
## Your Role
Transform resumes based on STRUCTURED INSTRUCTIONS provided. Focus on high-quality execution, not analysis.

## Language Output
**CRITICAL**: Generate ALL output in {output_language}
- Traditional Chinese (繁體中文): Use professional Traditional Chinese
- English: Use professional English
- Keep HTML/CSS tags and placeholders in English
""",
                "user": """Execute the following resume optimization:

## Original Resume
{original_resume}

## Optimization Instructions
{instructions_json}

## Output Language
{output_language}

Generate the optimized resume following the provided instructions precisely.

Return JSON with these fields:
{{
  "optimized_resume": "[Complete HTML with optimization markers]",
  "applied_improvements": [
    "[Section: Summary] Created new summary based on instructions",
    "[Section: Skills] Added 8 new skills from presentation gaps",
    "[Section: Experience - Company X] Converted 3 bullets to STAR format"
  ]
}}""",
            },
            "llm_config": {
                "model": "gpt4o-2",
                "temperature": 0.3,
                "max_tokens": 6000,
                "top_p": 0.2,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            }
        }

        # Build the context
        context = {
            "system_prompt": prompt_template["prompts"]["system"].format(
                output_language=output_language
            ),
            "user_prompt": prompt_template["prompts"]["user"].format(
                original_resume=original_resume,
                instructions_json=instructions_json,
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
    ) -> dict[str, Any]:
        """
        Process the optimization result and prepare the final response.

        Args:
            optimized_result: Result from LLM optimization
            original_resume: Original resume for comparison
            output_language: Target language
            stage_timings: Timing metrics from each stage
            instructions: Instructions from the compiler

        Returns:
            Final response with all metrics and improvements
        """
        try:
            optimized_html = optimized_result.get("optimized_resume", "")
            applied_improvements = optimized_result.get("applied_improvements", [])

            # Post-process the HTML
            # For v2.0.0, we'll skip post-processing for now
            # This can be enhanced later with proper standardizers

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
                message=f"Resume optimized successfully with {total_improvements} improvements using v2.0.0 pipeline",
                processing_time_ms=sum(stage_timings.values()),
                stage_timings=stage_timings,
                gap_analysis_insights={
                    "presentation_gaps_found": instructions['metadata']['presentation_gaps_found'],
                    "skill_gaps_found": instructions['metadata']['skill_gaps_found'],
                    "priority_keywords": instructions['optimization_strategy'].get('priority_keywords', []),
                    "overall_approach": instructions['optimization_strategy'].get('overall_approach', ''),
                },
                metadata={
                    "version": "v2.0.0",
                    "pipeline": "three-stage",
                    "models": {
                        "gap_analysis": "gpt4o-2",
                        "instruction_compiler": "gpt41-mini",
                        "resume_writer": "gpt4o-2",
                    },
                    "llm_processing_time_ms": optimized_result.get("llm_processing_time_ms", 0),
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
                    "presentation_gaps": result.get("gap_analysis_insights", {}).get("presentation_gaps_found", 0),
                    "skill_gaps": result.get("gap_analysis_insights", {}).get("skill_gaps_found", 0),
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
