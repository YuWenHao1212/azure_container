"""
Instruction Compiler Service for Resume Tailoring v2.0.0

This service uses GPT-4.1 mini to convert Gap Analysis results into
structured instructions for resume optimization.
"""

import json
import logging
import time
from typing import Any

from src.services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)


class InstructionCompiler:
    """
    Compiles Gap Analysis results into structured editing instructions
    using GPT-4.1 mini for lightweight, fast processing.
    """

    def __init__(self):
        """Initialize the Instruction Compiler with GPT-4.1 mini."""
        # Use gpt41-mini for fast, lightweight processing
        self.llm_client = get_llm_client(api_name="instruction_compiler")
        self.prompt_version = "v1.0.0"
        logger.info("InstructionCompiler initialized with GPT-4.1 mini")

    async def compile_instructions(
        self,
        resume_html: str,
        job_description: str,
        gap_analysis: dict[str, Any],
        covered_keywords: list[str],
        missing_keywords: list[str],
    ) -> dict[str, Any]:
        """
        Convert Gap Analysis results into structured optimization instructions.

        Args:
            resume_html: Original resume in HTML format
            job_description: Target job description
            gap_analysis: Gap Analysis results with classification markers
            covered_keywords: Keywords already present in resume
            missing_keywords: Keywords missing from resume

        Returns:
            Structured JSON instructions for resume optimization with timing metrics
        """
        start_time = time.time()
        try:
            # Load the instruction compiler prompt directly
            prompt_template = self._load_prompt_template()

            # Extract only needed gap analysis components for simplified analysis
            key_gaps = gap_analysis.get("KeyGaps", "")
            quick_improvements = gap_analysis.get("QuickImprovements", "")

            # Prepare minimal variables for prompt
            prompt_vars = {
                "resume_html": resume_html,
                "key_gaps": key_gaps,
                "quick_improvements": quick_improvements,
            }

            # Generate instructions using GPT-4.1 mini
            logger.info("Compiling optimization instructions with GPT-4.1 mini")

            messages = [
                {"role": "system", "content": prompt_template["system"]},
                {"role": "user", "content": prompt_template["user"].format(**prompt_vars)},
            ]

            # Track LLM call time
            llm_start_time = time.time()
            response = await self.llm_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
                top_p=0.1,
            )
            llm_processing_time = int((time.time() - llm_start_time) * 1000)

            # Parse the JSON response - AzureOpenAIClient returns dict format
            instructions_text = response["choices"][0]["message"]["content"].strip()

            # Clean up the response if it contains markdown code blocks
            if "```json" in instructions_text:
                instructions_text = instructions_text.split("```json")[1].split("```")[0].strip()
            elif "```" in instructions_text:
                instructions_text = instructions_text.split("```")[1].split("```")[0].strip()

            try:
                instructions = json.loads(instructions_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON instructions: {e}")
                logger.debug(f"Raw response: {instructions_text}")
                # Return a basic instruction set as fallback
                # Note: For simplified version, we don't need all the original parameters
                instructions = self._create_fallback_instructions(
                    "",  # core_strengths not needed in simplified version
                    key_gaps,
                    quick_improvements,
                    []  # missing_keywords not needed in simplified version
                )
                # Set llm_processing_time for fallback case
                if 'llm_processing_time' not in locals():
                    llm_processing_time = int((time.time() - llm_start_time) * 1000)

            # Validate and enhance instructions
            instructions = self._validate_instructions(instructions)

            # Calculate total processing time
            total_processing_time = int((time.time() - start_time) * 1000)

            # Add metadata with timing information
            instructions["metadata"] = {
                "compiler_version": self.prompt_version,
                "model": "gpt41-mini",
                "processing_time_ms": total_processing_time,
                "llm_processing_time_ms": llm_processing_time,
                "overhead_ms": total_processing_time - llm_processing_time,
            }

            logger.info(
                f"Structure analysis completed successfully. "
                f"Processing time: {total_processing_time}ms (LLM: {llm_processing_time}ms)"
            )

            return instructions

        except Exception as e:
            logger.error(f"Error compiling instructions: {e}")
            raise

    def _load_prompt_template(self) -> dict[str, str]:
        """
        Load the instruction compiler prompt template.

        Returns:
            Dictionary with 'system' and 'user' prompts
        """
        # Simplified prompt for minimal responsibility
        return {
            "system": """You are a Resume Structure Analyzer. Your role is to quickly identify the resume structure.

## Your Task
Provide a SIMPLE structural analysis. Do NOT make content decisions or classify gaps.

### Your Analysis Focus
1. Identify which resume sections exist and their actual titles (e.g., "Work Experience" vs "Employment History")
2. Count basic statistics (number of jobs, education entries, etc.)
3. Note any structural observations

## Output Structure

Return a simple JSON with this exact structure:

{
  "analysis": {
    "resume_sections": {
      "summary": "actual section title" or null,  // e.g., "Professional Summary", null if not exists
      "skills": "actual section title" or null,  // e.g., "Technical Skills"
      "experience": "actual section title" or null,  // e.g., "Work Experience"
      "education": "actual section title" or null,  // e.g., "Education"
      "certifications": "actual section title" or null,  // e.g., "Certifications"
      "projects": "actual section title" or null  // e.g., "Projects"
    },
    "section_metadata": {
      "total_experience_entries": number,
      "total_education_entries": number,
      "has_quantified_achievements": true/false,  // Are there metrics/numbers in achievements?
      "estimated_length": "1 page" or "2 pages" or "3+ pages"
    }
  }
}

## Important Rules
1. Only identify structure, don't make any content decisions
2. For resume_sections, use the ACTUAL section title from the resume
3. Use null if a section doesn't exist in the resume
4. Keep the output minimal and focused
5. Do NOT suggest improvements or actions - that's for the main LLM
6. Count actual entries, not make judgments about quality""",
            "user": """Analyze the resume structure:

## Resume HTML
{resume_html}

Provide a simple structural analysis following the exact JSON format specified."""
        }


    def _validate_instructions(self, instructions: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and ensure all required fields exist in simplified instructions.

        Args:
            instructions: Raw instructions from LLM

        Returns:
            Validated instructions with all required fields
        """
        # Ensure the analysis structure exists
        if "analysis" not in instructions:
            instructions = {"analysis": instructions}

        analysis = instructions["analysis"]

        # Default structure for simplified format
        default_analysis = {
            "resume_sections": {
                "summary": None,
                "skills": None,
                "experience": None,
                "education": None,
                "certifications": None,
                "projects": None,
            },
            "section_metadata": {
                "total_experience_entries": 0,
                "total_education_entries": 0,
                "has_quantified_achievements": False,
                "estimated_length": "unknown",
            },
        }

        # Merge with defaults to ensure all fields exist
        for key, default_value in default_analysis.items():
            if key not in analysis:
                analysis[key] = default_value
            elif isinstance(default_value, dict):
                # Merge nested dictionaries
                if key not in analysis:
                    analysis[key] = default_value
                else:
                    for sub_key, sub_default in default_value.items():
                        if sub_key not in analysis[key]:
                            analysis[key][sub_key] = sub_default

        instructions["analysis"] = analysis
        return instructions

    def _create_fallback_instructions(
        self,
        core_strengths: str,
        key_gaps: str,
        quick_improvements: str,
        missing_keywords: list[str],
    ) -> dict[str, Any]:
        """
        Create basic fallback structure if JSON parsing fails.

        Args:
            core_strengths: Core strengths (unused in simplified version)
            key_gaps: Key gaps (unused in simplified version)
            quick_improvements: Quick improvements (unused in simplified version)
            missing_keywords: Keywords (unused in simplified version)

        Returns:
            Basic structure analysis in simplified format
        """
        logger.warning("Using fallback structure due to JSON parsing failure")

        # Suppress unused variable warnings - these parameters are kept for interface compatibility
        _ = (core_strengths, key_gaps, quick_improvements, missing_keywords)

        return {
            "analysis": {
                "resume_sections": {
                    "summary": "Professional Summary",
                    "skills": "Skills",
                    "experience": "Experience",
                    "education": "Education",
                    "certifications": None,
                    "projects": None,
                },
                "section_metadata": {
                    "total_experience_entries": 2,
                    "total_education_entries": 1,
                    "has_quantified_achievements": False,
                    "estimated_length": "2 pages",
                },
            }
        }
