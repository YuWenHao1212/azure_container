"""Integration tests for LLM2 fallback detection and warning generation."""

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.resume_tailoring_v31 import ResumeTailoringServiceV31


class TestLLM2FallbackIntegration(unittest.TestCase):
    """Test LLM2 fallback detection and warning generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ResumeTailoringServiceV31()

        # Load test fixture
        fixture_path = Path(__file__).parent.parent / "fixtures" / "resume_tailoring" / "llm2_fallback_test.json"
        with open(fixture_path) as f:
            self.fixture = json.load(f)

        self.original_resume = self.fixture["sample_original_resume"]["html"]

    def test_empty_sections_trigger_fallback(self):
        """Test that completely empty LLM2 sections trigger fallback and warnings."""
        test_case = self.fixture["test_cases"][0]  # empty_sections case

        # Mock LLM responses
        llm1_result = {
            "optimized_sections": {
                "summary": "<p>Test summary</p>",
                "skills": "<p>Test skills</p>",
                "experience": "<p>Test experience</p>"
            },
            "tracking": ["[Summary] Enhanced", "[Skills] Added keywords"]
        }

        llm2_result = test_case["llm2_response"].copy()

        resume_structure = {"education_enhancement_needed": False}

        # Call _merge_sections
        merged = self.service._merge_sections(
            llm1_result, llm2_result, resume_structure, self.original_resume
        )

        # Verify fallback was triggered
        self.assertTrue(llm2_result.get("fallback_used"), "fallback_used should be True")

        # Verify sections have content from original resume
        self.assertIn("education", merged)
        self.assertIn("Master of Science", merged["education"])
        self.assertIn("projects", merged)
        self.assertIn("Python dashboard", merged["projects"])
        self.assertIn("certifications", merged)
        self.assertIn("Tableau Desktop", merged["certifications"])

    def test_partial_empty_sections_trigger_fallback(self):
        """Test that partially empty LLM2 sections trigger fallback for empty ones."""
        test_case = self.fixture["test_cases"][1]  # partial_empty_sections case

        llm1_result = {
            "optimized_sections": {
                "summary": "<p>Test summary</p>",
                "skills": "<p>Test skills</p>",
                "experience": "<p>Test experience</p>"
            }
        }

        llm2_result = test_case["llm2_response"].copy()
        resume_structure = {}

        # Call _merge_sections
        merged = self.service._merge_sections(
            llm1_result, llm2_result, resume_structure, self.original_resume
        )

        # Verify fallback was triggered for empty sections
        self.assertTrue(llm2_result.get("fallback_used"), "fallback_used should be True for partial empty")

        # Education should NOT be from fallback (has content)
        self.assertIn("education", merged)
        self.assertIn("Master of Science in Data Analytics", merged["education"])

        # Projects and Certifications should be from fallback
        self.assertIn("projects", merged)
        self.assertIn("Python dashboard", merged["projects"])
        self.assertIn("certifications", merged)
        self.assertIn("Tableau Desktop", merged["certifications"])

    def test_no_fallback_when_all_sections_present(self):
        """Test that no fallback occurs when all LLM2 sections have content."""
        test_case = self.fixture["test_cases"][2]  # all_sections_present case

        llm1_result = {
            "optimized_sections": {
                "summary": "<p>Test summary</p>",
                "skills": "<p>Test skills</p>",
                "experience": "<p>Test experience</p>"
            }
        }

        llm2_result = test_case["llm2_response"].copy()
        resume_structure = {}

        # Call _merge_sections
        merged = self.service._merge_sections(
            llm1_result, llm2_result, resume_structure, self.original_resume
        )

        # Verify no fallback was triggered
        self.assertFalse(llm2_result.get("fallback_used"), "fallback_used should not be set")

        # Verify LLM2 content is used (has opt-* classes)
        self.assertIn("education", merged)
        self.assertIn("opt-modified", merged["education"])
        self.assertIn("projects", merged)
        self.assertIn("opt-new", merged["projects"])

    @pytest.mark.asyncio
    async def test_fallback_warnings_in_api_response(self):
        """Test that fallback triggers appropriate warnings in API response."""
        # This would require mocking the entire tailor_resume flow
        # For now, we focus on unit testing the _merge_sections behavior
        pass

    def test_extract_original_section_handles_various_formats(self):
        """Test that _extract_original_section works with different HTML formats."""
        test_cases = [
            # H3 header
            ("<h3>Education:</h3><p>BS Computer Science</p>", "education", "BS Computer Science"),
            # H2 header
            ("<h2>Personal Project</h2><p>ML Model</p>", "projects", "ML Model"),
            # H4 header
            ("<h4>Certification</h4><p>AWS Certified</p>", "certifications", "AWS Certified"),
            # Case insensitive
            ("<h3>EDUCATION</h3><p>MS Data Science</p>", "education", "MS Data Science"),
            # With background in name
            ("<h3>Education Background:</h3><p>PhD Physics</p>", "education", "PhD Physics"),
        ]

        for html, section_name, expected_content in test_cases:
            with self.subTest(section=section_name):
                result = self.service._extract_original_section(section_name, html)
                self.assertIn(expected_content, result, f"Should extract {expected_content} from {section_name}")


if __name__ == "__main__":
    unittest.main()
