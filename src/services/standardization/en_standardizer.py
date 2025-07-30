"""
English keyword standardizer using the legacy KeywordStandardizer.
This wraps the existing standardizer to fit the multilingual interface.
"""

import logging

from ..keyword_standardizer import KeywordStandardizer
from .base_standardizer import BaseStandardizer, StandardizationResult

logger = logging.getLogger(__name__)


class EnglishStandardizer(BaseStandardizer):
    """
    English keyword standardizer that uses the legacy KeywordStandardizer.
    
    This provides access to 581 standardization mappings:
    - 250 skill mappings
    - 95 position mappings  
    - 170 tool mappings
    - 66 pattern rules
    """
    
    def __init__(self):
        """Initialize the English standardizer with legacy standardizer."""
        super().__init__()
        self.legacy_standardizer = KeywordStandardizer()
        logger.info("Initialized EnglishStandardizer with legacy KeywordStandardizer")
    
    def _load_config(self) -> dict:
        """Load configuration (not used for English, returns empty dict)."""
        return {}
    
    def get_supported_language(self) -> str:
        """Get the supported language code."""
        return "en"
    
    def standardize_keywords(self, keywords: list[str]) -> StandardizationResult:
        """
        Standardize English keywords using the legacy standardizer.
        
        Args:
            keywords: List of keywords to standardize
            
        Returns:
            StandardizationResult with standardized keywords and mappings
        """
        if not keywords:
            return StandardizationResult([], [])
        
        # Use the legacy standardizer
        standardized_keywords, mappings = self.legacy_standardizer.standardize_keywords(keywords)
        
        # Convert to our format
        formatted_mappings = []
        for mapping in mappings:
            formatted_mappings.append({
                'original': mapping['original'],
                'standardized': mapping['standardized'],
                'method': mapping['method']
            })
        
        logger.debug(f"Standardized {len(keywords)} English keywords, {len(mappings)} changes made")
        
        return StandardizationResult(
            original_keywords=keywords.copy(),
            standardized_keywords=standardized_keywords,
            mappings=formatted_mappings
        )
    
    def is_standardization_available(self) -> bool:
        """Check if English standardization is available."""
        # Check if legacy standardizer has loaded dictionaries
        return bool(self.legacy_standardizer.combined_dictionary) or bool(self.legacy_standardizer.patterns)
    
    def get_standardization_stats(self) -> dict:
        """Get standardization statistics."""
        stats = {
            "language": "en",
            "available": self.is_standardization_available(),
            "dictionary_entries": len(self.legacy_standardizer.combined_dictionary),
            "pattern_rules": len(self.legacy_standardizer.patterns),
            "skill_mappings": len(self.legacy_standardizer.skill_dictionary),
            "position_mappings": len(self.legacy_standardizer.position_dictionary),
            "tool_mappings": len(self.legacy_standardizer.tool_dictionary),
            "total_mappings": (
                len(self.legacy_standardizer.combined_dictionary) + 
                len(self.legacy_standardizer.patterns)
            )
        }
        
        if not stats["available"]:
            stats["reason"] = "Dictionary files not loaded"
        
        return stats