"""
Keyword Standardization Service

This module provides keyword standardization functionality using both
dictionary mapping and pattern-based rules to normalize technical terms.
All mappings are loaded from external YAML files for easy maintenance.
"""

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class KeywordStandardizer:
    """Service for standardizing keywords using dictionary and pattern rules."""
    
    def __init__(self, data_dir: str | None = None):
        """
        Initialize the standardizer by loading mappings from YAML files.
        
        Args:
            data_dir: Directory containing YAML files. If None, uses default location.
        """
        # Set data directory
        if data_dir is None:
            # Default to src/data/standardization relative to this file
            current_dir = Path(__file__).parent.parent
            self.data_dir = current_dir / "data" / "standardization"
        else:
            self.data_dir = Path(data_dir)
        
        # Load all dictionaries and patterns
        self.skill_dictionary = self._load_yaml_dictionary("skills.yaml")
        self.position_dictionary = self._load_yaml_dictionary("positions.yaml")
        self.tool_dictionary = self._load_yaml_dictionary("tools.yaml")
        self.patterns = self._load_patterns("patterns.yaml")
        
        # Combine all dictionaries for efficient lookup
        self.combined_dictionary = {}
        self.combined_dictionary.update(self.skill_dictionary)
        self.combined_dictionary.update(self.position_dictionary)
        self.combined_dictionary.update(self.tool_dictionary)
        
        logger.info(
            f"Initialized KeywordStandardizer with {len(self.combined_dictionary)} "
            f"dictionary entries and {len(self.patterns)} patterns from {self.data_dir}"
        )
    
    def _load_yaml_dictionary(self, filename: str) -> dict[str, str]:
        """
        Load a dictionary from a YAML file.
        
        Args:
            filename: Name of the YAML file to load
            
        Returns:
            Dictionary mapping original terms to standardized terms
        """
        filepath = self.data_dir / filename
        
        try:
            with open(filepath, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Flatten the nested structure
            dictionary = {}
            if isinstance(data, dict):
                for _category, mappings in data.items():
                    if isinstance(mappings, dict):
                        for original, standardized in mappings.items():
                            # Convert to lowercase for case-insensitive matching
                            dictionary[original.lower()] = standardized
            
            logger.info(f"Loaded {len(dictionary)} entries from {filename}")
            return dictionary
            
        except FileNotFoundError:
            logger.warning(f"Dictionary file not found: {filepath}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filename}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading {filename}: {e}")
            return {}
    
    def _load_patterns(self, filename: str) -> list[tuple[re.Pattern, str, str]]:
        """
        Load pattern rules from a YAML file.
        
        Args:
            filename: Name of the YAML file containing patterns
            
        Returns:
            List of (compiled_pattern, replacement, pattern_type) tuples
        """
        filepath = self.data_dir / filename
        patterns = []
        
        try:
            with open(filepath, encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if isinstance(data, dict):
                for _category, pattern_list in data.items():
                    if isinstance(pattern_list, list):
                        for pattern_info in pattern_list:
                            if isinstance(pattern_info, dict) and 'pattern' in pattern_info:
                                try:
                                    compiled = re.compile(
                                        pattern_info['pattern'], 
                                        re.IGNORECASE
                                    )
                                    replacement = pattern_info.get('replacement', '')
                                    pattern_type = pattern_info.get('type', 'unknown')
                                    patterns.append((compiled, replacement, pattern_type))
                                except re.error as e:
                                    logger.error(
                                        f"Invalid regex pattern '{pattern_info['pattern']}': {e}"
                                    )
            
            logger.info(f"Loaded {len(patterns)} patterns from {filename}")
            return patterns
            
        except FileNotFoundError:
            logger.warning(f"Pattern file not found: {filepath}")
            return []
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filename}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading {filename}: {e}")
            return []
    
    def reload_dictionaries(self):
        """
        Reload all dictionaries and patterns from YAML files.
        Useful for updating mappings without restarting the service.
        """
        logger.info("Reloading all dictionaries and patterns...")
        
        # Reload all components
        self.skill_dictionary = self._load_yaml_dictionary("skills.yaml")
        self.position_dictionary = self._load_yaml_dictionary("positions.yaml")
        self.tool_dictionary = self._load_yaml_dictionary("tools.yaml")
        self.patterns = self._load_patterns("patterns.yaml")
        
        # Rebuild combined dictionary
        self.combined_dictionary = {}
        self.combined_dictionary.update(self.skill_dictionary)
        self.combined_dictionary.update(self.position_dictionary)
        self.combined_dictionary.update(self.tool_dictionary)
        
        logger.info(
            f"Reload complete: {len(self.combined_dictionary)} dictionary entries, "
            f"{len(self.patterns)} patterns"
        )
    
    def standardize_keywords(
        self, 
        keywords: list[str],
        include_details: bool = False
    ) -> tuple[list[str], list[dict[str, str]]]:
        """
        Standardize a list of keywords.
        
        Args:
            keywords: List of keywords to standardize
            include_details: Whether to include standardization details
            
        Returns:
            Tuple of (standardized_keywords, standardization_details)
        """
        standardized_keywords = []
        standardization_details = []
        
        for keyword in keywords:
            standardized, method, category = self._standardize_single(keyword)
            standardized_keywords.append(standardized)
            
            if include_details and standardized != keyword:
                standardization_details.append({
                    "original": keyword,
                    "standardized": standardized,
                    "method": method,
                    "category": category
                })
        
        logger.info(
            f"Standardized {len(keywords)} keywords, "
            f"{len(standardization_details)} were modified"
        )
        
        return standardized_keywords, standardization_details
    
    def standardize(self, keyword: str) -> str:
        """
        Standardize a single keyword (compatibility method for tests).
        
        Args:
            keyword: Keyword to standardize
            
        Returns:
            Standardized keyword
        """
        standardized, _, _ = self._standardize_single(keyword)
        return standardized
    
    def _standardize_single(self, keyword: str) -> tuple[str, str, str]:
        """
        Standardize a single keyword.
        
        Returns:
            Tuple of (standardized_keyword, method, category)
        """
        if not keyword:
            return keyword, "none", "none"
        
        # Step 1: Try exact dictionary match (case-insensitive)
        lower_keyword = keyword.lower().strip()
        if lower_keyword in self.combined_dictionary:
            standardized = self.combined_dictionary[lower_keyword]
            category = self._get_category(lower_keyword)
            return standardized, "dictionary", category
        
        # Step 2: Apply intelligent Title Case for known patterns FIRST
        # This ensures position titles are properly cased before pattern matching
        title_cased_keyword = self._apply_intelligent_title_case(keyword)
        title_case_applied = (title_cased_keyword != keyword)
        
        # Step 3: Apply pattern-based standardization on the title-cased version
        # Skip abbreviation expansion for position titles
        modified_keyword = title_cased_keyword
        pattern_applied = False
        is_position_title = self._is_position_title(keyword)
        
        for pattern, replacement, pattern_type in self.patterns:
            # Skip abbreviation expansion for position titles (keep AI, ML, etc.)
            if is_position_title and pattern_type == 'abbreviation':
                continue
                
            new_keyword = pattern.sub(replacement, modified_keyword)
            if new_keyword != modified_keyword:
                modified_keyword = new_keyword
                pattern_applied = True
                
                # Check if pattern result exists in dictionary
                if modified_keyword.lower() in self.combined_dictionary:
                    standardized = self.combined_dictionary[modified_keyword.lower()]
                    category = self._get_category(modified_keyword.lower())
                    method = "title_case+pattern+dictionary" if title_case_applied else "pattern+dictionary"
                    return standardized, method, category
        
        if pattern_applied:
            method = "title_case+pattern" if title_case_applied else "pattern"
            return modified_keyword, method, "general"
        
        if title_case_applied:
            return title_cased_keyword, "title_case", "general"
        
        # Step 4: No standardization needed
        return keyword, "none", "none"
    
    def _get_category(self, keyword: str) -> str:
        """Determine the category of a keyword."""
        if keyword in self.skill_dictionary:
            return "skill"
        elif keyword in self.position_dictionary:
            return "position"
        elif keyword in self.tool_dictionary:
            return "tool"
        return "unknown"
    
    def _is_position_title(self, keyword: str) -> bool:
        """Check if a keyword is likely a position title."""
        position_indicators = {
            'analyst', 'engineer', 'developer', 'manager', 'director', 
            'specialist', 'coordinator', 'administrator', 'architect',
            'designer', 'scientist', 'researcher', 'consultant', 'lead',
            'supervisor', 'associate', 'assistant', 'officer', 'executive',
            'technician', 'expert', 'advisor', 'strategist', 'planner'
        }
        
        level_modifiers = {
            'senior', 'junior', 'lead', 'principal', 'staff', 'chief',
            'associate', 'assistant', 'deputy', 'vice', 'head', 'team'
        }
        
        lower_keyword = keyword.lower()
        words = lower_keyword.split()
        
        # Check if the keyword contains position indicators
        contains_position = any(
            indicator in lower_keyword 
            for indicator in position_indicators
        )
        
        # Check if it starts with a level modifier
        starts_with_level = (
            len(words) > 0 and 
            words[0] in level_modifiers
        )
        
        return contains_position or starts_with_level
    
    def _apply_intelligent_title_case(self, keyword: str) -> str:
        """
        Apply intelligent Title Case for position titles and other known patterns.
        
        Args:
            keyword: The keyword to process
            
        Returns:
            Title-cased keyword if applicable, otherwise original keyword
        """
        # Define position-related keywords that should trigger Title Case
        position_indicators = {
            'analyst', 'engineer', 'developer', 'manager', 'director', 
            'specialist', 'coordinator', 'administrator', 'architect',
            'designer', 'scientist', 'researcher', 'consultant', 'lead',
            'supervisor', 'associate', 'assistant', 'officer', 'executive',
            'technician', 'expert', 'advisor', 'strategist', 'planner'
        }
        
        # Define level modifiers that often appear with positions
        level_modifiers = {
            'senior', 'junior', 'lead', 'principal', 'staff', 'chief',
            'associate', 'assistant', 'deputy', 'vice', 'head', 'team'
        }
        
        # Convert to lowercase for checking
        lower_keyword = keyword.lower()
        words = lower_keyword.split()
        
        # Check if the keyword contains position indicators
        contains_position = any(
            indicator in lower_keyword 
            for indicator in position_indicators
        )
        
        # Check if it starts with a level modifier
        starts_with_level = (
            len(words) > 0 and 
            words[0] in level_modifiers
        )
        
        # Apply Title Case if it's likely a position title
        if contains_position or starts_with_level:
            # Special handling for acronyms and specific terms
            special_cases = {
                'ai': 'AI', 'ml': 'ML', 'bi': 'BI', 'it': 'IT', 
                'hr': 'HR', 'qa': 'QA', 'ux': 'UX', 'ui': 'UI',
                'vp': 'VP', 'ceo': 'CEO', 'cto': 'CTO', 'cfo': 'CFO',
                'phd': 'PhD', 'mba': 'MBA', 'sql': 'SQL', 'etl': 'ETL'
            }
            
            # Process each word
            title_cased_words = []
            for word in words:
                if word in special_cases:
                    title_cased_words.append(special_cases[word])
                elif len(word) > 3 or word in level_modifiers or word in position_indicators:
                    # Capitalize longer words and important keywords
                    title_cased_words.append(word.capitalize())
                elif word in ['of', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for']:
                    # Keep articles and prepositions lowercase (unless first word)
                    if len(title_cased_words) == 0:
                        title_cased_words.append(word.capitalize())
                    else:
                        title_cased_words.append(word)
                else:
                    title_cased_words.append(word.capitalize())
            
            return ' '.join(title_cased_words)
        
        # For technical skills with mixed case (e.g., "javaScript" -> "JavaScript")
        tech_patterns = {
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'mongodb': 'MongoDB',
            'postgresql': 'PostgreSQL',
            'mysql': 'MySQL',
            'nodejs': 'Node.js',
            'reactjs': 'React.js',
            'vuejs': 'Vue.js',
            'graphql': 'GraphQL',
            'restful': 'RESTful',
            'linkedin': 'LinkedIn',
            'github': 'GitHub',
            'gitlab': 'GitLab',
            'tensorflow': 'TensorFlow',
            'pytorch': 'PyTorch',
            'scikit-learn': 'Scikit-learn',
            'jupyter': 'Jupyter',
            'powerbi': 'Power BI',
            'tableau': 'Tableau'
        }
        
        # Check for technical terms that need specific casing
        for pattern, replacement in tech_patterns.items():
            if lower_keyword == pattern:
                return replacement
        
        # Return original if no rules apply
        return keyword
    
    def get_statistics(self) -> dict[str, int]:
        """Get standardization statistics."""
        return {
            "total_dictionary_entries": len(self.combined_dictionary),
            "skill_entries": len(self.skill_dictionary),
            "position_entries": len(self.position_dictionary),
            "tool_entries": len(self.tool_dictionary),
            "pattern_rules": len(self.patterns),
            "data_directory": str(self.data_dir)
        }
    
    def validate_dictionaries(self) -> dict[str, list[str]]:
        """
        Validate dictionaries for duplicates and conflicts.
        
        Returns:
            Dictionary containing validation results
        """
        issues = {
            "duplicates": [],
            "conflicts": [],
            "invalid_patterns": []
        }
        
        # Check for duplicates across dictionaries
        all_keys = {}
        for dict_name, dictionary in [
            ("skills", self.skill_dictionary),
            ("positions", self.position_dictionary),
            ("tools", self.tool_dictionary)
        ]:
            for key, value in dictionary.items():
                if key in all_keys:
                    issues["duplicates"].append(
                        f"'{key}' appears in both {all_keys[key]} and {dict_name}"
                    )
                else:
                    all_keys[key] = dict_name
        
        # Check for conflicting standardizations
        standardizations = {}
        for key, value in self.combined_dictionary.items():
            if value.lower() in standardizations:
                if standardizations[value.lower()] != key:
                    issues["conflicts"].append(
                        f"'{value}' is mapped from both '{standardizations[value.lower()]}' "
                        f"and '{key}'"
                    )
            else:
                standardizations[value.lower()] = key
        
        logger.info(f"Validation complete: {len(issues['duplicates'])} duplicates, "
                    f"{len(issues['conflicts'])} conflicts")
        
        return issues
    
    def export_to_dict(self) -> dict[str, dict[str, str]]:
        """
        Export all dictionaries as a single dictionary.
        Useful for debugging or external tools.
        
        Returns:
            Dictionary containing all mappings organized by category
        """
        return {
            "skills": self.skill_dictionary,
            "positions": self.position_dictionary,
            "tools": self.tool_dictionary,
            "combined": self.combined_dictionary
        }


# Singleton instance for backward compatibility
_default_standardizer = None


def get_default_standardizer() -> KeywordStandardizer:
    """Get the default standardizer instance (singleton pattern)."""
    global _default_standardizer
    if _default_standardizer is None:
        _default_standardizer = KeywordStandardizer()
    return _default_standardizer


# For backward compatibility
def get_statistics() -> dict[str, int]:
    """Get statistics from the default standardizer."""
    return get_default_standardizer().get_statistics()


def standardize_keywords(
    keywords: list[str], 
    include_details: bool = False
) -> tuple[list[str], list[dict[str, str]]]:
    """Standardize keywords using the default standardizer."""
    return get_default_standardizer().standardize_keywords(keywords, include_details)