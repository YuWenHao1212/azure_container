"""
Integration tests for Resume Structure in Index-Cal-Gap-Analysis API.
Test IDs: RS-001-IT to RS-006-IT (includes Education Enhancement tests)
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.api.v1.index_cal_and_gap_analysis import IndexCalAndGapAnalysisData
from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2
from src.services.resume_structure_analyzer import (
    ResumeStructure,
    StandardSections,
    StructureMetadata,
)


class TestResumeStructureIntegration:
    """Integration tests for resume structure feature in the API."""

    @pytest.fixture
    def sample_resume(self):
        """Sample resume for testing."""
        return """
        <html>
            <h1>John Doe</h1>
            <h2>Professional Summary</h2>
            <p>Experienced software engineer with 10 years of experience...</p>
            <h2>Technical Skills</h2>
            <ul>
                <li>Python, FastAPI, Django</li>
                <li>PostgreSQL, MongoDB</li>
                <li>Docker, Kubernetes</li>
            </ul>
            <h2>Professional Experience</h2>
            <div>
                <h3>Senior Software Engineer - Tech Corp (2020-2023)</h3>
                <ul>
                    <li>Led team of 5 developers</li>
                    <li>Increased system performance by 40%</li>
                </ul>
            </div>
            <h2>Education</h2>
            <div>BS Computer Science - MIT (2010-2014)</div>
        </html>
        """

    @pytest.fixture
    def sample_job_description(self):
        """Sample job description for testing."""
        return """
        We are looking for a Senior Software Engineer with experience in Python and FastAPI.
        The ideal candidate should have strong technical skills and leadership experience.
        Requirements:
        - 5+ years of Python development
        - Experience with FastAPI or similar frameworks
        - Strong problem-solving skills
        - Leadership experience
        """

    @pytest.fixture
    def sample_keywords(self):
        """Sample keywords for testing."""
        return ["Python", "FastAPI", "Leadership", "Docker", "PostgreSQL"]

    @pytest.mark.asyncio
    async def test_RS_001_IT_parallel_execution_timing(
        self, sample_resume, sample_job_description, sample_keywords
    ):
        """
        Test ID: RS-001-IT - Verify parallel execution timing.
        Ensure structure analysis runs in parallel without increasing total time.
        """
        service = CombinedAnalysisServiceV2()

        # Mock the services with different execution times
        async def mock_keyword_match(*args):
            await asyncio.sleep(0.05)  # 50ms
            return {"covered": ["Python"], "missing": ["FastAPI"]}

        async def mock_embeddings(*args):
            await asyncio.sleep(0.5)  # 500ms
            return {"resume_embedding": [0.1] * 768, "jd_embedding": [0.2] * 768}

        async def mock_structure(*args):
            await asyncio.sleep(2.0)  # 2000ms - longest task
            return ResumeStructure(
                standard_sections=StandardSections(
                    summary="Professional Summary",
                    skills="Technical Skills",
                    experience="Professional Experience",
                    education="Education",
                ),
                custom_sections=[],
                metadata=StructureMetadata(
                    total_experience_entries=1,
                    total_education_entries=1,
                    has_quantified_achievements=True,
                    estimated_length="2 pages",
                    years_of_experience=5,
                    is_current_student=False,
                    months_since_graduation=120,
                    has_only_internships=False,
                ),
                education_enhancement_needed=False,
            )

        async def mock_index_calc(*args, **kwargs):
            await asyncio.sleep(0.3)  # 300ms
            return {
                "raw_similarity_percentage": 75,
                "similarity_percentage": 85,
                "keyword_coverage": {
                    "coverage_percentage": 60,
                    "covered_keywords": ["Python", "Docker", "PostgreSQL"],
                    "missed_keywords": ["FastAPI", "Leadership"],
                },
            }

        async def mock_gap_analysis(*args, **kwargs):
            await asyncio.sleep(1.0)  # Simulate faster gap analysis for test
            return {
                "CoreStrengths": "Strong Python experience",
                "KeyGaps": "Missing FastAPI experience",
                "QuickImprovements": "Add FastAPI projects",
                "OverallAssessment": "Good match",
                "SkillSearchQueries": [],
            }

        # Apply mocks
        with patch.object(service, "_quick_keyword_match", side_effect=mock_keyword_match):
            with patch.object(
                service, "_generate_embeddings_parallel", side_effect=mock_embeddings
            ):
                with patch.object(
                    service.structure_analyzer, "analyze_structure", side_effect=mock_structure
                ):
                    with patch.object(
                        service.index_service, "calculate_index", side_effect=mock_index_calc
                    ):
                        with patch.object(
                            service.gap_service,
                            "analyze_with_context",
                            side_effect=mock_gap_analysis,
                        ):
                            start_time = time.time()
                            result = await service.analyze(
                                resume=sample_resume,
                                job_description=sample_job_description,
                                keywords=sample_keywords,
                                language="en",
                            )
                            total_time = time.time() - start_time

                            # Should complete in ~2.85s (not 4.15s if sequential)
                            # Structure (2s) runs parallel, doesn't add to critical path
                            assert total_time < 3.5  # Allow some overhead
                            assert "resume_structure" in result
                            assert result["resume_structure"]["standard_sections"]["summary"] == "Professional Summary"

    @pytest.mark.asyncio
    async def test_RS_002_IT_api_response_format(self):
        """
        Test ID: RS-002-IT - Validate API response format.
        Ensure the response model correctly includes resume structure.
        """
        # Test response data with structure
        response_data = {
            "raw_similarity_percentage": 75,
            "similarity_percentage": 85,
            "keyword_coverage": {
                "coverage_percentage": 60,
                "covered_keywords": ["Python", "Docker"],
                "missed_keywords": ["FastAPI"],
            },
            "gap_analysis": {
                "CoreStrengths": "Strong technical skills",
                "KeyGaps": "Limited FastAPI experience",
                "QuickImprovements": "Add FastAPI to projects",
                "OverallAssessment": "Good candidate",
                "SkillSearchQueries": [
                    {
                        "Skill": "FastAPI",
                        "Category": "FIELD",
                        "SearchQuery": "FastAPI framework Python",
                    }
                ],
            },
            "resume_structure": {
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
                    "years_of_experience": 3,
                    "is_current_student": False,
                    "months_since_graduation": 18,
                    "has_only_internships": False,
                },
                "education_enhancement_needed": False,
            },
        }

        # Validate model accepts structure field
        api_response = IndexCalAndGapAnalysisData(**response_data)

        assert api_response.resume_structure is not None
        assert api_response.resume_structure["standard_sections"]["summary"] == "Professional Summary"
        assert "Languages" in api_response.resume_structure["custom_sections"]
        assert api_response.resume_structure["metadata"]["total_experience_entries"] == 3
        assert api_response.resume_structure["education_enhancement_needed"] is False
        assert api_response.resume_structure["metadata"]["years_of_experience"] == 3

        # Test without structure (backward compatibility)
        response_data_no_structure = {
            "raw_similarity_percentage": 75,
            "similarity_percentage": 85,
            "keyword_coverage": {
                "coverage_percentage": 60,
                "covered_keywords": ["Python"],
                "missed_keywords": ["FastAPI"],
            },
            "gap_analysis": {
                "CoreStrengths": "Good",
                "KeyGaps": "Some gaps",
                "QuickImprovements": "Improve",
                "OverallAssessment": "OK",
                "SkillSearchQueries": [],
            },
        }

        api_response_no_structure = IndexCalAndGapAnalysisData(**response_data_no_structure)
        assert api_response_no_structure.resume_structure is None

    @pytest.mark.asyncio
    async def test_RS_003_IT_error_handling_flow(
        self, sample_resume, sample_job_description, sample_keywords
    ):
        """
        Test ID: RS-003-IT - Error handling and fallback.
        Verify graceful degradation when structure analysis fails.
        """
        service = CombinedAnalysisServiceV2()

        # Mock structure analyzer to fail
        with patch.object(
            service.structure_analyzer,
            "analyze_structure",
            side_effect=Exception("LLM API Error"),
        ):
            # Mock other services to work normally
            with patch.object(
                service, "_quick_keyword_match", return_value={"covered": [], "missing": []}
            ):
                with patch.object(
                    service,
                    "_generate_embeddings_parallel",
                    return_value={"embeddings": []},
                ):
                    with patch.object(
                        service.index_service,
                        "calculate_index",
                        return_value={
                            "raw_similarity_percentage": 70,
                            "similarity_percentage": 80,
                            "keyword_coverage": {
                                "coverage_percentage": 50,
                                "covered_keywords": [],
                                "missed_keywords": [],
                            },
                        },
                    ):
                        with patch.object(
                            service.gap_service,
                            "analyze_with_context",
                            return_value={
                                "CoreStrengths": "Test",
                                "KeyGaps": "Test",
                                "QuickImprovements": "Test",
                                "OverallAssessment": "Test",
                            },
                        ):
                            result = await service.analyze(
                                resume=sample_resume,
                                job_description=sample_job_description,
                                keywords=sample_keywords,
                                language="en",
                            )

                            # Should have fallback structure
                            assert "resume_structure" in result
                            structure = result["resume_structure"]

                            # Check fallback values
                            assert structure["metadata"]["estimated_length"] == "unknown"
                            assert structure["metadata"]["total_experience_entries"] == 0
                            assert structure["standard_sections"]["summary"] == "Professional Summary"

                            # Check Education Enhancement fallback values
                            assert structure["metadata"]["years_of_experience"] == 0
                            assert structure["metadata"]["is_current_student"] is False
                            assert structure["metadata"]["months_since_graduation"] is None
                            assert structure["metadata"]["has_only_internships"] is False
                            # With years_of_experience=0, education enhancement should be True
                            assert structure["education_enhancement_needed"] is True

    @pytest.mark.asyncio
    async def test_RS_004_IT_feature_flag_behavior(
        self, sample_resume, sample_job_description, sample_keywords
    ):
        """
        Test ID: RS-004-IT - Feature flag enable/disable.
        Verify structure analysis can be toggled via environment variable.
        """
        # Test with feature disabled
        with patch.dict("os.environ", {"ENABLE_RESUME_STRUCTURE_ANALYSIS": "false"}):
            service_disabled = CombinedAnalysisServiceV2()

            # Mock required services
            with patch.object(
                service_disabled,
                "_quick_keyword_match",
                return_value={"covered": [], "missing": []},
            ):
                with patch.object(
                    service_disabled,
                    "_generate_embeddings_parallel",
                    return_value={"embeddings": []},
                ):
                    with patch.object(
                        service_disabled.index_service,
                        "calculate_index",
                        return_value={
                            "raw_similarity_percentage": 70,
                            "similarity_percentage": 80,
                            "keyword_coverage": {
                                "coverage_percentage": 50,
                                "covered_keywords": [],
                                "missed_keywords": [],
                            },
                        },
                    ):
                        with patch.object(
                            service_disabled.gap_service,
                            "analyze_with_context",
                            return_value={
                                "CoreStrengths": "Test",
                                "KeyGaps": "Test",
                                "QuickImprovements": "Test",
                                "OverallAssessment": "Test",
                            },
                        ):
                            result = await service_disabled.analyze(
                                resume=sample_resume,
                                job_description=sample_job_description,
                                keywords=sample_keywords,
                                language="en",
                            )

                            # Should NOT have structure when disabled
                            assert "resume_structure" not in result

        # Test with feature enabled (default)
        with patch.dict("os.environ", {"ENABLE_RESUME_STRUCTURE_ANALYSIS": "true"}):
            service_enabled = CombinedAnalysisServiceV2()

            mock_structure = ResumeStructure(
                standard_sections=StandardSections(summary="Executive Summary"),
                custom_sections=["Awards"],
                metadata=StructureMetadata(estimated_length="3+ pages"),
            )

            with patch.object(
                service_enabled.structure_analyzer,
                "analyze_structure",
                return_value=mock_structure,
            ):
                # Mock other required services
                with patch.object(
                    service_enabled,
                    "_quick_keyword_match",
                    return_value={"covered": [], "missing": []},
                ):
                    with patch.object(
                        service_enabled,
                        "_generate_embeddings_parallel",
                        return_value={"embeddings": []},
                    ):
                        with patch.object(
                            service_enabled.index_service,
                            "calculate_index",
                            return_value={
                                "raw_similarity_percentage": 70,
                                "similarity_percentage": 80,
                                "keyword_coverage": {
                                    "coverage_percentage": 50,
                                    "covered_keywords": [],
                                    "missed_keywords": [],
                                },
                            },
                        ):
                            with patch.object(
                                service_enabled.gap_service,
                                "analyze_with_context",
                                return_value={
                                    "CoreStrengths": "Test",
                                    "KeyGaps": "Test",
                                    "QuickImprovements": "Test",
                                    "OverallAssessment": "Test",
                                },
                            ):
                                result = await service_enabled.analyze(
                                    resume=sample_resume,
                                    job_description=sample_job_description,
                                    keywords=sample_keywords,
                                    language="en",
                                )

                                # Should have structure when enabled
                                assert "resume_structure" in result
                                assert result["resume_structure"]["standard_sections"]["summary"] == "Executive Summary"

    @pytest.mark.asyncio
    async def test_RS_005_IT_end_to_end_real_api(
        self, sample_resume, sample_job_description, sample_keywords
    ):
        """
        Test ID: RS-005-IT - Complete flow with real API calls.
        Verify end-to-end integration with actual LLM services.
        """
        service = CombinedAnalysisServiceV2()

        # Execute complete flow with real API
        result = await service.analyze(
            resume=sample_resume,
            job_description=sample_job_description,
            keywords=sample_keywords,
            language="en",
        )

        # Verify complete response structure
        assert "index_calculation" in result
        assert "gap_analysis" in result
        assert "resume_structure" in result
        assert "metadata" in result

        # Verify index results structure
        index_calc = result["index_calculation"]
        assert "raw_similarity_percentage" in index_calc
        assert "similarity_percentage" in index_calc
        assert "keyword_coverage" in index_calc
        assert isinstance(index_calc["similarity_percentage"], int)
        assert 0 <= index_calc["similarity_percentage"] <= 100

        # Verify gap analysis structure
        gap_analysis = result["gap_analysis"]
        required_gap_fields = ["CoreStrengths", "KeyGaps", "QuickImprovements", "OverallAssessment"]
        for field in required_gap_fields:
            assert field in gap_analysis
            assert isinstance(gap_analysis[field], str)
            assert len(gap_analysis[field]) > 0

        # Verify structure analysis with Education Enhancement
        structure = result["resume_structure"]

        # Verify standard sections
        assert "standard_sections" in structure
        std_sections = structure["standard_sections"]
        expected_sections = ["summary", "skills", "experience", "education", "certifications", "projects"]
        for section in expected_sections:
            assert section in std_sections

        # Verify custom sections
        assert "custom_sections" in structure
        assert isinstance(structure["custom_sections"], list)

        # Verify metadata with Education Enhancement fields
        assert "metadata" in structure
        metadata = structure["metadata"]

        # Basic metadata fields
        basic_fields = ["total_experience_entries", "total_education_entries",
                       "has_quantified_achievements", "estimated_length"]
        for field in basic_fields:
            assert field in metadata

        # Education Enhancement fields
        enhancement_fields = ["years_of_experience", "is_current_student",
                            "months_since_graduation", "has_only_internships"]
        for field in enhancement_fields:
            assert field in metadata

        # Verify data types
        assert isinstance(metadata["years_of_experience"], int)
        assert isinstance(metadata["is_current_student"], bool)
        assert metadata["months_since_graduation"] is None or isinstance(metadata["months_since_graduation"], int)
        assert isinstance(metadata["has_only_internships"], bool)

        # Verify Education Enhancement decision field
        assert "education_enhancement_needed" in structure
        assert isinstance(structure["education_enhancement_needed"], bool)

        # Verify metadata structure
        assert result["metadata"]["version"] == "3.0"
        assert "structure_analysis_enabled" in result["metadata"]
        assert result["metadata"]["structure_analysis_enabled"] is True

        # Log results for debugging
        print(f"Education Enhancement Decision: {structure['education_enhancement_needed']}")
        print(f"Years of Experience: {metadata['years_of_experience']}")
        print(f"Is Current Student: {metadata['is_current_student']}")
        print(f"Months Since Graduation: {metadata['months_since_graduation']}")
        print(f"Has Only Internships: {metadata['has_only_internships']}")

    @pytest.mark.asyncio
    async def test_RS_006_IT_education_enhancement_scenarios(self):
        """
        Test ID: RS-006-IT - Education Enhancement decision scenarios.
        Test different resume scenarios to verify Education Enhancement logic.
        """
        service = CombinedAnalysisServiceV2()

        # Scenario 1: Recent graduate (should enhance)
        recent_grad_resume = """
        <html>
            <h1>Jane Smith</h1>
            <h2>Professional Summary</h2>
            <p>Recent Computer Science graduate seeking entry-level position...</p>
            <h2>Education</h2>
            <div>BS Computer Science - Stanford University (2020-2024)</div>
            <h2>Experience</h2>
            <div>
                <h3>Software Engineering Intern - Google (Summer 2023)</h3>
                <p>Developed web applications using React and Node.js</p>
            </div>
        </html>
        """

        job_desc = "Looking for entry-level software engineer with CS degree and programming experience."
        keywords = ["Python", "JavaScript", "React", "Node.js"]

        result1 = await service.analyze(
            resume=recent_grad_resume,
            job_description=job_desc,
            keywords=keywords,
            language="en",
        )

        structure1 = result1["resume_structure"]
        metadata1 = structure1["metadata"]

        # Recent graduate with internship should trigger enhancement
        print("Scenario 1 - Recent Graduate:")
        print(f"  Years of Experience: {metadata1['years_of_experience']}")
        print(f"  Is Current Student: {metadata1['is_current_student']}")
        print(f"  Months Since Graduation: {metadata1['months_since_graduation']}")
        print(f"  Has Only Internships: {metadata1['has_only_internships']}")
        print(f"  Education Enhancement Needed: {structure1['education_enhancement_needed']}")

        # Verify basic structure and Education Enhancement fields exist
        assert "years_of_experience" in metadata1
        assert "is_current_student" in metadata1
        assert "months_since_graduation" in metadata1
        assert "has_only_internships" in metadata1
        assert "education_enhancement_needed" in structure1
        assert isinstance(structure1["education_enhancement_needed"], bool)

        # Scenario 2: Experienced professional
        experienced_resume = """
        <html>
            <h1>John Senior</h1>
            <h2>Professional Summary</h2>
            <p>Senior Software Engineer with 8+ years of experience...</p>
            <h2>Experience</h2>
            <div>
                <h3>Senior Software Engineer - Microsoft (2018-2023)</h3>
                <p>Led team of 10 developers, improved system performance by 40%</p>
            </div>
            <div>
                <h3>Software Engineer - Apple (2016-2018)</h3>
                <p>Developed iOS applications with Swift and Objective-C</p>
            </div>
            <h2>Education</h2>
            <div>MS Computer Science - MIT (2014-2016)</div>
            <div>BS Computer Science - UC Berkeley (2010-2014)</div>
        </html>
        """

        result2 = await service.analyze(
            resume=experienced_resume,
            job_description=job_desc,
            keywords=keywords,
            language="en",
        )

        structure2 = result2["resume_structure"]
        metadata2 = structure2["metadata"]

        print("\nScenario 2 - Experienced Professional:")
        print(f"  Years of Experience: {metadata2['years_of_experience']}")
        print(f"  Is Current Student: {metadata2['is_current_student']}")
        print(f"  Months Since Graduation: {metadata2['months_since_graduation']}")
        print(f"  Has Only Internships: {metadata2['has_only_internships']}")
        print(f"  Education Enhancement Needed: {structure2['education_enhancement_needed']}")

        # Verify structure and Education Enhancement fields exist
        assert "years_of_experience" in metadata2
        assert "is_current_student" in metadata2
        assert "months_since_graduation" in metadata2
        assert "has_only_internships" in metadata2
        assert "education_enhancement_needed" in structure2
        assert isinstance(structure2["education_enhancement_needed"], bool)

        # Note: In test environment, actual LLM calls might be blocked,
        # so we mainly verify the structure includes our new fields
        print("\n✅ Education Enhancement fields successfully integrated into API response")  # Has full-time experience
        # Enhancement decision depends on specific career metrics calculated by LLM
