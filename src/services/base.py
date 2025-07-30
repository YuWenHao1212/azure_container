"""
Base service class for FHS architecture.
All services should inherit from this base class.
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class BaseService(ABC):
    """Abstract base class for all services."""
    
    def __init__(self, logger: logging.Logger | None = None):
        """Initialize base service with optional logger."""
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._start_time = None
    
    def _start_timer(self):
        """Start timing for performance measurement."""
        self._start_time = datetime.now()
    
    def _get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self._start_time:
            elapsed = datetime.now() - self._start_time
            return int(elapsed.total_seconds() * 1000)
        return 0
    
    def _log_info(self, message: str, **kwargs):
        """Log info message with optional context."""
        self.logger.info(message, extra=kwargs)
    
    def _log_error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with optional exception."""
        if error:
            self.logger.error(f"{message}: {str(error)}", exc_info=True, extra=kwargs)
        else:
            self.logger.error(message, extra=kwargs)
    
    def _log_warning(self, message: str, **kwargs):
        """Log warning message with optional context."""
        self.logger.warning(message, extra=kwargs)
    
    @abstractmethod
    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate input data. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process the main business logic. Must be implemented by subclasses."""
        pass
    
    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Execute service with validation and error handling."""
        try:
            self._start_timer()
            
            # Validate input
            validated_data = await self.validate_input(data)
            
            # Process business logic
            result = await self.process(validated_data)
            
            # Add processing time
            result['processing_time_ms'] = self._get_elapsed_ms()
            
            return result
            
        except Exception as e:
            self._log_error("Service execution failed", error=e)
            raise
