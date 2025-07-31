"""
Simplified prompt configuration models for LLM prompt management.
No template engine required - just basic configuration.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM parameters configuration."""
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, description="Maximum tokens to generate")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 0.0,
                "max_tokens": 400,
                "seed": 42,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
        }


class PromptMetadata(BaseModel):
    """Simple metadata for prompt versions."""
    author: str = Field(default="system", description="Author of the prompt")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Creation timestamp")
    description: str = Field(default="", description="Description of this version")
    status: str = Field(default="active", description="Status: active, testing, deprecated")


class PromptConfig(BaseModel):
    """Complete prompt configuration for a specific version."""
    version: str = Field(description="Semantic version (e.g., 1.0.0)")
    metadata: PromptMetadata = Field(default_factory=PromptMetadata, description="Version metadata")
    llm_config: LLMConfig = Field(default_factory=LLMConfig, description="LLM parameters")
    prompts: dict[str, str] = Field(
        default_factory=dict,
        description="Prompt texts - typically 'system' and 'user'"
    )
    multi_round_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for multi-round extraction"
    )

    def get_system_prompt(self) -> str:
        """Get system prompt with fallback."""
        return self.prompts.get("system", "")

    def get_user_prompt(self) -> str:
        """Get user prompt with fallback."""
        return self.prompts.get("user", "")

    def format_user_prompt(self, **kwargs) -> str:
        """Simple string formatting for user prompt."""
        user_prompt = self.get_user_prompt()
        try:
            return user_prompt.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable in prompt: {e}")

    class Config:
        json_schema_extra = {
            "example": {
                "version": "1.0.0",
                "metadata": {
                    "author": "Claude Code",
                    "description": "Standard keyword extraction prompt",
                    "status": "active"
                },
                "llm_config": {
                    "temperature": 0.0,
                    "max_tokens": 400,
                    "seed": 42
                },
                "prompts": {
                    "system": "You are an expert at extracting keywords...",
                    "user": "Extract keywords from: {job_description}"
                },
                "multi_round_config": {
                    "enabled": True,
                    "round1_seed": 42,
                    "round2_seed": 43
                }
            }
        }
