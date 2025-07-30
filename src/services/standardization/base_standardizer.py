"""
Base standardizer class for keyword standardization.
Provides common functionality for all language-specific standardizers.
"""

import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StandardizationResult:
    """Result of keyword standardization process."""
    
    def __init__(self, 
                 original_keywords: list[str],
                 standardized_keywords: list[str],
                 mappings: list[dict[str, str]] = None,
                 excluded_keywords: list[str] = None):
        self.original_keywords = original_keywords
        self.standardized_keywords = standardized_keywords
        self.mappings = mappings or []
        self.excluded_keywords = excluded_keywords or []
        
    @property
    def standardization_count(self) -> int:
        """Number of keywords that were standardized."""
        return len(self.mappings)
    
    @property
    def exclusion_count(self) -> int:
        """Number of keywords that were excluded."""
        return len(self.excluded_keywords)
    
    @property
    def final_count(self) -> int:
        """Final number of standardized keywords."""
        return len(self.standardized_keywords)
    
    def get_mapping_by_method(self, method: str) -> list[dict[str, str]]:
        """Get mappings by standardization method."""
        return [m for m in self.mappings if m.get('method') == method]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "original_count": len(self.original_keywords),
            "final_count": self.final_count,
            "standardization_count": self.standardization_count,
            "exclusion_count": self.exclusion_count,
            "mappings": self.mappings,
            "excluded_keywords": self.excluded_keywords
        }


class BaseStandardizer(ABC):
    """
    Abstract base class for keyword standardizers.
    Provides common functionality and defines the interface for language-specific standardizers.
    """
    
    def __init__(self, config_path: str | None = None):
        """
        Initialize base standardizer.
        
        Args:
            config_path: Path to standardization configuration file
        """
        self.config_path = config_path
        self.config = None
        self._load_config()
    
    @abstractmethod
    def _load_config(self):
        """Load standardization configuration. Must be implemented by subclasses."""
        pass
    
    @abstractmethod 
    def get_supported_language(self) -> str:
        """Get the language code supported by this standardizer."""
        pass
    
    def standardize_keywords(self, keywords: list[str]) -> StandardizationResult:
        """
        Standardize a list of keywords.
        
        Args:
            keywords: List of keywords to standardize
            
        Returns:
            StandardizationResult with standardized keywords and metadata
        """
        if not keywords:
            return StandardizationResult([], [])
        
        logger.info(f"Starting standardization for {len(keywords)} keywords")
        
        # 1. Clean and normalize input
        cleaned_keywords = self._clean_keywords(keywords)
        
        # 2. Apply exclusion rules
        filtered_keywords, excluded = self._apply_exclusion_rules(cleaned_keywords)
        
        # 3. Apply standardization mappings
        standardized, mappings = self._apply_standardization_mappings(filtered_keywords)
        
        # 4. Apply pattern rules
        final_keywords, pattern_mappings = self._apply_pattern_rules(standardized)
        
        # 5. Remove duplicates while preserving order
        final_keywords = self._remove_duplicates(final_keywords)
        
        # Combine all mappings
        all_mappings = mappings + pattern_mappings
        
        result = StandardizationResult(
            original_keywords=keywords,
            standardized_keywords=final_keywords,
            mappings=all_mappings,
            excluded_keywords=excluded
        )
        
        logger.info(f"Standardization complete: {len(keywords)} -> {len(final_keywords)} keywords")
        return result
    
    def _clean_keywords(self, keywords: list[str]) -> list[str]:
        """
        Clean and normalize keywords.
        
        Args:
            keywords: Raw keywords
            
        Returns:
            Cleaned keywords
        """
        cleaned = []
        for keyword in keywords:
            if not keyword or not isinstance(keyword, str):
                continue
                
            # Strip whitespace
            cleaned_keyword = keyword.strip()
            
            # Skip empty keywords
            if not cleaned_keyword:
                continue
                
            # Basic normalization
            cleaned_keyword = self._normalize_keyword(cleaned_keyword)
            cleaned.append(cleaned_keyword)
        
        return cleaned
    
    def _normalize_keyword(self, keyword: str) -> str:
        """
        Normalize a single keyword. Can be overridden by subclasses.
        
        Args:
            keyword: Keyword to normalize
            
        Returns:
            Normalized keyword
        """
        # Default normalization: strip and collapse whitespace
        return re.sub(r'\s+', ' ', keyword.strip())
    
    def _apply_exclusion_rules(self, keywords: list[str]) -> tuple[list[str], list[str]]:
        """
        Apply exclusion rules to filter out unwanted keywords.
        
        Args:
            keywords: Keywords to filter
            
        Returns:
            Tuple of (filtered_keywords, excluded_keywords)
        """
        if not self.config or 'exclusion_rules' not in self.config:
            return keywords, []
        
        filtered = []
        excluded = []
        
        exclusion_patterns = [
            re.compile(rule['pattern']) 
            for rule in self.config['exclusion_rules']
        ]
        
        for keyword in keywords:
            should_exclude = False
            
            for pattern in exclusion_patterns:
                if pattern.search(keyword):
                    excluded.append(keyword)
                    should_exclude = True
                    break
            
            if not should_exclude:
                filtered.append(keyword)
        
        logger.debug(f"Excluded {len(excluded)} keywords by exclusion rules")
        return filtered, excluded
    
    def _apply_standardization_mappings(self, keywords: list[str]) -> tuple[list[str], list[dict[str, str]]]:
        """
        Apply direct standardization mappings.
        
        Args:
            keywords: Keywords to standardize
            
        Returns:
            Tuple of (standardized_keywords, mappings_applied)
        """
        if not self.config or 'categories' not in self.config:
            return keywords, []
        
        standardized = []
        mappings = []
        
        # Build mapping dictionary from all categories
        mapping_dict = {}
        for _category, category_data in self.config['categories'].items():
            if 'mappings' in category_data:
                mapping_dict.update(category_data['mappings'])
        
        for keyword in keywords:
            if keyword in mapping_dict:
                standardized_term = mapping_dict[keyword]
                standardized.append(standardized_term)
                mappings.append({
                    'original': keyword,
                    'standardized': standardized_term,
                    'method': 'dictionary'
                })
            else:
                standardized.append(keyword)
        
        logger.debug(f"Applied {len(mappings)} dictionary mappings")
        return standardized, mappings
    
    def _apply_pattern_rules(self, keywords: list[str]) -> tuple[list[str], list[dict[str, str]]]:
        """
        Apply pattern-based standardization rules.
        
        Args:
            keywords: Keywords to apply patterns to
            
        Returns:
            Tuple of (standardized_keywords, pattern_mappings)
        """
        if not self.config or 'pattern_rules' not in self.config:
            return keywords, []
        
        standardized = []
        mappings = []
        
        for keyword in keywords:
            original_keyword = keyword
            
            for rule in self.config['pattern_rules']:
                pattern = rule['pattern']
                replacement = rule['replacement']
                
                new_keyword = re.sub(pattern, replacement, keyword)
                if new_keyword != keyword:
                    keyword = new_keyword
                    mappings.append({
                        'original': original_keyword,
                        'standardized': keyword,
                        'method': 'pattern'
                    })
                    break  # Only apply first matching pattern
            
            standardized.append(keyword)
        
        logger.debug(f"Applied {len(mappings)} pattern rules")
        return standardized, mappings
    
    def _remove_duplicates(self, keywords: list[str]) -> list[str]:
        """
        Remove duplicates while preserving order.
        
        Args:
            keywords: Keywords that may contain duplicates
            
        Returns:
            Keywords with duplicates removed
        """
        seen: set[str] = set()
        result = []
        
        for keyword in keywords:
            # Case-sensitive deduplication for now
            # Can be made case-insensitive if needed
            if keyword not in seen:
                seen.add(keyword)
                result.append(keyword)
        
        return result
    
    def is_standardization_available(self) -> bool:
        """
        Check if standardization is available (config loaded successfully).
        
        Returns:
            True if standardization is available
        """
        return self.config is not None
    
    def get_standardization_stats(self) -> dict:
        """
        Get statistics about the standardization configuration.
        
        Returns:
            Dictionary with configuration statistics
        """
        if not self.config:
            return {"available": False}
        
        stats = {
            "available": True,
            "language": self.get_supported_language(),
            "config_version": self.config.get("version", "unknown")
        }
        
        if "categories" in self.config:
            total_mappings = sum(
                len(cat_data.get("mappings", {}))
                for cat_data in self.config["categories"].values()
            )
            stats.update({
                "categories": len(self.config["categories"]),
                "total_mappings": total_mappings
            })
        
        if "pattern_rules" in self.config:
            stats["pattern_rules"] = len(self.config["pattern_rules"])
        
        if "exclusion_rules" in self.config:
            stats["exclusion_rules"] = len(self.config["exclusion_rules"])
        
        return stats