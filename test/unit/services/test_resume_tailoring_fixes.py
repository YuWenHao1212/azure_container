"""Test cases for Resume Tailoring v3.1 fixes."""

import re
import unittest
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.resume_tailoring_v31 import ResumeTailoringServiceV31


class TestResumeTailoringFixes(unittest.TestCase):
    """Test suite for Resume Tailoring v3.1.0 specific fixes."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ResumeTailoringServiceV31()

    def test_personal_project_not_in_experience(self):
        """Ensure Personal Projects don't appear in Experience section."""
        # Sample HTML with Personal Project incorrectly in Experience

        # The prompt should instruct LLM1 to skip Personal Projects
        # This test validates the prompt contains the rule
        with open('src/prompts/resume_tailoring/v1.0.0-resume-core.yaml', encoding='utf-8') as f:
            prompt_content = f.read()

        # Check for Project Placement Rules
        assert 'CRITICAL PROJECT PLACEMENT RULES' in prompt_content
        assert 'Personal    → Projects ✓ (LLM2 handles)' in prompt_content
        assert 'NEVER move personal projects into Experience' in prompt_content
        assert 'Project Boundary Rules' in prompt_content

    def test_llm2_empty_sections_trigger_fallback(self):
        """Verify that empty LLM2 sections trigger fallback and warnings."""
        # Test data
        original_resume = """
        <h3>Education:</h3>
        <p>Master of Science in Data Analytics</p>
        <h3>Personal Project:</h3>
        <p>Built a Python dashboard</p>
        <h3>Certification:</h3>
        <p>Tableau Desktop Specialist</p>
        """

        # Simulate LLM2 returning empty sections
        llm2_result = {
            "optimized_sections": {
                "education": "",  # Empty!
                "projects": "",   # Empty!
                "certifications": ""  # Empty!
            }
        }

        llm1_result = {
            "optimized_sections": {
                "summary": "Test summary",
                "skills": "Test skills",
                "experience": "Test experience"
            }
        }

        resume_structure = {}

        # The merge should detect empty sections and use fallback
        merged = self.service._merge_sections(llm1_result, llm2_result, resume_structure, original_resume)

        # Check that fallback_used was set
        assert llm2_result.get("fallback_used") is True

        # Check that sections now have content from original resume
        assert "education" in merged
        assert "Master of Science" in merged["education"]
        assert "projects" in merged
        assert "Python dashboard" in merged["projects"]
        assert "certifications" in merged
        assert "Tableau Desktop" in merged["certifications"]

    def test_no_css_nesting(self):
        """Verify CSS classes don't nest within each other."""
        # HTML with existing opt-modified class
        html_with_css = """
        <p class="opt-modified">Enhanced Python development with 5+ years experience</p>
        """

        # Test keywords that appear in the text
        covered_keywords = ['Python']
        newly_added = []

        # Apply keyword CSS
        result = self.service._apply_keyword_css(html_with_css, covered_keywords, newly_added)

        # Check that we don't have nested opt-* spans
        # Should not create: <span class="opt-modified"><span class="opt-keyword-existing">Python</span></span>
        assert '<span class="opt-modified"><span class="opt-keyword' not in result

        # The opt-modified class should still be there, but no nested keyword span inside it
        assert 'class="opt-modified"' in result

    def test_preserve_known_numbers(self):
        """Ensure known numbers aren't replaced with placeholders."""
        # Check the prompt for placeholder rules
        with open('src/prompts/resume_tailoring/v1.0.0-resume-core.yaml', encoding='utf-8') as f:
            prompt_content = f.read()

        # Verify placeholder usage rules exist
        assert 'Placeholder Usage Rules' in prompt_content
        assert 'PRESERVE Known Values' in prompt_content
        assert '"23 million units"' in prompt_content  # Check the example exists
        assert 'Keep exact number' in prompt_content  # Check the rule exists
        assert 'WRONG: "23 million units" → "[23 million] units"' in prompt_content

    def test_css_nesting_prevention_with_multiple_classes(self):
        """Test that CSS nesting prevention works with various opt-* classes."""
        # HTML with different opt-* classes
        test_cases = [
            ('<span class="opt-modified">Text with Python</span>', ['Python']),
            ('<span class="opt-new">New content with Docker</span>', ['Docker']),
            ('<span class="opt-placeholder">[X] years with AWS</span>', ['AWS']),
        ]

        for html, keywords in test_cases:
            result = self.service._apply_keyword_css(html, keywords, [])
            # Should not create nested spans
            assert not re.search(r'<span class="opt-[^"]+"><span class="opt-keyword', result), \
                f"Found nested spans in: {result}"

    def test_project_boundary_in_prompt(self):
        """Verify that Experience Processing has proper project boundary rules."""
        with open('src/prompts/resume_tailoring/v1.0.0-resume-core.yaml', encoding='utf-8') as f:
            prompt_content = f.read()

        # Check for specific project boundary instructions in Experience Processing
        assert 'IF entry contains "Personal Project" → SKIP' in prompt_content
        assert 'IF entry is clearly personal/hobby → SKIP' in prompt_content
        assert 'Only process actual employment positions' in prompt_content
        assert 'Work projects stay embedded within job descriptions' in prompt_content

    def test_keyword_css_with_existing_opt_classes(self):
        """Test keyword CSS application doesn't interfere with existing opt-* classes."""
        html = """
        <div>
            <p class="opt-modified">Experienced in Python and Java development</p>
            <p>Also skilled in Docker and Kubernetes</p>
        </div>
        """

        covered = ['Docker']
        newly_added = ['Kubernetes']

        result = self.service._apply_keyword_css(html, covered, newly_added)

        # First paragraph should keep opt-modified class
        assert 'class="opt-modified"' in result

        # Keywords SHOULD NOW be marked inside opt-modified (we only prevent keyword-inside-keyword)
        # Since Python and Java are not in our covered/newly_added lists, they won't be marked
        # But if they were, they would be allowed inside opt-modified

        # Second paragraph should have keyword spans
        second_paragraph = result.split('<p>')[2] if len(result.split('<p>')) > 2 else result
        assert 'class="opt-keyword-existing">Docker</span>' in second_paragraph
        assert 'class="opt-keyword-add">Kubernetes</span>' in second_paragraph

        # No nested keyword spans (but other opt-* nesting is allowed)
        # Look for actual nesting (one keyword span inside another)
        assert not re.search(r'<span class="opt-keyword-[^"]+">(?:(?!</span>).)*<span class="opt-keyword-', result)


if __name__ == '__main__':
    unittest.main()
