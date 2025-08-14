"""
Unit tests for Resume Structure Analyzer Service.
Test IDs: RS-001-UT to RS-005-UT
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.resume_structure_analyzer import (
    ResumeStructure,
    ResumeStructureAnalyzer,
    StandardSections,
    StructureMetadata,
)


class TestResumeStructureAnalyzer:
    """Unit tests for resume structure analysis functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing."""
        return ResumeStructureAnalyzer()

    @pytest.fixture
    def sample_resume_html(self):
        """Sample resume HTML for testing."""
        return """
        <html>
            <h2>Professional Summary</h2>
            <p>Experienced software engineer...</p>
            <h2>Technical Skills</h2>
            <ul><li>Python</li><li>FastAPI</li></ul>
            <h2>Work Experience</h2>
            <div>Senior Developer at Tech Corp (2020-2023)</div>
            <h2>Education</h2>
            <div>BS Computer Science, MIT (2016-2020)</div>
        </html>
        """

    @pytest.mark.asyncio
    async def test_RS_001_UT_basic_structure_analysis(self, analyzer, sample_resume_html):
        """
        Test ID: RS-001-UT - Basic structure analysis functionality.
        Verify that the analyzer correctly identifies resume sections.
        """
        # Mock LLM response with proper structure
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "standard_sections": {
                                    "summary": "Professional Summary",
                                    "skills": "Technical Skills",
                                    "experience": "Work Experience",
                                    "education": "Education",
                                    "certifications": None,
                                    "projects": None,
                                },
                                "custom_sections": ["Languages", "Publications"],
                                "metadata": {
                                    "total_experience_entries": 3,
                                    "total_education_entries": 1,
                                    "has_quantified_achievements": True,
                                    "estimated_length": "2 pages",
                                },
                            }
                        )
                    }
                }
            ]
        }

        with patch.object(
            analyzer.llm_client, "chat_completion", return_value=mock_response
        ) as mock_llm:
            result = await analyzer.analyze_structure(sample_resume_html)

            # Verify LLM was called
            mock_llm.assert_called_once()

            # Verify result structure
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Professional Summary"
            assert result.standard_sections.skills == "Technical Skills"
            assert result.standard_sections.experience == "Work Experience"
            assert result.standard_sections.education == "Education"
            assert result.standard_sections.certifications is None
            assert result.standard_sections.projects is None

            # Verify custom sections
            assert len(result.custom_sections) == 2
            assert "Languages" in result.custom_sections
            assert "Publications" in result.custom_sections

            # Verify metadata
            assert result.metadata.total_experience_entries == 3
            assert result.metadata.total_education_entries == 1
            assert result.metadata.has_quantified_achievements is True
            assert result.metadata.estimated_length == "2 pages"

    @pytest.mark.asyncio
    async def test_RS_002_UT_prompt_template_validation(self, analyzer):
        """
        Test ID: RS-002-UT - Prompt template validation.
        Verify that prompt template is properly loaded and formatted.
        """
        # Check prompt template exists
        assert analyzer.prompt_template is not None
        assert "system" in analyzer.prompt_template
        assert "user" in analyzer.prompt_template

        # Verify user prompt has placeholder
        assert "{resume_html}" in analyzer.prompt_template["user"]

        # Test prompt template structure
        fallback_template = analyzer._get_fallback_prompt_template()
        assert "system" in fallback_template
        assert "user" in fallback_template
        assert "{resume_html}" in fallback_template["user"]

    @pytest.mark.asyncio
    async def test_RS_003_UT_json_parsing_validation(self, analyzer, sample_resume_html):
        """
        Test ID: RS-003-UT - JSON parsing and validation.
        Verify proper handling of JSON parsing errors.
        """
        # Test with malformed JSON response
        mock_response_malformed = {
            "choices": [{"message": {"content": "```json\n{invalid json}```"}}]
        }

        with patch.object(
            analyzer.llm_client, "chat_completion", return_value=mock_response_malformed
        ):
            with pytest.raises(json.JSONDecodeError):
                await analyzer._analyze_once(sample_resume_html)

        # Test with valid JSON in markdown code block
        valid_json_in_markdown = {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"standard_sections": {"summary": "Summary"}, '
                        '"custom_sections": [], '
                        '"metadata": {"total_experience_entries": 0, '
                        '"total_education_entries": 0, '
                        '"has_quantified_achievements": false, '
                        '"estimated_length": "1 page"}}```'
                    }
                }
            ]
        }

        with patch.object(
            analyzer.llm_client, "chat_completion", return_value=valid_json_in_markdown
        ):
            result = await analyzer._analyze_once(sample_resume_html)
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Summary"

    @pytest.mark.asyncio
    async def test_RS_004_UT_retry_mechanism(self, analyzer, sample_resume_html):
        """
        Test ID: RS-004-UT - Retry mechanism validation.
        Verify that the analyzer retries failed attempts correctly.
        """
        # Set shorter delays for testing
        analyzer.retry_delay = 0.01
        analyzer.max_retries = 3

        # Create a mock that fails twice then succeeds
        call_count = 0

        async def mock_analyze_once(*args):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Temporary failure {call_count}")
            return ResumeStructure(
                standard_sections=StandardSections(summary="Success After Retries"),
                custom_sections=[],
                metadata=StructureMetadata(),
            )

        with patch.object(analyzer, "_analyze_once", side_effect=mock_analyze_once):
            result = await analyzer.analyze_structure(sample_resume_html)

            # Verify it retried and succeeded
            assert call_count == 3
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Success After Retries"

    @pytest.mark.asyncio
    async def test_RS_005_UT_fallback_structure_generation(self, analyzer, sample_resume_html):
        """
        Test ID: RS-005-UT - Fallback structure generation.
        Verify that fallback structure is returned when all retries fail.
        """
        # Set shorter delays for testing
        analyzer.retry_delay = 0.01
        analyzer.max_retries = 3

        # Mock to always fail
        with patch.object(
            analyzer, "_analyze_once", side_effect=Exception("Permanent failure")
        ):
            result = await analyzer.analyze_structure(sample_resume_html)

            # Verify fallback structure is returned
            assert isinstance(result, ResumeStructure)
            assert result.standard_sections.summary == "Professional Summary"
            assert result.standard_sections.skills == "Skills"
            assert result.standard_sections.experience == "Experience"
            assert result.standard_sections.education == "Education"
            assert result.standard_sections.certifications is None
            assert result.standard_sections.projects is None
            assert len(result.custom_sections) == 0
            assert result.metadata.estimated_length == "unknown"
            assert result.metadata.total_experience_entries == 0
            assert result.metadata.total_education_entries == 0
            assert result.metadata.has_quantified_achievements is False

    @pytest.mark.asyncio
    async def test_timeout_handling(self, analyzer, sample_resume_html):
        """Test timeout handling in structure analysis."""
        # Mock LLM to take too long
        async def slow_completion(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout
            return {"choices": [{"message": {"content": "{}"}}]}

        with patch.object(analyzer.llm_client, "chat_completion", side_effect=slow_completion):
            # Should timeout and raise
            with pytest.raises(asyncio.TimeoutError):
                await analyzer._analyze_once(sample_resume_html)

    @pytest.mark.asyncio
    async def test_html_truncation(self, analyzer):
        """Test that large HTML is properly truncated."""
        # Create very large HTML
        large_html = "<html>" + "x" * 15000 + "</html>"

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "standard_sections": {"summary": "Test"},
                                "custom_sections": [],
                                "metadata": {
                                    "total_experience_entries": 0,
                                    "total_education_entries": 0,
                                    "has_quantified_achievements": False,
                                    "estimated_length": "unknown",
                                },
                            }
                        )
                    }
                }
            ]
        }

        with patch.object(
            analyzer.llm_client, "chat_completion", return_value=mock_response
        ) as mock_llm:
            await analyzer._analyze_once(large_html)

            # Verify the HTML was truncated in the prompt
            call_args = mock_llm.call_args
            messages = call_args[1]["messages"]
            user_message = messages[1]["content"]

            # Should contain truncation marker
            assert "... [content truncated] ..." in user_message

    def test_model_validation(self):
        """Test Pydantic model validation."""
        # Test valid structure
        valid_structure = ResumeStructure(
            standard_sections=StandardSections(summary="Summary"),
            custom_sections=["Custom"],
            metadata=StructureMetadata(
                total_experience_entries=2,
                total_education_entries=1,
                has_quantified_achievements=True,
                estimated_length="2 pages",
            ),
        )
        assert valid_structure.standard_sections.summary == "Summary"

        # Test with missing optional fields
        minimal_structure = ResumeStructure(
            standard_sections=StandardSections(),
            custom_sections=[],
            metadata=StructureMetadata(),
        )
        assert minimal_structure.standard_sections.summary is None
        assert minimal_structure.metadata.total_experience_entries == 0
