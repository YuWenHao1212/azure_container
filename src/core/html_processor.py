"""
HTML processor for parsing and rebuilding resume HTML.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..models.domain.tailoring import OptimizationType, ResumeSection, ResumeStructure

logger = logging.getLogger(__name__)


class HTMLProcessor:
    """Process HTML resumes for parsing and reconstruction"""

    # CSS classes for optimization markers
    CSS_CLASSES = {
        OptimizationType.STRENGTH: "opt-strength",
        OptimizationType.KEYWORD: "opt-keyword",
        OptimizationType.PLACEHOLDER: "opt-placeholder",
        OptimizationType.NEW: "opt-new",
        OptimizationType.IMPROVEMENT: "opt-improvement"
    }

    # Common section headers to look for
    SECTION_HEADERS = ["h2", "h3"]

    def parse_resume(self, html: str) -> ResumeStructure:
        """Parse HTML resume into structured sections"""
        soup = BeautifulSoup(html, 'html.parser')
        sections = {}
        has_summary = False

        # Find all section headers
        headers = soup.find_all(self.SECTION_HEADERS)

        for section_order, header in enumerate(headers):
            section_name = header.get_text(strip=True)
            section_content = []

            # Collect content until next header
            for sibling in header.find_next_siblings():
                if sibling.name in self.SECTION_HEADERS:
                    break
                section_content.append(str(sibling))

            # Check if this is a summary section
            if self._is_summary_section(section_name):
                has_summary = True

            sections[section_name] = ResumeSection(
                name=section_name,
                content='\n'.join(section_content),
                html_element=header.name,
                order=section_order
            )

        # Also capture content before first header (contact info, etc.)
        first_header = headers[0] if headers else None
        if first_header:
            pre_header_content = []
            for element in soup.children:
                if element == first_header:
                    break
                if isinstance(element, Tag):
                    pre_header_content.append(str(element))

            if pre_header_content:
                sections["_header"] = ResumeSection(
                    name="_header",
                    content='\n'.join(pre_header_content),
                    html_element="div",
                    order=-1
                )

        return ResumeStructure(
            sections=sections,
            has_summary=has_summary,
            total_sections=len(sections)
        )

    def rebuild_resume(self, structure: ResumeStructure) -> str:
        """Rebuild resume HTML from structure"""
        # Sort sections by order
        sorted_sections = sorted(
            structure.sections.items(),
            key=lambda x: x[1].order
        )

        html_parts = []

        for section_name, section in sorted_sections:
            if section_name == "_header":
                # Header content goes directly
                html_parts.append(section.content)
            else:
                # Regular sections with headers
                header_tag = section.html_element or "h2"

                # Apply opt-new class if this is a new section
                if section.is_required and "opt-new" in section.content:
                    html_parts.append(f'<{header_tag} class="opt-new">{section.name}</{header_tag}>')
                else:
                    html_parts.append(f'<{header_tag}>{section.name}</{header_tag}>')

                html_parts.append(section.content)

        return '\n'.join(html_parts)

    def apply_marker(self, content: str, marker_type: OptimizationType) -> str:
        """Apply optimization marker to content"""
        css_class = self.CSS_CLASSES.get(marker_type, "opt-generic")
        return f'<span class="{css_class}">{content}</span>'

    def apply_markers_to_text(self, text: str, markers: list[tuple[str, OptimizationType]]) -> str:
        """Apply multiple markers to text"""
        # Sort markers by position (longest first to avoid conflicts)
        sorted_markers = sorted(markers, key=lambda x: len(x[0]), reverse=True)

        for content, marker_type in sorted_markers:
            marked_content = self.apply_marker(content, marker_type)
            text = text.replace(content, marked_content)

        return text

    def count_markers(self, html: str) -> dict[str, int]:
        """Count optimization markers in HTML"""
        counts = {}

        # Count old-style markers from CSS_CLASSES
        for marker_type, css_class in self.CSS_CLASSES.items():
            pattern = f'class="{css_class}"'
            count = html.count(pattern)
            counts[marker_type.value] = count

        # Count new-style markers
        new_markers = {
            "modified": "opt-modified",
            "keyword": "opt-keyword",
            "keyword-existing": "opt-keyword-existing"
        }

        for marker_key, css_class in new_markers.items():
            pattern = f'class="{css_class}"'
            count = html.count(pattern)
            counts[marker_key] = count

        return counts

    def remove_markers(self, html: str) -> str:
        """Remove all optimization markers from HTML"""
        soup = BeautifulSoup(html, 'html.parser')

        # Find all spans with optimization classes (old-style)
        for css_class in self.CSS_CLASSES.values():
            for span in soup.find_all('span', class_=css_class):
                # Replace span with its contents
                span.unwrap()

        # Find all spans with new-style optimization classes
        new_marker_classes = ["opt-modified", "opt-keyword", "opt-keyword-existing"]
        for css_class in new_marker_classes:
            for span in soup.find_all('span', class_=css_class):
                # Replace span with its contents
                span.unwrap()

        # Also remove opt-new class from headers
        for tag in soup.find_all(class_="opt-new"):
            if tag.get('class'):
                classes = tag['class']
                if 'opt-new' in classes:
                    classes.remove('opt-new')
                    if classes:
                        tag['class'] = classes
                    else:
                        del tag['class']

        return str(soup)

    def _is_summary_section(self, section_name: str) -> bool:
        """Check if section name indicates a summary section"""
        summary_keywords = [
            'summary', 'professional summary', 'executive summary', 'career summary',
            'objective', 'profile', 'about', 'about me', 'introduction',
            '摘要', '簡介', '個人簡介', '自我介紹', '專業摘要', '職涯簡介'
        ]

        section_lower = section_name.lower().strip()

        # Exact match check
        if section_lower in summary_keywords:
            return True

        # Partial match check
        return any(keyword in section_lower for keyword in summary_keywords)

    def standardize_section_titles(self, html: str) -> str:
        """Standardize section titles to avoid duplication"""
        soup = BeautifulSoup(html, 'html.parser')

        # Map of variations to standard titles
        title_mapping = {
            # Summary variations
            'summary': 'Professional Summary',
            'professional summary': 'Professional Summary',
            'executive summary': 'Professional Summary',
            'career summary': 'Professional Summary',
            'profile': 'Professional Summary',
            'about me': 'Professional Summary',
            'about': 'Professional Summary',
            'introduction': 'Professional Summary',
            # Chinese variations
            '摘要': 'Professional Summary',
            '簡介': 'Professional Summary',
            '個人簡介': 'Professional Summary',
            '自我介紹': 'Professional Summary',
            '專業摘要': 'Professional Summary',
            '職涯簡介': 'Professional Summary',
        }

        # Find all section headers
        headers = soup.find_all(self.SECTION_HEADERS)

        for header in headers:
            original_title = header.get_text(strip=True)
            title_lower = original_title.lower().strip()

            # Check if this title should be standardized
            if title_lower in title_mapping:
                new_title = title_mapping[title_lower]

                # Only standardize if the title is actually different
                if original_title != new_title:
                    logger.info(f"Standardizing section title: '{original_title}' → '{new_title}' (will be marked as opt-modified)")

                    # Clear the header and add new content with opt-modified
                    header.clear()
                    new_span = soup.new_tag('span', **{'class': 'opt-modified'})
                    new_span.string = new_title
                    header.append(new_span)
                else:
                    # Title is already standardized, no change needed
                    pass

        return str(soup)

    def validate_html_structure(self, html: str) -> tuple[bool, str | None]:
        """Validate HTML structure"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Check for text content
            text_content = soup.get_text(strip=True)
            if not text_content:
                return False, "No text content found"

            # Check if it's plain text (no HTML tags)
            if not soup.find():
                # It's plain text, which is valid
                return True, None

            # If it has HTML tags, just ensure it has content
            # No need to require specific structural elements
            return True, None

        except Exception as e:
            return False, f"HTML parsing error: {e!s}"

    def normalize_to_html(self, content: str) -> str:
        """Convert plain text to basic HTML if needed"""
        soup = BeautifulSoup(content, 'html.parser')

        # Check if it's already HTML (has any tags)
        if soup.find():
            # Already HTML, return as is
            return content

        # It's plain text, convert to basic HTML
        # Split by double newlines for paragraphs
        paragraphs = content.split('\n\n')
        html_parts = []

        for para in paragraphs:
            para = para.strip()
            if para:
                # Replace single newlines with <br> within paragraphs
                para_html = para.replace('\n', '<br>')
                html_parts.append(f'<p>{para_html}</p>')

        return '\n'.join(html_parts) if html_parts else f'<p>{content}</p>'
