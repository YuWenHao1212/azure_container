"""
Services package for Azure FastAPI application.
Contains all business logic services.
"""

# Import key services for easier access
from .keyword_extraction import KeywordExtractionService
from .keyword_extraction_v2 import KeywordExtractionServiceV2
from .openai_client import AzureOpenAIClient
from .resource_pool_manager import ResourcePoolManager
from .unified_prompt_service import UnifiedPromptService

__all__ = [
    'AzureOpenAIClient',
    'KeywordExtractionService',
    'KeywordExtractionServiceV2',
    'ResourcePoolManager',
    'UnifiedPromptService'
]
