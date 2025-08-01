"""
Traditional Chinese (Taiwan) keyword standardizer.
Provides standardization for Traditional Chinese professional terms.
"""

import json
import logging
import re
from pathlib import Path

from .base_standardizer import BaseStandardizer

logger = logging.getLogger(__name__)


class TraditionalChineseStandardizer(BaseStandardizer):
    """
    Traditional Chinese keyword standardizer for Taiwan workplace terminology.

    Features:
    - Taiwan-specific professional terminology
    - Traditional Chinese character standardization
    - Technology and business term mapping
    - Pattern-based normalization
    """

    DEFAULT_CONFIG_PATH = "src/data/standardization/zh_tw_standard_terms.json"

    def __init__(self, config_path: str | None = None):
        """
        Initialize Traditional Chinese standardizer.

        Args:
            config_path: Path to Traditional Chinese standardization config
        """
        super().__init__(config_path or self.DEFAULT_CONFIG_PATH)

    def get_supported_language(self) -> str:
        """Get the language code supported by this standardizer."""
        return "zh-TW"

    def _load_config(self):
        """Load Traditional Chinese standardization configuration."""
        try:
            config_path = Path(self.config_path)

            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                self.config = None
                return

            with open(config_path, encoding='utf-8') as f:
                self.config = json.load(f)

            # Validate config structure
            if not self._validate_config():
                logger.error("Invalid Traditional Chinese standardization config")
                self.config = None
                return

            logger.info(f"Loaded Traditional Chinese standardization config: {self.config.get('version', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to load Traditional Chinese config: {e!s}")
            self.config = None

    def _validate_config(self) -> bool:
        """
        Validate the loaded configuration structure.

        Returns:
            True if config is valid
        """
        if not self.config:
            return False

        required_fields = ['version', 'language', 'categories']
        for field in required_fields:
            if field not in self.config:
                logger.error(f"Missing required field in config: {field}")
                return False

        if self.config['language'] != 'zh-TW':
            logger.error(f"Config language mismatch: expected zh-TW, got {self.config['language']}")
            return False

        return True

    def _normalize_keyword(self, keyword: str) -> str:
        """
        Normalize Traditional Chinese keyword.

        Args:
            keyword: Keyword to normalize

        Returns:
            Normalized keyword
        """
        # Apply parent normalization first
        keyword = super()._normalize_keyword(keyword)

        # Traditional Chinese specific normalization
        keyword = self._normalize_chinese_punctuation(keyword)
        keyword = self._normalize_english_terms(keyword)
        keyword = self._normalize_mixed_content(keyword)

        return keyword

    def _normalize_chinese_punctuation(self, keyword: str) -> str:
        """
        Normalize Chinese punctuation marks.

        Args:
            keyword: Keyword with potential Chinese punctuation

        Returns:
            Normalized keyword
        """
        # Remove common Chinese punctuation that shouldn't be in keywords
        punctuation_map = {
            '，': '',  # noqa: RUF001
            '。': '',
            '！': '',  # noqa: RUF001
            '？': '',  # noqa: RUF001
            '：': '',  # noqa: RUF001
            '；': '',  # noqa: RUF001
            '「': '',
            '」': '',
            '『': '',
            '』': '',
            '（': '',  # noqa: RUF001
            '）': '',  # noqa: RUF001
            '【': '',
            '】': ''
        }

        for chinese_punct, replacement in punctuation_map.items():
            keyword = keyword.replace(chinese_punct, replacement)

        return keyword.strip()

    def _normalize_english_terms(self, keyword: str) -> str:
        """
        Normalize English terms within Chinese keywords.

        Args:
            keyword: Keyword that may contain English terms

        Returns:
            Normalized keyword
        """
        # Standardize common English terms
        english_normalizations = {
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'nodejs': 'Node.js',
            'reactjs': 'React',
            'vuejs': 'Vue.js',
            'angularjs': 'Angular',
            'github': 'GitHub',
            'restful': 'RESTful',
            'graphql': 'GraphQL',
            'mongodb': 'MongoDB',
            'postgresql': 'PostgreSQL',
            'mysql': 'MySQL'
        }

        for incorrect, correct in english_normalizations.items():
            # Case-insensitive replacement
            keyword = re.sub(
                re.escape(incorrect),
                correct,
                keyword,
                flags=re.IGNORECASE
            )

        return keyword

    def _normalize_mixed_content(self, keyword: str) -> str:
        """
        Normalize mixed Chinese-English content.

        Args:
            keyword: Keyword with mixed content

        Returns:
            Normalized keyword
        """
        # Add space between Chinese and English if needed
        # This helps with proper tokenization
        keyword = re.sub(r'([\u4e00-\u9fff])([A-Za-z])', r'\1 \2', keyword)
        keyword = re.sub(r'([A-Za-z])([\u4e00-\u9fff])', r'\1 \2', keyword)

        # Collapse multiple spaces
        keyword = re.sub(r'\s+', ' ', keyword)

        return keyword.strip()

    def get_category_keywords(self, category: str) -> list[str]:
        """
        Get all standardized keywords for a specific category.

        Args:
            category: Category name (e.g., 'programming_languages')

        Returns:
            List of standardized keywords in the category
        """
        if not self.config or 'categories' not in self.config:
            return []

        if category not in self.config['categories']:
            return []

        category_data = self.config['categories'][category]
        if 'mappings' not in category_data:
            return []

        # Return unique standardized terms
        standardized_terms = set(category_data['mappings'].values())
        return sorted(standardized_terms)

    def get_all_categories(self) -> list[str]:
        """
        Get all available categories.

        Returns:
            List of category names
        """
        if not self.config or 'categories' not in self.config:
            return []

        return list(self.config['categories'].keys())

    def search_keywords(self, query: str, limit: int = 10) -> list[str]:
        """
        Search for keywords that match a query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching keywords
        """
        if not self.config or 'categories' not in self.config:
            return []

        query_lower = query.lower()
        matches = []

        # Search in all mappings
        for category_data in self.config['categories'].values():
            if 'mappings' not in category_data:
                continue

            for original, standardized in category_data['mappings'].items():
                if (query_lower in original.lower() or
                    query_lower in standardized.lower()) and standardized not in matches:
                    matches.append(standardized)

        return matches[:limit]

    def get_taiwan_specific_terms(self) -> list[str]:
        """
        Get terms that are specifically Taiwan-localized.

        Returns:
            List of Taiwan-specific terms
        """
        taiwan_terms = []

        if not self.config or 'categories' not in self.config:
            return taiwan_terms

        # Look for terms with Taiwan-specific variants
        taiwan_indicators = ['台灣', '臺灣', '繁體', '正體']

        for category_data in self.config['categories'].values():
            if 'mappings' not in category_data:
                continue

            for original, standardized in category_data['mappings'].items():
                if any(indicator in original or indicator in standardized
                       for indicator in taiwan_indicators) and standardized not in taiwan_terms:
                    taiwan_terms.append(standardized)

        return taiwan_terms

    def validate_traditional_chinese(self, text: str) -> bool:
        """
        Validate if text contains Traditional Chinese characters.

        Args:
            text: Text to validate

        Returns:
            True if text contains Traditional Chinese
        """
        # Check for Traditional Chinese specific characters
        traditional_chars = set('繁體語機業資訊軟體開發設計測試資料庫網路計劃團隊責任工作經驗技能專業證照學歷')
        text_chars = set(text)

        # If text contains Traditional-specific chars, likely Traditional
        if text_chars.intersection(traditional_chars):
            return True

        # Check for general Chinese characters
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars) > 0

    def get_config_metadata(self) -> dict:
        """
        Get metadata about the configuration.

        Returns:
            Configuration metadata
        """
        if not self.config:
            return {"available": False}

        metadata = self.config.get('metadata', {})
        metadata.update({
            "available": True,
            "language": self.get_supported_language(),
            "config_version": self.config.get('version'),
            "taiwan_specific": self.config.get('taiwan_specific', False)
        })

        return metadata
