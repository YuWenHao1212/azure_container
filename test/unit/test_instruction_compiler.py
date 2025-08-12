"""
Unit tests for Instruction Compiler Service.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.instruction_compiler import InstructionCompiler


class TestInstructionCompiler:
    """Test suite for InstructionCompiler."""

    @pytest.fixture
    def compiler(self):
        """Create an InstructionCompiler instance."""
        with patch("src.services.instruction_compiler.get_llm_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            compiler = InstructionCompiler()
            compiler.llm_client = mock_client
            return compiler

    @pytest.fixture
    def sample_gap_analysis(self):
        """Sample gap analysis with classification markers."""
        return {
            "CoreStrengths": "<ul><li>Python Backend Development (5 years)</li></ul>",
            "KeyGaps": (
                "<ul>"
                "<li>[Skill Gap] Kubernetes orchestration - No experience found</li>"
                "<li>[Presentation Gap] Machine Learning - Has scikit-learn but doesn't mention ML</li>"
                "</ul>"
            ),
            "QuickImprovements": "<ul><li>Add ML to skills section</li></ul>",
        }

    @pytest.fixture
    def sample_resume_html(self):
        """Sample resume HTML."""
        return """
        <h2>Experience</h2>
        <ul>
            <li>Built recommendation engine using scikit-learn</li>
            <li>Developed Python backend services</li>
        </ul>
        """

    @pytest.fixture
    def sample_job_description(self):
        """Sample job description."""
        return "Looking for ML engineer with Python, Kubernetes, and Machine Learning experience."

    def test_compiler_initialization(self, compiler):
        """Test that InstructionCompiler initializes correctly."""
        assert compiler is not None
        assert compiler.prompt_version == "v1.0.0"
        assert compiler.llm_client is not None

    @pytest.mark.asyncio
    async def test_compile_instructions_success(
        self, compiler, sample_gap_analysis, sample_resume_html, sample_job_description
    ):
        """Test successful instruction compilation."""
        # Mock LLM response - correct format for AzureOpenAIClient
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": {
                                    "action": "MODIFY",
                                    "focus_areas": ["Machine Learning", "Python"],
                                    "keywords_to_integrate": ["ML", "Kubernetes"],
                                    "positioning_strategy": "Emphasize ML experience",
                                },
                                "skills": {
                                    "add_skills": ["Machine Learning", "scikit-learn"],
                                    "reorganize": True,
                                    "categories": ["ML/AI", "Backend"],
                                    "presentation_gaps_to_surface": ["Machine Learning"],
                                    "skill_gaps_to_imply": ["Container orchestration"],
                                },
                                "experience": [],
                                "education": {"action": "NONE"},
                                "optimization_strategy": {
                                    "presentation_gaps_count": 1,
                                    "skill_gaps_count": 1,
                                    "priority_keywords": ["ML", "Python"],
                                    "overall_approach": "Surface ML skills",
                                },
                            }
                        )
                    }
                }
            ]
        }
        compiler.llm_client.chat_completion.return_value = mock_response

        # Test compilation
        instructions = await compiler.compile_instructions(
            resume_html=sample_resume_html,
            job_description=sample_job_description,
            gap_analysis=sample_gap_analysis,
            covered_keywords=["Python"],
            missing_keywords=["Machine Learning", "Kubernetes"],
        )

        # Verify results
        assert instructions is not None
        assert instructions["summary"]["action"] == "MODIFY"
        assert "Machine Learning" in instructions["skills"]["add_skills"]
        assert instructions["metadata"]["presentation_gaps_found"] == 1
        assert instructions["metadata"]["skill_gaps_found"] == 1

        # Verify timing information is present
        assert "processing_time_ms" in instructions["metadata"]
        assert "llm_processing_time_ms" in instructions["metadata"]
        assert "overhead_ms" in instructions["metadata"]
        assert instructions["metadata"]["processing_time_ms"] >= 0
        assert instructions["metadata"]["llm_processing_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_compile_instructions_with_json_markdown(
        self, compiler, sample_gap_analysis, sample_resume_html, sample_job_description
    ):
        """Test handling of JSON wrapped in markdown code blocks."""
        # Mock LLM response with markdown
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": """```json
                        {
                            "summary": {"action": "CREATE"},
                            "skills": {"add_skills": []},
                            "experience": [],
                            "education": {"action": "NONE"},
                            "optimization_strategy": {}
                        }
                        ```"""
                    }
                }
            ]
        }
        compiler.llm_client.chat_completion.return_value = mock_response

        # Test compilation
        instructions = await compiler.compile_instructions(
            resume_html=sample_resume_html,
            job_description=sample_job_description,
            gap_analysis=sample_gap_analysis,
            covered_keywords=[],
            missing_keywords=[],
        )

        # Verify JSON was parsed correctly
        assert instructions["summary"]["action"] == "CREATE"

    @pytest.mark.asyncio
    async def test_compile_instructions_fallback(
        self, compiler, sample_gap_analysis, sample_resume_html, sample_job_description
    ):
        """Test fallback instructions when JSON parsing fails."""
        # Mock LLM response with invalid JSON
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Invalid JSON response"
                    }
                }
            ]
        }
        compiler.llm_client.chat_completion.return_value = mock_response

        # Test compilation
        instructions = await compiler.compile_instructions(
            resume_html=sample_resume_html,
            job_description=sample_job_description,
            gap_analysis=sample_gap_analysis,
            covered_keywords=["Python"],
            missing_keywords=["ML", "K8s"],
        )

        # Verify fallback instructions were created
        assert instructions is not None
        assert "summary" in instructions
        assert "skills" in instructions
        assert instructions["optimization_strategy"]["presentation_gaps_count"] == 1
        assert instructions["optimization_strategy"]["skill_gaps_count"] == 1

    def test_count_gap_type(self, compiler):
        """Test gap type counting."""
        key_gaps = (
            "[Skill Gap] K8s - Missing. "
            "[Presentation Gap] ML - Hidden. "
            "[Skill Gap] Docker - Missing."
        )

        assert compiler._count_gap_type(key_gaps, "[Skill Gap]") == 2
        assert compiler._count_gap_type(key_gaps, "[Presentation Gap]") == 1
        assert compiler._count_gap_type("", "[Skill Gap]") == 0
        assert compiler._count_gap_type(None, "[Skill Gap]") == 0

    def test_validate_instructions(self, compiler):
        """Test instruction validation and field completion."""
        # Incomplete instructions
        incomplete = {
            "summary": {"action": "MODIFY"},
            "experience": [],
        }

        # Validate
        validated = compiler._validate_instructions(incomplete)

        # Check that missing fields were added
        assert "skills" in validated
        assert "education" in validated
        assert "optimization_strategy" in validated
        assert validated["skills"]["reorganize"] is False
        assert validated["education"]["action"] == "NONE"

    @pytest.mark.asyncio
    async def test_timing_tracking(self, compiler, sample_gap_analysis):
        """Test that timing metrics are properly tracked."""
        # Mock a slow LLM response
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"summary": {"action": "CREATE"}})
                    }
                }
            ]
        }

        # Add artificial delay to simulate LLM processing
        async def delayed_create(*args, **kwargs):
            import asyncio
            await asyncio.sleep(0.1)  # 100ms delay
            return mock_response

        compiler.llm_client.chat_completion = delayed_create

        # Test compilation
        instructions = await compiler.compile_instructions(
            resume_html="<p>Test</p>",
            job_description="Test JD",
            gap_analysis=sample_gap_analysis,
            covered_keywords=[],
            missing_keywords=[],
        )

        # Verify timing metrics
        assert "processing_time_ms" in instructions["metadata"]
        assert "llm_processing_time_ms" in instructions["metadata"]
        assert "overhead_ms" in instructions["metadata"]

        # LLM processing should be at least 100ms due to our delay
        assert instructions["metadata"]["llm_processing_time_ms"] >= 100

        # Total processing time should be greater than LLM time
        assert instructions["metadata"]["processing_time_ms"] >= instructions["metadata"]["llm_processing_time_ms"]

        # Overhead should be the difference
        assert instructions["metadata"]["overhead_ms"] == (
            instructions["metadata"]["processing_time_ms"]
            - instructions["metadata"]["llm_processing_time_ms"]
        )

    def test_create_fallback_instructions(self, compiler):
        """Test fallback instruction creation."""
        core_strengths = "Python expertise"
        key_gaps = "[Skill Gap] K8s. [Presentation Gap] ML."
        quick_improvements = "Add summary section"
        missing_keywords = ["ML", "K8s", "Docker", "AWS", "GCP"]

        fallback = compiler._create_fallback_instructions(
            core_strengths, key_gaps, quick_improvements, missing_keywords
        )

        # Verify fallback structure
        assert fallback["summary"]["action"] == "CREATE"  # Due to "summary" in improvements
        assert len(fallback["skills"]["add_skills"]) <= 10
        assert fallback["optimization_strategy"]["presentation_gaps_count"] == 1
        assert fallback["optimization_strategy"]["skill_gaps_count"] == 1
        assert len(fallback["optimization_strategy"]["priority_keywords"]) == 5
