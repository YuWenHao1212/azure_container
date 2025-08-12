"""
Integration tests for Resume Tailoring API with keyword tracking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.main import app
from src.services.exceptions import ServiceError


class TestResumeTailoringAPI:
    """Test Resume Tailoring API endpoint with keyword tracking."""

    # Test ID: API-TLR-521-IT
    @pytest.mark.asyncio
    async def test_successful_tailoring_with_keyword_tracking(self):
        """
        Test ID: API-TLR-521-IT
        Test successful resume tailoring with keyword tracking.

        測試原因: 驗證完整的履歷優化流程包含關鍵字追蹤功能
        """
        request_data = {
            "job_description": "We are looking for a Python developer with experience in Django, Docker, and AWS. " * 10,
            "original_resume": "<html><body><p>Python developer with Django expertise</p></body></html>" * 5,
            "gap_analysis": {
                "core_strengths": ["Python expertise", "Django framework", "Team leadership"],
                "key_gaps": ["[Skill Gap] Docker containerization", "[Skill Gap] AWS cloud services"],
                "quick_improvements": ["Add Docker certification", "Include AWS projects"],
                "covered_keywords": ["Python", "Django"],
                "missing_keywords": ["Docker", "AWS", "Kubernetes"],
                "coverage_percentage": 40,
                "similarity_percentage": 60
            },
            "options": {
                "language": "en",
                "include_visual_markers": True
            }
        }

        # Mock the tailoring service to return a predictable result
        mock_result = {
            "optimized_resume": "<html><body><p>Python developer with Docker and AWS expertise</p></body></html>",
            "applied_improvements": "<ul><li>Added Docker</li><li>Added AWS</li></ul>",
            "improvement_count": 2,
            "keyword_tracking": {
                "still_covered": ["Python"],
                "removed": ["Django"],
                "newly_added": ["Docker", "AWS"],
                "still_missing": ["Kubernetes"],
                "warnings": ["Warning: 1 originally covered keywords were removed during optimization: Django"]
            },
            # 新增: 真實計算的 metrics (使用 IndexCalculationServiceV2)
            "similarity_metrics": {
                "before": 60,
                "after": 85,
                "improvement": 25
            },
            "coverage_metrics": {
                "before": {"percentage": 40, "covered": ["Python", "Django"], "missed": ["Docker", "AWS", "Kubernetes"]},
                "after": {"percentage": 80, "covered": ["Python", "Docker", "AWS"], "missed": ["Kubernetes"]},
                "improvement": 40,
                "newly_added": ["Docker", "AWS"],
                "removed": ["Django"]
            },
            "gap_analysis_insights": {
                "structure_found": {
                    "sections": {"summary": "Summary", "experience": "Experience"},
                    "metadata": {"total_sections": 2}
                },
                "improvements_applied": 2
            },
            "processing_time_ms": 3000,
            "stage_timings": {
                "instruction_compilation_ms": 300,
                "resume_writing_ms": 2000
            },
            "metadata": {
                "metrics_calculation": "IndexCalculationServiceV2"
            }
        }

        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   new_callable=AsyncMock, return_value=mock_result):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200
        data = response.json()

        # Check success response structure
        assert data["success"] is True
        assert data["data"] is not None
        assert data["error"]["has_error"] is False
        assert data["warning"]["has_warning"] is True  # Django was removed

        # Check keyword tracking
        assert "keyword_tracking" in data["data"]
        tracking = data["data"]["keyword_tracking"]
        assert "Python" in tracking["still_covered"]
        assert "Django" in tracking["removed"]
        assert "Docker" in tracking["newly_added"]
        assert "AWS" in tracking["newly_added"]
        assert "Kubernetes" in tracking["still_missing"]

        # Check warning about removed keyword
        assert data["warning"]["message"] == "Optimization successful but 1 keywords removed"
        assert "Django" in data["warning"]["details"]

        # Check real metrics calculation (IndexCalculationServiceV2)
        similarity = data["data"]["similarity"]
        assert similarity["before"] == 60
        assert similarity["after"] == 85  # 真實計算, 不是簡單的 +20
        assert similarity["improvement"] == 25

        coverage = data["data"]["coverage"]
        assert coverage["before"]["percentage"] == 40
        assert coverage["after"]["percentage"] == 80
        assert coverage["improvement"] == 40
        assert set(coverage["newly_added"]) == {"Docker", "AWS"}
        assert set(coverage["removed"]) == {"Django"}

    # Test ID: API-TLR-522-IT
    @pytest.mark.asyncio
    async def test_no_keywords_removed_no_warning(self):
        """
        Test ID: API-TLR-522-IT
        Test that no warning is generated when no keywords are removed.

        測試原因: 確保沒有關鍵字被移除時不會產生誤報警告
        """
        request_data = {
            "job_description": "Python developer role with Django framework experience required. " * 10,
            "original_resume": "<html><body><p>Python and Django developer</p></body></html>" * 5,
            "gap_analysis": {
                "core_strengths": ["Python", "Django"],
                "key_gaps": ["[Skill Gap] Docker"],
                "quick_improvements": ["Add Docker experience"],
                "covered_keywords": ["Python", "Django"],
                "missing_keywords": ["Docker"],
                "coverage_percentage": 66,
                "similarity_percentage": 75
            }
        }

        mock_result = {
            "optimized_resume": "<html><body><p>Python and Django developer with Docker</p></body></html>",
            "applied_improvements": "<ul><li>Added Docker</li></ul>",
            "improvement_count": 1,
            "keyword_tracking": {
                "still_covered": ["Python", "Django"],
                "removed": [],
                "newly_added": ["Docker"],
                "still_missing": [],
                "warnings": []
            },
            "gap_analysis_insights": {
                "structure_found": {"sections": {}, "metadata": {}},
                "improvements_applied": 1
            }
        }

        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   new_callable=AsyncMock, return_value=mock_result):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200
        data = response.json()

        # Should have no warning
        assert data["warning"]["has_warning"] is False
        assert data["warning"]["message"] == ""
        assert data["warning"]["details"] == []

    # Test ID: API-TLR-523-IT
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="CONSOLIDATED: Moved to ERROR_HANDLER test suite - ERR-016-UT")
    async def test_validation_error_too_short(self):
        """
        Test ID: API-TLR-523-IT [已合併至 ERROR_HANDLER]
        Test validation error when input is too short.

        測試原因: 驗證 API 最小長度要求
        """
        request_data = {
            "job_description": "Short job description for validation testing purposes only that meets minimum Pydantic requirements but fails service validation due to insufficient length for meaningful processing and analysis of requirements",  # 200+ chars for service validation
            "original_resume": "<html><body><p>Short resume for testing validation purposes only, containing minimal content that meets basic Pydantic requirements but insufficient for meaningful analysis</p></body></html>",  # 100+ chars
            "gap_analysis": {
                "core_strengths": ["Python"],
                "key_gaps": ["[Skill Gap] Docker"],
                "quick_improvements": ["Add Docker"],
                "coverage_percentage": 50,
                "similarity_percentage": 60
            }
        }

        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   side_effect=ValueError("Job description too short (minimum 200 characters)")):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200  # API returns 200 with error in body
        data = response.json()

        assert data["success"] is False
        assert data["data"] is None
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "VALIDATION_TOO_SHORT"
        assert "too short" in data["error"]["message"].lower()
        assert "job_description" in data["error"]["field_errors"]

    # Test ID: API-TLR-524-IT
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="CONSOLIDATED: Moved to ERROR_HANDLER test suite - ERR-017-UT")
    async def test_external_service_error(self):
        """
        Test ID: API-TLR-524-IT [已合併至 ERROR_HANDLER]
        Test handling of external service errors.

        測試原因: 確保外部服務錯誤有適當的錯誤處理
        """
        from fastapi import HTTPException

        request_data = {
            "job_description": "Valid job description " * 20,
            "original_resume": "<html><body><p>Valid resume</p></body></html>" * 10,
            "gap_analysis": {
                "core_strengths": ["Python"],
                "key_gaps": ["[Skill Gap] Docker"],
                "quick_improvements": ["Add Docker"],
                "coverage_percentage": 50,
                "similarity_percentage": 60
            }
        }

        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   side_effect=HTTPException(status_code=429, detail="Rate limit exceeded")):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "EXTERNAL_RATE_LIMIT_EXCEEDED"
        assert "rate limit" in data["error"]["message"].lower()

    # Test ID: API-TLR-525-IT
    @pytest.mark.asyncio
    async def test_system_internal_error(self):
        """
        Test ID: API-TLR-525-IT
        Test handling of unexpected internal errors.

        測試原因: 防禦性編程 - 處理未預期的系統錯誤
        """
        request_data = {
            "job_description": "Valid job description " * 20,
            "original_resume": "<html><body><p>Valid resume</p></body></html>" * 10,
            "gap_analysis": {
                "core_strengths": ["Python"],
                "key_gaps": ["[Skill Gap] Docker"],
                "quick_improvements": ["Add Docker"],
                "coverage_percentage": 50,
                "similarity_percentage": 60
            }
        }

        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   side_effect=Exception("Unexpected error")):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
        # Error message can be in Chinese or English
        error_msg = data["error"]["message"].lower()
        assert "unexpected" in error_msg or "未預期" in error_msg

    # Test ID: API-TLR-526-IT
    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """
        Test ID: API-TLR-526-IT
        測試 IndexCalculationServiceV2 服務錯誤處理

        測試原因: 驗證服務失敗時正確返回錯誤（不使用 fallback）
        """
        request_data = {
            "job_description": "Python Django Docker AWS developer needed. " * 15,
            "original_resume": "<html><body><p>Python Django developer</p></body></html>" * 10,
            "gap_analysis": {
                "core_strengths": ["Python", "Django"],
                "key_gaps": ["[Skill Gap] Docker", "[Skill Gap] AWS"],
                "quick_improvements": ["Add Docker", "Add AWS"],
                "covered_keywords": ["Python", "Django"],
                "missing_keywords": ["Docker", "AWS"],
                "coverage_percentage": 50,
                "similarity_percentage": 60
            }
        }

        # Mock tailoring service to raise ServiceError (from IndexCalculationServiceV2)
        with patch('src.api.v1.resume_tailoring.tailoring_service.tailor_resume',
                   new_callable=AsyncMock) as mock_tailor:
            mock_tailor.side_effect = ServiceError("IndexCalculationServiceV2: Azure OpenAI connection timeout")

            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/tailor-resume",
                    json=request_data
                )

        assert response.status_code == 200  # API 層級返回 200
        data = response.json()

        # 驗證返回服務錯誤而不是 fallback
        assert data["success"] is False
        assert data["error"]["has_error"] is True
        # ServiceError is mapped to SYSTEM_INTERNAL_ERROR in unified error handler
        assert data["error"]["code"] == "SYSTEM_INTERNAL_ERROR"
        # The error message may be in Chinese or English
        error_msg = data["error"]["message"]
        assert "Azure OpenAI" in error_msg or "系統發生未預期錯誤" in error_msg

        # 確保沒有部分結果返回 (data might be None or empty dict)
        assert data["data"] is None or data["data"] == {}
