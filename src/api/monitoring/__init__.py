"""
Monitoring API endpoints for lightweight error tracking and performance monitoring.
"""

from .cache_dashboard import router as cache_dashboard_router
from .error_dashboard import router as error_dashboard_router

__all__ = ["error_dashboard_router", "cache_dashboard_router"]
