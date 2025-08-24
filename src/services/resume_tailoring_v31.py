"""
Resume Tailoring Service v3.1.0 - Parallel LLM Pipeline Architecture.

This service implements a high-performance parallel approach:
1. Python Pre-process - Simple data allocation
2. Parallel LLM execution - Core Optimizer || Additional Manager
3. Python Post-process - Merge results + Add keyword CSS + Calculate metrics

Note: No backward compatibility with v2.x. Direct upgrade to v3.1.0.
"""

import asyncio
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
from ..services.index_calculation_v2 import get_index_calculation_service_v2
from ..services.llm_factory import get_llm_client
from ..services.unified_prompt_service import UnifiedPromptService

logger = logging.getLogger(__name__)


class ResumeTailoringServiceV31:
    """
    Resume Tailoring Service v3.1.0 - Two-LLM Parallel Pipeline.

    LLM1 (Core Optimizer): Professional Summary, Skills, Experience
    LLM2 (Additional Manager): Education, Projects, Certifications, Custom Sections
    """

    def __init__(self):
        """Initialize the Resume Tailoring v3.1.0 service."""
        self.settings = get_settings()

        # Initialize LLM clients using factory
        self.llm1_client = get_llm_client(api_name="resume_tailor")  # Core Optimizer
        self.llm2_client = get_llm_client(api_name="resume_tailor")  # Additional Manager

        # Initialize services
        self.prompt_service = UnifiedPromptService()
        self.html_processor = HTMLProcessor()
        self.language_handler = LanguageHandler()
        self.star_formatter = STARFormatter()
        self.marker_fixer = MarkerFixer()
        self.monitoring = MonitoringService()

        # Load prompts
        self.core_prompt = self.prompt_service.load_prompt("resume_tailoring", "v1.0.0-resume-core")
        self.additional_prompt = self.prompt_service.load_prompt("resume_tailoring", "v1.0.0-resume-additional")

        # Initialize metrics service
        self.index_service = get_index_calculation_service_v2()

        logger.info("ResumeTailoringServiceV31 initialized with parallel LLM pipeline")

    async def tailor_resume(
        self,
        original_resume: str,
        job_description: str,
        original_index: dict,
        output_language: str = "English",
    ) -> dict[str, Any]:
        """
        Tailor a resume using the v3.1.0 parallel pipeline architecture.

        Args:
            original_resume: HTML content of the original resume
            job_description: Target job description
            original_index: Complete index calculation and gap analysis results
            output_language: Output language for the tailored resume

        Returns:
            TailoringResponse with optimized resume and metrics
        """

        start_time = time.time()
        pre_start = start_time

        try:
            # Pre-processing: Extract data from original_index
            logger.info("Starting v3.1.0 pre-processing")

            # Extract components from original_index
            # Handle both formats: nested (from Gap Analysis API) and flat (from Bubble.io)
            if "keyword_coverage" in original_index:
                # Nested format from Gap Analysis API
                keyword_coverage = original_index.get("keyword_coverage", {})
                gap_analysis = original_index.get("gap_analysis", {})
                resume_structure = original_index.get("resume_structure", {})
                covered_keywords = keyword_coverage.get("covered_keywords", [])
                missed_keywords = keyword_coverage.get("missed_keywords", [])
            else:
                # Flat format from Bubble.io
                keyword_coverage = {
                    "covered_keywords": original_index.get("covered_keywords", []),
                    "missed_keywords": original_index.get("missing_keywords", []),
                    "coverage_percentage": original_index.get("coverage_percentage", 0)
                }
                gap_analysis = {
                    "core_strengths": original_index.get("core_strengths", []),
                    "key_gaps": original_index.get("key_gaps", []),
                    "quick_improvements": original_index.get("quick_improvements", [])
                }
                resume_structure = {}  # Not provided in flat format
                covered_keywords = original_index.get("covered_keywords", [])
                missed_keywords = original_index.get("missing_keywords", [])

            # Prepare data bundles for parallel LLMs
            bundle1, bundle2 = self._allocate_bundles(
                original_resume=original_resume,
                job_description=job_description,
                gap_analysis=gap_analysis,
                covered_keywords=covered_keywords,
                missing_keywords=missed_keywords,
                resume_structure=resume_structure,
                output_language=output_language
            )

            pre_processing_ms = int((time.time() - pre_start) * 1000)

            # Parallel LLM execution
            logger.info("Executing parallel LLM calls")
            llm_start = time.time()

            llm1_task = self._call_llm1(bundle1)
            llm2_task = self._call_llm2(bundle2)

            # Record individual start times
            llm1_start_ms = int((llm_start - start_time) * 1000)
            llm2_start_ms = llm1_start_ms  # Both start at same time

            # Execute in parallel
            llm1_result, llm2_result = await asyncio.gather(llm1_task, llm2_task)

            # Record individual finish times
            llm_finish = time.time()
            llm1_finish_ms = int((llm_finish - start_time) * 1000)
            llm2_finish_ms = llm1_finish_ms  # Both finish around same time

            llm1_processing_ms = llm1_result.get("processing_time_ms", 0)
            llm2_processing_ms = llm2_result.get("processing_time_ms", 0)

            # Post-processing: Merge results
            logger.info("Starting post-processing")
            post_start = time.time()

            # Merge sections from both LLMs
            merged_sections = self._merge_sections(llm1_result, llm2_result, resume_structure)

            # Build final HTML
            final_html = self._build_final_html(merged_sections, resume_structure)

            # Apply keyword CSS marking
            final_html = self._apply_keyword_css(
                html=final_html,
                covered_keywords=covered_keywords,
                newly_added=self._get_newly_added_keywords(final_html, missed_keywords)
            )

            # Merge tracking arrays
            applied_improvements = self._merge_tracking(llm1_result, llm2_result)

            # Calculate metrics
            metrics = await self._calculate_metrics_v3(
                original_resume=original_resume,
                optimized_resume=final_html,
                job_description=job_description,
                original_index=original_index,
                all_keywords=covered_keywords + missed_keywords
            )

            post_processing_ms = int((time.time() - post_start) * 1000)
            total_processing_ms = int((time.time() - start_time) * 1000)

            # Check if LLM2 had issues and add warnings
            warnings = []
            if llm2_result.get("fallback_used"):
                warnings.append({
                    "type": "LLM2_FALLBACK_USED",
                    "message": ("Education/Projects/Certifications sections using original content "
                                "due to LLM2 parsing failure"),
                    "details": {
                        "parse_error": llm2_result.get("parse_error"),
                        "had_core_strengths": bool(bundle2.get("core_strengths")),
                        "had_key_gaps": bool(bundle2.get("key_gaps"))
                    }
                })
                logger.warning(f"LLM2 fallback was used: {llm2_result.get('parse_error')}")

            # Check if LLM2 sections are empty
            llm2_sections = llm2_result.get("optimized_sections", {})
            if not any([llm2_sections.get("education"),
                       llm2_sections.get("projects"),
                       llm2_sections.get("certifications")]):
                warnings.append({
                    "type": "LLM2_CONTENT_MISSING",
                    "message": "Some sections may be incomplete",
                    "details": {
                        "education_present": bool(llm2_sections.get("education")),
                        "projects_present": bool(llm2_sections.get("projects")),
                        "certifications_present": bool(llm2_sections.get("certifications"))
                    }
                })

            # Build response
            response = {
                "optimized_resume": final_html,
                "applied_improvements": applied_improvements,
                "total_processing_time_ms": total_processing_ms,
                "pre_processing_ms": pre_processing_ms,
                "llm1_processing_time_ms": llm1_processing_ms,
                "llm2_processing_time_ms": llm2_processing_ms,
                "post_processing_ms": post_processing_ms,
                "stage_timings": {
                    "llm1_start_time_ms": llm1_start_ms,
                    "llm1_finish_time_ms": llm1_finish_ms,
                    "llm2_start_time_ms": llm2_start_ms,
                    "llm2_finish_time_ms": llm2_finish_ms
                },
                "Keywords": metrics["keywords"],
                "similarity": metrics["similarity"],
                "metadata": {
                    "llm1_prompt_version": "v1.0.0-resume-core",
                    "llm2_prompt_version": "v1.0.0-resume-additional",
                    "llm1_models": "gpt-4.1",
                    "llm2_models": "gpt-4.1"
                }
            }

            # Add warnings if any exist
            if warnings:
                response["warnings"] = warnings

            logger.info(
                f"Resume tailoring v3.1.0 completed in {total_processing_ms}ms "
                f"(Pre: {pre_processing_ms}ms, LLM1: {llm1_processing_ms}ms, "
                f"LLM2: {llm2_processing_ms}ms, Post: {post_processing_ms}ms)"
            )

            return response

        except Exception as e:
            logger.error(f"Error in resume tailoring v3.1.0: {e!s}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Resume tailoring failed: {e!s}"
            ) from e

    def _allocate_bundles(
        self,
        original_resume: str,
        job_description: str,
        gap_analysis: dict,
        covered_keywords: list[str],
        missing_keywords: list[str],
        resume_structure: dict,
        output_language: str
    ) -> tuple[dict, dict]:
        """
        Allocate data bundles for parallel LLM processing.
        Both LLMs get full data but with different focus instructions.
        """

        # Common data for both LLMs
        common_data = {
            "original_resume": original_resume,
            "job_description": job_description,
            "output_language": output_language,
            "covered_keywords": covered_keywords,
            "missing_keywords": missing_keywords
        }

        # Bundle for LLM1 (Core Optimizer)
        bundle1 = {
            **common_data,
            "core_strengths": gap_analysis.get("CoreStrengths") or gap_analysis.get("core_strengths", ""),
            "key_gaps": gap_analysis.get("KeyGaps") or gap_analysis.get("key_gaps", ""),
            "quick_improvements": gap_analysis.get("QuickImprovements") or gap_analysis.get("quick_improvements", ""),
            "focus": "Professional Summary, Core Competencies/Skills, Professional Experience"
        }

        # Bundle for LLM2 (Additional Manager)
        bundle2 = {
            **common_data,
            # May need for context
            "core_strengths": gap_analysis.get("CoreStrengths") or gap_analysis.get("core_strengths", ""),
            "key_gaps": gap_analysis.get("KeyGaps") or gap_analysis.get("key_gaps", ""),
            "quick_improvements": gap_analysis.get("QuickImprovements") or gap_analysis.get("quick_improvements", ""),
            "education_enhancement_needed": resume_structure.get("education_enhancement_needed", False),
            "standard_sections": resume_structure.get("standard_sections", {}),
            "custom_sections": resume_structure.get("custom_sections", []),
            "focus": "Education, Projects, Certifications, Custom Sections"
        }

        return bundle1, bundle2

    async def _call_llm1(self, bundle: dict) -> dict:
        """Call LLM1 (Core Optimizer) with v1.0.0-resume-core prompt."""

        start_time = time.time()

        try:
            # Build messages from prompt template
            system_prompt = self.core_prompt["prompts"]["system"]
            user_prompt = self.core_prompt["prompts"]["user"].format(
                original_resume=bundle["original_resume"],
                job_description=bundle["job_description"],
                core_strengths=bundle["core_strengths"],
                key_gaps=bundle["key_gaps"],
                quick_improvements=bundle["quick_improvements"],
                covered_keywords=", ".join(bundle["covered_keywords"]) if bundle["covered_keywords"] else "None",
                missing_keywords=", ".join(bundle["missing_keywords"]) if bundle["missing_keywords"] else "None",
                output_language=bundle["output_language"]
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Get LLM config
            llm_config = self.core_prompt.get("llm_config", {})

            # Call LLM
            response = await self.llm1_client.chat_completion(
                messages=messages,
                temperature=llm_config.get("temperature", 0.2),
                max_tokens=llm_config.get("max_tokens", 5000),
                top_p=llm_config.get("top_p", 0.15),
                frequency_penalty=llm_config.get("frequency_penalty", 0.0),
                presence_penalty=llm_config.get("presence_penalty", 0.0)
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Parse response
            content = response["choices"][0]["message"]["content"].strip()
            result = self._parse_llm_response(content)
            result["processing_time_ms"] = processing_time_ms

            logger.info(f"LLM1 (Core Optimizer) completed in {processing_time_ms}ms")

            return result

        except Exception as e:
            logger.error(f"LLM1 call failed: {e}")
            raise

    async def _call_llm2(self, bundle: dict) -> dict:
        """Call LLM2 (Additional Manager) with v1.0.0-resume-additional prompt."""

        start_time = time.time()

        try:
            # Build messages from prompt template
            system_prompt = self.additional_prompt["prompts"]["system"]
            user_prompt = self.additional_prompt["prompts"]["user"].format(
                original_resume=bundle["original_resume"],
                job_description=bundle["job_description"],
                core_strengths=bundle["core_strengths"],
                key_gaps=bundle["key_gaps"],
                quick_improvements=bundle["quick_improvements"],
                covered_keywords=", ".join(bundle["covered_keywords"]) if bundle["covered_keywords"] else "None",
                missing_keywords=", ".join(bundle["missing_keywords"]) if bundle["missing_keywords"] else "None",
                education_enhancement_needed=bundle["education_enhancement_needed"],
                standard_sections=json.dumps(bundle["standard_sections"]),
                custom_sections=json.dumps(bundle["custom_sections"]),
                output_language=bundle["output_language"]
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Get LLM config
            llm_config = self.additional_prompt.get("llm_config", {})

            # Call LLM
            response = await self.llm2_client.chat_completion(
                messages=messages,
                temperature=llm_config.get("temperature", 0.2),
                max_tokens=llm_config.get("max_tokens", 5000),
                top_p=llm_config.get("top_p", 0.15),
                frequency_penalty=llm_config.get("frequency_penalty", 0.0),
                presence_penalty=llm_config.get("presence_penalty", 0.0)
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Parse response
            content = response["choices"][0]["message"]["content"].strip()
            # Pass is_llm2=True and original_resume for fallback
            result = self._parse_llm_response(content, is_llm2=True, original_resume=bundle.get("original_resume", ""))
            result["processing_time_ms"] = processing_time_ms

            # Log diagnostic information
            logger.info(f"LLM2 completed in {processing_time_ms}ms")
            logger.debug(f"LLM2 bundle had: core_strengths={bool(bundle.get('core_strengths'))}, "
                        f"key_gaps={bool(bundle.get('key_gaps'))}, "
                        f"quick_improvements={bool(bundle.get('quick_improvements'))}")

            return result

        except Exception as e:
            logger.error(f"LLM2 call failed: {e}")
            raise

    def _extract_original_section(self, section_name: str, original_resume: str = "") -> str:
        """Extract a section from the original resume as fallback."""

        from bs4 import BeautifulSoup

        if not original_resume:
            return ""

        soup = BeautifulSoup(original_resume, 'html.parser')

        # Common section headers to look for
        section_headers = {
            "education": ["education", "學歷", "educational background", "academic"],
            "projects": ["project", "專案", "portfolio", "work samples"],
            "certifications": ["certification", "證照", "certificate", "qualification", "license"]
        }

        headers = section_headers.get(section_name.lower(), [section_name])

        # Try to find the section
        for header in headers:
            # Look for headers containing the keyword
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                if header.lower() in tag.get_text().lower():
                    # Get content after this header until next header
                    content_parts = []
                    for sibling in tag.find_next_siblings():
                        if sibling.name and sibling.name.startswith('h'):
                            break
                        content_parts.append(str(sibling))

                    if content_parts:
                        return f"<h2>{tag.get_text()}</h2>\n" + "\n".join(content_parts)

        return ""

    def _parse_llm_response(self, content: str, is_llm2: bool = False, original_resume: str = "") -> dict:
        """Parse JSON response from LLM with robust error handling."""

        try:
            # Extract JSON from response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content and "}" in content:
                start_idx = content.index("{")
                end_idx = content.rindex("}") + 1
                json_str = content[start_idx:end_idx]
            else:
                raise ValueError("No JSON found in response")

            # Parse JSON
            result = json.loads(json_str)

            # Ensure required fields exist
            if "optimized_sections" not in result:
                raise ValueError("Missing 'optimized_sections' in response")

            if "tracking" not in result:
                result["tracking"] = []

            # Log successful parsing for LLM2
            if is_llm2:
                sections = result.get("optimized_sections", {})
                logger.info(f"LLM2 sections parsed successfully: {list(sections.keys())}")

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse {'LLM2' if is_llm2 else 'LLM'} response: {e}")
            logger.debug(f"Raw response preview: {content[:500]}...")

            # For LLM2, try to provide fallback with original content
            if is_llm2 and original_resume:
                logger.warning("Using fallback content from original resume for LLM2 sections")
                return {
                    "optimized_sections": {
                        "education": self._extract_original_section("education", original_resume),
                        "projects": self._extract_original_section("projects", original_resume),
                        "certifications": self._extract_original_section("certifications", original_resume)
                    },
                    "tracking": ["LLM2 parsing failed - using original content as fallback"],
                    "parse_error": str(e),
                    "fallback_used": True
                }

            # Return a minimal fallback response
            return {
                "optimized_sections": {},
                "tracking": [f"Failed to parse {'LLM2' if is_llm2 else 'LLM'} response"],
                "parse_error": str(e)
            }

    def _merge_sections(self, llm1_result: dict, llm2_result: dict, resume_structure: dict) -> dict:
        """Merge sections from both LLM outputs."""

        sections1 = llm1_result.get("optimized_sections", {})
        sections2 = llm2_result.get("optimized_sections", {})

        # Merge all sections
        merged = {
            # From LLM1
            "summary": sections1.get("summary", ""),
            "skills": sections1.get("skills", ""),
            "experience": sections1.get("experience", ""),
            # From LLM2
            "education": sections2.get("education", ""),
            "projects": sections2.get("projects", ""),
            "certifications": sections2.get("certifications", ""),
            "supplementary_details": sections2.get("supplementary_details", "")
        }

        # Remove empty sections
        merged = {k: v for k, v in merged.items() if v}

        return merged

    def _build_final_html(self, sections: dict, resume_structure: dict) -> str:
        """Build final HTML with proper section ordering."""

        # Determine section order based on education_enhancement_needed
        education_enhanced = resume_structure.get("education_enhancement_needed", False)

        if education_enhanced:
            # Education comes before Experience for recent grads
            section_order = [
                "summary", "skills", "education", "experience",
                "projects", "certifications", "supplementary_details"
            ]
        else:
            # Standard order for experienced professionals
            section_order = [
                "summary", "skills", "experience", "education",
                "projects", "certifications", "supplementary_details"
            ]

        # Build HTML
        html_parts = []

        # Add contact information if available (usually handled separately)
        # For now, we'll start directly with sections

        for section_key in section_order:
            if sections.get(section_key):
                html_parts.append(sections[section_key])

        return "\n\n".join(html_parts)

    def _apply_keyword_css(self, html: str, covered_keywords: list[str], newly_added: list[str]) -> str:
        """
        Apply keyword CSS classes with proper nesting prevention.

        Args:
            html: HTML content to process
            covered_keywords: Keywords from original resume (mark as opt-keyword-existing)
            newly_added: Newly added keywords (mark as opt-keyword-add)

        Returns:
            HTML with keyword CSS classes applied
        """
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Function to check if a node is inside a keyword span
        def is_inside_keyword_span(element):
            """Check if element is inside a keyword span tag."""
            parent = element.parent
            while parent:
                if parent.name == 'span' and parent.get('class'):
                    classes = parent.get('class')
                    if 'opt-keyword-existing' in classes or 'opt-keyword-add' in classes:
                        return True
                parent = parent.parent
            return False

        # Function to mark keywords in text
        def mark_keywords_in_text(text, keywords, css_class):
            """Mark all occurrences of keywords with CSS class."""
            for keyword in keywords:
                # Use word boundary to match complete words only
                pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)

                def replacer(match):
                    return f'<span class="{css_class}">{match.group()}</span>'

                text = pattern.sub(replacer, text)
            return text

        # Process all text nodes
        for text_node in soup.find_all(text=True):
            # Skip if parent is script, style
            if text_node.parent.name in ['script', 'style']:
                continue

            # IMPORTANT: Skip only if already inside a keyword span (not just any span)
            if is_inside_keyword_span(text_node):
                continue

            original_text = str(text_node)
            modified_text = original_text

            # First mark newly added keywords (higher priority)
            if newly_added:
                modified_text = mark_keywords_in_text(modified_text, newly_added, "opt-keyword-add")

            # Then mark existing keywords (but not if already marked)
            if covered_keywords:
                # Only mark if not already marked with opt-keyword-add
                temp_text = modified_text
                for keyword in covered_keywords:
                    # Check if this keyword is not already marked as newly added
                    if keyword not in newly_added:
                        pattern = re.compile(rf'{re.escape(keyword)}', re.IGNORECASE)

                        def replacer(match):
                            # Check if this match is not already inside a span
                            return f'<span class="opt-keyword-existing">{match.group()}</span>'

                        temp_text = pattern.sub(replacer, temp_text)
                modified_text = temp_text

            # Replace the text node if modified
            if modified_text != original_text:
                new_soup = BeautifulSoup(modified_text, 'html.parser')
                # Extract all children from new_soup and insert them
                for element in list(new_soup.children):
                    text_node.insert_before(element)
                text_node.extract()

        return str(soup)

    def _get_newly_added_keywords(self, html: str, missed_keywords: list[str]) -> list[str]:
        """
        Detect which missing keywords were successfully added to the HTML.
        Uses word boundary detection for accurate matching.

        Args:
            html: Optimized HTML content
            missed_keywords: Keywords that were missing in original resume

        Returns:
            List of keywords that were successfully added
        """
        import re

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)

        newly_added = []
        for keyword in missed_keywords:
            # Use word boundary regex for accurate matching
            # This prevents "Java" from matching "JavaScript"
            pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
            if pattern.search(text_content):
                newly_added.append(keyword)

        return newly_added

    def _merge_tracking(self, llm1_result: dict, llm2_result: dict) -> list[str]:
        """Merge tracking arrays from both LLMs."""

        tracking1 = llm1_result.get("tracking", [])
        tracking2 = llm2_result.get("tracking", [])

        # Categorize tracking messages
        categorized = []

        # Process LLM1 tracking (Core sections)
        for item in tracking1:
            if "[Summary]" in item:
                categorized.append(f"[Structure: Summary] {item.split(']', 1)[1].strip()}")
            elif "[Skills]" in item:
                categorized.append(f"[Quick Win: Skills] {item.split(']', 1)[1].strip()}")
            elif "[Experience]" in item:
                categorized.append(f"[Presentation Gap: Experience] {item.split(']', 1)[1].strip()}")
            else:
                categorized.append(item)

        # Process LLM2 tracking (Additional sections)
        for item in tracking2:
            if "[Education]" in item:
                categorized.append(f"[Structure: Education] {item.split(']', 1)[1].strip()}")
            elif "[Projects]" in item:
                categorized.append(f"[Skill Gap: Projects] {item.split(']', 1)[1].strip()}")
            elif "[Certifications]" in item:
                categorized.append(f"[Skill Gap: Certifications] {item.split(']', 1)[1].strip()}")
            else:
                categorized.append(item)

        return categorized

    async def _calculate_metrics_v3(
        self,
        original_resume: str,
        optimized_resume: str,
        job_description: str,
        original_index: dict,
        all_keywords: list[str]
    ) -> dict:
        """
        Calculate Keywords and Similarity metrics for v3.1.0.

        Returns:
            Dictionary with 'keywords' and 'similarity' metrics
        """

        try:
            # Get before metrics from original_index
            # Handle both formats: nested and flat
            if "keyword_coverage" in original_index:
                # Nested format from Gap Analysis API
                keyword_coverage_before = original_index.get("keyword_coverage", {})
                similarity_before = original_index.get("similarity_percentage", 0)
            else:
                # Flat format from Bubble.io
                keyword_coverage_before = {
                    "covered_keywords": original_index.get("covered_keywords", []),
                    "missed_keywords": original_index.get("missing_keywords", []),
                    "coverage_percentage": original_index.get("coverage_percentage", 0)
                }
                similarity_before = original_index.get("similarity_percentage", 0)

            # Calculate after metrics using IndexCalculationServiceV2
            after_result = await self.index_service.calculate_index(
                resume=optimized_resume,
                job_description=job_description,
                keywords=all_keywords,
                include_timing=False
            )

            # Extract after metrics
            keyword_coverage_after = after_result["keyword_coverage"]

            # Get similarity from after_result (already transformed by IndexCalculationServiceV2)
            # IndexCalculationServiceV2 returns both raw and transformed similarity
            similarity_after = after_result.get("similarity_percentage", 0)

            # Build Keywords metrics
            kw_before_covered = keyword_coverage_before.get("covered_keywords", [])
            kw_before_missed = keyword_coverage_before.get("missed_keywords", [])
            kw_after_covered = keyword_coverage_after.get("covered_keywords", [])
            kw_after_missed = keyword_coverage_after.get("missed_keywords", [])

            # Calculate newly added and removed
            before_set = set(kw_before_covered)
            after_set = set(kw_after_covered)
            newly_added = list(after_set - before_set)
            kw_removed = list(before_set - after_set)

            # Calculate improvements
            kcr_before = keyword_coverage_before.get("coverage_percentage", 0)
            kcr_after = keyword_coverage_after.get("coverage_percentage", 0)
            kcr_improvement = kcr_after - kcr_before

            ss_improvement = similarity_after - similarity_before

            return {
                "keywords": {
                    "kcr_improvement": int(kcr_improvement),
                    "kcr_before": int(kcr_before),
                    "kcr_after": int(kcr_after),
                    "kw_before_covered": kw_before_covered,
                    "kw_before_missed": kw_before_missed,
                    "kw_after_covered": kw_after_covered,
                    "kw_after_missed": kw_after_missed,
                    "newly_added": newly_added,
                    "kw_removed": kw_removed
                },
                "similarity": {
                    "SS_improvement": round(ss_improvement),  # round() returns int
                    "SS_before": similarity_before,  # Already an integer from original_index
                    "SS_after": round(similarity_after)  # round() returns int
                }
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            # Return default metrics on error
            return {
                "keywords": {
                    "kcr_improvement": 0,
                    "kcr_before": 0,
                    "kcr_after": 0,
                    "kw_before_covered": [],
                    "kw_before_missed": [],
                    "kw_after_covered": [],
                    "kw_after_missed": [],
                    "newly_added": [],
                    "kw_removed": []
                },
                "similarity": {
                    "SS_improvement": 0,
                    "SS_before": 0,
                    "SS_after": 0
                }
            }
