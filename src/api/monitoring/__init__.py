"""
Monitoring API endpoints for lightweight error tracking and performance monitoring.
"""

from .error_dashboard import router as error_dashboard_router

__all__ = ["error_dashboard_router"]
