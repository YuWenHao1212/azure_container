"""
Text processing utilities for HTML cleaning and content manipulation.
Provides functions for HTML sanitization, text extraction, and content validation.
"""

import html
import re

from bs4 import BeautifulSoup


def clean_html_text(html_text: str) -> str:
    """
    Extract plain text from HTML content.
    
    Args:
        html_text: HTML formatted text
        
    Returns:
        Clean plain text with normalized whitespace
    """
    if not html_text:
        return ""
    
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Normalize whitespace
    return re.sub(r'\s+', ' ', text).strip()


def remove_dangerous_content(html_content: str) -> str:
    """
    Remove dangerous tags and their complete content for security.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        HTML with dangerous content removed
    """
    if not html_content:
        return ""
    
    # Remove script tags and their complete content
    html_content = re.sub(
        r'<script[^>]*>.*?</script>', 
        '', 
        html_content, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove style tags and their complete content
    html_content = re.sub(
        r'<style[^>]*>.*?</style>', 
        '', 
        html_content, 
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove other potentially dangerous tags (but keep content)
    dangerous_tags = [
        'iframe', 'object', 'embed', 'form', 'input', 
        'button', 'select', 'textarea', 'canvas', 'svg'
    ]
    for tag in dangerous_tags:
        # Remove opening and closing tags but keep content
        html_content = re.sub(
            f'</?{tag}[^>]*>', 
            '', 
            html_content, 
            flags=re.IGNORECASE
        )
    
    # Remove comments (may contain malicious code)
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    return html_content


def basic_security_cleanup(content: str) -> str:
    """
    Perform basic security cleanup on HTML content.
    
    Args:
        content: HTML content to clean
        
    Returns:
        Cleaned HTML content
    """
    if not content:
        return ""
    
    # Remove JavaScript protocol
    content = re.sub(
        r'javascript:[^"\'>\s]*', 
        '#', 
        content, 
        flags=re.IGNORECASE
    )
    
    # Remove data protocol (except safe images)
    content = re.sub(
        r'data:(?!image/[a-zA-Z]*;base64,)[^"\'>\s]*', 
        '#', 
        content, 
        flags=re.IGNORECASE
    )
    
    # Remove event handler attributes (onclick, onload, etc.)
    content = re.sub(
        r'\s+on\w+\s*=\s*["\'][^"\']*["\']', 
        '', 
        content, 
        flags=re.IGNORECASE
    )
    content = re.sub(
        r'\s+on\w+\s*=\s*[^"\'>\s]+', 
        '', 
        content, 
        flags=re.IGNORECASE
    )
    
    # Remove possible CSS expressions
    content = re.sub(
        r'expression\s*\([^)]*\)', 
        '', 
        content, 
        flags=re.IGNORECASE
    )
    
    # Remove illegal characters
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Clean up extra whitespace
    content = re.sub(r'\s+', ' ', content)
    
    return content.strip()


def clean_llm_output(content: str) -> str:
    """
    Clean LLM output more thoroughly - handles markdown and encoding issues.
    
    Args:
        content: Raw LLM output
        
    Returns:
        Cleaned content
    """
    if not content:
        return ""
    
    # Remove various markdown code block markers
    content = re.sub(r'^```\w*\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n?```$', '', content, flags=re.MULTILINE)
    
    # Remove extra blank lines
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # Handle encoding issues without breaking HTML tags
    try:
        content = content.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        # If encoding fails, return cleaned string
        pass
    
    return content.strip()


def validate_html_for_tinymce(html_content: str) -> str:
    """
    Validate HTML to meet TinyMCE requirements - secure improved version.
    
    Args:
        html_content: HTML content to validate
        
    Returns:
        TinyMCE-compatible HTML
    """
    try:
        if not html_content or not html_content.strip():
            raise ValueError("Empty HTML content")
        
        # Completely remove dangerous tags and their content
        content = remove_dangerous_content(html_content)
        
        # Use BeautifulSoup to extract body content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract body content or use entire content
        body = soup.find('body')
        content = str(body) if body else str(soup)
        
        # Apply basic security cleanup
        content = basic_security_cleanup(content)
        
        # Final validation - ensure we have valid HTML
        final_soup = BeautifulSoup(content, 'html.parser')
        
        # If parsing results in empty content, raise error
        if not final_soup.get_text(strip=True):
            raise ValueError("HTML parsing resulted in empty content")
        
        return str(final_soup)
        
    except Exception:
        # Log error and return safe fallback
        # In production, should log the actual error
        return '<p>Content processing failed - please check the original format</p>'


def sanitize_html_content(html_content: str) -> str:
    """
    Complete HTML sanitization pipeline for safe display.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Sanitized HTML safe for display
    """
    # Apply all cleaning steps in order
    content = remove_dangerous_content(html_content)
    content = basic_security_cleanup(content)
    content = validate_html_for_tinymce(content)
    
    return content


def normalize_keywords(keywords: list[str]) -> list[str]:
    """
    Normalize keywords for consistent matching.
    
    Args:
        keywords: List of keywords
        
    Returns:
        Normalized keyword list
    """
    normalized = []
    for keyword in keywords:
        # Convert to lowercase and strip whitespace
        keyword = keyword.lower().strip()
        if keyword:
            normalized.append(keyword)
    
    return normalized


def convert_markdown_to_html(text: str) -> str:
    """
    Convert markdown syntax to HTML.
    
    Args:
        text: Markdown text
        
    Returns:
        HTML formatted text
    """
    if not text:
        return ""
    
    # Convert markdown syntax
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    
    # Remove illegal characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text