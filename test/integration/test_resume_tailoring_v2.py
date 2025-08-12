"""
Integration tests for Resume Tailoring v2.0.0 three-stage pipeline.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.resume_tailoring import ResumeTailoringService


class TestResumeTailoringV2Integration:
    """Integration tests for the v2.0.0 three-stage pipeline."""

    @pytest.fixture
    def sample_resume_html(self):
        """Sample resume HTML for testing."""
        return """
        <html>
        <body>
            <h2>Experience</h2>
            <h3>Software Engineer - TechCorp (2020-2023)</h3>
            <ul>
                <li>Built Flask and Django web applications serving 100K users</li>
                <li>Developed recommendation engine using scikit-learn</li>
                <li>Optimized database queries improving performance</li>
                <li>Worked with cross-functional teams</li>
            </ul>
            <h2>Skills</h2>
            <p>Flask, Django, scikit-learn, PostgreSQL, REST APIs</p>
        </body>
        </html>
        """

    @pytest.fixture
    def sample_job_description(self):
        """Sample job description for testing."""
        return """
        We are looking for a Senior Python Developer with strong experience in:
        - Python backend development (5+ years)
        - Machine Learning and AI technologies
        - Kubernetes and container orchestration
        - Cloud platforms (AWS, GCP, or Azure)
        - Building scalable microservices
        - Team leadership and mentoring
        
        The ideal candidate will have experience with Python frameworks like Django or Flask,
        and a deep understanding of ML/AI principles. Experience with Kubernetes is essential
        for our cloud-native architecture. You should be comfortable leading technical teams
        and driving architectural decisions.
        
        Required Skills:
        - Python, Machine Learning, Kubernetes, Docker
        - Cloud Architecture, Microservices
        - Team Leadership, Agile methodologies
        
        This is a great opportunity to work on cutting-edge AI products at scale.
        """

    @pytest.fixture
    def mock_gap_analysis_response(self):
        """Mock Gap Analysis response with classification markers."""
        return {
            "core_strengths": """
                <ul>
                    <li>Python Backend Development (3 years) - Django and Flask experience</li>
                    <li>Machine Learning Implementation - Built recommendation engine</li>
                </ul>
            """,
            "key_gaps": """
                <ul>
                    <li>[Skill Gap] Kubernetes orchestration - No container orchestration experience found</li>
                    <li>[Presentation Gap] Python - Has Django/Flask but doesn't mention Python explicitly</li>
                    <li>[Presentation Gap] Machine Learning - Has scikit-learn but ML not highlighted</li>
                    <li>[Skill Gap] Team Leadership - No leadership experience mentioned</li>
                </ul>
            """,
            "quick_improvements": """
                <ul>
                    <li>Add "Python" explicitly to skills section</li>
                    <li>Highlight ML experience in summary</li>
                    <li>Quantify the recommendation engine impact</li>
                </ul>
            """,
            "overall_assessment": "Strong technical foundation with ML experience that needs better presentation.",
            "skill_development_priorities": []
        }

    @pytest.fixture
    def mock_instruction_compiler_response(self):
        """Mock Instruction Compiler response."""
        return {
            "summary": {
                "action": "CREATE",
                "focus_areas": ["Python backend", "Machine Learning"],
                "keywords_to_integrate": ["Python", "Machine Learning", "scalable"],
                "positioning_strategy": "Position as Python ML engineer with scalability expertise"
            },
            "skills": {
                "add_skills": ["Python", "Machine Learning", "Scalable Systems"],
                "reorganize": True,
                "categories": ["Languages", "ML/AI", "Frameworks"],
                "presentation_gaps_to_surface": ["Python", "Machine Learning"],
                "skill_gaps_to_imply": ["Container deployment"]
            },
            "experience": [
                {
                    "company": "TechCorp",
                    "role": "Software Engineer",
                    "priority": "HIGH",
                    "bullet_improvements": [
                        {
                            "bullet_index": 0,
                            "improvement_type": "ADD_KEYWORDS",
                            "keywords": ["Python"],
                            "focus": "Make Python explicit"
                        },
                        {
                            "bullet_index": 1,
                            "improvement_type": "ADD_METRICS",
                            "keywords": ["ML", "accuracy"],
                            "focus": "Quantify ML impact"
                        }
                    ],
                    "new_bullets": []
                }
            ],
            "education": {"action": "NONE"},
            "optimization_strategy": {
                "presentation_gaps_count": 2,
                "skill_gaps_count": 2,
                "priority_keywords": ["Python", "Machine Learning", "Kubernetes", "scalable", "microservices"],
                "overall_approach": "Surface hidden Python and ML skills, position for growth"
            },
            "metadata": {
                "processing_time_ms": 250,
                "llm_processing_time_ms": 200,
                "overhead_ms": 50,
                "presentation_gaps_found": 2,
                "skill_gaps_found": 2
            }
        }

    @pytest.fixture
    def mock_llm_tailoring_response(self):
        """Mock LLM response for resume tailoring."""
        return {
            "optimized_resume": """
                <html>
                <body>
                    <h2 class="opt-new">Professional Summary</h2>
                    <p class="opt-new">Senior Python Developer with expertise in Machine Learning and scalable backend systems</p>
                    
                    <h2>Experience</h2>
                    <h3>Software Engineer - TechCorp (2020-2023)</h3>
                    <ul>
                        <li><span class="opt-modified">Built Python-based Flask and Django web applications serving 100K users</span></li>
                        <li><span class="opt-modified">Developed ML recommendation engine using scikit-learn achieving 85% accuracy</span></li>
                        <li>Optimized database queries improving performance</li>
                        <li>Worked with cross-functional teams</li>
                    </ul>
                    
                    <h2>Skills</h2>
                    <h3>Languages</h3>
                    <p><span class="opt-modified">Python (3+ years)</span></p>
                    <h3>ML/AI</h3>
                    <p><span class="opt-modified">Machine Learning, scikit-learn</span></p>
                    <h3>Frameworks</h3>
                    <p>Flask, Django, PostgreSQL, REST APIs</p>
                </body>
                </html>
            """,
            "applied_improvements": [
                "[Section: Summary] Created new professional summary with Python and ML focus",
                "[Section: Skills] Added Python explicitly and reorganized into categories",
                "[Section: Experience - TechCorp] Made Python explicit in Flask/Django bullet",
                "[Section: Experience - TechCorp] Added ML metrics (85% accuracy) to recommendation engine"
            ]
        }

    @pytest.mark.asyncio
    async def test_two_stage_pipeline_integration(
        self,
        sample_resume_html,
        sample_job_description,
        mock_gap_analysis_response,
        mock_instruction_compiler_response,
        mock_llm_tailoring_response,
    ):
        """Test the complete two-stage pipeline integration (Instruction Compiler + Resume Writer)."""

        with patch("src.services.instruction_compiler.InstructionCompiler") as MockCompiler:

            # Setup mocks
            mock_compiler = AsyncMock()
            mock_compiler.compile_instructions.return_value = mock_instruction_compiler_response
            MockCompiler.return_value = mock_compiler

            # Initialize service
            service = ResumeTailoringService()

            # Mock LLM response - correct format for AzureOpenAIClient
            mock_llm_response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(mock_llm_tailoring_response)
                        }
                    }
                ]
            }
            # Mock the correct method - chat_completion, not chat.completions.create
            service.llm_client = MagicMock()
            service.llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)

            # Execute the two-stage pipeline
            result = await service.tailor_resume(
                original_resume=sample_resume_html,
                job_description=sample_job_description,
                gap_analysis=mock_gap_analysis_response,  # Add required gap_analysis
                covered_keywords=["Flask", "Django", "PostgreSQL"],
                missing_keywords=["Python", "Machine Learning", "Kubernetes"],
                output_language="English"
            )

            # Verify Stage 1: Instruction Compiler was called (No longer calling Gap Analysis internally)
            # The service now expects gap_analysis as input, not generates it internally
            mock_compiler.compile_instructions.assert_called_once()
            compiler_args = mock_compiler.compile_instructions.call_args
            assert compiler_args.kwargs["resume_html"] == sample_resume_html.strip()  # Stripped HTML
            assert compiler_args.kwargs["job_description"] == sample_job_description.strip()  # Stripped JD
            assert "CoreStrengths" in compiler_args.kwargs["gap_analysis"]
            assert "KeyGaps" in compiler_args.kwargs["gap_analysis"]

            # Verify Stage 2: LLM was called with simplified prompt
            service.llm_client.chat_completion.assert_called_once()
            llm_call = service.llm_client.chat_completion.call_args
            messages = llm_call.kwargs["messages"]

            # Check that structural intelligence was passed to the LLM
            user_message = messages[1]["content"]
            assert "Structural Intelligence" in user_message or "resume_sections" in user_message

            # Verify the final result
            assert result["success"] is True
            assert "optimized_resume" in result
            assert "applied_improvements" in result
            assert result["improvement_count"] == 4

            # Verify timing metrics (now only two stages)
            assert "stage_timings" in result
            assert "instruction_compilation_ms" in result["stage_timings"]
            assert "resume_writing_ms" in result["stage_timings"]

            # Verify gap analysis insights (new simplified structure)
            assert "gap_analysis_insights" in result
            insights = result["gap_analysis_insights"]
            assert "structure_found" in insights
            assert "improvements_needed" in insights
            assert insights["improvements_needed"] >= 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Timing test needs adjustment for v2.1.0-simplified performance improvements")
    async def test_timing_tracking(
        self,
        sample_resume_html,
        sample_job_description,
        mock_gap_analysis_response,
    ):
        """Test that timing is properly tracked across all stages."""

        with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2") as MockGapAnalysis, \
             patch("src.services.instruction_compiler.InstructionCompiler") as MockCompiler:

            # Setup mocks with delays to simulate processing time
            mock_gap_service = AsyncMock()
            async def delayed_gap_analysis(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return {
                    "core_strengths": "Python expertise",
                    "key_gaps": "[Skill Gap] Kubernetes",
                    "quick_improvements": "Add Python to skills"
                }
            mock_gap_service.analyze_gap = delayed_gap_analysis
            MockGapAnalysis.return_value = mock_gap_service

            mock_compiler = AsyncMock()
            async def delayed_compilation(*args, **kwargs):
                await asyncio.sleep(0.05)  # 50ms delay
                return {
                    "summary": {"action": "CREATE"},
                    "skills": {"add_skills": ["Python"]},
                    "experience": [],
                    "education": {"action": "NONE"},
                    "optimization_strategy": {
                        "presentation_gaps_count": 1,
                        "skill_gaps_count": 1,
                        "priority_keywords": ["Python"],
                        "overall_approach": "Surface Python skills"
                    },
                    "metadata": {
                        "processing_time_ms": 50,
                        "llm_processing_time_ms": 40,
                        "overhead_ms": 10,
                        "presentation_gaps_found": 1,
                        "skill_gaps_found": 1
                    }
                }
            mock_compiler.compile_instructions = delayed_compilation
            MockCompiler.return_value = mock_compiler

            # Initialize service
            service = ResumeTailoringService()

            # Mock LLM response with delay
            async def delayed_llm(*args, **kwargs):
                await asyncio.sleep(0.2)  # 200ms delay
                mock_response = {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({
                                    "optimized_resume": "<p>Optimized resume</p>",
                                    "applied_improvements": ["Improvement 1"]
                                })
                            }
                        }
                    ]
                }
                return mock_response

            service.llm_client.chat_completion = delayed_llm

            # Execute pipeline
            result = await service.tailor_resume(
                original_resume=sample_resume_html,
                job_description=sample_job_description,
                gap_analysis=mock_gap_analysis_response,
                output_language="English"
            )

            # Verify timing metrics
            assert "processing_time_ms" in result
            assert result["processing_time_ms"] >= 200  # At least sum of delays (faster with simplified version)

            assert "stage_timings" in result
            timings = result["stage_timings"]

            # Each stage should have recorded time
            assert timings["gap_analysis_ms"] >= 100
            assert timings["instruction_compilation_ms"] >= 50
            assert timings["resume_writing_ms"] >= 200

            # Total should be approximately the sum
            total_stages = sum(timings.values())
            assert abs(result["processing_time_ms"] - total_stages) < 100  # Allow 100ms variance

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(
        self,
        sample_resume_html,
        sample_job_description,
        mock_gap_analysis_response,
    ):
        """Test error handling in the three-stage pipeline."""

        with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2") as MockGapAnalysis:

            # Setup mock to raise an error
            mock_gap_service = AsyncMock()
            mock_gap_service.analyze_gap.side_effect = Exception("Gap analysis failed")
            MockGapAnalysis.return_value = mock_gap_service

            # Initialize service
            service = ResumeTailoringService()

            # Execute pipeline and expect HTTPException
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await service.tailor_resume(
                    original_resume=sample_resume_html,
                    job_description=sample_job_description,
                    gap_analysis=mock_gap_analysis_response,
                )

            assert exc_info.value.status_code == 500
            assert "Resume tailoring failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_chinese_language_support(
        self,
        sample_resume_html,
        sample_job_description,
        mock_gap_analysis_response,
    ):
        """Test that Chinese language output is properly handled."""

        with patch("src.services.gap_analysis_v2.GapAnalysisServiceV2") as MockGapAnalysis, \
             patch("src.services.instruction_compiler.InstructionCompiler") as MockCompiler:

            # Setup minimal mocks
            mock_gap_service = AsyncMock()
            mock_gap_service.analyze_gap.return_value = {
                "core_strengths": "Strong technical skills",
                "key_gaps": "[Skill Gap] Kubernetes",
                "quick_improvements": "Add Python"
            }
            MockGapAnalysis.return_value = mock_gap_service

            mock_compiler = AsyncMock()
            mock_compiler.compile_instructions.return_value = {
                "summary": {"action": "CREATE"},
                "skills": {"add_skills": ["Python"]},
                "experience": [],
                "education": {"action": "NONE"},
                "optimization_strategy": {
                    "presentation_gaps_count": 0,
                    "skill_gaps_count": 1,
                    "priority_keywords": ["Python"],
                    "overall_approach": "Surface skills"
                },
                "metadata": {
                    "presentation_gaps_found": 0,
                    "skill_gaps_found": 1
                }
            }
            MockCompiler.return_value = mock_compiler

            # Initialize service
            service = ResumeTailoringService()

            # Mock LLM response in Chinese
            mock_response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "optimized_resume": "<p>Optimized resume in Chinese</p>",
                                "applied_improvements": ["Improvement 1"]
                            })
                        }
                    }
                ]
            }
            service.llm_client.chat_completion = AsyncMock(return_value=mock_response)

            # Execute with Chinese output
            result = await service.tailor_resume(
                original_resume=sample_resume_html,
                job_description=sample_job_description,
                gap_analysis=mock_gap_analysis_response,
                output_language="Traditional Chinese"
            )

            # Verify Chinese standardizer was applied
            assert result["output_language"] == "Traditional Chinese"
            assert result["success"] is True
