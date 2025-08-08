"""
Feature Flags Management for Azure Container API.

Provides centralized feature flag management for gradual V2 rollout.
"""
import hashlib
import os
from typing import Optional


class FeatureFlags:
    """
    Feature flags for controlling V2 implementation rollout.

    Supports both full enable/disable and percentage-based rollout.
    """

    # Main feature flag - from environment variable
    USE_V2_IMPLEMENTATION = os.getenv("USE_V2_IMPLEMENTATION", "true").lower() == "true"

    # Percentage-based rollout (0-100)
    V2_ROLLOUT_PERCENTAGE = int(os.getenv("V2_ROLLOUT_PERCENTAGE", "0"))

    # Resource pool configuration
    RESOURCE_POOL_MIN_SIZE = int(os.getenv("RESOURCE_POOL_MIN_SIZE", "2"))
    RESOURCE_POOL_MAX_SIZE = int(os.getenv("RESOURCE_POOL_MAX_SIZE", "10"))
    RESOURCE_POOL_IDLE_TIMEOUT = int(os.getenv("RESOURCE_POOL_IDLE_TIMEOUT", "300"))

    # Retry configuration
    ADAPTIVE_RETRY_ENABLED = os.getenv("ADAPTIVE_RETRY_ENABLED", "true").lower() == "true"
    MAX_RETRY_DELAY_SECONDS = int(os.getenv("MAX_RETRY_DELAY_SECONDS", "20"))

    # Partial results support
    ENABLE_PARTIAL_RESULTS = os.getenv("ENABLE_PARTIAL_RESULTS", "false").lower() == "true"

    @classmethod
    def should_use_v2(cls, user_id: Optional[str] = None) -> bool:
        """
        Determine whether to use V2 implementation.

        Args:
            user_id: Optional user identifier for stable rollout assignment

        Returns:
            True if V2 should be used, False for V1
        """
        # If explicitly enabled, always use V2
        if cls.USE_V2_IMPLEMENTATION:
            return True

        # If percentage rollout is configured and user_id provided
        if cls.V2_ROLLOUT_PERCENTAGE > 0 and user_id:
            # Use hash of user_id for stable assignment
            # Use SHA256 for better security (first 8 chars for consistent distribution)
            hash_value = int(hashlib.sha256(user_id.encode()).hexdigest()[:8], 16)
            return (hash_value % 100) < cls.V2_ROLLOUT_PERCENTAGE

        # Default to V1
        return False

    @classmethod
    def get_resource_pool_config(cls) -> dict:
        """Get resource pool configuration from environment variables."""
        return {
            "min_pool_size": cls.RESOURCE_POOL_MIN_SIZE,
            "max_pool_size": cls.RESOURCE_POOL_MAX_SIZE,
            "idle_timeout": cls.RESOURCE_POOL_IDLE_TIMEOUT
        }

    @classmethod
    def get_all_flags(cls) -> dict:
        """Get all feature flags for debugging/monitoring."""
        return {
            "use_v2_implementation": cls.USE_V2_IMPLEMENTATION,
            "v2_rollout_percentage": cls.V2_ROLLOUT_PERCENTAGE,
            "resource_pool_config": cls.get_resource_pool_config(),
            "adaptive_retry_enabled": cls.ADAPTIVE_RETRY_ENABLED,
            "max_retry_delay_seconds": cls.MAX_RETRY_DELAY_SECONDS,
            "enable_partial_results": cls.ENABLE_PARTIAL_RESULTS
        }
