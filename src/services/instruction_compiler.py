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

            # Extract gap analysis components
            core_strengths = gap_analysis.get("CoreStrengths", "")
            key_gaps = gap_analysis.get("KeyGaps", "")
            quick_improvements = gap_analysis.get("QuickImprovements", "")

            # Format keywords for better readability
            covered_keywords_str = ", ".join(covered_keywords) if covered_keywords else "None"
            missing_keywords_str = ", ".join(missing_keywords) if missing_keywords else "None"

            # Prepare variables for prompt
            prompt_vars = {
                "resume_html": resume_html,
                "job_description": job_description,
                "core_strengths": core_strengths,
                "key_gaps": key_gaps,
                "quick_improvements": quick_improvements,
                "covered_keywords": covered_keywords_str,
                "missing_keywords": missing_keywords_str,
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
                instructions = self._create_fallback_instructions(
                    core_strengths, key_gaps, quick_improvements, missing_keywords
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
                "presentation_gaps_found": self._count_gap_type(key_gaps, "[Presentation Gap]"),
                "skill_gaps_found": self._count_gap_type(key_gaps, "[Skill Gap]"),
                "processing_time_ms": total_processing_time,
                "llm_processing_time_ms": llm_processing_time,
                "overhead_ms": total_processing_time - llm_processing_time,
            }

            logger.info(
                f"Instructions compiled successfully. "
                f"Presentation gaps: {instructions['metadata']['presentation_gaps_found']}, "
                f"Skill gaps: {instructions['metadata']['skill_gaps_found']}, "
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
        # For now, return the prompt directly embedded
        # In production, this would load from YAML file
        return {
            "system": """You are an Instruction Compiler for resume optimization. Your role is to analyze gap analysis
results and generate PRECISE, STRUCTURED instructions for resume enhancement.

## Your Task
Convert gap analysis findings into actionable JSON instructions. You DO NOT write content - only instructions
for what needs to be changed.

## Input Understanding

### Gap Classification in KeyGaps
- [Skill Gap]: Skills the candidate genuinely lacks - need creative positioning
- [Presentation Gap]: Skills that exist but aren't visible - need surfacing

### Core Strengths
These are proven capabilities to emphasize and expand upon.

### Quick Improvements
Immediate changes that can improve match percentage.

## Output Structure

Generate a JSON object with precise instructions for each resume section:

{
  "summary": {
    "action": "CREATE" or "MODIFY",
    "focus_areas": ["key area 1", "key area 2"],
    "keywords_to_integrate": ["keyword1", "keyword2"],
    "positioning_strategy": "Brief description of how to position candidate"
  },
  "skills": {
    "add_skills": ["skill1", "skill2"],
    "reorganize": true/false,
    "categories": ["Category1", "Category2"],
    "presentation_gaps_to_surface": ["skill from presentation gap"],
    "skill_gaps_to_imply": ["skill to position through related experience"]
  },
  "experience": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "priority": "HIGH/MEDIUM/LOW",
      "bullet_improvements": [
        {
          "bullet_index": 0,
          "improvement_type": "ADD_METRICS" | "ADD_KEYWORDS" | "CONVERT_TO_STAR" | "ADD_RESULT",
          "keywords": ["keyword1", "keyword2"],
          "focus": "What to emphasize"
        }
      ],
      "new_bullets": [
        {
          "purpose": "Address specific gap or highlight strength",
          "keywords": ["keyword1", "keyword2"],
          "format": "STAR" or "PAR"
        }
      ]
    }
  ],
  "education": {
    "action": "NONE" | "ADD_COURSEWORK" | "ADD_PROJECTS",
    "relevant_courses": ["course1", "course2"],
    "keywords": ["keyword1", "keyword2"]
  },
  "optimization_strategy": {
    "presentation_gaps_count": 0,
    "skill_gaps_count": 0,
    "priority_keywords": ["top 5 most important keywords"],
    "overall_approach": "Brief strategy description"
  }
}

## Rules
1. Be specific about which sections need changes
2. Prioritize high-impact improvements
3. Focus on keywords from job description
4. Ensure instructions are actionable and clear
5. Do NOT write actual content, only instructions
6. Maintain realistic positioning (don't claim skills they don't have)""",
            "user": """Analyze this gap analysis and generate optimization instructions:

## Original Resume HTML
{resume_html}

## Job Description
{job_description}

## Gap Analysis Results

### Core Strengths
{core_strengths}

### Key Gaps (with classifications)
{key_gaps}

### Quick Improvements
{quick_improvements}

### Keywords
Covered: {covered_keywords}
Missing: {missing_keywords}

Generate precise JSON instructions for optimizing this resume."""
        }

    def _count_gap_type(self, key_gaps: str, gap_type: str) -> int:
        """Count occurrences of a specific gap type in the key gaps string."""
        if not key_gaps:
            return 0
        return key_gaps.count(gap_type)

    def _validate_instructions(self, instructions: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and ensure all required fields exist in instructions.

        Args:
            instructions: Raw instructions from LLM

        Returns:
            Validated instructions with all required fields
        """
        # Ensure all main sections exist
        default_structure = {
            "summary": {
                "action": "MODIFY",
                "focus_areas": [],
                "keywords_to_integrate": [],
                "positioning_strategy": "",
            },
            "skills": {
                "add_skills": [],
                "reorganize": False,
                "categories": [],
                "presentation_gaps_to_surface": [],
                "skill_gaps_to_imply": [],
            },
            "experience": [],
            "education": {
                "action": "NONE",
                "relevant_courses": [],
                "keywords": [],
            },
            "optimization_strategy": {
                "presentation_gaps_count": 0,
                "skill_gaps_count": 0,
                "priority_keywords": [],
                "overall_approach": "",
            },
        }

        # Merge with defaults to ensure all fields exist
        for key, default_value in default_structure.items():
            if key not in instructions:
                instructions[key] = default_value
            elif isinstance(default_value, dict):
                # Merge nested dictionaries
                for sub_key, sub_default in default_value.items():
                    if sub_key not in instructions[key]:
                        instructions[key][sub_key] = sub_default

        return instructions

    def _create_fallback_instructions(
        self,
        core_strengths: str,
        key_gaps: str,
        quick_improvements: str,
        missing_keywords: list[str],
    ) -> dict[str, Any]:
        """
        Create basic fallback instructions if JSON parsing fails.

        Args:
            core_strengths: Core strengths from gap analysis
            key_gaps: Key gaps with classification markers
            quick_improvements: Quick improvements suggestions
            missing_keywords: Keywords missing from resume

        Returns:
            Basic instruction set
        """
        logger.warning("Using fallback instructions due to JSON parsing failure")

        # Count gap types
        presentation_gaps = self._count_gap_type(key_gaps, "[Presentation Gap]")
        skill_gaps = self._count_gap_type(key_gaps, "[Skill Gap]")

        return {
            "summary": {
                "action": "CREATE" if "summary" in quick_improvements.lower() else "MODIFY",
                "focus_areas": ["Professional expertise", "Key achievements"],
                "keywords_to_integrate": missing_keywords[:5] if missing_keywords else [],
                "positioning_strategy": "Highlight transferable skills and relevant experience",
            },
            "skills": {
                "add_skills": missing_keywords[:10] if missing_keywords else [],
                "reorganize": True,
                "categories": ["Technical Skills", "Tools & Technologies", "Soft Skills"],
                "presentation_gaps_to_surface": [],
                "skill_gaps_to_imply": [],
            },
            "experience": [
                {
                    "company": "All Companies",
                    "role": "All Roles",
                    "priority": "HIGH",
                    "bullet_improvements": [
                        {
                            "bullet_index": -1,  # Apply to all bullets
                            "improvement_type": "CONVERT_TO_STAR",
                            "keywords": missing_keywords[:3] if missing_keywords else [],
                            "focus": "Add metrics and results",
                        }
                    ],
                    "new_bullets": [],
                }
            ],
            "education": {
                "action": "NONE",
                "relevant_courses": [],
                "keywords": [],
            },
            "optimization_strategy": {
                "presentation_gaps_count": presentation_gaps,
                "skill_gaps_count": skill_gaps,
                "priority_keywords": missing_keywords[:5] if missing_keywords else [],
                "overall_approach": "Surface hidden skills and position transferable experience",
            },
        }
