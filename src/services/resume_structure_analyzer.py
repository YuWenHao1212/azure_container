"""
Resume Structure Analyzer Service for Index-Cal-Gap-Analysis V4.

This service identifies resume sections using GPT-4.1 mini for fast processing.
It runs in parallel with other analysis tasks to provide zero-latency structure identification.
"""

import asyncio
import json
import logging
import os
import time

from pydantic import BaseModel, Field

from src.core.simple_prompt_manager import SimplePromptManager
from src.services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)


class StandardSections(BaseModel):
    """Standard resume section mappings."""

    summary: str | None = Field(None, description="Professional summary section title")
    skills: str | None = Field(None, description="Skills section title")
    experience: str | None = Field(None, description="Work experience section title")
    education: str | None = Field(None, description="Education section title")
    certifications: str | None = Field(None, description="Certifications section title")
    projects: str | None = Field(None, description="Projects section title")


class StructureMetadata(BaseModel):
    """Resume structure metadata."""

    total_experience_entries: int = Field(0, description="Number of job positions")
    total_education_entries: int = Field(0, description="Number of education entries")
    has_quantified_achievements: bool = Field(False, description="Contains metrics/numbers")
    estimated_length: str = Field("unknown", description="Estimated page length")


class ResumeStructure(BaseModel):
    """Resume structure analysis result."""

    standard_sections: StandardSections = Field(..., description="Standard section mappings")
    custom_sections: list[str] = Field(default_factory=list, description="Non-standard sections")
    metadata: StructureMetadata = Field(..., description="Structure metadata")


class ResumeStructureAnalyzer:
    """
    Analyzes resume HTML to identify section structure.
    Uses GPT-4.1 mini for fast, lightweight processing.
    Includes retry mechanism and fallback for resilience.
    """

    def __init__(self):
        """Initialize with GPT-4.1 mini client and configuration."""
        # Use GPT-4.1 mini for fast processing
        self.llm_client = get_llm_client(api_name="resume_structure")

        # Retry configuration
        self.max_retries = int(os.getenv("STRUCTURE_ANALYSIS_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("STRUCTURE_ANALYSIS_RETRY_DELAY", "0.5"))
        self.timeout = float(os.getenv("STRUCTURE_ANALYSIS_TIMEOUT", "5.0"))

        # Use Prompt Management System
        self.prompt_manager = SimplePromptManager()
        # Use RESUME_STRUCTURE_PROMPT_VERSION for consistency with CI/CD naming
        prompt_version = os.getenv("RESUME_STRUCTURE_PROMPT_VERSION", "v1.0.1")

        try:
            # Load prompt from YAML
            self.prompt_config = self.prompt_manager.load_prompt_config_by_filename(
                "instruction_compiler",
                f"{prompt_version}.yaml"
            )
            # PromptConfig has prompts attribute with system and user keys
            self.prompt_template = {
                "system": self.prompt_config.prompts.get("system", ""),
                "user": self.prompt_config.prompts.get("user", "")
            }
            logger.info(f"Loaded prompt version {prompt_version} from YAML")
        except Exception as e:
            logger.warning(f"Failed to load prompt {prompt_version}, using fallback: {e}")
            # Fallback to simple prompt if YAML loading fails
            self.prompt_template = self._get_fallback_prompt()

        logger.info(
            f"ResumeStructureAnalyzer initialized with GPT-4.1 mini "
            f"(retries={self.max_retries}, timeout={self.timeout}s, prompt={prompt_version})"
        )

    async def analyze_structure(self, resume_html: str) -> ResumeStructure:
        """
        Analyze resume structure with retry mechanism.

        Test IDs:
        - RS-001-UT: Basic structure analysis
        - RS-004-UT: Retry mechanism validation
        - RS-005-UT: Fallback structure generation

        Args:
            resume_html: Resume content in HTML format

        Returns:
            ResumeStructure with identified sections and metadata
        """
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                # Test ID: RS-001-UT - Basic analysis
                result = await self._analyze_once(resume_html)

                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Structure analysis succeeded on attempt {attempt + 1}/{self.max_retries} "
                    f"(duration={duration_ms}ms)"
                )

                # Log success metrics
                logger.info(
                    "Resume structure analysis completed",
                    extra={
                        "attempt": attempt + 1,
                        "duration_ms": duration_ms,
                        "sections_found": len(
                            [s for s in result.standard_sections.dict().values() if s]
                        ),
                        "custom_sections": len(result.custom_sections),
                    },
                )

                return result

            except TimeoutError:
                # Test ID: RS-004-UT - Timeout handling
                logger.warning(
                    f"Structure analysis timeout on attempt {attempt + 1}/{self.max_retries}"
                )
                logger.error(
                    f"Structure analysis timeout: Analysis timed out after {self.timeout}s",
                    extra={"attempt": attempt + 1, "resume_length": len(resume_html)},
                )

            except json.JSONDecodeError as e:
                # JSON parsing error
                logger.warning(
                    f"Structure analysis JSON parse error on attempt {attempt + 1}: {e}"
                )
                logger.error(
                    f"Structure analysis JSON parse error: Failed to parse JSON response: {e}",
                    extra={"attempt": attempt + 1},
                )

            except Exception as e:
                # General error
                logger.warning(f"Structure analysis error on attempt {attempt + 1}: {e}")
                logger.error(
                    f"Structure analysis error: {e}",
                    extra={"attempt": attempt + 1},
                )

            # Retry delay (except for last attempt)
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)

        # Test ID: RS-005-UT - All attempts failed, use fallback
        logger.error(
            f"All {self.max_retries} structure analysis attempts failed, using fallback"
        )
        logger.error(
            "Structure fallback activated: Using fallback structure after all retries failed",
            extra={"max_retries": self.max_retries, "total_duration_ms": int((time.time() - start_time) * 1000)},
        )

        return self._get_fallback_structure()

    async def _analyze_once(self, resume_html: str) -> ResumeStructure:
        """
        Single attempt at structure analysis.

        Test ID: RS-003-UT - JSON parsing validation

        Args:
            resume_html: Resume content in HTML format

        Returns:
            ResumeStructure parsed from LLM response

        Raises:
            asyncio.TimeoutError: If analysis exceeds timeout
            json.JSONDecodeError: If response parsing fails
            Exception: For other errors
        """
        start_time = time.time()

        try:
            # Prepare prompt with resume HTML (limit size to avoid token overflow)
            max_html_length = 10000
            truncated_html = resume_html[:max_html_length]
            if len(resume_html) > max_html_length:
                truncated_html += "\n... [content truncated] ..."

            user_prompt = self.prompt_template["user"].format(resume_html=truncated_html)

            messages = [
                {"role": "system", "content": self.prompt_template["system"]},
                {"role": "user", "content": user_prompt},
            ]

            # Call LLM with timeout
            llm_start = time.time()
            response = await asyncio.wait_for(
                self.llm_client.chat_completion(
                    messages=messages, temperature=0.3, max_tokens=1000, top_p=0.1
                ),
                timeout=self.timeout,
            )
            llm_duration_ms = int((time.time() - llm_start) * 1000)

            # Extract content from response
            content = response["choices"][0]["message"]["content"]

            # Clean JSON if wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            # Test ID: RS-003-UT - Parse and validate JSON
            content = content.strip()
            data = json.loads(content)

            # Validate and convert to model
            structure = ResumeStructure(
                standard_sections=StandardSections(**data.get("standard_sections", {})),
                custom_sections=data.get("custom_sections", []),
                metadata=StructureMetadata(**data.get("metadata", {})),
            )

            total_duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                f"Structure analysis completed (total={total_duration_ms}ms, llm={llm_duration_ms}ms)"
            )

            return structure

        except TimeoutError:
            # Re-raise timeout errors for retry handling
            raise

        except json.JSONDecodeError:
            # Log the problematic content for debugging
            logger.debug(f"Failed to parse JSON content: {content[:500] if 'content' in locals() else 'N/A'}")
            raise

        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error in structure analysis: {e}")
            raise

    def _get_fallback_structure(self) -> ResumeStructure:
        """
        Return basic structure when analysis fails.

        Test ID: RS-005-UT - Fallback structure validation

        Returns:
            Basic ResumeStructure with common defaults
        """
        return ResumeStructure(
            standard_sections=StandardSections(
                summary="Professional Summary",
                skills="Skills",
                experience="Experience",
                education="Education",
                certifications=None,
                projects=None,
            ),
            custom_sections=[],
            metadata=StructureMetadata(
                total_experience_entries=0,
                total_education_entries=0,
                has_quantified_achievements=False,
                estimated_length="unknown",
            ),
        )

    def _get_fallback_prompt(self) -> dict[str, str]:
        """
        Get fallback prompt template if YAML loading fails.

        Returns:
            Basic prompt template dictionary
        """
        return {
            "system": """You are a Resume Structure Analyzer. Identify resume sections and return JSON with:
{
  "standard_sections": {
    "summary": null, "skills": null, "experience": null,
    "education": null, "certifications": null, "projects": null
  },
  "custom_sections": [],
  "metadata": {
    "total_experience_entries": 0, "total_education_entries": 0,
    "has_quantified_achievements": false, "estimated_length": "unknown"
  }
}""",
            "user": "Analyze structure of: {resume_html}",
        }
