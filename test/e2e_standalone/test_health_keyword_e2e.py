"""
E2E tests for Health Check + Keyword Extraction - Real Azure OpenAI API.

Based on TEST_SPEC_HEALTH_KEYWORDS.md v3.1.0
Implements API-KW-301-E2E: Complete health + keyword workflow test.
"""

import os
import sys
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from src.main import create_app


class TestHealthKeywordE2E:
    """E2E tests for complete health + keyword workflow."""

    @pytest.fixture
    def test_client(self):
        """Create test client without mocking services for real API tests."""
        # Ensure we don't use mocks for E2E tests
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def valid_traditional_chinese_jd_request(self):
        """Valid Traditional Chinese job description request for E2E testing."""
        return {
            "job_description": "我們正在尋找一位資深的全端工程師，需要具備React前端開發和Python後端開發的豐富經驗。"
                             "理想的候選人應該熟悉FastAPI框架、Docker容器技術和Azure雲端服務的部署。"
                             "必須對微服務架構有深入理解，並且有RESTful API和GraphQL的開發經驗。"
                             "具備CI/CD流程和測試驅動開發經驗者優先考慮。同時需要熟悉分散式系統設計，"
                             "具備系統架構規劃能力和優秀的團隊合作精神。需要至少五年以上的軟體開發經驗，"
                             "能夠在快節奏的敏捷開發環境中獨立工作。必須具備良好的溝通能力和問題解決技能，"
                             "並能夠指導初級工程師的技術成長。對於新技術學習有熱忱，能夠持續提升個人技能。",
            "max_keywords": 12
        }

    def test_API_KW_301_E2E_complete_health_keyword_workflow(self, test_client, valid_traditional_chinese_jd_request):
        """
        TEST ID: API-KW-301-E2E
        測試名稱: 完整健康檢查 + 關鍵字提取工作流程
        優先級: P0
        類型: E2E 測試
        測試目標: 驗證系統健康檢查和關鍵字提取的完整端對端流程
        
        判斷標準:
        1. 健康檢查端點正常運作
        2. 關鍵字提取能夠處理繁體中文 JD
        3. 系統在真實 API 環境下穩定運作
        4. 所有回應格式正確且完整
        """
        print("\n🔍 Starting complete Health + Keyword E2E workflow test...")

        # Step 1: Health Check Validation
        print("  Step 1: Testing health check endpoint...")
        health_start = time.time()
        health_response = test_client.get("/health")
        health_duration = time.time() - health_start

        # Validate health check response
        assert health_response.status_code == 200, f"Health check failed with status {health_response.status_code}"
        health_data = health_response.json()
        assert health_data["success"] is True, "Health check success field is not True"
        assert "data" in health_data, "Health check missing data field"
        assert health_data["data"]["status"] == "healthy", "Health status is not healthy"

        print(f"    ✅ Health check passed in {health_duration:.3f}s")

        # Step 2: Keyword Extraction with Traditional Chinese
        print("  Step 2: Testing keyword extraction with Traditional Chinese JD...")
        keyword_start = time.time()

        keyword_response = test_client.post(
            "/api/v1/extract-jd-keywords",
            json=valid_traditional_chinese_jd_request,
            headers={"Content-Type": "application/json"}
        )
        keyword_duration = time.time() - keyword_start

        # Validate keyword extraction response
        assert keyword_response.status_code == 200, f"Keyword extraction failed with status {keyword_response.status_code}"
        keyword_data = keyword_response.json()
        assert keyword_data["success"] is True, "Keyword extraction success field is not True"
        assert "data" in keyword_data, "Keyword extraction missing data field"

        # Validate keyword data structure
        kw_data = keyword_data["data"]
        required_fields = ["keywords", "keyword_count", "detected_language", "processing_time_ms"]
        for field in required_fields:
            assert field in kw_data, f"Missing required field: {field}"

        # Validate Traditional Chinese language detection
        assert kw_data["detected_language"] == "zh-TW", f"Expected zh-TW, got {kw_data['detected_language']}"

        # Validate keywords content
        keywords = kw_data["keywords"]
        assert isinstance(keywords, list), "Keywords should be a list"
        assert len(keywords) > 0, "Keywords list should not be empty"
        assert kw_data["keyword_count"] == len(keywords), "Keyword count mismatch"

        # Validate Traditional Chinese keywords are present
        chinese_keywords_found = 0
        for keyword in keywords:
            if any('\u4e00' <= char <= '\u9fff' for char in keyword):  # Chinese character range
                chinese_keywords_found += 1

        assert chinese_keywords_found > 0, "No Traditional Chinese keywords found in results"

        print(f"    ✅ Keyword extraction passed in {keyword_duration:.3f}s")
        print(f"    📋 Extracted {len(keywords)} keywords ({chinese_keywords_found} Chinese)")

        # Step 3: System Integration Validation
        print("  Step 3: Validating system integration...")

        # Check that the system handles both endpoints consistently
        total_time = health_duration + keyword_duration
        assert total_time < 30.0, f"Total workflow time {total_time:.3f}s exceeds 30s limit"

        # Validate response consistency
        assert health_data["timestamp"], "Health check missing timestamp"
        assert keyword_data["timestamp"], "Keyword extraction missing timestamp"

        # Check for proper error handling structure (even in success cases)
        assert "error" in health_data, "Health check missing error field"
        assert "error" in keyword_data, "Keyword extraction missing error field"
        assert health_data["error"] is None, "Health check error should be null on success"
        assert keyword_data["error"] is None, "Keyword extraction error should be null on success"

        # Step 4: Advanced Validation - Language Detection Accuracy
        print("  Step 4: Validating language detection accuracy...")

        # Check if prompt version indicates Traditional Chinese processing
        if "prompt_version_used" in kw_data:
            prompt_version = kw_data["prompt_version_used"]
            assert "zh-TW" in prompt_version or "chinese" in prompt_version.lower(), \
                f"Prompt version '{prompt_version}' doesn't indicate Chinese processing"

        # Validate processing time is reasonable for real API
        processing_time_s = kw_data["processing_time_ms"] / 1000.0
        assert processing_time_s < 20.0, f"Processing time {processing_time_s:.3f}s too high"
        assert processing_time_s > 0.5, f"Processing time {processing_time_s:.3f}s suspiciously low"

        print(f"    ✅ Language detection validated (processing time: {processing_time_s:.3f}s)")

        # Final Summary
        print("\n📊 E2E Test Summary:")
        print(f"   Health Check: ✅ {health_duration:.3f}s")
        print(f"   Keyword Extraction: ✅ {keyword_duration:.3f}s")
        print(f"   Total Workflow Time: {total_time:.3f}s")
        print(f"   Detected Language: {kw_data['detected_language']}")
        print(f"   Keywords Extracted: {len(keywords)} total, {chinese_keywords_found} Chinese")
        print(f"   Sample Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

        # Save E2E test summary
        log_dir = "test/logs"
        os.makedirs(log_dir, exist_ok=True)
        summary_file = f"{log_dir}/e2e_field_validation_API-KW-301-E2E.txt"

        with open(summary_file, 'w') as f:
            f.write("API-KW-301-E2E Field Validation Summary:\n")
            f.write(f"Health Check Duration: {health_duration:.3f}s\n")
            f.write(f"Keyword Processing Time: {processing_time_s:.3f}s\n")
            f.write(f"Total Workflow Time: {total_time:.3f}s\n")
            f.write(f"Detected Language: {kw_data['detected_language']}\n")
            f.write(f"Keywords Count: {len(keywords)}\n")
            f.write(f"Chinese Keywords: {chinese_keywords_found}\n")

        print(f"   Summary saved: {summary_file}")
        print("\n🎉 Complete E2E workflow test passed!")
