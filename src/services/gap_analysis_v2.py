"""
Enhanced Gap Analysis Service V2 for Azure Container API.

Improved gap analysis with context-aware processing and index result integration.
Key component of Index Cal and Gap Analysis V2 refactoring.
"""
import logging
import time
from typing import Any, Optional

from src.core.config import get_settings
from src.core.simple_prompt_manager import prompt_manager
from src.services.gap_analysis_utils import parse_gap_response
from src.services.token_tracking_mixin import TokenTrackingMixin
from src.services.unified_prompt_service import UnifiedPromptService

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


class GapAnalysisServiceV2(TokenTrackingMixin):
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
        # Initialize base attributes from V1
        self.settings = get_settings()
        self.prompt_service = UnifiedPromptService(task_path="gap_analysis")
        self.logger = logging.getLogger(self.__class__.__name__)

        # V2 specific attributes
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

            # Load LLM config dynamically with proper fallback chain
            # Pass resume and job_description for dynamic token calculation
            llm_config = self._load_llm_config(language, resume, job_description)

            # Execute enhanced analysis with all LLM config parameters
            response = await self._call_llm_with_context(
                enhanced_prompt,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                **llm_config["additional_params"]
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
        # Use replace instead of format to avoid issues with JSON braces in prompt
        enhanced_prompt = base_prompt.replace("{job_description}", job_description)
        enhanced_prompt = enhanced_prompt.replace("{resume}", resume)
        enhanced_prompt = enhanced_prompt.replace("{context}", context_section)
        enhanced_prompt = enhanced_prompt.replace("{options}", options_section)

        return enhanced_prompt

    def _load_llm_config(self, language: str, resume: str = "", job_description: str = "") -> dict[str, Any]:
        """
        Load LLM configuration with proper fallback chain and dynamic token calculation.

        Priority:
        1. YAML configuration file
        2. Environment variables (override)
        3. Dynamic calculation based on input
        4. Default values

        Args:
            language: Language code for selecting correct YAML file
            resume: Resume content for token calculation
            job_description: Job description for token calculation

        Returns:
            Dictionary with temperature, max_tokens, and additional_params
        """
        import os

        # Default configuration
        config = {
            "temperature": 0.3,
            "max_tokens": 3000,
            "additional_params": {}
        }

        try:
            # Load from YAML configuration
            filename = "v2.0.0-zh-TW.yaml" if language == "zh-TW" else "v2.0.0.yaml"
            prompt_config = prompt_manager.load_prompt_config_by_filename("gap_analysis", filename)

            if hasattr(prompt_config, 'llm_config'):
                llm_config_obj = prompt_config.llm_config

                # Load base configuration from YAML
                config["temperature"] = getattr(llm_config_obj, 'temperature', config["temperature"])
                config["max_tokens"] = getattr(llm_config_obj, 'max_tokens', config["max_tokens"])

                # Load additional parameters
                for attr in ['seed', 'top_p', 'frequency_penalty', 'presence_penalty']:
                    if hasattr(llm_config_obj, attr):
                        config["additional_params"][attr] = getattr(llm_config_obj, attr)

                logger.info(f"Loaded LLM config from YAML: {filename}")
        except Exception as e:
            logger.warning(f"Failed to load LLM config from YAML: {e}, using defaults")

        # Override with environment variables if present
        if os.getenv("GAP_ANALYSIS_TEMPERATURE"):
            try:
                config["temperature"] = float(os.getenv("GAP_ANALYSIS_TEMPERATURE"))
                logger.info(f"Overriding temperature from env: {config['temperature']}")
            except ValueError:
                logger.warning("Invalid GAP_ANALYSIS_TEMPERATURE value, using default")

        if os.getenv("GAP_ANALYSIS_MAX_TOKENS"):
            try:
                config["max_tokens"] = int(os.getenv("GAP_ANALYSIS_MAX_TOKENS"))
                logger.info(f"Overriding max_tokens from env: {config['max_tokens']}")
            except ValueError:
                logger.warning("Invalid GAP_ANALYSIS_MAX_TOKENS value, using default")

        # Dynamic token calculation based on input size
        if resume or job_description:
            calculated_tokens = self._calculate_required_tokens(resume, job_description)
            if calculated_tokens > config["max_tokens"]:
                logger.info(
                    f"Adjusting max_tokens from {config['max_tokens']} "
                    f"to {calculated_tokens} based on input size"
                )
                config["max_tokens"] = calculated_tokens

        # Ensure minimum tokens for proper response
        min_required_tokens = 2000  # Minimum to avoid truncation
        if config["max_tokens"] < min_required_tokens:
            logger.warning(f"max_tokens {config['max_tokens']} is below minimum {min_required_tokens}, adjusting")
            config["max_tokens"] = min_required_tokens

        # Cap at maximum allowed tokens
        max_allowed_tokens = 4096  # Azure OpenAI typical limit
        if config["max_tokens"] > max_allowed_tokens:
            logger.warning(f"max_tokens {config['max_tokens']} exceeds maximum {max_allowed_tokens}, capping")
            config["max_tokens"] = max_allowed_tokens

        logger.info(f"Final LLM config: temperature={config['temperature']}, max_tokens={config['max_tokens']}")

        return config

    def _calculate_required_tokens(self, resume: str, job_description: str) -> int:
        """
        Calculate required tokens based on input size.

        Uses a simple heuristic:
        - Estimate input tokens from text length
        - Add buffer for prompt template
        - Ensure enough tokens for complete response

        Args:
            resume: Resume content
            job_description: Job description content

        Returns:
            Calculated required max_tokens
        """
        # Rough estimation: 1 token ≈ 4 characters (English)
        # For safety, use 1 token ≈ 3 characters
        chars_per_token = 3

        # Calculate input size
        input_chars = len(resume) + len(job_description)
        estimated_input_tokens = input_chars // chars_per_token

        # Add buffer for prompt template and context (approximately 500 tokens)
        prompt_overhead = 500
        total_input_tokens = estimated_input_tokens + prompt_overhead

        # Expected output size for Gap Analysis
        # - CoreStrengths: ~300 tokens
        # - KeyGaps: ~300 tokens
        # - QuickImprovements: ~300 tokens
        # - OverallAssessment: ~400 tokens
        # - SkillSearchQueries: ~200 tokens
        # Total: ~1500 tokens minimum, 2500 tokens comfortable

        base_output_tokens = 2500

        # For large inputs, scale output proportionally
        if total_input_tokens > 2000:
            # Add 20% more tokens for comprehensive analysis
            additional_tokens = int(base_output_tokens * 0.2)
            base_output_tokens += additional_tokens

        # Final calculation
        required_tokens = base_output_tokens

        logger.info(f"Token calculation: input_chars={input_chars}, "
                   f"estimated_input_tokens={estimated_input_tokens}, "
                   f"required_output_tokens={required_tokens}")

        return required_tokens

    async def _call_llm_with_context(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 3000,
        **kwargs
    ) -> str:
        """
        Call LLM with enhanced context and optimized parameters.

        Uses LLM Factory for consistent model selection across V1/V2.

        Args:
            prompt: Enhanced prompt with context
            temperature: Temperature for response consistency
            max_tokens: Maximum tokens for response
            **kwargs: Additional LLM parameters (seed, top_p, etc.)

        Returns:
            LLM response text
        """
        from src.services.llm_factory import get_llm_client

        # Get OpenAI client using LLM Factory for consistent deployment selection
        openai_client = get_llm_client(api_name="gap_analysis")

        try:
            # Build messages array properly
            messages = [{"role": "user", "content": prompt}]

            # Call LLM with V2 optimized parameters - using proper method signature
            response = await openai_client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Validate response structure
            if not response or 'choices' not in response:
                logger.error(f"[GAP_V2] Invalid LLM response structure: {response}")
                raise ValueError("Invalid response from LLM: missing 'choices'")

            if not response['choices'] or len(response['choices']) == 0:
                logger.error("[GAP_V2] Empty choices in LLM response")
                raise ValueError("Invalid response from LLM: empty choices")

            if 'message' not in response['choices'][0]:
                logger.error(f"[GAP_V2] Missing message in choice: {response['choices'][0]}")
                raise ValueError("Invalid response from LLM: missing message")

            if 'content' not in response['choices'][0]['message']:
                logger.error(f"[GAP_V2] Missing content in message: {response['choices'][0]['message']}")
                raise ValueError("Invalid response from LLM: missing content")

            content = response['choices'][0]['message']['content']
            if not content:
                logger.error("[GAP_V2] Empty content in LLM response")
                raise ValueError("Invalid response from LLM: empty content")

            # Extract response text (following V1 pattern)
            return content.strip()

        finally:
            # Safe close handling - check if client has close method
            if hasattr(openai_client, 'close'):
                await openai_client.close()

    def _parse_enhanced_response(self, response: str) -> dict[str, Any]:
        """
        Parse enhanced LLM response with V2-specific improvements.

        Args:
            response: Raw LLM response

        Returns:
            Parsed gap analysis results
        """
        # Log the raw response for debugging
        logger.info(f"[GAP_V2] Raw response length: {len(response)}")
        logger.info(f"[GAP_V2] Raw response preview: {response[:500]}...")

        # Handle empty response
        if not response or not response.strip():
            logger.warning("[GAP_V2] Received empty response from LLM")
            return self._create_fallback_response("Empty response from LLM")

        # V2 returns JSON format, not XML
        try:
            # Parse JSON response - handle markdown code blocks if present
            import json
            import re

            cleaned_response = response.strip()

            # Remove ```json and ``` markers if present
            if "```json" in cleaned_response:
                # Extract JSON from markdown code block
                json_match = re.search(r'```json\s*\n?(.*?)\n?```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()
            elif "```" in cleaned_response:
                # Handle generic code blocks
                json_match = re.search(r'```\s*\n?(.*?)\n?```', cleaned_response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(1).strip()

            # Check for JSON completeness before parsing
            if not self._is_json_complete(cleaned_response):
                logger.warning("[GAP_V2] JSON appears to be truncated")
                # Try to fix common truncation issues
                cleaned_response = self._attempt_json_repair(cleaned_response)

            gap_data = json.loads(cleaned_response)

            logger.info("[GAP_V2] Successfully parsed JSON response")

            # Validate required fields
            required_fields = ["CoreStrengths", "KeyGaps", "QuickImprovements", "OverallAssessment"]
            missing_fields = [field for field in required_fields if field not in gap_data]

            if missing_fields:
                logger.warning(f"[GAP_V2] Missing required fields: {missing_fields}")
                # Fill missing fields with defaults
                for field in missing_fields:
                    if field == "OverallAssessment":
                        gap_data[field] = "<p>Analysis completed with partial data.</p>"
                    else:
                        gap_data[field] = "<ol><li>Analysis in progress</li></ol>"

            # Process SkillSearchQueries
            skill_queries = gap_data.get("SkillSearchQueries", [])
            formatted_skills = self._format_skill_queries(skill_queries)

            # Ensure valid non-empty strings for required fields
            core_strengths = gap_data.get("CoreStrengths") or "<ol><li>Analysis in progress</li></ol>"
            key_gaps = gap_data.get("KeyGaps") or "<ol><li>Analysis in progress</li></ol>"
            quick_improvements = gap_data.get("QuickImprovements") or "<ol><li>Analysis in progress</li></ol>"
            overall_assessment = gap_data.get("OverallAssessment") or "<p>Analysis completed successfully.</p>"

            return {
                "CoreStrengths": core_strengths,
                "KeyGaps": key_gaps,
                "QuickImprovements": quick_improvements,
                "OverallAssessment": overall_assessment,
                "SkillSearchQueries": formatted_skills,
                "enhanced_analysis": True,
                "version": "2.0"
            }

        except json.JSONDecodeError as e:
            logger.error(f"[GAP_V2] JSON parse error: {e}")
            logger.error(f"[GAP_V2] Error at position: {e.pos if hasattr(e, 'pos') else 'unknown'}")

            # Try XML fallback as last resort
            return self._try_xml_fallback(response)

    def _is_json_complete(self, json_str: str) -> bool:
        """
        Check if JSON string appears to be complete.

        Args:
            json_str: JSON string to check

        Returns:
            True if JSON appears complete, False otherwise
        """
        # Simple heuristic: count braces and brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')

        # Check if they match
        braces_match = open_braces == close_braces
        brackets_match = open_brackets == close_brackets

        # Check if string ends properly (allowing whitespace)
        import re
        ends_properly = bool(re.search(r'[}\]]\s*$', json_str))

        return braces_match and brackets_match and ends_properly

    def _attempt_json_repair(self, json_str: str) -> str:
        """
        Attempt to repair truncated or malformed JSON.

        Args:
            json_str: Potentially truncated JSON string

        Returns:
            Repaired JSON string
        """
        import re

        logger.info("[GAP_V2] Attempting JSON repair")

        # Count unclosed braces and brackets
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')

        # Add missing closing characters
        repaired = json_str

        # Add missing closing brackets first (inner structures)
        for _ in range(open_brackets - close_brackets):
            repaired += ']'

        # Add missing closing braces
        for _ in range(open_braces - close_braces):
            repaired += '}'

        # Fix trailing commas
        repaired = re.sub(r',\s*}', '}', repaired)
        repaired = re.sub(r',\s*]', ']', repaired)

        # Handle incomplete string values
        # If last quote is not closed, close it
        if repaired.count('"') % 2 != 0:
            repaired += '"'

        logger.info(f"[GAP_V2] Repair added: {repaired[len(json_str):]}")

        return repaired

    def _format_skill_queries(self, skill_queries: list) -> list[dict[str, Any]]:
        """
        Format skill queries to ensure consistent structure.

        Args:
            skill_queries: Raw skill queries from JSON

        Returns:
            Formatted skill queries
        """
        formatted_skills = []

        for skill in skill_queries:
            if isinstance(skill, str):
                # Convert string to SkillQuery format
                formatted_skills.append({
                    "skill_name": skill,
                    "skill_category": "TECHNICAL",  # Default to technical
                    "description": f"Learn {skill} skills"
                })
            elif isinstance(skill, dict):
                # Ensure required fields exist
                formatted_skill = {
                    "skill_name": skill.get("skill_name", "Unknown"),
                    "skill_category": skill.get("skill_category", "TECHNICAL"),
                    "description": skill.get("description", "")
                }
                formatted_skills.append(formatted_skill)

        return formatted_skills

    def _create_fallback_response(self, reason: str) -> dict[str, Any]:
        """
        Create a fallback response when parsing fails.

        Args:
            reason: Reason for fallback

        Returns:
            Safe fallback response
        """
        logger.warning(f"[GAP_V2] Creating fallback response: {reason}")

        return {
            "CoreStrengths": "<ol><li>Unable to complete analysis. Please try again.</li></ol>",
            "KeyGaps": "<ol><li>Unable to complete analysis. Please try again.</li></ol>",
            "QuickImprovements": "<ol><li>Unable to complete analysis. Please try again.</li></ol>",
            "OverallAssessment": f"<p>Analysis could not be completed: {reason}. Please retry the request.</p>",
            "SkillSearchQueries": [],
            "enhanced_analysis": False,
            "version": "2.0",
            "error": reason
        }

    def _try_xml_fallback(self, response: str) -> dict[str, Any]:
        """
        Try to parse response as XML (V1 format) and convert to V2 format.

        Args:
            response: Raw response that failed JSON parsing

        Returns:
            Converted response or fallback
        """
        logger.warning("[GAP_V2] Attempting XML parsing as fallback")

        try:
            # parse_gap_response is already imported at the top
            base_result = parse_gap_response(response)

            # Convert V1 format to V2 format
            strengths_list = base_result.get("strengths", [])
            gaps_list = base_result.get("gaps", [])
            improvements_list = base_result.get("improvements", [])
            assessment = base_result.get("assessment", "")

            # Convert lists to HTML ordered lists
            def list_to_html_ol(items):
                if not items or not isinstance(items, list):
                    return "<ol><li>Analysis in progress</li></ol>"
                html_items = [f"<li>{item}</li>" for item in items if item]
                return f"<ol>{''.join(html_items)}</ol>" if html_items else "<ol><li>Analysis in progress</li></ol>"

            return {
                "CoreStrengths": list_to_html_ol(strengths_list),
                "KeyGaps": list_to_html_ol(gaps_list),
                "QuickImprovements": list_to_html_ol(improvements_list),
                "OverallAssessment": (
                    assessment if assessment and isinstance(assessment, str)
                    else "<p>Analysis completed using fallback parsing.</p>"
                ),
                "SkillSearchQueries": base_result.get("skill_queries", []),
                "enhanced_analysis": True,
                "version": "2.0",
                "fallback_used": "XML"
            }

        except Exception as e:
            logger.error(f"[GAP_V2] XML fallback also failed: {e}")
            return self._create_fallback_response("Both JSON and XML parsing failed")

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
