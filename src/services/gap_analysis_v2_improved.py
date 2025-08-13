"""
Improved Gap Analysis V2 - Using existing prompt management system
"""
import logging
import os

from src.core.config import get_settings
from src.services.unified_prompt_service import UnifiedPromptService


class GapAnalysisServiceV2Improved:
    def __init__(self):
        self.settings = get_settings()
        self.prompt_service = UnifiedPromptService(task_path="gap_analysis")
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_llm_config(self, language: str):
        """Load LLM config using existing prompt management."""

        # Method 1: Use environment variable if set
        version = os.getenv('GAP_ANALYSIS_PROMPT_VERSION')

        if not version:
            # Method 2: Use active version from metadata
            version = self.prompt_service.get_active_version()

        if not version:
            # Method 3: Use latest version
            version = "latest"

        self.logger.info(f"Using Gap Analysis prompt version: {version}")

        # Load using existing system
        prompt_config = self.prompt_service.get_prompt_config(
            version=version,
            language=language
        )

        return {
            "temperature": prompt_config.llm_config.temperature,
            "max_tokens": prompt_config.llm_config.max_tokens,
            "prompts": prompt_config.prompts,
            "version": version
        }
