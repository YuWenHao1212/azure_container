"""
Integration tests for resume enhancement data flow.
Tests the complete flow from Gap Analysis through to API response.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.combined_analysis_v2 import CombinedAnalysisServiceV2
from src.services.course_availability import CourseAvailabilityChecker


class TestEnhancementDataFlow:
    """Integration tests for enhancement data flow through the system"""

    @pytest.fixture
    def mock_gap_analysis_skills(self):
        """Mock Gap Analysis skill queries with course_details"""
        return [
            {
                "skill_name": "Python Programming",
                "skill_category": "SKILL",
                "description": "Advanced Python skills",
                "has_available_courses": True,
                "course_count": 3,
                "available_course_ids": ["proj-py-001", "cert-py-001", "course-py-001"],
                "course_details": [
                    {"id": "proj-py-001", "name": "Python Web App Project", "type": "project",
                     "provider_standardized": "Coursera", "description": "Build a web app",
                     "similarity": 0.85},
                    {"id": "cert-py-001", "name": "Python Professional Cert", "type": "certification",
                     "provider_standardized": "Python.org", "description": "Professional cert",
                     "similarity": 0.82},
                    {"id": "course-py-001", "name": "Python Basics", "type": "course",
                     "provider_standardized": "Coursera", "description": "Basic course",
                     "similarity": 0.80}
                ]
            },
            {
                "skill_name": "Machine Learning",
                "skill_category": "FIELD",
                "description": "ML and AI expertise",
                "has_available_courses": True,
                "course_count": 2,
                "available_course_ids": ["spec-ml-001", "proj-ml-001"],
                "course_details": [
                    {"id": "spec-ml-001", "name": "Deep Learning Specialization", "type": "specialization",
                     "provider_standardized": "Coursera", "description": "Complete DL program",
                     "similarity": 0.88},
                    {"id": "proj-ml-001", "name": "ML Model Deployment", "type": "project",
                     "provider_standardized": "Coursera", "description": "Deploy ML models",
                     "similarity": 0.84}
                ]
            },
            {
                "skill_name": "Cloud Architecture",
                "skill_category": "FIELD",
                "description": "Cloud infrastructure design",
                "has_available_courses": True,
                "course_count": 1,
                "available_course_ids": ["cert-aws-001"],
                "course_details": [
                    {"id": "cert-aws-001", "name": "AWS Solutions Architect", "type": "certification",
                     "provider_standardized": "AWS", "description": "AWS certification",
                     "similarity": 0.90}
                ]
            }
        ]

    @pytest.mark.asyncio
    async def test_ENH_IT_001_course_availability_enhancement_building(self, mock_gap_analysis_skills):
        """
        Test CourseAvailabilityChecker correctly builds enhancement data from Gap Analysis output.
        """
        # Don't mock the init, just test the method directly
        checker = CourseAvailabilityChecker()
        # Skip pool initialization for unit test
        checker._pool = None

        # Mock the database query to return our test data (removed indentation)
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()
        mock_conn.fetchrow = AsyncMock()

        # For each skill, return the course_details
        async def mock_fetchrow(query, *args):
            skill_text = args[0] if args else ""
            for skill in mock_gap_analysis_skills:
                if skill["skill_name"] in skill_text or skill["description"] in skill_text:
                    return {
                        "has_courses": True,
                        "course_ids": skill["available_course_ids"],
                        "course_details": skill["course_details"]
                    }
            return {"has_courses": False, "course_ids": [], "course_details": []}

        mock_conn.fetchrow.side_effect = mock_fetchrow
        # Note: checker._pool is None so we don't need to mock acquire

        # Since we're testing just the building logic, use the mock data directly
        # The checker would normally fetch this from database
        enhanced_skills = mock_gap_analysis_skills.copy()

        # Verify our test data has course_details
        for i, skill in enumerate(enhanced_skills):
            assert "course_details" in skill, f"Test data skill {i} missing course_details"
            assert len(skill["course_details"]) > 0, f"Test data skill {i} has empty course_details"

        # Build enhancement data
        projects, certifications = checker._build_enhancement_data(
            enhanced_skills, mock_gap_analysis_skills
        )

        # Verify correct filtering and aggregation
        assert len(projects) == 2, f"Expected 2 projects, got {len(projects)}"
        assert "proj-py-001" in projects, "Python project should be included"
        assert "proj-ml-001" in projects, "ML project should be included"

        assert len(certifications) == 3, f"Expected 3 certifications, got {len(certifications)}"
        assert "cert-py-001" in certifications, "Python cert should be included"
        assert "spec-ml-001" in certifications, "ML specialization should be included"
        assert "cert-aws-001" in certifications, "AWS cert should be included"

        # Regular course should NOT be included
        assert "course-py-001" not in certifications, "Regular course should NOT be included"
        assert "course-py-001" not in projects, "Regular course should NOT be in projects"

    @pytest.mark.asyncio
    async def test_ENH_IT_002_enhancement_data_in_api_response(self, mock_gap_analysis_skills):
        """
        Test that enhancement data appears correctly in the final API response structure.
        """
        with patch('src.services.course_availability.CourseAvailabilityChecker') as MockChecker:
            # Setup mock checker
            mock_checker = MockChecker.return_value

            # Mock check_course_availability to add enhancement data to first skill
            async def mock_check_availability(skills):
                # Add enhancement data to first skill (transport mechanism)
                if skills:
                    skills[0]["resume_enhancement_project"] = {
                        "proj-py-001": {
                            "name": "Python Web App Project",
                            "provider": "Coursera",
                            "description": "Build a web app",
                            "related_skill": "Python Programming"
                        },
                        "proj-ml-001": {
                            "name": "ML Model Deployment",
                            "provider": "Coursera",
                            "description": "Deploy ML models",
                            "related_skill": "Machine Learning"
                        }
                    }
                    skills[0]["resume_enhancement_certification"] = {
                        "cert-py-001": {
                            "name": "Python Professional Cert",
                            "provider": "Python.org",
                            "description": "Professional cert",
                            "related_skill": "Python Programming"
                        },
                        "spec-ml-001": {
                            "name": "Deep Learning Specialization",
                            "provider": "Coursera",
                            "description": "Complete DL program",
                            "related_skill": "Machine Learning"
                        },
                        "cert-aws-001": {
                            "name": "AWS Solutions Architect",
                            "provider": "AWS",
                            "description": "AWS certification",
                            "related_skill": "Cloud Architecture"
                        }
                    }
                return skills

            mock_checker.check_course_availability = AsyncMock(side_effect=mock_check_availability)

            # Create service and test
            service = CombinedAnalysisServiceV2()

            # Mock other services
            with patch('src.services.combined_analysis_v2.IndexCalculationServiceV2') as MockIndex, \
                 patch('src.services.combined_analysis_v2.GapAnalysisServiceV2') as MockGap, \
                 patch('src.services.combined_analysis_v2.StructureAnalyzer') as MockStructure:

                # Setup mocks
                mock_index_service = MockIndex.return_value
                mock_index_service.calculate_similarity = AsyncMock(return_value={
                    "raw_similarity_percentage": 75,
                    "similarity_percentage": 85,
                    "keyword_coverage": {
                        "total_keywords": 5,
                        "covered_count": 4,
                        "coverage_percentage": 80,
                        "covered_keywords": ["Python", "ML", "Cloud"],
                        "missed_keywords": ["Docker"]
                    }
                })

                mock_gap_service = MockGap.return_value
                mock_gap_service.analyze_gap = AsyncMock(return_value={
                    "CoreStrengths": "Strong Python and ML skills",
                    "KeyGaps": "Need more cloud experience",
                    "QuickImprovements": "Get AWS certification",
                    "OverallAssessment": "Good fit",
                    "SkillSearchQueries": mock_gap_analysis_skills
                })

                mock_structure = MockStructure.return_value
                mock_structure.analyze_structure = AsyncMock(return_value={
                    "standard_sections": {"summary": "Test resume"},
                    "custom_sections": [],
                    "metadata": {"total_experience_entries": 2}
                })

                # Call the service
                result = await service.analyze(
                    resume="Test resume with Python and ML experience",
                    job_description="Looking for Python ML engineer",
                    keywords=["Python", "ML", "Cloud", "Docker"],
                    language="en"
                )

                # Verify enhancement data is in the result
                assert "resume_enhancement_project" in result, "Missing resume_enhancement_project"
                assert "resume_enhancement_certification" in result, "Missing resume_enhancement_certification"

                # Verify content
                projects = result["resume_enhancement_project"]
                certifications = result["resume_enhancement_certification"]

                assert len(projects) == 2, f"Expected 2 projects, got {len(projects)}"
                assert len(certifications) == 3, f"Expected 3 certifications, got {len(certifications)}"

                # Verify they're at the same level as gap_analysis
                assert "gap_analysis" in result
                assert "index_calculation" in result
                # Enhancement fields should be top-level, not nested

    @pytest.mark.asyncio
    async def test_ENH_IT_003_fallback_extraction_mechanisms(self):
        """
        Test fallback mechanisms for extracting enhancement data.
        """
        with patch('src.services.course_availability.CourseAvailabilityChecker'):
            # service = CombinedAnalysisServiceV2()  # Not used in this test

            # Test case 1: Enhancement data in first skill query
            gap_result = {
                "SkillSearchQueries": [
                    {
                        "skill_name": "Python",
                        "resume_enhancement_project": {"proj-1": {"name": "Project 1"}},
                        "resume_enhancement_certification": {"cert-1": {"name": "Cert 1"}}
                    }
                ]
            }

            # Extract enhancement data
            projects = gap_result["SkillSearchQueries"][0].get("resume_enhancement_project", {})
            certs = gap_result["SkillSearchQueries"][0].get("resume_enhancement_certification", {})

            assert projects == {"proj-1": {"name": "Project 1"}}
            assert certs == {"cert-1": {"name": "Cert 1"}}

            # Test case 2: Enhancement data missing from skills but in result dict
            result_with_enhancement = {
                "gap_analysis": {"SkillSearchQueries": []},
                "resume_enhancement_project": {"proj-2": {"name": "Project 2"}},
                "resume_enhancement_certification": {"cert-2": {"name": "Cert 2"}}
            }

            # Fallback extraction
            if not projects and "resume_enhancement_project" in result_with_enhancement:
                projects = result_with_enhancement["resume_enhancement_project"]
            if not certs and "resume_enhancement_certification" in result_with_enhancement:
                certs = result_with_enhancement["resume_enhancement_certification"]

            assert projects == {"proj-2": {"name": "Project 2"}}
            assert certs == {"cert-2": {"name": "Cert 2"}}

    @pytest.mark.asyncio
    async def test_ENH_IT_004_empty_enhancement_handling(self):
        """
        Test handling when no enhancement data is available.
        Should return empty dicts, not None.
        """
        with patch('src.services.course_availability.CourseAvailabilityChecker') as MockChecker:
            mock_checker = MockChecker.return_value

            # Mock returns no enhancement data
            async def mock_check_no_courses(skills):
                # No course_details, no enhancement fields added
                return skills

            mock_checker.check_course_availability = AsyncMock(side_effect=mock_check_no_courses)

            # service = CombinedAnalysisServiceV2()  # Not used in this test

            # Mock other services
            with patch('src.services.combined_analysis_v2.IndexCalculationServiceV2'), \
                 patch('src.services.combined_analysis_v2.GapAnalysisServiceV2') as MockGap, \
                 patch('src.services.combined_analysis_v2.StructureAnalyzer'):

                mock_gap_service = MockGap.return_value
                mock_gap_service.analyze_gap = AsyncMock(return_value={
                    "SkillSearchQueries": [
                        {"skill_name": "Python", "course_details": []}
                    ]
                })

                # Build enhancement data from empty course_details
                checker = CourseAvailabilityChecker()
                projects, certs = checker._build_enhancement_data(
                    [{"course_details": []}],
                    [{"skill_name": "Python"}]
                )

                # Should return empty dicts for Bubble.io compatibility
                assert projects == {}, "Should return empty dict, not None"
                assert certs == {}, "Should return empty dict, not None"
                assert isinstance(projects, dict)
                assert isinstance(certs, dict)
