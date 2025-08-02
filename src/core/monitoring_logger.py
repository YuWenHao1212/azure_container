"""
Monitoring logger configuration with dual output support.
Supports both local file logging and Azure stdout logging based on environment variables.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class MonitoringLoggerSetup:
    """Setup monitoring logger with dual output support."""

    _initialized = False
    _logger: Optional[logging.Logger] = None

    @classmethod
    def setup_business_logger(cls) -> logging.Logger:
        """
        Setup business events logger with dual output support.

        Returns:
            logging.Logger: Configured business events logger
        """
        if cls._initialized and cls._logger:
            return cls._logger

        # Re-create settings to get latest environment variables
        from src.core.config import Settings
        settings = Settings()

        logger = logging.getLogger("business_events")

        # Clear any existing handlers
        logger.handlers.clear()
        logger.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Local file logging (if MONITORING_LOG_FILE is set)
        if settings.monitoring_log_file:
            cls._setup_file_handler(logger, formatter, settings)

        # Always add console handler for Azure Container Apps auto-collection
        cls._setup_console_handler(logger, formatter)

        # Prevent propagation to root logger
        logger.propagate = False

        cls._logger = logger
        cls._initialized = True

        # Log initialization
        logger.info(
            f"Monitoring logger initialized - "
            f"File: {'Yes (' + settings.monitoring_log_file + ')' if settings.monitoring_log_file else 'No'}, "
            f"Console: Yes (Azure auto-collect)"
        )

        return logger

    @classmethod
    def _setup_file_handler(
        cls,
        logger: logging.Logger,
        formatter: logging.Formatter,
        settings
    ) -> None:
        """Setup rotating file handler for local development."""
        try:
            # Create logs directory if it doesn't exist
            log_path = Path(settings.monitoring_log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create rotating file handler
            max_bytes = settings.monitoring_log_max_size * 1024 * 1024  # Convert MB to bytes
            file_handler = RotatingFileHandler(
                filename=str(log_path),
                maxBytes=max_bytes,
                backupCount=settings.monitoring_log_backup_count,
                encoding='utf-8'
            )

            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)

        except Exception as e:
            # If file logging fails, continue with console only
            print(f"Warning: Failed to setup file logging: {e}")

    @classmethod
    def _setup_console_handler(
        cls,
        logger: logging.Logger,
        formatter: logging.Formatter
    ) -> None:
        """Setup console handler for Azure Container Apps auto-collection."""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the configured business events logger."""
        if not cls._initialized:
            return cls.setup_business_logger()
        return cls._logger


def get_business_logger() -> logging.Logger:
    """
    Get the configured business events logger.

    This function provides a simple interface to get the monitoring logger
    with proper dual output configuration.

    Returns:
        logging.Logger: Configured business events logger
    """
    return MonitoringLoggerSetup.get_logger()


# Backwards compatibility - create the logger instance
business_logger = get_business_logger()
