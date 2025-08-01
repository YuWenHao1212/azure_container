"""
Monitoring configuration with environment-aware defaults.
Automatically selects appropriate storage mode based on environment.
"""
import os
import tempfile
from enum import Enum

from pydantic import validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environments"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageMode(str, Enum):
    """Error storage modes"""
    MEMORY = "memory"
    DISK = "disk"
    BLOB = "blob"


class MonitoringConfig(BaseSettings):
    """
    Monitoring configuration with smart defaults.
    Automatically configures based on environment.
    """

    # Environment detection
    environment: Environment = Environment.LOCAL
    is_container_app: bool = False
    is_azure_function: bool = False

    # Monitoring toggles
    monitoring_enabled: bool = False  # Heavy Application Insights
    lightweight_monitoring: bool = True
    error_capture_enabled: bool = True

    # Error storage configuration
    error_storage_mode: StorageMode | None = None  # Auto-detect if not set
    max_memory_errors: int = 100
    error_retention_hours: int = 24
    max_capture_body_size: int = 10240  # 10KB
    capture_success_samples: bool = False

    # Storage paths
    # S108: Use proper temp directory functions instead of hardcoded paths
    error_log_path: str = os.path.join(tempfile.gettempdir(), "api_errors")
    error_blob_container: str = "api-errors"

    # Azure Storage (for blob mode)
    azure_storage_connection_string: str | None = None
    azure_storage_account_name: str | None = None
    azure_storage_account_key: str | None = None

    # Performance thresholds
    slow_request_threshold_ms: int = 2000
    error_threshold_4xx: int = 50
    error_threshold_5xx: int = 10
    stats_interval_seconds: int = 300

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env file

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Auto-detect environment
        self._detect_environment()

        # Auto-configure storage mode if not explicitly set
        if self.error_storage_mode is None:
            self.error_storage_mode = self._auto_select_storage_mode()

        # Validate configuration
        self._validate_storage_config()

    def _detect_environment(self):
        """Detect the running environment"""
        # Check if running in Container Apps
        if os.getenv("CONTAINER_APP_NAME"):
            self.is_container_app = True

        # Check if running in Azure Functions
        if os.getenv("FUNCTIONS_WORKER_RUNTIME"):
            self.is_azure_function = True

        # Determine environment from various sources
        env_indicators = {
            # Container Apps environments
            "CONTAINER_APP_ENV_NAME": {
                "dev": Environment.DEVELOPMENT,
                "staging": Environment.STAGING,
                "prod": Environment.PRODUCTION,
                "production": Environment.PRODUCTION
            },
            # Generic environment variable
            "ENVIRONMENT": {
                "local": Environment.LOCAL,
                "dev": Environment.DEVELOPMENT,
                "development": Environment.DEVELOPMENT,
                "staging": Environment.STAGING,
                "prod": Environment.PRODUCTION,
                "production": Environment.PRODUCTION
            },
            # Azure-specific
            "ASPNETCORE_ENVIRONMENT": {
                "Development": Environment.DEVELOPMENT,
                "Staging": Environment.STAGING,
                "Production": Environment.PRODUCTION
            }
        }

        for env_var, mappings in env_indicators.items():
            value = os.getenv(env_var, "").lower()
            if value in mappings:
                self.environment = mappings[value]
                break

    def _auto_select_storage_mode(self) -> StorageMode:
        """
        Automatically select storage mode based on environment.

        Decision matrix:
        - Local development: Memory (fast debugging)
        - Container Apps Development: Disk (persistent across requests)
        - Container Apps Staging: Disk or Blob (based on connection string)
        - Container Apps Production: Blob (scalable, permanent)
        - Azure Functions: Memory (stateless)
        """
        # Azure Functions should use memory (stateless)
        if self.is_azure_function:
            return StorageMode.MEMORY

        # Production environment
        if self.environment == Environment.PRODUCTION:
            # Use blob if connection string is available
            if self._has_blob_storage_config():
                return StorageMode.BLOB
            else:
                # Fallback to disk with warning
                import logging
                logging.warning(
                    "Production environment without blob storage configured. "
                    "Consider setting AZURE_STORAGE_CONNECTION_STRING for better scalability."
                )
                return StorageMode.DISK

        # Staging environment
        if self.environment == Environment.STAGING:
            # Prefer blob if available, otherwise disk
            if self._has_blob_storage_config():
                return StorageMode.BLOB
            return StorageMode.DISK

        # Development on Container Apps
        if self.environment == Environment.DEVELOPMENT and self.is_container_app:
            return StorageMode.DISK

        # Local development
        return StorageMode.MEMORY

    def _has_blob_storage_config(self) -> bool:
        """Check if blob storage is properly configured"""
        return bool(
            self.azure_storage_connection_string or
            (self.azure_storage_account_name and self.azure_storage_account_key)
        )

    def _validate_storage_config(self):
        """Validate storage configuration"""
        if self.error_storage_mode == StorageMode.BLOB and not self._has_blob_storage_config():
            raise ValueError(
                "Blob storage mode requires either "
                "AZURE_STORAGE_CONNECTION_STRING or "
                "AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY"
            )

        # Adjust retention based on environment
        if self.environment == Environment.PRODUCTION:
            # Production: keep errors longer
            if self.error_retention_hours < 168:  # 7 days
                self.error_retention_hours = 168
        elif self.environment == Environment.LOCAL and self.error_retention_hours > 24:
            # Local: shorter retention
            self.error_retention_hours = 24

    def get_storage_info(self) -> dict:
        """Get human-readable storage configuration"""
        return {
            "environment": self.environment.value,
            "is_container_app": self.is_container_app,
            "is_azure_function": self.is_azure_function,
            "storage_mode": self.error_storage_mode.value,
            "storage_location": self._get_storage_location(),
            "retention_hours": self.error_retention_hours,
            "auto_selected": os.getenv("ERROR_STORAGE_MODE") is None
        }

    def _get_storage_location(self) -> str:
        """Get the actual storage location"""
        if self.error_storage_mode == StorageMode.MEMORY:
            return f"In-memory (last {self.max_memory_errors} errors)"
        elif self.error_storage_mode == StorageMode.DISK:
            return self.error_log_path
        elif self.error_storage_mode == StorageMode.BLOB:
            if self.azure_storage_account_name:
                return f"{self.azure_storage_account_name}/{self.error_blob_container}"
            return f"Azure Blob Storage/{self.error_blob_container}"
        return "Unknown"

    @validator("error_retention_hours")
    def validate_retention(cls, v, values):
        """Ensure reasonable retention periods"""
        environment = values.get("environment", Environment.LOCAL)

        # Set maximum retention based on environment
        max_retention = {
            Environment.LOCAL: 24,      # 1 day
            Environment.DEVELOPMENT: 168,  # 7 days
            Environment.STAGING: 720,   # 30 days
            Environment.PRODUCTION: 2160  # 90 days
        }

        max_hours = max_retention.get(environment, 168)
        if v > max_hours:
            return max_hours

        return v


# Global configuration instance
monitoring_config = MonitoringConfig()


def get_monitoring_config() -> MonitoringConfig:
    """Get the monitoring configuration instance"""
    return monitoring_config


# Convenience functions
def is_production() -> bool:
    """Check if running in production"""
    return monitoring_config.environment == Environment.PRODUCTION


def is_development() -> bool:
    """Check if running in development"""
    return monitoring_config.environment in [Environment.LOCAL, Environment.DEVELOPMENT]


def should_capture_errors() -> bool:
    """Check if error capture is enabled"""
    return monitoring_config.error_capture_enabled


def get_storage_mode() -> StorageMode:
    """Get the configured storage mode"""
    return monitoring_config.error_storage_mode
