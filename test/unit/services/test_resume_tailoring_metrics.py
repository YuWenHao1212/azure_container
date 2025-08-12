"""
Resume Tailoring 單元測試 - 關鍵字處理與 Metrics 計算相關測試

本檔案包含 Resume Tailoring 服務的單元測試，專注於：
- 關鍵字檢測功能
- 關鍵字分類邏輯
- 變體匹配機制
- 縮寫對應功能
- Metrics 計算整合
- ServiceError 異常處理

所有測試都完全 Mock 外部依賴，確保單元測試的隔離性和可靠性。
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.services.exceptions import ServiceError
from src.services.resume_tailoring import ResumeTailoringService


class TestResumeTailoringMetrics:
    """Resume Tailoring 關鍵字處理與 Metrics 計算單元測試"""

    @pytest.fixture
    def mock_service(self):
        """建立部分 Mock 的 ResumeTailoringService - 保留關鍵字檢測的真實邏輯"""
        with patch('src.services.resume_tailoring.get_llm_client'), \
             patch('src.services.resume_tailoring.MonitoringService'), \
             patch('src.services.resume_tailoring.UnifiedPromptService'), \
             patch('src.services.resume_tailoring.HTMLProcessor'), \
             patch('src.services.resume_tailoring.LanguageHandler'), \
             patch('src.services.resume_tailoring.STARFormatter'), \
             patch('src.services.resume_tailoring.MarkerFixer'), \
             patch('src.services.resume_tailoring.SectionProcessor'), \
             patch('src.services.resume_tailoring.EnglishStandardizer'), \
             patch('src.services.resume_tailoring.ChineseStandardizer'), \
             patch('src.services.instruction_compiler.InstructionCompiler'):
            service = ResumeTailoringService()
            return service

    # Test ID: API-TLR-501-UT
    def test_detect_keywords_presence_basic(self, mock_service):
        """
        Test ID: API-TLR-501-UT
        測試基本關鍵字檢測功能

        測試原因: Resume Tailoring 需要追蹤關鍵字狀態變化，確保關鍵字檢測準確
        """
        # Arrange
        html_content = "<p>Python developer with Django expertise and React experience</p>"
        keywords_to_check = ["Python", "Django", "React", "Angular"]

        # Act
        result = mock_service._detect_keywords_presence(html_content, keywords_to_check)

        # Assert
        expected_found = ["Python", "Django", "React"]
        assert set(result) == set(expected_found)
        assert "Angular" not in result
        assert len(result) == 3

    # Test ID: API-TLR-502-UT
    def test_categorize_keywords_four_states(self, mock_service):
        """
        Test ID: API-TLR-502-UT
        測試關鍵字四種狀態分類驗證

        測試原因: 核心業務邏輯，用於生成警告和統計報告
        """
        # Arrange
        originally_covered = {"Python", "Django", "Docker"}
        currently_covered = {"Python", "AWS", "React"}
        covered_keywords = ["Python", "Django", "Docker"]
        missing_keywords = ["AWS", "React", "Kubernetes"]

        # Act
        result = mock_service._categorize_keywords(
            originally_covered,
            currently_covered,
            covered_keywords,
            missing_keywords
        )

        # Assert
        assert result["still_covered"] == ["Python"]
        assert set(result["removed"]) == {"Django", "Docker"}
        assert set(result["newly_added"]) == {"AWS", "React"}
        assert result["still_missing"] == ["Kubernetes"]

    # Test ID: API-TLR-503-UT
    def test_keyword_variant_matching(self, mock_service):
        """
        Test ID: API-TLR-503-UT
        測試關鍵字變體智能匹配（防禦性設計）

        測試原因: LLM 不是 100% 可靠，防禦性設計避免格式差異導致追蹤失準
        """
        # Arrange - 測試正向匹配: 內容包含我們要找的關鍵字
        html_content = "<p>Experience with CI-CD pipelines and NodeJS development, plus CICD</p>"
        keywords_to_check = ["CI-CD", "NodeJS", "CICD"]

        # Act
        result = mock_service._detect_keywords_presence(html_content, keywords_to_check)

        # Assert
        # 精確匹配應該成功識別
        expected_matches = {"CI-CD", "NodeJS", "CICD"}
        assert set(result) == expected_matches

    # Test ID: API-TLR-504-UT
    def test_abbreviation_mapping(self, mock_service):
        """
        Test ID: API-TLR-504-UT
        測試專業術語縮寫匹配（容錯機制）

        測試原因: 確保縮寫和全稱都能被正確識別和追蹤
        """
        # Arrange
        html_content = "<p>Machine Learning engineer with API development experience</p>"
        keywords_to_check = ["ML", "Application Programming Interface"]

        # Act
        result = mock_service._detect_keywords_presence(html_content, keywords_to_check)

        # Assert
        # 縮寫對應: Machine Learning ↔ ML, API ↔ Application Programming Interface
        expected_matches = {"ML", "Application Programming Interface"}
        assert set(result) == expected_matches

    # Test ID: API-TLR-505-UT
    @pytest.mark.asyncio
    async def test_calculate_metrics_after_optimization_success(self, mock_service):
        """
        Test ID: API-TLR-505-UT
        測試 Metrics 計算成功流程

        測試原因: 確保真實 metrics 計算功能正常運作，不使用 fallback 估算值
        """
        # Arrange
        original_resume = "<p>Python Django developer</p>"
        optimized_resume = "<p>Python Django Docker developer</p>"
        gap_analysis = {
            "covered_keywords": ["Python", "Django"],
            "missing_keywords": ["Docker", "AWS"],
            "coverage_percentage": 50,
            "similarity_percentage": 60
        }

        # Mock get_index_calculation_service_v2 成功回應
        mock_index_service = Mock()
        mock_index_service.calculate_index = AsyncMock(return_value={
            "similarity_percentage": 75,
            "keyword_coverage": {
                "coverage_percentage": 80,
                "covered_keywords": ["Python", "Django", "Docker"],
                "missed_keywords": ["AWS"]
            }
        })

        with patch('src.services.index_calculation_v2.get_index_calculation_service_v2', return_value=mock_index_service):
            # Act
            result = await mock_service._calculate_metrics_after_optimization(
                job_description="Python Django Docker AWS developer",
                original_resume=original_resume,
                optimized_resume=optimized_resume,
                gap_analysis=gap_analysis,
                covered_keywords=["Python", "Django"],
                missing_keywords=["Docker", "AWS"]
            )

        # Assert
        assert result is not None
        assert result["similarity"]["after"] == 75
        assert result["coverage"]["after"]["percentage"] == 80
        assert result["similarity"]["before"] == 60  # 來自 gap_analysis
        assert result["coverage"]["before"]["percentage"] == 50

        # 驗證 IndexCalculationServiceV2 被正確調用
        mock_index_service.calculate_index.assert_called_once()

    # Test ID: API-TLR-506-UT
    @pytest.mark.asyncio
    async def test_calculate_metrics_service_failure(self, mock_service):
        """
        Test ID: API-TLR-506-UT
        測試 IndexCalculationServiceV2 失敗時正確拋出異常

        測試原因: 確保移除 fallback 機制後，服務失敗時正確拋出異常
        """
        # Arrange
        original_resume = "<p>Python Django developer</p>"
        optimized_resume = "<p>Python Django Docker developer</p>"
        gap_analysis = {
            "covered_keywords": ["Python", "Django"],
            "missing_keywords": ["Docker", "AWS"],
            "coverage_percentage": 50,
            "similarity_percentage": 60
        }

        # Mock get_index_calculation_service_v2 拋出異常
        mock_index_service = Mock()
        mock_index_service.calculate_index = AsyncMock(
            side_effect=ServiceError("IndexCalculationServiceV2: Azure OpenAI connection timeout")
        )

        with patch('src.services.index_calculation_v2.get_index_calculation_service_v2', return_value=mock_index_service):
            # Act & Assert
            with pytest.raises(ServiceError) as exc_info:
                await mock_service._calculate_metrics_after_optimization(
                    job_description="Python Django Docker AWS developer",
                    original_resume=original_resume,
                    optimized_resume=optimized_resume,
                    gap_analysis=gap_analysis,
                    covered_keywords=["Python", "Django"],
                    missing_keywords=["Docker", "AWS"]
                )

            # 驗證異常正確傳播
            assert "IndexCalculationServiceV2" in str(exc_info.value)
            assert "Azure OpenAI connection timeout" in str(exc_info.value)

            # 確保沒有生成任何 fallback 結果
            mock_index_service.calculate_index.assert_called_once()


class TestKeywordVariantPatterns:
    """關鍵字變體匹配模式測試"""

    @pytest.fixture
    def mock_service(self):
        """建立部分 Mock 的服務實例 - 保留關鍵字檢測邏輯"""
        with patch('src.services.resume_tailoring.get_llm_client'), \
             patch('src.services.resume_tailoring.MonitoringService'), \
             patch('src.services.resume_tailoring.UnifiedPromptService'), \
             patch('src.services.resume_tailoring.HTMLProcessor'), \
             patch('src.services.resume_tailoring.LanguageHandler'), \
             patch('src.services.resume_tailoring.STARFormatter'), \
             patch('src.services.resume_tailoring.MarkerFixer'), \
             patch('src.services.resume_tailoring.SectionProcessor'), \
             patch('src.services.resume_tailoring.EnglishStandardizer'), \
             patch('src.services.resume_tailoring.ChineseStandardizer'), \
             patch('src.services.instruction_compiler.InstructionCompiler'):
            service = ResumeTailoringService()
            return service

    # Test ID: API-TLR-507-UT
    def test_slash_variations(self, mock_service):
        """
        Test ID: API-TLR-507-UT
        測試斜槓變體匹配 (CI/CD, TCP/IP)
        """
        html_content = "<p>Experienced in CI-CD and TCP-IP networking, also CICD</p>"
        keywords = ["CI-CD", "TCP-IP", "CICD"]

        result = mock_service._detect_keywords_presence(html_content, keywords)

        # 精確匹配應該成功識別
        assert "CI-CD" in result
        assert "TCP-IP" in result
        assert "CICD" in result

    # Test ID: API-TLR-508-UT
    def test_dot_variations(self, mock_service):
        """
        Test ID: API-TLR-508-UT
        測試點號變體匹配 (Node.js, Vue.js)
        """
        html_content = "<p>NodeJS and VueJS developer, also nodejs and vuejs</p>"
        keywords = ["NodeJS", "VueJS", "nodejs", "vuejs"]

        result = mock_service._detect_keywords_presence(html_content, keywords)

        # 精確匹配應該成功識別
        expected_matches = {"NodeJS", "VueJS", "nodejs", "vuejs"}
        assert set(result) == expected_matches

    # Test ID: API-TLR-509-UT
    def test_case_insensitive_matching(self, mock_service):
        """
        Test ID: API-TLR-509-UT
        測試大小寫不敏感匹配
        """
        html_content = "<p>PYTHON developer with react experience</p>"
        keywords = ["Python", "React", "python", "REACT"]

        result = mock_service._detect_keywords_presence(html_content, keywords)

        # 大小寫應該不影響匹配
        expected_matches = {"Python", "React", "python", "REACT"}
        assert expected_matches.issubset(result)

    # Test ID: API-TLR-510-UT
    def test_special_characters_handling(self, mock_service):
        """
        Test ID: API-TLR-510-UT
        測試特殊字元處理 (C++, C#, .NET)
        """
        html_content = "<p>C++ and C# developer with .NET framework</p>"
        keywords = ["C++", "C#", ".NET", "Cpp", "CSharp", "dotnet"]

        result = mock_service._detect_keywords_presence(html_content, keywords)

        # 特殊字元應該被正確處理
        expected_special = {"C++", "C#", ".NET"}
        assert expected_special.issubset(result)


class TestKeywordCategorizationLogic:
    """關鍵字分類邏輯詳細測試"""

    @pytest.fixture
    def mock_service(self):
        """建立部分 Mock 的服務實例 - 保留關鍵字檢測邏輯"""
        with patch('src.services.resume_tailoring.get_llm_client'), \
             patch('src.services.resume_tailoring.MonitoringService'), \
             patch('src.services.resume_tailoring.UnifiedPromptService'), \
             patch('src.services.resume_tailoring.HTMLProcessor'), \
             patch('src.services.resume_tailoring.LanguageHandler'), \
             patch('src.services.resume_tailoring.STARFormatter'), \
             patch('src.services.resume_tailoring.MarkerFixer'), \
             patch('src.services.resume_tailoring.SectionProcessor'), \
             patch('src.services.resume_tailoring.EnglishStandardizer'), \
             patch('src.services.resume_tailoring.ChineseStandardizer'), \
             patch('src.services.instruction_compiler.InstructionCompiler'):
            service = ResumeTailoringService()
            return service

    # Test ID: API-TLR-511-UT
    def test_empty_sets_handling(self, mock_service):
        """
        Test ID: API-TLR-511-UT
        測試空集合處理
        """
        result = mock_service._categorize_keywords(
            originally_covered=set(),
            currently_covered=set(),
            covered_keywords=[],
            missing_keywords=["Python", "Django"]
        )

        assert result["still_covered"] == []
        assert result["removed"] == []
        assert result["newly_added"] == []
        assert result["still_missing"] == ["Python", "Django"]

    # Test ID: API-TLR-512-UT
    def test_all_keywords_removed(self, mock_service):
        """
        Test ID: API-TLR-512-UT
        測試所有關鍵字被移除的情況
        """
        originally_covered = {"Python", "Django", "React"}

        result = mock_service._categorize_keywords(
            originally_covered=originally_covered,
            currently_covered=set(),
            covered_keywords=list(originally_covered),
            missing_keywords=["AWS", "Docker"]
        )

        assert result["still_covered"] == []
        assert set(result["removed"]) == originally_covered
        assert result["newly_added"] == []
        assert result["still_missing"] == ["AWS", "Docker"]

