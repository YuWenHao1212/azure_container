"""
LLM Client Factory for dynamic model selection.
Enables switching between different LLM models based on configuration.

Implements the hybrid approach with multiple selection strategies:
1. Request parameter (highest priority)
2. HTTP Header
3. Environment variable configuration
4. Default value
"""
import logging
from typing import Literal

from src.core.config import get_settings
from src.core.monitoring_service import monitoring_service
from src.services.openai_client import AzureOpenAIClient
from src.services.openai_client_gpt41 import (
    AzureOpenAIGPT41Client,
    get_gpt41_mini_client,
)

# Type definitions
LLMModel = Literal["gpt4o-2", "gpt41-mini"]
LLMClient = AzureOpenAIClient | AzureOpenAIGPT41Client
ModelSource = Literal["request", "header", "config", "default"]

# Model to Azure deployment name mapping
DEPLOYMENT_MAP = {
    "gpt4o-2": "gpt-4.1-japan",
    "gpt41-mini": "gpt-4-1-mini-japaneast"
}

logger = logging.getLogger(__name__)


def get_llm_client(
    model: LLMModel = None,
    api_name: str | None = None
) -> LLMClient:
    """
    Get LLM client with dynamic model selection (Basic version).

    Args:
        model: Direct model specification ("gpt4o-2" or "gpt41-mini")
        api_name: API name for environment-based configuration
                  (e.g., "keywords", "gap_analysis", "resume_format")

    Returns:
        LLM client instance (AzureOpenAIClient or AzureOpenAIGPT41Client)

    Priority:
        1. Direct model parameter
        2. Environment variable (LLM_MODEL_{API_NAME})
        3. Default model from settings
    """
    settings = get_settings()

    # Determine which model to use
    if model:
        # Direct specification takes priority
        selected_model = model
        source = "request"
        logger.info(f"Using directly specified model: {selected_model}")
    elif api_name:
        # Check for API-specific configuration
        # e.g., LLM_MODEL_KEYWORDS, LLM_MODEL_GAP_ANALYSIS
        env_key = f"llm_model_{api_name.lower()}"
        selected_model = getattr(settings, env_key, None)

        if selected_model:
            source = "config"
            logger.info(f"Using model from env for {api_name}: {selected_model}")
        else:
            # Fallback to default
            selected_model = getattr(settings, "llm_model_default", "gpt4o-2")
            source = "default"
            logger.info(f"No specific model for {api_name}, using default: {selected_model}")
    else:
        # Use default model
        selected_model = getattr(settings, "llm_model_default", "gpt4o-2")
        source = "default"
        logger.info(f"Using default model: {selected_model}")

    # Track model selection
    _track_model_selection(api_name, selected_model, source)

    # Create and return appropriate client
    return _create_client(selected_model)


def get_llm_client_smart(
    api_name: str,
    request_model: str | None = None,
    headers: dict[str, str] | None = None
) -> LLMClient:
    """
    Get LLM client with smart model selection (Hybrid approach).

    This is the full hybrid implementation with multiple selection strategies.

    Args:
        api_name: API name (required for tracking and config lookup)
        request_model: Model specified in request (highest priority)
        headers: HTTP headers (may contain X-LLM-Model)

    Returns:
        LLM client instance

    Priority:
        1. Request parameter
        2. HTTP Header (X-LLM-Model)
        3. Environment variable configuration
        4. Default model
    """
    settings = get_settings()
    selected_model = None
    source: ModelSource = "default"

    # 1. Request parameter has highest priority
    if request_model and getattr(settings, "enable_llm_model_override", True):
        selected_model = request_model
        source = "request"
        logger.info(f"Using model from request parameter: {selected_model}")

    # 2. HTTP Header is second priority
    elif headers and getattr(settings, "enable_llm_model_header", True):
        header_model = headers.get("X-LLM-Model")
        if header_model and header_model in ["gpt4o-2", "gpt41-mini"]:
            selected_model = header_model
            source = "header"
            logger.info(f"Using model from HTTP header: {selected_model}")

    # 3. Environment variable configuration
    if not selected_model:
        env_key = f"llm_model_{api_name.lower()}"
        config_model = getattr(settings, env_key, None)
        if config_model:
            selected_model = config_model
            source = "config"
            logger.info(f"Using model from config for {api_name}: {selected_model}")

    # 4. Default fallback
    if not selected_model:
        selected_model = getattr(settings, "llm_model_default", "gpt4o-2")
        source = "default"
        logger.info(f"Using default model: {selected_model}")

    # Track model selection with source
    _track_model_selection(api_name, selected_model, source)

    # Create and return client
    return _create_client(selected_model)


def _create_client(model: str) -> LLMClient:
    """
    Create LLM client instance based on model name.

    Args:
        model: Model identifier

    Returns:
        LLM client instance
    """
    if model == "gpt41-mini":
        try:
            client = get_gpt41_mini_client()
            logger.info("Successfully created GPT-4.1 mini client")
            return client
        except Exception as e:
            logger.warning(
                f"Failed to create GPT-4.1 mini client: {e}. "
                "Falling back to GPT-4o-2"
            )
            # Fallback to GPT-4o-2 using LLM Factory pattern
            # Use the correct deployment mapping from DEPLOYMENT_MAP
            deployment_name = DEPLOYMENT_MAP.get("gpt4o-2", "gpt-4.1-japan")
            # Use the proper Azure OpenAI client creation following LLM Factory pattern
            import os

            from src.services.openai_client import AzureOpenAIClient

            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")

            if not endpoint or not api_key:
                raise ValueError("Missing Azure OpenAI credentials")

            return AzureOpenAIClient(
                endpoint=endpoint,
                api_key=api_key,
                deployment_name=deployment_name
            )
    else:
        # Default to GPT-4o-2 with correct deployment name using LLM Factory pattern
        deployment_name = DEPLOYMENT_MAP.get(model, "gpt-4.1-japan")
        logger.info(f"Creating {model} client with deployment: {deployment_name}")

        # Use proper Azure OpenAI client creation following LLM Factory pattern
        import os

        from src.services.openai_client import AzureOpenAIClient

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if not endpoint or not api_key:
            raise ValueError("Missing Azure OpenAI credentials")

        return AzureOpenAIClient(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=deployment_name
        )


def _track_model_selection(
    api_name: str | None,
    model: str,
    source: ModelSource
) -> None:
    """
    Track model selection for monitoring and analytics.

    Args:
        api_name: Name of the API using the model
        model: Selected model name
        source: Source of the selection (request/header/config/default)
    """
    try:
        monitoring_service.track_event(
            "LLMModelSelected",
            {
                "api_name": api_name or "unknown",
                "model": model,
                "source": source
            }
        )
    except Exception as e:
        logger.warning(f"Failed to track model selection: {e}")


def get_llm_info(client: LLMClient) -> dict:
    """
    Get information about the LLM client.

    Args:
        client: LLM client instance

    Returns:
        Dictionary with client information
    """
    if isinstance(client, AzureOpenAIGPT41Client):
        return {
            "model": "gpt41-mini",
            "deployment": client.deployment_name,
            "endpoint": client.endpoint,
            "region": "japaneast",
            "type": "AzureOpenAIGPT41Client"
        }
    else:
        # AzureOpenAIClient
        settings = get_settings()
        return {
            "model": "gpt4o-2",
            "deployment": "gpt-4o-2",
            "endpoint": settings.azure_openai_endpoint,
            "region": "swedencentral",
            "type": "AzureOpenAIClient"
        }


# Model cost information (per 1K tokens)
MODEL_COSTS = {
    "gpt4o-2": {
        "input": 0.01,      # $0.01 per 1K input tokens
        "output": 0.03      # $0.03 per 1K output tokens
    },
    "gpt41-mini": {
        "input": 0.00015,   # $0.00015 per 1K input tokens
        "output": 0.0006    # $0.0006 per 1K output tokens
    }
}


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> dict:
    """
    Estimate the cost of using a specific model.

    Args:
        model: Model name ("gpt4o-2" or "gpt41-mini")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Dictionary with cost breakdown
    """
    if model not in MODEL_COSTS:
        return {
            "error": f"Unknown model: {model}",
            "input_cost": 0,
            "output_cost": 0,
            "total_cost": 0
        }

    costs = MODEL_COSTS[model]
    input_cost = (input_tokens / 1000) * costs["input"]
    output_cost = (output_tokens / 1000) * costs["output"]

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost, 6),
        "cost_per_1k_input": costs["input"],
        "cost_per_1k_output": costs["output"]
    }
