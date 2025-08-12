"""Decorators module for Azure Container API."""

from src.decorators.error_handler import handle_api_errors, handle_sync_api_errors

__all__ = ["handle_api_errors", "handle_sync_api_errors"]
