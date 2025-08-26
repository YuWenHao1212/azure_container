"""
Unit tests for SkillQuery model serialization with environment variable control.
Tests the INCLUDE_COURSE_DETAILS environment variable functionality.
"""

import os
from unittest import mock

import pytest

from src.api.v1.index_cal_and_gap_analysis import SkillQuery


class TestSkillQuerySerialization:
    """Test suite for SkillQuery environment variable control"""

    @pytest.fixture
    def sample_skill_data(self):
        """Sample skill data for testing"""
        return {
            "skill_name": "Python Programming",
            "skill_category": "SKILL",
            "description": "Advanced Python development skills",
            "has_available_courses": True,
            "course_count": 3,
            "available_course_ids": ["proj-001", "cert-001", "course-001"],
            "course_details": [
                {
                    "id": "proj-001",
                    "name": "Python Web Development Project",
                    "type": "project",
                    "provider_standardized": "Coursera",
                    "description": "Build a full-stack web application using Python"
                },
                {
                    "id": "cert-001",
                    "name": "Python Professional Certification",
                    "type": "certification",
                    "provider_standardized": "Python.org",
                    "description": "Professional Python certification"
                },
                {
                    "id": "course-001",
                    "name": "Python Fundamentals",
                    "type": "course",
                    "provider_standardized": "edX",
                    "description": "Learn Python programming basics"
                }
            ]
        }

    def test_SQS_001_UT_default_excludes_course_details(self, sample_skill_data):
        """
        Test that course_details is excluded by default (INCLUDE_COURSE_DETAILS not set).
        This is the production optimization behavior.
        """
        # Ensure environment variable is not set
        with mock.patch.dict(os.environ, {}, clear=True):
            # Remove INCLUDE_COURSE_DETAILS if it exists
            os.environ.pop("INCLUDE_COURSE_DETAILS", None)

            skill = SkillQuery(**sample_skill_data)
            serialized = skill.model_dump()

            # Verify course_details is excluded
            assert "course_details" not in serialized, "course_details should be excluded by default"

            # Verify other fields are included
            expected_fields = {
                "skill_name", "skill_category", "description",
                "has_available_courses", "course_count", "available_course_ids"
            }
            assert expected_fields.issubset(set(serialized.keys())), "Other fields should be included"

    def test_SQS_002_UT_explicit_false_excludes_course_details(self, sample_skill_data):
        """
        Test that course_details is excluded when INCLUDE_COURSE_DETAILS=false.
        """
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "false"}):
            skill = SkillQuery(**sample_skill_data)
            serialized = skill.model_dump()

            assert "course_details" not in serialized, "course_details should be excluded when INCLUDE_COURSE_DETAILS=false"

    def test_SQS_003_UT_true_includes_course_details(self, sample_skill_data):
        """
        Test that course_details is included when INCLUDE_COURSE_DETAILS=true.
        This is the development/debugging behavior.
        """
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "true"}):
            skill = SkillQuery(**sample_skill_data)
            serialized = skill.model_dump()

            # Verify course_details is included
            assert "course_details" in serialized, "course_details should be included when INCLUDE_COURSE_DETAILS=true"
            assert isinstance(serialized["course_details"], list), "course_details should be a list"
            assert len(serialized["course_details"]) == 3, "All course details should be included"

            # Verify content is correct
            course_ids = [course["id"] for course in serialized["course_details"]]
            assert "proj-001" in course_ids, "Project should be included"
            assert "cert-001" in course_ids, "Certification should be included"
            assert "course-001" in course_ids, "Course should be included"

    def test_SQS_004_UT_case_insensitive_true_values(self, sample_skill_data):
        """
        Test that case insensitive "true" values work correctly.
        """
        test_cases = ["TRUE", "True", "true", "tRuE"]

        for true_value in test_cases:
            with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": true_value}):
                skill = SkillQuery(**sample_skill_data)
                serialized = skill.model_dump()

                assert "course_details" in serialized, f"course_details should be included for INCLUDE_COURSE_DETAILS={true_value}"

    def test_SQS_005_UT_case_insensitive_false_values(self, sample_skill_data):
        """
        Test that case insensitive "false" values work correctly.
        """
        test_cases = ["FALSE", "False", "false", "fAlSe"]

        for false_value in test_cases:
            with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": false_value}):
                skill = SkillQuery(**sample_skill_data)
                serialized = skill.model_dump()

                assert "course_details" not in serialized, f"course_details should be excluded for INCLUDE_COURSE_DETAILS={false_value}"

    def test_SQS_006_UT_invalid_values_default_to_exclude(self, sample_skill_data):
        """
        Test that invalid values for INCLUDE_COURSE_DETAILS default to excluding course_details.
        """
        invalid_values = ["yes", "no", "1", "0", "invalid", ""]

        for invalid_value in invalid_values:
            with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": invalid_value}):
                skill = SkillQuery(**sample_skill_data)
                serialized = skill.model_dump()

                assert "course_details" not in serialized, f"course_details should be excluded for invalid value: {invalid_value}"

    def test_SQS_007_UT_empty_course_details_handling(self, sample_skill_data):
        """
        Test handling when course_details is empty or None.
        """
        # Test with empty course_details
        empty_data = sample_skill_data.copy()
        empty_data["course_details"] = []

        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "true"}):
            skill = SkillQuery(**empty_data)
            serialized = skill.model_dump()

            assert "course_details" in serialized, "course_details field should be included even when empty"
            assert serialized["course_details"] == [], "Empty course_details should serialize as empty list"

        # Test with None course_details
        none_data = sample_skill_data.copy()
        none_data["course_details"] = None

        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "true"}):
            skill = SkillQuery(**none_data)
            serialized = skill.model_dump()

            assert "course_details" in serialized, "course_details field should be included even when None"
            assert serialized["course_details"] is None, "None course_details should serialize as None"

    def test_SQS_008_UT_exclude_behavior_with_empty_course_details(self, sample_skill_data):
        """
        Test that when excluding, the field is properly removed regardless of content.
        """
        test_data = [
            sample_skill_data,  # With content
            {**sample_skill_data, "course_details": []},  # Empty list
            {**sample_skill_data, "course_details": None},  # None
        ]

        for data in test_data:
            with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "false"}):
                skill = SkillQuery(**data)
                serialized = skill.model_dump()

                assert "course_details" not in serialized, "course_details should always be excluded when INCLUDE_COURSE_DETAILS=false"

    def test_SQS_009_UT_runtime_environment_change_detection(self, sample_skill_data):
        """
        Test that environment variable changes are detected at runtime.
        This is important for dynamic configuration changes.
        """
        # Start with exclude behavior
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "false"}):
            skill = SkillQuery(**sample_skill_data)
            serialized1 = skill.model_dump()
            assert "course_details" not in serialized1, "Should exclude initially"

        # Change to include behavior and test the same instance
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "true"}):
            serialized2 = skill.model_dump()
            assert "course_details" in serialized2, "Should include after environment change"

        # Change back to exclude
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "false"}):
            serialized3 = skill.model_dump()
            assert "course_details" not in serialized3, "Should exclude after changing back"

    def test_SQS_010_UT_performance_impact_measurement(self, sample_skill_data):
        """
        Test to measure the performance impact of the dynamic check.
        This ensures our implementation doesn't significantly impact performance.
        """
        import time

        # Test with exclusion (production case)
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "false"}):
            skill = SkillQuery(**sample_skill_data)

            start_time = time.perf_counter()
            for _ in range(1000):  # Run multiple times to measure average
                skill.model_dump()
            exclude_time = time.perf_counter() - start_time

        # Test with inclusion (development case)
        with mock.patch.dict(os.environ, {"INCLUDE_COURSE_DETAILS": "true"}):
            skill = SkillQuery(**sample_skill_data)

            start_time = time.perf_counter()
            for _ in range(1000):  # Run multiple times to measure average
                skill.model_dump()
            include_time = time.perf_counter() - start_time

        # Performance should be reasonable (less than 1ms per call on average)
        avg_exclude_time = exclude_time / 1000
        avg_include_time = include_time / 1000

        assert avg_exclude_time < 0.001, f"Exclude serialization too slow: {avg_exclude_time:.6f}s per call"
        assert avg_include_time < 0.001, f"Include serialization too slow: {avg_include_time:.6f}s per call"

        # The difference should not be dramatic (within 100% of each other)
        time_ratio = max(avg_exclude_time, avg_include_time) / min(avg_exclude_time, avg_include_time)
        assert time_ratio < 2.0, f"Performance difference too large: {time_ratio:.2f}x"
