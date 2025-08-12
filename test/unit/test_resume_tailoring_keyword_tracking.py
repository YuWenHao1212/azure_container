"""
Unit tests for Resume Tailoring keyword tracking functionality.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.resume_tailoring import ResumeTailoringService


class TestKeywordDetection:
    """Test keyword detection and categorization methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ResumeTailoringService()

    def test_detect_keywords_presence_basic(self):
        """Test basic keyword detection in HTML content."""
        html_content = """
        <div>
            <p>Experience with Python and Django framework</p>
            <p>Proficient in Docker containerization</p>
        </div>
        """
        keywords = ["Python", "Django", "Kubernetes", "Docker"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        assert "Python" in found
        assert "Django" in found
        assert "Docker" in found
        assert "Kubernetes" not in found
        assert len(found) == 3

    def test_detect_keywords_with_variations(self):
        """Test keyword detection with variations (CI/CD, Node.js, etc)."""
        html_content = """
        <div>
            <p>Experience with CI-CD pipelines</p>
            <p>NodeJS development experience</p>
            <p>Machine Learning and AI expertise</p>
        </div>
        """
        keywords = ["CI/CD", "Node.js", "Machine Learning", "Deep Learning"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        # Should match CI-CD as variant of CI/CD
        assert "CI/CD" in found
        # Should match NodeJS as variant of Node.js
        assert "Node.js" in found
        # Should match exactly
        assert "Machine Learning" in found
        # Should not match
        assert "Deep Learning" not in found

    def test_detect_keywords_with_abbreviations(self):
        """Test keyword detection with abbreviations (ML for Machine Learning)."""
        html_content = """
        <div>
            <p>Experience with ML models and AI systems</p>
            <p>Building REST APIs</p>
        </div>
        """
        keywords = ["Machine Learning", "Artificial Intelligence", "API", "GraphQL"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        # Should match ML as abbreviation for Machine Learning
        assert "Machine Learning" in found
        # Should match AI as abbreviation for Artificial Intelligence
        assert "Artificial Intelligence" in found
        # Should match API
        assert "API" in found
        # Should not match GraphQL
        assert "GraphQL" not in found

    def test_create_keyword_patterns(self):
        """Test creation of keyword pattern variations."""
        # Test CI/CD variations
        patterns = self.service._create_keyword_patterns("CI/CD")
        assert len(patterns) >= 4  # Original + 3 variations

        # Test Node.js variations
        patterns = self.service._create_keyword_patterns("Node.js")
        assert len(patterns) >= 3  # Original + 2 variations

        # Test Machine Learning with abbreviation
        patterns = self.service._create_keyword_patterns("Machine Learning")
        assert any("ML" in p for p in patterns)

        # Test simple keyword
        patterns = self.service._create_keyword_patterns("Python")
        assert len(patterns) >= 1

    def test_categorize_keywords_all_scenarios(self):
        """Test keyword categorization into four states."""
        originally_covered = ["Python", "Django", "PostgreSQL"]
        currently_covered = ["PostgreSQL", "Docker", "AWS"]
        covered_keywords = ["Python", "Django", "PostgreSQL", "Redis"]
        missing_keywords = ["Docker", "AWS", "Kubernetes"]

        result = self.service._categorize_keywords(
            originally_covered,
            currently_covered,
            covered_keywords,
            missing_keywords
        )

        # Keywords that were covered and remain
        assert result["still_covered"] == ["PostgreSQL"]

        # Keywords that were covered but removed
        assert set(result["removed"]) == {"Python", "Django"}

        # Keywords that were missing but added
        assert set(result["newly_added"]) == {"Docker", "AWS"}

        # Keywords that were missing and remain missing
        assert result["still_missing"] == ["Kubernetes"]

    def test_categorize_keywords_with_warnings(self):
        """Test that warnings are logged when keywords are removed."""
        originally_covered = ["Python", "Django"]
        currently_covered = []  # All removed
        covered_keywords = ["Python", "Django"]
        missing_keywords = ["Docker"]

        with patch('src.services.resume_tailoring.logger') as mock_logger:
            self.service._categorize_keywords(
                originally_covered,
                currently_covered,
                covered_keywords,
                missing_keywords
            )

            # Check that warning was logged
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "Keywords removed during optimization" in warning_msg
            assert "Python" in warning_msg
            assert "Django" in warning_msg

    def test_categorize_keywords_empty_lists(self):
        """Test categorization with empty keyword lists."""
        result = self.service._categorize_keywords(
            originally_covered=[],
            currently_covered=[],
            covered_keywords=[],
            missing_keywords=[]
        )

        assert result["still_covered"] == []
        assert result["removed"] == []
        assert result["newly_added"] == []
        assert result["still_missing"] == []

    def test_categorize_keywords_none_values(self):
        """Test categorization with None values."""
        result = self.service._categorize_keywords(
            originally_covered=[],
            currently_covered=["Python"],
            covered_keywords=None,
            missing_keywords=None
        )

        assert result["still_covered"] == []
        assert result["removed"] == []
        assert result["newly_added"] == []
        assert result["still_missing"] == []

    def test_detect_keywords_case_insensitive(self):
        """Test that keyword detection is case-insensitive."""
        html_content = """
        <div>
            <p>experience with python and DJANGO</p>
            <p>Docker and kubernetes</p>
        </div>
        """
        keywords = ["Python", "Django", "Docker", "Kubernetes"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        assert "Python" in found
        assert "Django" in found
        assert "Docker" in found
        assert "Kubernetes" in found

    def test_detect_keywords_word_boundaries(self):
        """Test that keyword detection respects word boundaries."""
        html_content = """
        <div>
            <p>Using Python for development</p>
            <p>Not using Pythonic code</p>
            <p>Javscript and Java</p>
        </div>
        """
        keywords = ["Python", "Java"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        assert "Python" in found
        assert "Java" in found
        assert len(found) == 2

    def test_special_characters_in_keywords(self):
        """Test keywords with special characters like C++, C#."""
        html_content = """
        <div>
            <p>Programming in C++ and C#</p>
            <p>Using .NET framework</p>
        </div>
        """
        keywords = ["C++", "C#", ".NET", "Java"]

        found = self.service._detect_keywords_presence(html_content, keywords)

        # Note: These might need special handling in the actual implementation
        assert "C++" in found
        assert "C#" in found
        assert ".NET" in found
        assert "Java" not in found


class TestKeywordTrackingIntegration:
    """Test integration of keyword tracking with resume processing."""

    @pytest.mark.asyncio
    async def test_process_optimization_result_with_keyword_tracking(self):
        """Test that _process_optimization_result_v2 properly tracks keywords."""
        service = ResumeTailoringService()

        # Mock the optimized result from LLM
        optimized_result = {
            "optimized_resume": """
            <div>
                <p>Python developer with Docker expertise</p>
                <p>Experience with AWS cloud services</p>
            </div>
            """,
            "applied_improvements": ["Added Docker", "Added AWS"],
            "llm_processing_time_ms": 2000
        }

        original_resume = """
        <div>
            <p>Python and Django developer</p>
        </div>
        """

        instructions = {
            "analysis": {
                "resume_sections": {"summary": "Summary", "experience": "Experience"},
                "section_metadata": {"total_sections": 2}
            }
        }

        # Test with keywords being removed
        result = await service._process_optimization_result_v2(
            optimized_result=optimized_result,
            original_resume=original_resume,
            output_language="English",
            stage_timings={"instruction_compilation_ms": 300, "resume_writing_ms": 2000},
            instructions=instructions,
            covered_keywords=["Python", "Django"],
            missing_keywords=["Docker", "AWS", "Kubernetes"]
        )

        # Check keyword tracking
        assert "keyword_tracking" in result
        tracking = result["keyword_tracking"]

        # Python should be still covered
        assert "Python" in tracking["still_covered"]

        # Django was removed (not in optimized)
        assert "Django" in tracking["removed"]

        # Docker and AWS were added
        assert "Docker" in tracking["newly_added"]
        assert "AWS" in tracking["newly_added"]

        # Kubernetes still missing
        assert "Kubernetes" in tracking["still_missing"]

        # Should have warning about removed keyword
        assert len(tracking["warnings"]) > 0
        assert "Django" in tracking["warnings"][0]
