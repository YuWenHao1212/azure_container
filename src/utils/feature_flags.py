"""
Feature Flags Management for Azure Container API.

Provides centralized feature flag management for application configuration.
"""
import os


class FeatureFlags:
    """
    Feature flags for controlling application behavior.

    Simplified after V1 removal - V2 is now the only implementation.
    """

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
            "resource_pool_config": cls.get_resource_pool_config(),
            "adaptive_retry_enabled": cls.ADAPTIVE_RETRY_ENABLED,
            "max_retry_delay_seconds": cls.MAX_RETRY_DELAY_SECONDS,
            "enable_partial_results": cls.ENABLE_PARTIAL_RESULTS
        }
