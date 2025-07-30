"""
Dependency injection for FastAPI application.
Provides singleton instances of heavy resources to avoid reloading on each request.
"""

import logging
from functools import lru_cache

from src.services.keyword_standardizer import KeywordStandardizer
from src.services.standardization.en_standardizer import EnglishStandardizer
from src.services.standardization.multilingual_standardizer import (
    MultilingualStandardizer,
)
from src.services.standardization.zh_tw_standardizer import (
    TraditionalChineseStandardizer,
)
from src.services.unified_prompt_service import UnifiedPromptService
from src.services.unified_prompt_service import (
    get_unified_prompt_service as get_prompt_service_instance,
)

logger = logging.getLogger(__name__)

# Global instances (initialized at startup)
_keyword_standardizer: KeywordStandardizer | None = None
_multilingual_standardizer: MultilingualStandardizer | None = None
_english_standardizer: EnglishStandardizer | None = None
_chinese_standardizer: TraditionalChineseStandardizer | None = None
_unified_prompt_service: UnifiedPromptService | None = None


def initialize_dependencies():
    """
    Initialize all heavy dependencies at application startup.
    This function should be called in the FastAPI startup event.
    """
    global _keyword_standardizer, _multilingual_standardizer
    global _english_standardizer, _chinese_standardizer
    global _unified_prompt_service
    
    logger.info("Initializing application dependencies...")
    
    # Initialize KeywordStandardizer (loads YAML files)
    logger.info("Loading keyword standardizer dictionaries...")
    _keyword_standardizer = KeywordStandardizer()
    logger.info(f"  ✓ Loaded {len(_keyword_standardizer.skill_dictionary)} skills")
    logger.info(f"  ✓ Loaded {len(_keyword_standardizer.position_dictionary)} positions")
    logger.info(f"  ✓ Loaded {len(_keyword_standardizer.tool_dictionary)} tools")
    logger.info(f"  ✓ Loaded {len(_keyword_standardizer.patterns)} patterns")
    
    # Initialize language-specific standardizers
    logger.info("Loading language-specific standardizers...")
    _english_standardizer = EnglishStandardizer()
    _chinese_standardizer = TraditionalChineseStandardizer()
    _multilingual_standardizer = MultilingualStandardizer()
    logger.info("  ✓ English, Chinese, and Multilingual standardizers loaded")
    
    # Initialize UnifiedPromptService (use existing singleton)
    logger.info("Loading unified prompt service...")
    _unified_prompt_service = get_prompt_service_instance()
    logger.info(f"  ✓ Prompt service loaded with languages: {_unified_prompt_service.SUPPORTED_LANGUAGES}")
    
    logger.info("✅ All dependencies initialized successfully!")


# Dependency injection functions for FastAPI
@lru_cache
def get_keyword_standardizer() -> KeywordStandardizer:
    """Get the singleton KeywordStandardizer instance."""
    if _keyword_standardizer is None:
        raise RuntimeError("KeywordStandardizer not initialized. Call initialize_dependencies() first.")
    return _keyword_standardizer


@lru_cache
def get_multilingual_standardizer() -> MultilingualStandardizer:
    """Get the singleton MultilingualStandardizer instance."""
    if _multilingual_standardizer is None:
        raise RuntimeError("MultilingualStandardizer not initialized. Call initialize_dependencies() first.")
    return _multilingual_standardizer


@lru_cache
def get_english_standardizer() -> EnglishStandardizer:
    """Get the singleton EnglishStandardizer instance."""
    if _english_standardizer is None:
        raise RuntimeError("EnglishStandardizer not initialized. Call initialize_dependencies() first.")
    return _english_standardizer


@lru_cache
def get_chinese_standardizer() -> TraditionalChineseStandardizer:
    """Get the singleton TraditionalChineseStandardizer instance."""
    if _chinese_standardizer is None:
        raise RuntimeError("TraditionalChineseStandardizer not initialized. Call initialize_dependencies() first.")
    return _chinese_standardizer


@lru_cache
def get_unified_prompt_service() -> UnifiedPromptService:
    """Get the singleton UnifiedPromptService instance."""
    if _unified_prompt_service is None:
        raise RuntimeError("UnifiedPromptService not initialized. Call initialize_dependencies() first.")
    return _unified_prompt_service


# For backward compatibility - direct access to instances
def get_dependencies():
    """Get all initialized dependencies as a dictionary."""
    return {
        "keyword_standardizer": _keyword_standardizer,
        "multilingual_standardizer": _multilingual_standardizer,
        "english_standardizer": _english_standardizer,
        "chinese_standardizer": _chinese_standardizer,
        "unified_prompt_service": _unified_prompt_service
    }