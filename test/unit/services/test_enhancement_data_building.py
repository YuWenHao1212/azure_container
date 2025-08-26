"""
Unit tests for resume enhancement data building functionality.
Tests the _build_enhancement_data method to ensure correct filtering and aggregation.
"""

from unittest.mock import Mock, patch

import pytest

from src.services.course_availability import CourseAvailabilityChecker


class TestEnhancementDataBuilding:
    """Test suite for enhancement data building logic"""

    @pytest.fixture
    def checker(self):
        """Create a CourseAvailabilityChecker instance"""
        with patch('asyncpg.create_pool'):
            checker = CourseAvailabilityChecker()
            checker._pool = Mock()
            return checker

    def test_ENH_001_UT_correct_course_type_filtering(self, checker):
        """
        Test that only project, certification, and specialization types are included.
        Regular 'course' type should be excluded.
        """
        # Prepare test data with various course types
        enhanced_skills = [
            {
                "course_details": [
                    {"id": "proj-001", "type": "project", "name": "ML Project",
                     "provider_standardized": "Coursera", "description": "Build ML model"},
                    {"id": "cert-001", "type": "certification", "name": "AWS Cert",
                     "provider_standardized": "AWS", "description": "Cloud certification"},
                    {"id": "spec-001", "type": "specialization", "name": "Deep Learning",
                     "provider_standardized": "Coursera", "description": "DL specialization"},
                    {"id": "course-001", "type": "course", "name": "Python Basics",
                     "provider_standardized": "Coursera", "description": "Regular course"},
                    {"id": "unknown-001", "type": "unknown", "name": "Unknown Type",
                     "provider_standardized": "Unknown", "description": "Unknown type"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Machine Learning", "skill_category": "FIELD"}
        ]

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Assertions
        assert "proj-001" in projects, "Project type should be included"
        assert "cert-001" in certifications, "Certification type should be included"
        assert "spec-001" in certifications, "Specialization type should be included"
        assert "course-001" not in certifications, "Regular course type should NOT be included"
        assert "course-001" not in projects, "Regular course should not be in projects either"
        assert "unknown-001" not in projects, "Unknown type should not be included"
        assert "unknown-001" not in certifications, "Unknown type should not be included"

    def test_ENH_002_UT_quota_limits_per_skill(self, checker):
        """
        Test that quotas are enforced:
        - Max 2 projects per skill
        - Max 4 certifications/specializations per skill
        """
        # Create many courses of each type
        enhanced_skills = [
            {
                "course_details": [
                    {"id": f"proj-{i:03d}", "type": "project",
                     "name": f"Project {i}", "provider_standardized": "Coursera",
                     "description": f"Project {i} description"}
                    for i in range(5)  # 5 projects
                ] + [
                    {"id": f"cert-{i:03d}", "type": "certification",
                     "name": f"Cert {i}", "provider_standardized": "Coursera",
                     "description": f"Certification {i} description"}
                    for i in range(6)  # 6 certifications
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Python", "skill_category": "SKILL"}
        ]

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Check quotas
        assert len(projects) == 2, f"Should have max 2 projects per skill, got {len(projects)}"
        assert len(certifications) == 4, f"Should have max 4 certifications per skill, got {len(certifications)}"

        # Verify it takes the first ones (in order)
        assert "proj-000" in projects
        assert "proj-001" in projects
        assert "cert-000" in certifications
        assert "cert-003" in certifications

    def test_ENH_003_UT_cross_skill_aggregation(self, checker):
        """
        Test that enhancement data aggregates courses across ALL skills.
        Each skill contributes to the final result.
        """
        enhanced_skills = [
            {
                "course_details": [
                    {"id": "proj-py-001", "type": "project", "name": "Python Project",
                     "provider_standardized": "Coursera", "description": "Python proj"},
                    {"id": "cert-py-001", "type": "certification", "name": "Python Cert",
                     "provider_standardized": "Python.org", "description": "Python cert"}
                ]
            },
            {
                "course_details": [
                    {"id": "proj-ml-001", "type": "project", "name": "ML Project",
                     "provider_standardized": "Coursera", "description": "ML proj"},
                    {"id": "spec-ml-001", "type": "specialization", "name": "ML Spec",
                     "provider_standardized": "Coursera", "description": "ML specialization"}
                ]
            },
            {
                "course_details": [
                    {"id": "cert-cloud-001", "type": "certification", "name": "AWS Cert",
                     "provider_standardized": "AWS", "description": "Cloud cert"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Python", "skill_category": "SKILL"},
            {"skill_name": "Machine Learning", "skill_category": "FIELD"},
            {"skill_name": "Cloud Computing", "skill_category": "FIELD"}
        ]

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Check cross-skill aggregation
        assert len(projects) == 2, "Should have projects from multiple skills"
        assert "proj-py-001" in projects, "Python project should be included"
        assert "proj-ml-001" in projects, "ML project should be included"

        assert len(certifications) == 3, "Should have certifications from all skills"
        assert "cert-py-001" in certifications, "Python cert should be included"
        assert "spec-ml-001" in certifications, "ML specialization should be included"
        assert "cert-cloud-001" in certifications, "Cloud cert should be included"

        # Verify related_skill is correctly set
        assert projects["proj-py-001"]["related_skill"] == "Python"
        assert projects["proj-ml-001"]["related_skill"] == "Machine Learning"
        assert certifications["cert-cloud-001"]["related_skill"] == "Cloud Computing"

    def test_ENH_004_UT_handle_empty_and_none_course_details(self, checker):
        """
        Test graceful handling of empty or None course_details.
        Should return empty dicts without errors.
        """
        enhanced_skills = [
            {"course_details": []},  # Empty list
            {"course_details": None},  # None
            {},  # Missing course_details key
            {
                "course_details": [
                    {"id": "proj-001", "type": "project", "name": "Valid Project",
                     "provider_standardized": "Coursera", "description": "Valid"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Empty Skill", "skill_category": "SKILL"},
            {"skill_name": "None Skill", "skill_category": "SKILL"},
            {"skill_name": "Missing Skill", "skill_category": "SKILL"},
            {"skill_name": "Valid Skill", "skill_category": "SKILL"}
        ]

        # Should not raise any errors
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Only the valid project should be included
        assert len(projects) == 1, "Should have one valid project"
        assert "proj-001" in projects
        assert len(certifications) == 0, "No certifications in test data"

    def test_ENH_005_UT_handle_malformed_course_data(self, checker):
        """
        Test handling of malformed course data (missing required fields).
        Should skip invalid entries gracefully.
        """
        enhanced_skills = [
            {
                "course_details": [
                    {"id": "valid-001", "type": "project", "name": "Valid Project",
                     "provider_standardized": "Coursera", "description": "Valid"},
                    {"type": "project", "name": "No ID"},  # Missing id
                    {"id": "", "type": "project", "name": "Empty ID"},  # Empty id
                    {"id": "no-type-001", "name": "No Type"},  # Missing type
                    {"id": "null-type-001", "type": None, "name": "Null Type"},  # None type
                    None,  # None entry
                    {},  # Empty dict
                    {"id": "valid-cert-001", "type": "certification", "name": "Valid Cert",
                     "provider_standardized": "AWS", "description": "Valid cert"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Test Skill", "skill_category": "SKILL"}
        ]

        # Should handle gracefully without errors
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Only valid entries should be included
        assert len(projects) == 1, "Should have one valid project"
        assert "valid-001" in projects
        assert len(certifications) == 1, "Should have one valid certification"
        assert "valid-cert-001" in certifications

    def test_ENH_006_UT_deduplication_across_skills(self, checker):
        """
        Test that duplicate course IDs across different skills are deduplicated.
        Dictionary keys ensure automatic deduplication.
        """
        enhanced_skills = [
            {
                "course_details": [
                    {"id": "shared-proj-001", "type": "project", "name": "Shared Project",
                     "provider_standardized": "Coursera", "description": "Appears in skill 1"}
                ]
            },
            {
                "course_details": [
                    {"id": "shared-proj-001", "type": "project", "name": "Same Project",
                     "provider_standardized": "Coursera", "description": "Appears in skill 2"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Skill 1", "skill_category": "SKILL"},
            {"skill_name": "Skill 2", "skill_category": "SKILL"}
        ]

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Should have only one entry (deduplicated)
        assert len(projects) == 1, "Duplicate course IDs should be deduplicated"
        assert "shared-proj-001" in projects
        # The last occurrence wins (Skill 2)
        assert projects["shared-proj-001"]["related_skill"] == "Skill 2"

    def test_ENH_007_UT_maximum_aggregation_limits(self, checker):
        """
        Test maximum possible aggregation with 6 skills.
        Should produce max 12 projects and 24 certifications.
        """
        # Create 6 skills, each with max quotas
        enhanced_skills = []
        skill_queries = []

        for skill_num in range(6):
            enhanced_skills.append({
                "course_details": [
                    {"id": f"proj-s{skill_num}-{i}", "type": "project",
                     "name": f"Project {i} for Skill {skill_num}",
                     "provider_standardized": "Coursera",
                     "description": "Project description"}
                    for i in range(3)  # 3 projects per skill (will be limited to 2)
                ] + [
                    {"id": f"cert-s{skill_num}-{i}", "type": "certification",
                     "name": f"Cert {i} for Skill {skill_num}",
                     "provider_standardized": "Coursera",
                     "description": "Cert description"}
                    for i in range(5)  # 5 certs per skill (will be limited to 4)
                ]
            })
            skill_queries.append({
                "skill_name": f"Skill {skill_num}",
                "skill_category": "SKILL"
            })

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Check maximum limits
        assert len(projects) == 12, f"Should have max 12 projects (2×6), got {len(projects)}"
        assert len(certifications) == 24, f"Should have max 24 certifications (4×6), got {len(certifications)}"

    def test_ENH_008_UT_empty_result_returns_empty_dict(self, checker):
        """
        Test that when no courses match criteria, empty dicts are returned.
        This ensures Bubble.io compatibility (expecting {} not None).
        """
        # No matching course types
        enhanced_skills = [
            {
                "course_details": [
                    {"id": "course-001", "type": "course", "name": "Regular Course",
                     "provider_standardized": "Coursera", "description": "Not included"},
                    {"id": "unknown-001", "type": "video", "name": "Video Course",
                     "provider_standardized": "YouTube", "description": "Not included"}
                ]
            }
        ]

        skill_queries = [
            {"skill_name": "Test Skill", "skill_category": "SKILL"}
        ]

        # Call the method
        projects, certifications = checker._build_enhancement_data(enhanced_skills, skill_queries)

        # Should return empty dicts, not None
        assert projects == {}, "Should return empty dict for projects"
        assert certifications == {}, "Should return empty dict for certifications"
        assert projects is not None, "Should not be None"
        assert certifications is not None, "Should not be None"
