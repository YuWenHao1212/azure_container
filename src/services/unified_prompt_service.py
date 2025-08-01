"""
Unified Prompt Service for managing prompts and LLM configurations.
Combines multilingual support with YAML-based configuration management.
"""
import logging
from pathlib import Path
from typing import ClassVar

from src.core.simple_prompt_manager import SimplePromptManager
from src.models.prompt_config import LLMConfig, PromptConfig

logger = logging.getLogger(__name__)


class UnifiedPromptService:
    """
    Unified service for prompt management that:
    1. Loads prompts from YAML files
    2. Supports multiple languages
    3. Provides LLM configuration from YAML
    4. Handles version management
    """

    SUPPORTED_LANGUAGES: ClassVar[list] = ["en", "zh-TW"]

    # Task path for all languages (now using unified directory with language-specific filenames)
    TASK_PATH = "keyword_extraction"

    def __init__(self, prompts_base_dir: str | None = None, task_path: str | None = None):
        """
        Initialize the unified prompt service.

        Args:
            prompts_base_dir: Base directory for prompts (default: src/prompts)
            task_path: Task-specific path (default: keyword_extraction)
        """
        if prompts_base_dir is None:
            prompts_base_dir = "src/prompts"
        self.simple_prompt_manager = SimplePromptManager(prompts_base_dir)
        self._cache = {}  # Cache for loaded configs
        # Allow overriding the default task path
        if task_path:
            self.TASK_PATH = task_path

        logger.info(
            f"Initialized UnifiedPromptService with languages: {self.SUPPORTED_LANGUAGES}"
        )

    def get_prompt_with_config(
        self,
        language: str,
        version: str = "latest",
        variables: dict[str, str] | None = None
    ) -> tuple[str, LLMConfig]:
        """
        Get formatted prompt and LLM configuration for specified language and version.

        Args:
            language: Language code ("en" or "zh-TW")
            version: Prompt version (e.g., "1.0.0", "1.2.0", "latest")
            variables: Variables to format the prompt (e.g., {"job_description": "..."})

        Returns:
            Tuple of (formatted_prompt, llm_config)

        Raises:
            ValueError: If language is not supported
            FileNotFoundError: If prompt file doesn't exist
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Language '{language}' not supported. "
                f"Supported: {self.SUPPORTED_LANGUAGES}"
            )

        # Create filename with language suffix
        if version == "latest":
            # For "latest", need to find the highest version for this language
            available_versions = self.list_versions(language)
            if not available_versions or len(available_versions) <= 1:  # Only "latest" in list
                raise ValueError(f"No versioned prompts found for language '{language}'")
            # Get the highest numeric version (skip "latest")
            numeric_versions = [v for v in available_versions if v != "latest"]
            version = max(numeric_versions)

        # Add 'v' prefix if not already present
        version_str = version if version.startswith('v') else f"v{version}"
        filename = f"{version_str}-{language}.yaml"

        # Check cache first
        cache_key = f"{language}-{version}"
        if cache_key not in self._cache:
            try:
                # Load prompt configuration from YAML with language-specific filename
                prompt_config = self.simple_prompt_manager.load_prompt_config_by_filename(
                    self.TASK_PATH, filename
                )
                self._cache[cache_key] = prompt_config
                logger.info(
                    f"Loaded prompt config: language={language}, version={version}"
                )
            except FileNotFoundError as e:
                logger.error(f"Prompt file not found: {e}")
                raise ValueError(
                    f"Version '{version}' not available for language '{language}'. "
                    f"Available: {self.list_versions(language)}"
                ) from e
        else:
            prompt_config = self._cache[cache_key]

        # Format the prompt with variables
        if variables:
            formatted_prompt = prompt_config.format_user_prompt(**variables)
        else:
            formatted_prompt = prompt_config.get_user_prompt()

        # Combine system and user prompts if both exist
        system_prompt = prompt_config.get_system_prompt()
        # For models that support system prompts, we'll need to handle this differently
        # For now, we'll concatenate them
        full_prompt = f"{system_prompt}\n\n{formatted_prompt}" if system_prompt else formatted_prompt

        return full_prompt, prompt_config.llm_config

    def get_prompt_config(self, language: str, version: str = "latest") -> PromptConfig:
        """
        Get the full prompt configuration for a language and version.

        Args:
            language: Language code
            version: Prompt version

        Returns:
            PromptConfig object
        """
        # Use the same logic as get_prompt_with_config
        if version == "latest":
            available_versions = self.list_versions(language)
            if not available_versions or len(available_versions) <= 1:
                raise ValueError(f"No versioned prompts found for language '{language}'")
            numeric_versions = [v for v in available_versions if v != "latest"]
            version = max(numeric_versions)

        # Add 'v' prefix if not already present
        version_str = version if version.startswith('v') else f"v{version}"
        filename = f"{version_str}-{language}.yaml"
        return self.simple_prompt_manager.load_prompt_config_by_filename(
            self.TASK_PATH, filename
        )

    def list_versions(self, language: str) -> list[str]:
        """
        List all available versions for a language.

        Args:
            language: Language code

        Returns:
            List of available versions
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return []

        # Scan the task directory for files with language suffix
        task_dir = Path(self.simple_prompt_manager.prompts_dir) / self.TASK_PATH
        if not task_dir.exists():
            return []

        versions = []
        pattern = f"*-{language}.yaml"
        for file in task_dir.glob(pattern):
            # Extract version from filename (v1.3.0-zh-TW.yaml -> 1.3.0)
            filename = file.stem  # Remove .yaml
            if '-' in filename:
                version = filename.split('-')[0]  # Get part before first dash
                if version.startswith('v'):
                    version = version[1:]  # Remove 'v' prefix
                versions.append(version)

        # Sort versions in descending order
        if versions:
            versions.sort(reverse=True, key=lambda v: tuple(map(int, v.split('.'))))
            # Always include 'latest' as an option
            if 'latest' not in versions:
                versions.insert(0, 'latest')

        return versions

    def get_active_version(self, language: str) -> str | None:
        """
        Get the currently active version for a language.

        Args:
            language: Language code

        Returns:
            Active version or None
        """
        if language not in self.SUPPORTED_LANGUAGES:
            return None

        # Check each version to find the one marked as "active"
        available_versions = self.list_versions(language)
        if not available_versions:
            return None

        # Look for version marked as "active" in metadata
        for version in available_versions:
            if version == "latest":
                continue
            try:
                config = self.get_prompt_config(language, version)
                if config.metadata.status == "active":
                    return version
            except Exception as e:
                logger.warning(f"Error checking version {version}: {e}")
                continue

        # If no active version found, return the highest numeric version
        numeric_versions = [v for v in available_versions if v != "latest"]
        if numeric_versions:
            return max(numeric_versions)

        return None

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.info("Cleared UnifiedPromptService cache")

    def get_llm_config_for_version(
        self,
        language: str,
        version: str = "latest"
    ) -> LLMConfig:
        """
        Get just the LLM configuration for a specific version.

        Args:
            language: Language code
            version: Prompt version

        Returns:
            LLMConfig object
        """
        prompt_config = self.get_prompt_config(language, version)
        return prompt_config.llm_config

    def format_prompt(
        self,
        language: str,
        version: str,
        job_description: str
    ) -> str:
        """
        Convenience method for keyword extraction - formats prompt with job description.

        Args:
            language: Language code
            version: Prompt version
            job_description: Job description text

        Returns:
            Formatted prompt string
        """
        prompt, _ = self.get_prompt_with_config(
            language,
            version,
            {"job_description": job_description}
        )
        return prompt


# Singleton instance
_unified_prompt_service = None


def get_unified_prompt_service(prompts_base_dir: str | None = None) -> UnifiedPromptService:
    """
    Get singleton instance of UnifiedPromptService.

    Args:
        prompts_base_dir: Base directory for prompts

    Returns:
        UnifiedPromptService instance
    """
    global _unified_prompt_service

    if _unified_prompt_service is None:
        _unified_prompt_service = UnifiedPromptService(prompts_base_dir)

    return _unified_prompt_service
