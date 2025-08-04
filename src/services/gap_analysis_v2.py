"""
Enhanced Gap Analysis Service V2 for Azure Container API.

Improved gap analysis with context-aware processing and index result integration.
Key component of Index Cal and Gap Analysis V2 refactoring.
"""
import logging
import time
from typing import Any, Optional

from src.core.simple_prompt_manager import prompt_manager
from src.services.gap_analysis import GapAnalysisService

logger = logging.getLogger(__name__)


def get_prompt(task: str, version: str, language: str = "en") -> str:
    """
    Wrapper function for getting prompts from prompt manager.

    Args:
        task: Task identifier (e.g., 'gap_analysis')
        version: Version string (e.g., '2.0.0')
        language: Language code (e.g., 'en', 'zh-TW')

    Returns:
        Prompt string
    """
    # For V2, try to load the prompt configuration
    try:
        # Try to construct filename with language and version
        filename = f"v{version}-zh-TW.yaml" if language == "zh-TW" else f"v{version}.yaml"

        config = prompt_manager.load_prompt_config_by_filename(task, filename)

        # Return the main prompt (assuming 'main' key exists)
        if hasattr(config, 'prompts') and 'main' in config.prompts:
            return config.prompts['main']
        elif hasattr(config, 'prompts') and len(config.prompts) > 0:
            # Return first available prompt
            return next(iter(config.prompts.values()))
        else:
            # Fallback: return a default prompt template
            return "Analyze the gap between resume and job requirements. Provide detailed feedback."

    except Exception as e:
        logger.warning(f"Failed to load prompt for {task} v{version} ({language}): {e}")
        # Fallback: return a default prompt template
        return "Analyze the gap between resume and job requirements. Provide detailed feedback."


class GapAnalysisServiceV2(GapAnalysisService):
    """
    Enhanced Gap Analysis Service V2.

    Improvements over V1:
    1. Uses index calculation results as context
    2. Intelligent prompt optimization based on matching data
    3. Skill priority analysis
    4. Better error handling with context preservation
    """

    def __init__(self, **kwargs):
        """Initialize V2 service with enhanced capabilities."""
        super().__init__(**kwargs)
        self.enable_context_enhancement = True
        self.enable_skill_priorities = True

        # V2 specific statistics
        self.v2_stats = {
            "context_enhanced_calls": 0,
            "skill_priority_requests": 0,
            "avg_context_processing_time": 0
        }

    async def analyze_with_context(
        self,
        resume: str,
        job_description: str,
        index_result: dict[str, Any],
        language: str = "en",
        options: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Analyze gap with enhanced context from index calculation results.

        Args:
            resume: Resume content (HTML or plain text)
            job_description: Job description content
            index_result: Results from IndexCalculationServiceV2
            language: Output language (en or zh-TW)
            options: Additional analysis options

        Returns:
            Enhanced gap analysis results with context awareness
        """
        start_time = time.time()
        self.v2_stats["context_enhanced_calls"] += 1

        try:
            # Build enhanced prompt with index context
            enhanced_prompt = self._build_enhanced_prompt(
                resume,
                job_description,
                index_result,
                language,
                options
            )

            # Load LLM config from prompt YAML
            try:
                filename = "v2.0.0-zh-TW.yaml" if language == "zh-TW" else "v2.0.0.yaml"
                config = prompt_manager.load_prompt_config_by_filename("gap_analysis", filename)
                
                # Extract LLM config attributes
                if hasattr(config, 'llm_config'):
                    llm_config_obj = config.llm_config
                    temperature = getattr(llm_config_obj, 'temperature', 0.3)
                    max_tokens = getattr(llm_config_obj, 'max_tokens', 1500)
                    # Build additional parameters dict
                    llm_params = {}
                    for attr in ['seed', 'top_p', 'frequency_penalty', 'presence_penalty']:
                        if hasattr(llm_config_obj, attr):
                            llm_params[attr] = getattr(llm_config_obj, attr)
                else:
                    temperature = 0.3
                    max_tokens = 1500
                    llm_params = {}
            except Exception as e:
                logger.warning(f"Failed to load LLM config from prompt YAML: {e}")
                # Use default values
                temperature = 0.3
                max_tokens = 1500
                llm_params = {}

            # Execute enhanced analysis with all LLM config parameters
            response = await self._call_llm_with_context(
                enhanced_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **llm_params
            )

            # Parse enhanced response
            result = self._parse_enhanced_response(response)

            # Add skill priorities if requested
            if (self.enable_skill_priorities and
                options and
                options.get("include_skill_priorities", False)):

                result["skill_priorities"] = await self._analyze_skill_priorities(
                    result.get("KeyGaps", ""),
                    index_result
                )
                self.v2_stats["skill_priority_requests"] += 1

            # Add V2 metadata
            result["metadata"] = {
                "version": "2.0",
                "context_enhanced": True,
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                "similarity_score": index_result.get("similarity_percentage", 0),
                "keyword_coverage": index_result.get("keyword_coverage", {}).get("coverage_percentage", 0)
            }

            # Update timing statistics
            context_time = time.time() - start_time
            current_avg = self.v2_stats["avg_context_processing_time"]
            call_count = self.v2_stats["context_enhanced_calls"]
            self.v2_stats["avg_context_processing_time"] = (
                (current_avg * (call_count - 1) + context_time) / call_count
            )

            return result

        except Exception as e:
            logger.error(f"Enhanced gap analysis V2 failed: {e}")
            # Re-raise the exception with enhanced error message
            # Do NOT fallback to V1 - V2 should operate independently
            raise Exception(f"Gap Analysis V2 failed: {e!s}") from e

    def _build_enhanced_prompt(
        self,
        resume: str,
        job_description: str,
        index_result: dict[str, Any],
        language: str,
        options: Optional[dict[str, Any]]
    ) -> str:
        """
        Build enhanced prompt incorporating index calculation context.

        Args:
            resume: Resume content
            job_description: Job description
            index_result: Index calculation results for context
            language: Target language
            options: Analysis options

        Returns:
            Enhanced prompt with context information
        """
        # Get base prompt template
        try:
            base_prompt = get_prompt("gap_analysis", version="2.0.0", language=language)
        except Exception:
            # Fallback to V1 prompt if V2 not available
            base_prompt = get_prompt("gap_analysis", version="1.0.0", language=language)

        # Extract context from index results
        similarity_score = index_result.get("similarity_percentage", 0)
        keyword_coverage = index_result.get("keyword_coverage", {})
        covered_keywords = keyword_coverage.get("covered_keywords", [])
        missed_keywords = keyword_coverage.get("missed_keywords", [])

        # Build context section
        context_section = f"""
### Analysis Context from Index Calculation:
- Overall Match Score: {similarity_score}%
- Keyword Coverage: {keyword_coverage.get('coverage_percentage', 0)}%
- Strengths (Covered Keywords): {', '.join(covered_keywords[:10])}
- Gaps (Missing Keywords): {', '.join(missed_keywords[:10])}

Please use this matching data to provide more targeted and specific analysis.
Focus on the identified gaps while acknowledging the existing strengths.
"""

        # Add analysis options if provided
        options_section = ""
        if options:
            if options.get("focus_areas"):
                areas = ", ".join(options["focus_areas"])
                options_section += f"\nFocus Areas: {areas}"

            if options.get("max_improvements"):
                options_section += f"\nLimit improvements to {options['max_improvements']} items"

            if options.get("experience_level"):
                options_section += f"\nConsider experience level: {options['experience_level']}"

        # Combine all sections
        enhanced_prompt = base_prompt.format(
            job_description=job_description,
            resume=resume,
            context=context_section,
            options=options_section
        )

        return enhanced_prompt

    async def _call_llm_with_context(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        **kwargs
    ) -> str:
        """
        Call LLM with enhanced context and optimized parameters.

        Args:
            prompt: Enhanced prompt with context
            temperature: Temperature for response consistency
            max_tokens: Maximum tokens for response
            **kwargs: Additional LLM parameters (seed, top_p, etc.)

        Returns:
            LLM response text
        """
        from src.services.openai_client import get_azure_openai_client

        # Get OpenAI client
        openai_client = get_azure_openai_client()

        try:
            # Build messages array properly
            messages = [{"role": "user", "content": prompt}]

            # Call LLM with V2 optimized parameters - using proper method signature
            response = await openai_client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract response text (following V1 pattern)
            return response['choices'][0]['message']['content'].strip()

        finally:
            await openai_client.close()

    def _parse_enhanced_response(self, response: str) -> dict[str, Any]:
        """
        Parse enhanced LLM response with V2-specific improvements.

        Args:
            response: Raw LLM response

        Returns:
            Parsed gap analysis results
        """
        # Use parsing logic from gap_analysis module
        from src.services.gap_analysis import parse_gap_response
        base_result = parse_gap_response(response)

        # Add V2 enhancements
        base_result["enhanced_analysis"] = True
        base_result["version"] = "2.0"

        return base_result

    async def _analyze_skill_priorities(
        self,
        key_gaps: str,
        index_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Analyze skill development priorities based on gaps and missing keywords.

        Args:
            key_gaps: Gap analysis text
            index_result: Index calculation results

        Returns:
            List of prioritized skills with development recommendations
        """
        missed_keywords = index_result.get("keyword_coverage", {}).get("missed_keywords", [])
        similarity_score = index_result.get("similarity_percentage", 0)

        skill_priorities = []

        # Prioritize top missing keywords
        for i, keyword in enumerate(missed_keywords[:5]):  # Top 5 missing keywords
            # Determine priority based on position and similarity score
            if i < 2 and similarity_score < 70:
                priority = "high"
                reason = "Critical skill gap - high impact on match score"
            elif i < 4 or similarity_score < 80:
                priority = "medium"
                reason = "Important skill gap - moderate impact on match score"
            else:
                priority = "low"
                reason = "Nice-to-have skill - low impact on match score"

            skill_priorities.append({
                "skill": keyword,
                "priority": priority,
                "reason": reason,
                "mentioned_in_gaps": keyword.lower() in key_gaps.lower(),
                "development_urgency": "immediate" if priority == "high" else "medium-term"
            })

        return skill_priorities

    def get_v2_stats(self) -> dict[str, Any]:
        """
        Get V2-specific statistics for monitoring.

        Returns:
            Dict containing V2 service statistics
        """
        return {
            "service_version": "2.0",
            "v2_statistics": self.v2_stats.copy(),
            "performance_metrics": {
                "avg_context_processing_time_ms": round(
                    self.v2_stats["avg_context_processing_time"] * 1000, 2
                ),
                "context_enhancement_rate": (
                    (self.v2_stats["context_enhanced_calls"] - self.v2_stats["fallback_to_v1_count"]) /
                    max(self.v2_stats["context_enhanced_calls"], 1)
                ),
                "skill_priority_adoption_rate": (
                    self.v2_stats["skill_priority_requests"] /
                    max(self.v2_stats["context_enhanced_calls"], 1)
                )
            }
        }
