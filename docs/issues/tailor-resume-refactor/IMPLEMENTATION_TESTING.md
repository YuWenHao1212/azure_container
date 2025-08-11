# Resume Tailoring v2.1.0-simplified 實作與測試指南

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-11  
**基於**: API_ANALYSIS_20250811.md v1.2.0  
**狀態**: 實作待開始

## 📋 執行摘要

本文檔為 `/api/v1/tailor-resume` API v2.1.0-simplified 的實作指南與測試計畫，基於 API_ANALYSIS_20250811.md 中的混合 CSS 標記方案。

## 🎯 實作目標

### 核心功能
1. **混合 CSS 標記系統**
   - LLM 生成語意標記（opt-modified, opt-new, opt-placeholder）
   - Python 後處理加入關鍵字標記（opt-keyword, opt-keyword-existing）

2. **四種關鍵字狀態追蹤**
   - still_covered → 保留的關鍵字
   - removed → 被移除的關鍵字（觸發警告）
   - newly_added → 新增的關鍵字
   - still_missing → 仍缺少的關鍵字

3. **標準錯誤處理**
   - 使用 VALIDATION_*, EXTERNAL_*, SYSTEM_* 錯誤碼
   - 支援 has_error 和 field_errors
   - 雙層警告機制

## 🛠️ 實作步驟

### Step 1: 實作關鍵字檢測方法

```python
# src/services/resume_tailoring.py

def _detect_keywords_presence(
    self, 
    html_content: str, 
    keywords_to_check: list[str]
) -> list[str]:
    """
    檢測 HTML 內容中哪些關鍵字實際存在
    
    智能匹配規則：
    - "CI/CD" → 可匹配 "CI-CD", "CI CD", "CICD"
    - "Node.js" → 可匹配 "NodeJS", "nodejs", "Node JS"
    - "Machine Learning" → 可匹配 "ML"
    """
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator=' ', strip=True).lower()
    
    found_keywords = []
    for keyword in keywords_to_check:
        patterns = self._create_keyword_patterns(keyword)
        for pattern in patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                found_keywords.append(keyword)
                break
                
    return found_keywords

def _create_keyword_patterns(self, keyword: str) -> list[str]:
    """
    為關鍵字建立多種匹配模式
    """
    patterns = []
    base = re.escape(keyword)
    
    # 基本模式
    patterns.append(base)
    
    # 處理特殊情況
    if "/" in keyword:  # CI/CD → CI-CD, CI CD
        variants = [
            keyword.replace("/", "-"),
            keyword.replace("/", " "),
            keyword.replace("/", "")
        ]
        patterns.extend([re.escape(v) for v in variants])
    
    if "." in keyword:  # Node.js → NodeJS, Node JS
        variants = [
            keyword.replace(".", ""),
            keyword.replace(".", " ")
        ]
        patterns.extend([re.escape(v) for v in variants])
    
    # 縮寫對照
    abbreviations = {
        "Machine Learning": ["ML"],
        "Artificial Intelligence": ["AI"],
        "Deep Learning": ["DL"],
        "Natural Language Processing": ["NLP"]
    }
    
    if keyword in abbreviations:
        patterns.extend([re.escape(abbr) for abbr in abbreviations[keyword]])
    
    return patterns

def _categorize_keywords(
    self,
    original_resume: str,
    optimized_html: str,
    covered_keywords: list[str],
    missing_keywords: list[str]
) -> dict[str, list[str]]:
    """
    分類所有關鍵字的狀態變化
    """
    # 檢測原始履歷中的關鍵字
    originally_present = self._detect_keywords_presence(
        original_resume, 
        covered_keywords or []
    )
    
    # 檢測優化後履歷中的所有關鍵字
    all_keywords = list(set((covered_keywords or []) + (missing_keywords or [])))
    currently_present = self._detect_keywords_presence(
        optimized_html,
        all_keywords
    )
    
    # 分類
    result = {
        "still_covered": [
            kw for kw in (covered_keywords or []) 
            if kw in currently_present
        ],
        "removed": [
            kw for kw in (covered_keywords or []) 
            if kw not in currently_present
        ],
        "newly_added": [
            kw for kw in (missing_keywords or []) 
            if kw in currently_present
        ],
        "still_missing": [
            kw for kw in (missing_keywords or []) 
            if kw not in currently_present
        ]
    }
    
    # 記錄警告
    if result["removed"]:
        logger.warning(
            f"⚠️ Keywords removed during optimization: {result['removed']}"
        )
    
    return result
```

### Step 2: 更新 _process_optimization_result_v2 方法

已在 API_ANALYSIS_20250811.md 中詳細說明（第 547-591 行）

### Step 3: 更新 API 路由

```python
# src/api/v1/resume_tailoring.py

# 更新 tailor_resume 端點的錯誤處理
async def tailor_resume(
    request: TailorResumeRequest,
    settings: Settings = Depends(get_settings)
) -> TailoringResponse:
    try:
        result = await tailoring_service.tailor_resume(
            job_description=request.job_description,
            original_resume=request.original_resume,
            gap_analysis=request.gap_analysis,
            language=request.options.language,
            include_markers=request.options.include_visual_markers
        )
        
        # 處理關鍵字移除警告
        warning = None
        if result.get("keyword_tracking", {}).get("removed"):
            removed = result["keyword_tracking"]["removed"]
            warning = {
                "has_warning": True,
                "message": f"Optimization successful but {len(removed)} keywords removed",
                "details": removed
            }
        else:
            warning = {
                "has_warning": False,
                "message": "",
                "details": []
            }
        
        return TailoringResponse(
            success=True,
            data=result,
            error={
                "has_error": False,
                "code": "",
                "message": "",
                "details": "",
                "field_errors": {}
            },
            warning=warning
        )
        
    except ValueError as e:
        # 使用 VALIDATION_* 錯誤碼
        # 詳見 API_ANALYSIS_20250811.md 第 936-963 行
        pass
```

### Step 4: 更新 Pydantic 模型

```python
# src/models/api/resume_tailoring.py

class KeywordTracking(BaseModel):
    """關鍵字追蹤資訊"""
    originally_covered: list[str]
    originally_missing: list[str]
    still_covered: list[str]
    removed: list[str]
    newly_added: list[str]
    still_missing: list[str]
    coverage_change: dict[str, int]
    warnings: list[str]

class ErrorInfo(BaseModel):
    """錯誤資訊（標準格式）"""
    has_error: bool
    code: str
    message: str
    details: str
    field_errors: dict[str, list[str]] = {}

class WarningInfo(BaseModel):
    """警告資訊"""
    has_warning: bool
    message: str
    details: list[str] = []

class TailoringResponse(BaseModel):
    """API 回應格式"""
    success: bool
    data: TailoringResult | None
    error: ErrorInfo
    warning: WarningInfo
```

## 🧪 測試計畫

### 單元測試

#### UT-01: 關鍵字檢測測試
```python
def test_detect_keywords_presence():
    """測試關鍵字檢測邏輯"""
    service = ResumeTailoringService()
    html = "<p>Experience with CI/CD pipelines and Node.js development</p>"
    
    # 測試變體匹配
    found = service._detect_keywords_presence(html, ["CI-CD", "NodeJS"])
    assert "CI-CD" in found  # 應該匹配 CI/CD
    assert "NodeJS" in found  # 應該匹配 Node.js

def test_categorize_keywords():
    """測試關鍵字分類邏輯"""
    service = ResumeTailoringService()
    
    original = "<p>Python and Django developer</p>"
    optimized = "<p>Full-stack developer with Docker expertise</p>"
    
    result = service._categorize_keywords(
        original,
        optimized,
        covered_keywords=["Python", "Django"],
        missing_keywords=["Docker", "AWS"]
    )
    
    assert result["removed"] == ["Python", "Django"]
    assert result["newly_added"] == ["Docker"]
    assert result["still_missing"] == ["AWS"]
```

#### UT-02: 警告生成測試
```python
def test_warning_generation_for_removed_keywords():
    """測試關鍵字被移除時的警告生成"""
    # 模擬優化結果移除了原有關鍵字
    # 驗證生成正確的警告訊息
    pass
```

### 整合測試

#### IT-01: 完整流程測試
```python
async def test_full_pipeline_with_keyword_tracking():
    """測試完整的關鍵字追蹤流程"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tailor-resume",
            json={
                "job_description": "..." * 100,  # ≥200 chars
                "original_resume": "<html>..." * 50,  # ≥200 chars
                "gap_analysis": {
                    "core_strengths": ["Python", "Leadership"],
                    "key_gaps": ["[Skill Gap] Docker"],
                    "quick_improvements": ["Add Docker certification"],
                    "covered_keywords": ["Python", "Django"],
                    "missing_keywords": ["Docker", "Kubernetes"],
                    "coverage_percentage": 60,
                    "similarity_percentage": 70
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "keyword_tracking" in data["data"]
        assert data["warning"]["has_warning"] == False  # 假設沒有移除關鍵字
```

#### IT-02: 關鍵字移除警告測試
```python
async def test_keyword_removal_warning():
    """測試關鍵字被移除時返回警告但仍為 200 狀態"""
    # 構造會導致關鍵字被移除的測試案例
    # 驗證返回 HTTP 200 + warning
    pass
```

### 效能測試

#### PT-01: 關鍵字檢測效能
```python
def test_keyword_detection_performance():
    """測試關鍵字檢測的效能影響"""
    # 測試處理 50+ 關鍵字的效能
    # 確保後處理時間 < 100ms
    pass
```

## 📊 測試覆蓋要求

| 測試類型 | 目標覆蓋率 | 關鍵測試點 |
|---------|-----------|-----------|
| 單元測試 | > 90% | 關鍵字檢測、分類、警告生成 |
| 整合測試 | > 80% | API 端點、錯誤處理、警告機制 |
| 效能測試 | 100% | P50 < 4.5s, P95 < 7.5s |

## 🚀 部署計畫

### 前置條件
1. 所有測試通過
2. Ruff 檢查無錯誤：`ruff check src/ --line-length=120`
3. 文檔更新完成

### 部署步驟
1. **本地測試**
   ```bash
   pytest test/unit/test_resume_tailoring_v2.py -v
   pytest test/integration/test_resume_tailoring_v2.py -v
   ```

2. **性能驗證**
   ```bash
   python test/performance/test_resume_tailoring_performance.py
   ```

3. **部署到開發環境**
   ```bash
   docker build -t resume-tailoring:v2.1.0 .
   docker run -e ENVIRONMENT=development ...
   ```

4. **生產部署**
   - 無需向後相容（沒有 live users）
   - 直接替換現有版本
   - 監控關鍵指標 24 小時

## 📈 成功標準

### 必須達成
- ✅ 關鍵字追蹤功能正常運作
- ✅ 警告機制正確觸發
- ✅ P50 < 4.5s, P95 < 7.5s
- ✅ 所有測試通過
- ✅ Ruff 檢查無錯誤

### 監控指標
- keyword_removal_rate: 關鍵字被移除的比率
- warning_trigger_rate: 警告觸發率
- response_time_p50/p95: 回應時間百分位數

## 🔄 回滾計畫

如果部署後發現嚴重問題：
1. 立即回滾到 v2.0.0 版本
2. 分析日誌找出問題
3. 修復後重新部署

---

**最後更新**: 2025-08-11  
**基於**: API_ANALYSIS_20250811.md v1.2.0  
**狀態**: 待實作