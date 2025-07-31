"""
Input parsing utilities for handling various input formats from Bubble.io and other sources.
"""

import re

from bs4 import BeautifulSoup


def parse_flexible_keywords(value: str | list) -> list[str]:
    """
    Parse keywords from various formats.

    Supports:
    - Comma-separated: "keyword1, keyword2, keyword3"
    - Semicolon-separated: "keyword1; keyword2; keyword3"
    - Newline-separated: "keyword1\nkeyword2\nkeyword3"
    - Mixed separators: "keyword1, keyword2; keyword3"
    - List format: ["keyword1", "keyword2"]
    - List with embedded separators: ["keyword1, keyword2", "keyword3"]

    Args:
        value: Keywords in string or list format

    Returns:
        List of cleaned, unique keywords
    """
    if not value:
        return []

    keywords = []

    # Handle list input
    if isinstance(value, list):
        for item in value:
            if item:
                # Recursively parse each item (might contain separators)
                keywords.extend(parse_flexible_keywords(str(item).strip()))
        return _deduplicate_keywords(keywords)

    # Handle string input
    text = str(value).strip()
    if not text:
        return []

    # Try multiple separators in order of likelihood
    # First check if any separator exists
    has_comma = ',' in text
    has_semicolon = ';' in text
    has_newline = '\n' in text or '\r\n' in text

    if has_comma or has_semicolon or has_newline:
        # Use regex to split by multiple separators
        # This handles mixed separators like "keyword1, keyword2; keyword3\nkeyword4"
        items = re.split(r'[,;\n\r]+', text)
    else:
        # No common separators found - might be space-separated or single keyword
        # Check if it looks like multiple keywords without separators
        # e.g., "Senior HR Data AnalystPower BI" (from Bubble.io bug)
        if len(text) > 30 and ' ' not in text:
            # Likely concatenated keywords - try smart splitting
            items = _smart_split_keywords(text)
        else:
            # Treat as single keyword or space-separated
            items = [text]

    # Clean and filter keywords
    for item in items:
        cleaned = item.strip()
        # Remove common punctuation that might be left over
        cleaned = cleaned.strip('.,;:')
        if cleaned and len(cleaned) > 1:  # Skip single characters
            keywords.append(cleaned)

    return _deduplicate_keywords(keywords)


def parse_multiline_items(content: str | list) -> list[str]:
    """
    Parse multi-line text items (for core_strengths, key_gaps, quick_improvements).

    Handles:
    - HTML bullet points: <ol><li>item1</li><li>item2</li></ol>
    - HTML with formatting preserved from JSON-safe conversion
    - Plain text with newlines
    - Numbered lists: "1. item1\n2. item2"
    - Bullet lists: "• item1\n• item2" or "- item1\n- item2"

    Args:
        content: Multi-line content in various formats

    Returns:
        List of parsed items
    """
    if not content:
        return []

    # If already a list, return it
    if isinstance(content, list):
        return [str(item).strip() for item in content if item]

    text = str(content).strip()
    if not text:
        return []

    items = []

    # Check if it contains HTML tags
    if '<' in text and '>' in text:
        try:
            # Parse HTML
            soup = BeautifulSoup(text, 'html.parser')

            # Look for list items
            list_items = soup.find_all('li')
            if list_items:
                for li in list_items:
                    item_text = li.get_text().strip()
                    if item_text:
                        items.append(item_text)
                return items

            # If no list items, try to get all text
            text = soup.get_text()
        except Exception:
            # If HTML parsing fails, continue with text parsing
            pass

    # Parse as plain text
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common bullet points and numbering
        # Numbered lists: "1.", "2)", "1)", etc.
        line = re.sub(r'^\d+[.)]\s*', '', line)

        # Bullet points: "•", "-", "*", "·", ">", "→"
        for bullet in ['•', '-', '*', '·', '>', '→', '▪', '◦']:
            if line.startswith(bullet):
                line = line[len(bullet):].strip()
                break

        # Remove any remaining leading punctuation
        line = line.lstrip('.,;:')

        if line:
            items.append(line)

    return items


def _smart_split_keywords(text: str) -> list[str]:
    """
    Smart splitting for concatenated keywords without separators.
    e.g., "Senior HR Data AnalystPower BISupersetData Visualization"
    """
    # Known multi-word keywords that should not be split
    known_phrases = [
        "Senior HR Data Analyst",
        "Power BI",
        "Data Visualization",
        "HR Analytics",
        "Business Insights",
        "Cross Functional Collaboration",
        "Data Analyst",
        "Statistical Analysis",
        "Predictive Modeling",
        "Problem Solving",
        "Critical Thinking",
        "Machine Learning",
        "Deep Learning",
        "Project Management",
        "Team Leadership",
        "Stakeholder Management"
    ]

    keywords = []
    remaining = text

    # Try to match known phrases first
    for phrase in sorted(known_phrases, key=len, reverse=True):
        # Case-insensitive matching
        pattern = re.compile(re.escape(phrase.replace(' ', '')), re.IGNORECASE)
        if pattern.search(remaining):
            keywords.append(phrase)
            remaining = pattern.sub(' ', remaining, count=1)

    # Handle any remaining text
    remaining = remaining.strip()
    if remaining and len(remaining) > 2:
        # Try to split on capital letters (but keep acronyms together)
        parts = re.split(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', remaining)
        current_keyword = ""

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # If part is very short, likely part of a larger keyword
            if len(part) <= 2:
                current_keyword += part
            else:
                if current_keyword:
                    keywords.append(current_keyword)
                current_keyword = part

        if current_keyword:
            keywords.append(current_keyword)

    return keywords


def _deduplicate_keywords(keywords: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen = set()
    unique = []

    for keyword in keywords:
        # Case-insensitive deduplication
        key = keyword.lower()
        if key not in seen:
            seen.add(key)
            unique.append(keyword)

    return unique


def normalize_gap_analysis_input(data: dict) -> dict:
    """
    Normalize gap analysis input data to ensure consistent format.

    Converts string inputs to lists where needed and handles various formats.
    """
    normalized = data.copy()

    # Parse multi-line fields
    for field in ['core_strengths', 'key_gaps', 'quick_improvements']:
        if field in normalized:
            value = normalized[field]
            if isinstance(value, str):
                normalized[field] = parse_multiline_items(value)
            elif not isinstance(value, list):
                normalized[field] = []

    # Parse keyword fields
    for field in ['covered_keywords', 'missing_keywords']:
        if field in normalized:
            value = normalized[field]
            if isinstance(value, str):
                normalized[field] = parse_flexible_keywords(value)
            elif not isinstance(value, list):
                normalized[field] = []

    # Ensure key_gaps exists if not provided (for backward compatibility)
    if 'key_gaps' not in normalized:
        normalized['key_gaps'] = []

    return normalized
