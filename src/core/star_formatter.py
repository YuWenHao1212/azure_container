"""
STAR/PAR formatter for converting experience descriptions.
"""

import re
from typing import Optional


class STARFormatter:
    """Format experience descriptions using STAR/PAR methodology"""

    # Common action verbs by experience level
    ACTION_VERBS = {
        "junior": [
            "Assisted", "Contributed", "Participated", "Supported",
            "Learned", "Developed", "Created", "Built", "Implemented"
        ],
        "mid": [
            "Led", "Managed", "Implemented", "Designed", "Developed",
            "Optimized", "Streamlined", "Coordinated", "Delivered"
        ],
        "senior": [
            "Spearheaded", "Transformed", "Pioneered", "Architected",
            "Orchestrated", "Championed", "Established", "Drove", "Directed"
        ]
    }

    # Patterns that indicate STAR/PAR format markers (to be removed)
    FORMAT_MARKERS = [
        r'\s*\(S\)\s*', r'\s*\(T\)\s*', r'\s*\(A\)\s*', r'\s*\(R\)\s*',
        r'\s*\(P\)\s*', r'\s*\[S\]\s*', r'\s*\[T\]\s*', r'\s*\[A\]\s*',
        r'\s*\[R\]\s*', r'\s*\[P\]\s*'
    ]

    def format_bullet_point(self, text: str, style: str = "STAR") -> str:
        """
        Format a bullet point using STAR or PAR methodology.
        This is primarily for guidance - the actual formatting is done by LLM.
        """
        # Remove any existing format markers
        cleaned_text = self.remove_format_markers(text)

        # Return cleaned text - actual STAR/PAR formatting done by LLM
        return cleaned_text

    def remove_format_markers(self, text: str) -> str:
        """Remove STAR/PAR format markers from text"""
        result = text

        # Remove all format markers
        for pattern in self.FORMAT_MARKERS:
            result = re.sub(pattern, ' ', result)

        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()

        # Remove markers at sentence boundaries
        result = re.sub(r'\.\s*\(S\)', '.', result)
        result = re.sub(r'\.\s*\(T\)', '.', result)
        result = re.sub(r'\.\s*\(A\)', '.', result)
        result = re.sub(r'\.\s*\(R\)', '.', result)
        result = re.sub(r'\.\s*\(P\)', '.', result)

        return result

    def identify_experience_level(self, resume_text: str) -> str:
        """Identify experience level from resume content"""
        # Look for year indicators
        years_pattern = r'(\d+)\+?\s*years?\s*(?:of\s*)?experience'
        matches = re.findall(years_pattern, resume_text.lower())

        if matches:
            max_years = max(int(match) for match in matches)
            if max_years >= 7:
                return "senior"
            elif max_years >= 3:
                return "mid"

        # Look for senior indicators
        senior_indicators = [
            'senior', 'lead', 'principal', 'director', 'manager',
            'architect', 'head of', 'vp', 'vice president'
        ]

        resume_lower = resume_text.lower()
        if any(indicator in resume_lower for indicator in senior_indicators):
            return "senior"

        # Look for mid-level indicators
        mid_indicators = ['team lead', 'coordinator', 'specialist']
        if any(indicator in resume_lower for indicator in mid_indicators):
            return "mid"

        # Default to junior
        return "junior"

    def get_action_verbs(self, experience_level: str) -> list[str]:
        """Get appropriate action verbs for experience level"""
        return self.ACTION_VERBS.get(experience_level, self.ACTION_VERBS["junior"])

    def enhance_bullet_point(self, text: str, keywords: Optional[list[str]] = None) -> str:
        """
        Enhance a bullet point with better structure.
        This provides guidance for the LLM.
        """
        # Remove format markers first
        cleaned_text = self.remove_format_markers(text)

        # Note: Could check if it starts with an action verb
        # and flag for LLM improvement if needed

        return cleaned_text

    def validate_star_format(self, text: str) -> tuple[bool, str]:
        """
        Validate if text follows STAR/PAR format principles.
        Returns (is_valid, message)
        """
        # Check for format markers (should not exist)
        if any(re.search(pattern, text) for pattern in self.FORMAT_MARKERS):
            return False, "Contains STAR/PAR format markers"

        # Check if it starts with action verb
        words = text.split()
        if not words:
            return False, "Empty text"

        # Check minimum length (too short might not be STAR/PAR)
        if len(words) < 10:
            return False, "Too short for STAR/PAR format"

        # Check for result indicators
        result_indicators = [
            'resulting', 'achieved', 'improved', 'reduced', 'increased',
            'delivered', 'saved', 'generated', 'led to'
        ]

        text_lower = text.lower()
        has_result = any(indicator in text_lower for indicator in result_indicators)

        if not has_result:
            return False, "No clear result/impact stated"

        return True, "Valid STAR/PAR format"
