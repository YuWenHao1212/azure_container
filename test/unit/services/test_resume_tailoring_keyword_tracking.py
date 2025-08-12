"""
Unit tests for Resume Tailoring keyword tracking functionality.

Following Gap Analysis V2 pattern with Test ID markers.
Implements defensive testing approach for LLM output variability.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.resume_tailoring import ResumeTailoringService


class TestKeywordDetection:
    """Test keyword detection functionality."""

    # Test ID: API-TAILOR-001-UT
    def test_exact_keyword_matching(self):
        """
        Test ID: API-TAILOR-001-UT
        Test exact keyword detection in HTML content.
        
        測試原因: 確保系統能準確檢測關鍵字是否存在於履歷中
        """
        service = ResumeTailoringService()

        html_content = """
        <div>
            <p>Experience with Python, JavaScript and React</p>
            <p>Strong knowledge of SQL databases</p>
        </div>
        """

        keywords = ["Python", "JavaScript", "React", "SQL", "MongoDB"]

        found = service._detect_keywords_presence(html_content, keywords)

        assert "Python" in found
        assert "JavaScript" in found
        assert "React" in found
        assert "SQL" in found
        assert "MongoDB" not in found

    # Test ID: API-TAILOR-002-UT
    def test_keyword_variant_matching(self):
        """
        Test ID: API-TAILOR-002-UT
        Test keyword variant detection (CI/CD → CI-CD, Node.js → NodeJS).
        
        測試原因: 驗證系統能處理關鍵字的常見變體寫法
        實際案例: LLM 可能將 "CI/CD" 寫成 "CI-CD" 或 "CICD"
        """
        service = ResumeTailoringService()

        html_content = """
        <div>
            <p>Experience with CI-CD pipelines</p>
            <p>NodeJS backend development</p>
            <p>Dotnet framework expertise</p>
        </div>
        """

        keywords = ["CI/CD", "Node.js", ".NET"]

        found = service._detect_keywords_presence(html_content, keywords)

        # Should find CI/CD despite being written as CI-CD
        assert "CI/CD" in found
        # Should find Node.js despite being written as NodeJS
        assert "Node.js" in found
        # Should find .NET despite being written as dotnet
        assert ".NET" in found

    # Test ID: API-TAILOR-003-UT
    def test_abbreviation_mapping(self):
        """
        Test ID: API-TAILOR-003-UT
        Test abbreviation bidirectional matching (ML ↔ Machine Learning).
        
        測試原因: 確保縮寫和全稱都能被正確識別
        實作細節: 使用內建字典進行雙向映射
        """
        service = ResumeTailoringService()

        # Test abbreviation → full form
        html_content_1 = """
        <div>
            <p>Expert in ML and AI technologies</p>
        </div>
        """

        keywords_1 = ["Machine Learning", "Artificial Intelligence"]
        found_1 = service._detect_keywords_presence(html_content_1, keywords_1)

        assert "Machine Learning" in found_1  # ML should match
        assert "Artificial Intelligence" in found_1  # AI should match

        # Test full form → abbreviation
        html_content_2 = """
        <div>
            <p>Deep understanding of Machine Learning algorithms</p>
        </div>
        """

        keywords_2 = ["ML", "AI"]
        found_2 = service._detect_keywords_presence(html_content_2, keywords_2)

        assert "ML" in found_2  # Machine Learning should match
        assert "AI" not in found_2  # AI is not present


class TestKeywordCategorization:
    """Test keyword state categorization."""

    # Test ID: API-TAILOR-005-UT
    def test_keyword_state_tracking(self):
        """
        Test ID: API-TAILOR-005-UT
        Test categorization into four states: still_covered, removed, newly_added, still_missing.
        
        測試原因: 核心功能 - 追蹤關鍵字在優化前後的狀態變化
        """
        service = ResumeTailoringService()

        originally_covered = ["Python", "JavaScript", "SQL"]
        currently_covered = ["Python", "SQL", "MongoDB", "React"]
        covered_keywords = ["Python", "JavaScript", "SQL"]
        missing_keywords = ["MongoDB", "React", "Docker"]

        result = service._categorize_keywords(
            originally_covered,
            currently_covered,
            covered_keywords,
            missing_keywords
        )

        # Keywords that were and still are present
        assert set(result["still_covered"]) == {"Python", "SQL"}

        # Keywords that were present but now missing
        assert set(result["removed"]) == {"JavaScript"}

        # Keywords that were missing but now added
        assert set(result["newly_added"]) == {"MongoDB", "React"}

        # Keywords that were missing and still missing
        assert set(result["still_missing"]) == {"Docker"}
