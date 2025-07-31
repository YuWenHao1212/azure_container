"""
Simple Prompt Manager for handling versioned prompts.
No template engine - just basic YAML configuration and string formatting.
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.models.prompt_config import PromptConfig


class SimplePromptManager:
    """
    Simple prompt manager that loads YAML configurations.
    No complex templating - just basic string formatting.
    """

    def __init__(self, prompts_dir: str = "src/prompts"):
        """Initialize the prompt manager."""
        self.prompts_dir = Path(prompts_dir)
        self.logger = logging.getLogger(__name__)
        self._cache: dict[str, PromptConfig] = {}

        # Ensure prompts directory exists
        self.prompts_dir.mkdir(parents=True, exist_ok=True)

    def load_prompt_config(
        self,
        task: str,
        version: str = "latest"
    ) -> PromptConfig:
        """
        Load prompt configuration for a specific task and version.

        Args:
            task: Task identifier (e.g., 'keyword_extraction')
            version: Version string or 'latest'

        Returns:
            PromptConfig instance
        """
        # Resolve version
        if version == "latest":
            version = self._get_latest_version(task)

        # Check cache
        cache_key = f"{task}:{version}"
        if cache_key in self._cache:
            self.logger.debug(f"Loading from cache: {cache_key}")
            return self._cache[cache_key]

        # Load from file
        # Handle version prefix - don't add 'v' if already present
        version_str = version if version.startswith('v') else f"v{version}"
        file_path = self.prompts_dir / task / f"{version_str}.yaml"

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Create config object
        config = PromptConfig(**data)

        # Cache it
        self._cache[cache_key] = config

        self.logger.info(f"Loaded prompt config: task={task}, version={version}")

        return config

    def load_prompt_config_by_filename(
        self,
        task: str,
        filename: str
    ) -> PromptConfig:
        """
        Load prompt configuration by specific filename.

        Args:
            task: Task identifier (e.g., 'keyword_extraction')
            filename: Specific filename (e.g., 'v1.3.0-zh-TW.yaml')

        Returns:
            PromptConfig instance
        """
        # Check cache using filename
        cache_key = f"{task}:{filename}"
        if cache_key in self._cache:
            self.logger.debug(f"Loading from cache: {cache_key}")
            return self._cache[cache_key]

        # Load from file
        file_path = self.prompts_dir / task / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        with open(file_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Create config object
        config = PromptConfig(**data)

        # Cache it
        self._cache[cache_key] = config

        self.logger.info(f"Loaded prompt config: task={task}, filename={filename}")

        return config

    def format_prompt(self, template: str, variables: dict[str, str]) -> str:
        """
        Simple string formatting using Python's format method.

        Args:
            template: Prompt template with {variable} placeholders
            variables: Dictionary of variables to substitute

        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required variable in prompt: {e}")

    def list_versions(self, task: str) -> list[str]:
        """List all available versions for a task."""
        task_dir = self.prompts_dir / task
        if not task_dir.exists():
            return []

        versions = []
        for file in task_dir.glob("v*.yaml"):
            # Extract version from filename (v1.0.0.yaml -> 1.0.0)
            version = file.stem[1:]
            versions.append(version)

        # Sort versions in descending order
        versions.sort(reverse=True, key=lambda v: tuple(map(int, v.split('.'))))

        return versions

    def get_active_version(self, task: str) -> str | None:
        """Get the currently active version for a task."""
        versions = self.list_versions(task)

        for version in versions:
            try:
                config = self.load_prompt_config(task, version)
                if config.metadata.status == "active":
                    return version
            except Exception as e:
                self.logger.warning(f"Error loading version {version}: {e}")
                continue

        return None

    def save_prompt_config(self, task: str, config: PromptConfig) -> Path:
        """Save a prompt configuration to file."""
        # Ensure task directory exists
        task_dir = self.prompts_dir / task
        task_dir.mkdir(parents=True, exist_ok=True)

        # Generate file path
        # Handle version prefix - don't add 'v' if already present
        version_str = config.version if config.version.startswith('v') else f"v{config.version}"
        file_path = task_dir / f"{version_str}.yaml"

        # Convert to dict and save
        data = config.dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self.logger.info(f"Saved prompt config to {file_path}")

        # Clear cache for this task
        self._clear_cache_for_task(task)

        return file_path

    def _get_latest_version(self, task: str) -> str:
        """Get the latest version for a task."""
        versions = self.list_versions(task)
        if not versions:
            raise FileNotFoundError(f"No prompt versions found for task: {task}")
        return versions[0]

    def _clear_cache_for_task(self, task: str):
        """Clear cache entries for a specific task."""
        keys_to_remove = [
            key for key in self._cache
            if key.startswith(f"{task}:")
        ]
        for key in keys_to_remove:
            del self._cache[key]

    @lru_cache(maxsize=32)
    def get_prompt_info(self, task: str, version: str) -> dict[str, Any]:
        """Get summary information about a prompt configuration."""
        config = self.load_prompt_config(task, version)

        return {
            "task": task,
            "version": config.version,
            "status": config.metadata.status,
            "author": config.metadata.author,
            "description": config.metadata.description,
            "llm_config": {
                "temperature": config.llm_config.temperature,
                "max_tokens": config.llm_config.max_tokens,
                "seed": config.llm_config.seed
            },
            "prompts_available": list(config.prompts.keys()),
            "multi_round_enabled": config.multi_round_config.get("enabled", False)
        }


# Global instance
prompt_manager = SimplePromptManager()
