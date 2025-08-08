"""
Services package for Azure FastAPI application.
Contains all business logic services.

CLEANUP HISTORY:
- 2025-08-08: Removed KeywordExtractionService (V1) - only V2 exported
  Reason: V1 no longer used by API endpoints, only V2 implementation needed
"""

# Import key services for easier access
from .keyword_extraction_v2 import KeywordExtractionServiceV2
from .openai_client import AzureOpenAIClient
from .unified_prompt_service import UnifiedPromptService

__all__ = [
    'AzureOpenAIClient',
    'KeywordExtractionServiceV2',
    'UnifiedPromptService'
]
