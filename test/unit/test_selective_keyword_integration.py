"""
Unit tests for selective keyword integration in Resume Tailoring v2.1.1.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.resume_tailoring import ResumeTailoringService


class TestSelectiveKeywordIntegration:
    """Test that keywords are selectively integrated based on relevance."""

    @pytest.mark.asyncio
    async def test_selective_keyword_integration_software_to_customer_success(self):
        """
        Test that irrelevant keywords are not forced into resume.

        Scenario: Software Engineer applying for Customer Success Manager role.
        Expected: Technical keywords added, but industry-specific terms skipped.
        """
        service = ResumeTailoringService()

        # Mock dependencies
        service.llm_client = MagicMock()
        service.prompt_service = MagicMock()
        service.instruction_compiler = MagicMock()

        # Setup test data - Software Engineer to Customer Success
        # Need to meet minimum length requirements
        job_description = """
        Customer Success Manager role at Veeva Systems, a Life Sciences company.
        Manage CSMs team, ensure renewals, handle escalations in clinical domain.
        Build strong relationships with customers and drive product adoption.
        Collaborate with cross-functional teams to deliver value.
        """*5  # Repeat to meet 200+ char requirement

        original_resume = """
        <html><body>
        <h2>Software Engineer</h2>
        <p>5 years developing Python applications with Django framework.</p>
        <p>Led team of developers, improved performance metrics.</p>
        <p>Experience with agile methodologies and continuous integration.</p>
        <p>Strong problem-solving skills and attention to detail.</p>
        </body></html>
        """*3  # Repeat to meet 200+ char requirement

        gap_analysis = {
            "CoreStrengths": "Technical leadership, Performance optimization",
            "KeyGaps": "[Skill Gap] Customer Success, [Skill Gap] Life Sciences",
            "QuickImprovements": "Emphasize team leadership",
            "covered_keywords": ["Python", "Django", "team", "performance", "metrics"],
            "missing_keywords": ["Customer Success", "Life Sciences", "Veeva",
                               "clinical", "CSMs", "renewals", "escalations"],
            "coverage_percentage": 42,
            "similarity_percentage": 35
        }

        # Mock instruction compiler response
        service.instruction_compiler.compile_instructions = AsyncMock(return_value={
            "analysis": {
                "resume_sections": {"experience": "Experience"},
                "section_metadata": {"total_sections": 1}
            },
            "execution_directives": ["Emphasize leadership"],
            "presentation_gaps": [],
            "quick_improvements": ["Emphasize team leadership"]
        })

        # Mock prompt service to return v2.1.1-selective prompt
        service.prompt_service.load_prompt = MagicMock(return_value={
            "prompts": {
                "system": "You are a resume optimizer. {output_language}",
                "user": """Optimize resume:
                Original: {original_resume}
                Job: {job_description}
                Instructions: {instructions_json}
                Covered: {covered_keywords}
                Missing: {missing_keywords}
                Strengths: {core_strengths}
                Gaps: {key_gaps}
                Improvements: {quick_improvements}
                Language: {output_language}"""
            },
            "llm_config": {}
        })

        # Mock LLM response - should skip irrelevant keywords
        mock_llm_response = {
            "optimized_resume": """
            <html><body>
            <h2 class="opt-modified">Technical Team Leader</h2>
            <p class="opt-modified">5 years developing Python applications with Django framework,
            leading cross-functional teams and managing stakeholder relationships.</p>
            <p>Led team of developers, improved performance metrics, handled escalations.</p>
            </body></html>
            """,
            "applied_improvements": [
                "[Quick Win: Leadership] Emphasized team leadership experience",
                "[Keywords: escalations] Integrated into experience",
                "[Keywords Skipped: Life Sciences, Veeva, clinical, CSMs] Not relevant to candidate background"
            ]
        }

        service.llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)

        # Mock the parsing
        with patch.object(service, '_parse_llm_response', return_value=mock_llm_response):
            # Execute the tailoring
            result = await service.tailor_resume(
                job_description=job_description,
                original_resume=original_resume,
                gap_analysis=gap_analysis,
                covered_keywords=gap_analysis["covered_keywords"],
                missing_keywords=gap_analysis["missing_keywords"],
                output_language="en"
            )

        # Verify that irrelevant keywords were tracked as skipped
        assert "[Keywords Skipped:" in str(result.get("applied_improvements", []))

        # If metrics were calculated, verify some keywords remain missing
        if "coverage_metrics" in result:
            after_missed = result["coverage_metrics"]["after"]["missed"]
            # Should still have industry-specific keywords missing
            assert "Life Sciences" in after_missed or "Veeva" in after_missed or "clinical" in after_missed
            assert len(after_missed) > 0, "Some keywords should remain missing"

    @pytest.mark.asyncio
    async def test_all_relevant_keywords_added(self):
        """
        Test that all relevant keywords are added when they make sense.

        Scenario: Python developer applying for Python/Django role.
        Expected: All technical keywords should be added.
        """
        service = ResumeTailoringService()

        # Mock dependencies
        service.llm_client = MagicMock()
        service.prompt_service = MagicMock()
        service.instruction_compiler = MagicMock()

        # Setup test data - Python dev to Python role
        job_description = """
        Senior Python Developer role at leading tech company.
        Requirements: Django, FastAPI, Docker, PostgreSQL, REST APIs.
        Experience with microservices architecture and cloud deployment.
        Strong understanding of software design patterns and best practices.
        """*5  # Repeat to meet length requirement

        original_resume = """
        <html><body>
        <h2>Python Developer</h2>
        <p>3 years Python development with web frameworks.</p>
        <p>Building scalable web applications and RESTful services.</p>
        <p>Experience with database design and optimization.</p>
        </body></html>
        """*3  # Repeat to meet length requirement

        gap_analysis = {
            "CoreStrengths": "Python expertise",
            "KeyGaps": "[Presentation Gap] Specific frameworks not mentioned",
            "QuickImprovements": "Add specific technologies",
            "covered_keywords": ["Python"],
            "missing_keywords": ["Django", "FastAPI", "Docker", "PostgreSQL", "REST APIs"],
            "coverage_percentage": 20,
            "similarity_percentage": 40
        }

        # Mock instruction compiler
        service.instruction_compiler.compile_instructions = AsyncMock(return_value={
            "analysis": {"resume_sections": {}, "section_metadata": {}},
            "execution_directives": [],
            "presentation_gaps": ["Specific frameworks"],
            "quick_improvements": ["Add specific technologies"]
        })

        # Mock prompt service
        service.prompt_service.load_prompt = MagicMock(return_value={
            "prompts": {
                "system": "Resume optimizer",
                "user": "Optimize: {original_resume}"
            },
            "llm_config": {}
        })

        # Mock LLM response - should add all relevant keywords
        mock_llm_response = {
            "optimized_resume": """
            <html><body>
            <h2>Python Developer</h2>
            <p class="opt-modified">3 years Python development with Django, FastAPI,
            working with Docker containers and PostgreSQL databases, building REST APIs.</p>
            </body></html>
            """,
            "applied_improvements": [
                "[Keywords: Django, FastAPI, Docker, PostgreSQL, REST APIs] Integrated into experience"
            ]
        }

        service.llm_client.chat_completion = AsyncMock(return_value=mock_llm_response)

        with patch.object(service, '_parse_llm_response', return_value=mock_llm_response):
            result = await service.tailor_resume(
                job_description=job_description,
                original_resume=original_resume,
                gap_analysis=gap_analysis,
                covered_keywords=gap_analysis["covered_keywords"],
                missing_keywords=gap_analysis["missing_keywords"],
                output_language="en"
            )

        # All technical keywords should be integrated
        improvements_str = str(result.get("applied_improvements", []))
        assert "Django" in improvements_str
        assert "FastAPI" in improvements_str
        assert "[Keywords Skipped:" not in improvements_str  # Nothing should be skipped
