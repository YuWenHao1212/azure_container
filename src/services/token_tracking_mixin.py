"""
Token tracking mixin for OpenAI API calls.
Provides a reusable way to track token usage across services.
"""
from typing import Any

from src.core.monitoring_service import monitoring_service


class TokenTrackingMixin:
    """Mixin to add token tracking capabilities to services using OpenAI."""
    
    def track_openai_usage(
        self,
        response: dict[str, Any],
        operation: str,
        additional_properties: dict[str, Any] | None = None
    ) -> dict[str, int]:
        """
        Track OpenAI token usage from API response.
        
        Args:
            response: OpenAI API response containing usage data
            operation: Name of the operation (e.g., "gap_analysis", "keyword_extraction")
            additional_properties: Additional properties to track
            
        Returns:
            Dictionary with token usage statistics
        """
        usage = response.get("usage", {})
        token_info = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
        
        # Build tracking properties
        properties = {
            "operation": operation,
            "prompt_tokens": token_info["prompt_tokens"],
            "completion_tokens": token_info["completion_tokens"],
            "total_tokens": token_info["total_tokens"],
            "model": response.get("model", "unknown"),
            "finish_reason": response.get("choices", [{}])[0].get("finish_reason", "unknown")
        }
        
        # Add any additional properties
        if additional_properties:
            properties.update(additional_properties)
        
        # Track the event
        monitoring_service.track_event("OpenAITokenUsage", properties)
        
        # Also track as a metric for aggregation
        monitoring_service.track_metric(
            "openai_tokens_used",
            token_info["total_tokens"],
            {"operation": operation}
        )
        
        return token_info
    
    def estimate_token_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4o-2"
    ) -> float:
        """
        Estimate cost based on token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Model name for pricing
            
        Returns:
            Estimated cost in USD
        """
        # Pricing per 1K tokens (adjust based on actual Azure pricing)
        pricing = {
            "gpt-4o-2": {
                "prompt": 0.01,      # $0.01 per 1K prompt tokens
                "completion": 0.03   # $0.03 per 1K completion tokens
            },
            "text-embedding-3-large": {
                "prompt": 0.00013,   # $0.00013 per 1K tokens
                "completion": 0      # No completion for embeddings
            }
        }
        
        model_pricing = pricing.get(model, pricing["gpt-4o-2"])
        
        prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * model_pricing["completion"]
        
        return round(prompt_cost + completion_cost, 6)