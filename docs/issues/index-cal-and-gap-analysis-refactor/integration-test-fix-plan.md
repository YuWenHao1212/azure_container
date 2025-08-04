# API 輸入驗證實作計劃

**文檔版本**: 1.0  
**建立日期**: 2025-08-04  
**狀態**: 待實作  
**預估工時**: 2-4小時  

---

## 📊 修復成果分析

### ✅ 測試修復成功指標
- **整合測試通過率**: 7.1% → 64.3% (**提升 827%**)
- **SSL連接問題**: 完全解決 ✅
- **測試環境隔離**: 100% 完成 ✅
- **Mock策略**: 成功實施 ✅
- **V2服務獨立運作**: 完全正常 ✅

### ⚠️ 剩餘問題確認
測試驗證報告確認：**剩餘 5 個失敗測試揭露的是 API 實作問題，非測試問題**

---

## 🎯 待修復的API缺失功能

| 測試編號 | 失敗原因 | API缺失功能 | 期望行為 |
|----------|----------|-------------|----------|
| **API-GAP-002** | JD長度 < 200字元未被拒絕 | 缺少最小長度驗證 | 返回400錯誤 + TEXT_TOO_SHORT |
| **API-GAP-003** | Resume長度 < 200字元未被拒絕 | 缺少最小長度驗證 | 返回400錯誤 + TEXT_TOO_SHORT |
| **API-GAP-006** | 無效語言(fr,ja)未被拒絕 | 缺少語言白名單驗證 | 返回400錯誤 + INVALID_LANGUAGE |
| **API-GAP-010** | 超時錯誤未正確處理 | 缺少超時處理邏輯 | 返回408/503 + timeout message |
| **API-GAP-011** | 限速錯誤未正確處理 | 缺少限速處理邏輯 | 返回429/503 + rate limit message |

---

## 🏗️ 架構分析

### 當前實作狀況
```python
# src/api/v1/index_cal_and_gap_analysis.py
class IndexCalAndGapAnalysisRequest(BaseModel):
    """當前的Request模型 - 缺少驗證"""
    resume: str = Field(..., description="Resume content (HTML or plain text)")
    job_description: str = Field(..., description="JD (HTML or plain text)")
    keywords: list[str] | str = Field(..., description="Keywords list or CSV string")
    language: str = Field(default="en", description="Output language (en or zh-TW)")
    # ❌ 缺少: min_length 驗證
    # ❌ 缺少: language 白名單驗證
```

### 錯誤處理現況
- ✅ 已有統一的 `UnifiedResponse` 模型
- ✅ 已有 `create_error_response` 函數
- ⚠️ 缺少特定錯誤類型的處理邏輯

---

## 🛠️ 實作方案

### 方案 1: Pydantic 驗證器 (推薦)

#### 1.1 Request Model 強化
```python
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, status

class IndexCalAndGapAnalysisRequest(BaseModel):
    """Enhanced request model with comprehensive validation."""
    
    resume: str = Field(
        ..., 
        min_length=200,
        description="Resume content (HTML or plain text), minimum 200 characters"
    )
    job_description: str = Field(
        ..., 
        min_length=200,
        description="Job description (HTML or plain text), minimum 200 characters"
    )
    keywords: list[str] | str = Field(
        ..., 
        description="Keywords list or CSV string"
    )
    language: str = Field(
        default="en", 
        description="Output language (en or zh-TW)"
    )

    @validator('language')
    def validate_language(cls, v):
        """Validate language parameter against whitelist."""
        valid_languages = {'en', 'zh-tw', 'zh-TW'}
        if v.lower() not in {lang.lower() for lang in valid_languages}:
            raise ValueError(f"Unsupported language: {v}. Supported: en, zh-TW")
        # Normalize case
        return 'zh-TW' if v.lower() == 'zh-tw' else v

    @validator('resume')
    def validate_resume_content(cls, v):
        """Additional resume content validation."""
        if not v.strip():
            raise ValueError("Resume content cannot be empty")
        return v.strip()

    @validator('job_description')
    def validate_jd_content(cls, v):
        """Additional job description content validation."""
        if not v.strip():
            raise ValueError("Job description content cannot be empty")
        return v.strip()

    @validator('keywords')
    def validate_keywords(cls, v):
        """Ensure keywords are not empty."""
        if isinstance(v, str):
            keywords_list = [k.strip() for k in v.split(",") if k.strip()]
        else:
            keywords_list = [k.strip() for k in v if k.strip()]
        
        if not keywords_list:
            raise ValueError("Keywords cannot be empty")
        return keywords_list

    class Config:
        # Custom error messages for validation
        schema_extra = {
            "example": {
                "resume": "Senior Software Engineer with 8+ years experience in Python, FastAPI, React, and cloud technologies. Proven track record in building scalable web applications and leading development teams. Expert in microservices architecture, Docker, Kubernetes, and CI/CD pipelines.",
                "job_description": "Looking for Senior Full Stack Developer with 5+ years experience. Must have expertise in Python, FastAPI, React, Docker, Kubernetes, AWS. Experience with microservices architecture and database design required. Strong problem-solving and team collaboration skills essential.",
                "keywords": ["Python", "FastAPI", "React", "Docker", "Kubernetes", "AWS"],
                "language": "en"
            }
        }
```

#### 1.2 錯誤處理增強
```python
# src/models/response.py - 添加新的錯誤類型
class ErrorCodes:
    """Centralized error code definitions."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TEXT_TOO_SHORT = "TEXT_TOO_SHORT"
    INVALID_LANGUAGE = "INVALID_LANGUAGE"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def create_validation_error_response(field: str, message: str) -> UnifiedResponse:
    """Create validation error response."""
    return UnifiedResponse(
        success=False,
        data={},
        error=ErrorDetail(
            has_error=True,
            code=ErrorCodes.TEXT_TOO_SHORT if "200" in message else ErrorCodes.VALIDATION_ERROR,
            message=f"Validation failed for field '{field}'",
            details=message
        ),
        timestamp=datetime.utcnow().isoformat()
    )
```

#### 1.3 API端點錯誤處理
```python
# src/api/v1/index_cal_and_gap_analysis.py - 在端點函數中添加
async def calculate_index_and_analyze_gap(
    request: IndexCalAndGapAnalysisRequest,
    req: Request,
    settings=Depends(get_settings)
) -> UnifiedResponse:
    """Enhanced endpoint with comprehensive error handling."""
    start_time = time.time()

    try:
        # 現有邏輯...
        
    except ValidationError as e:
        # Handle Pydantic validation errors
        error_details = []
        for error in e.errors():
            field = error['loc'][-1] if error['loc'] else 'unknown'
            message = error['msg']
            error_details.append(f"{field}: {message}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_validation_error_response(
                field="request",
                message="; ".join(error_details)
            ).model_dump()
        )
    
    except asyncio.TimeoutError as e:
        # Handle timeout errors
        processing_time = time.time() - start_time
        logger.error(f"Request timeout after {processing_time:.2f}s: {e}")
        
        monitoring_service.track_event("APITimeoutError", {
            "processing_time_ms": round(processing_time * 1000, 2),
            "error_type": "timeout"
        })
        
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=create_error_response(
                code=ErrorCodes.TIMEOUT_ERROR,
                message="Request timed out",
                details="The request took too long to process. Please try again."
            ).model_dump()
        )
    
    except Exception as e:
        # Handle rate limit errors specifically
        if hasattr(e, 'status_code') and e.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=create_error_response(
                    code=ErrorCodes.RATE_LIMIT_ERROR,
                    message="Rate limit exceeded",
                    details="Too many requests. Please wait and try again."
                ).model_dump()
            )
        
        # Handle other errors...
        # 現有錯誤處理邏輯
```

### 方案 2: 手動驗證 (備用方案)

```python
async def validate_request_manually(request: IndexCalAndGapAnalysisRequest):
    """Manual validation as fallback approach."""
    
    # Length validation
    if len(request.resume.strip()) < 200:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                code="TEXT_TOO_SHORT",
                message="Resume too short",
                details="Resume must be at least 200 characters long"
            ).model_dump()
        )
    
    if len(request.job_description.strip()) < 200:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                code="TEXT_TOO_SHORT", 
                message="Job description too short",
                details="Job description must be at least 200 characters long"
            ).model_dump()
        )
    
    # Language validation
    valid_languages = {'en', 'zh-TW'}
    if request.language not in valid_languages:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                code="INVALID_LANGUAGE",
                message="Unsupported language",
                details=f"Language '{request.language}' not supported. Use: {', '.join(valid_languages)}"
            ).model_dump()
        )
```

---

## 📝 實作步驟

### Phase 1: Pydantic 驗證器實作 (1小時)
1. **修改 Request Model**
   - 添加 `min_length=200` 到 resume 和 job_description
   - 實作 `@validator('language')` 語言白名單檢查
   - 添加內容清理和驗證
   
2. **更新錯誤定義**
   - 在 `src/models/response.py` 添加 `ErrorCodes` 類別
   - 添加 `create_validation_error_response` 函數

### Phase 2: 錯誤處理增強 (1小時)
1. **API端點錯誤處理**
   - 添加 `ValidationError` 處理
   - 實作 `asyncio.TimeoutError` 處理  
   - 添加 429 狀態碼的 rate limit 處理

2. **監控集成**
   - 添加驗證錯誤的監控事件
   - 記錄錯誤類型和頻率

### Phase 3: 測試驗證 (30分鐘)
```bash
# 執行整合測試驗證修復
./test/scripts/run_gap_analysis_v2_tests.sh --stage integration

# 預期結果: 14/14 通過 (100%)
```

### Phase 4: 程式碼品質檢查 (30分鐘)
```bash
# Ruff 檢查 - 必須通過
ruff check src/api/v1/index_cal_and_gap_analysis.py --line-length=120
ruff check src/models/response.py --line-length=120

# 修復任何樣式問題
ruff check src/ --fix --line-length=120
```

---

## 🧪 驗證計劃

### 測試案例驗證
```bash
# 1. 短文本驗證
curl -X POST "http://localhost:8000/api/v1/index-cal-and-gap-analysis" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{
    "resume": "短履歷",
    "job_description": "長度足夠的職位描述...(200+ 字元)",
    "keywords": ["Python"]
  }'
# 預期: 400 錯誤, TEXT_TOO_SHORT

# 2. 無效語言驗證  
curl -X POST "http://localhost:8000/api/v1/index-cal-and-gap-analysis" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{
    "resume": "有效的長履歷內容...(200+ 字元)",
    "job_description": "有效的長職位描述...(200+ 字元)", 
    "keywords": ["Python"],
    "language": "fr"
  }'
# 預期: 400 錯誤, INVALID_LANGUAGE

# 3. 有效請求驗證
curl -X POST "http://localhost:8000/api/v1/index-cal-and-gap-analysis" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{
    "resume": "完整的有效履歷內容...(200+ 字元)",
    "job_description": "完整的有效職位描述...(200+ 字元)",
    "keywords": ["Python", "FastAPI"],
    "language": "en"
  }'
# 預期: 200 成功響應
```

### 自動化測試驗證
```bash
# 整合測試 - 預期 100% 通過
pytest test/integration/test_gap_analysis_v2_integration_complete.py::test_API_GAP_002_IT_jd_length_validation -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py::test_API_GAP_003_IT_resume_length_validation -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py::test_API_GAP_006_IT_language_parameter_validation -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py::test_API_GAP_010_IT_service_timeout_handling -v
pytest test/integration/test_gap_analysis_v2_integration_complete.py::test_API_GAP_011_IT_rate_limit_handling -v
```

---

## 📊 成功指標

### 技術指標
- [ ] 整合測試通過率: 64.3% → **100%** 
- [ ] 5個失敗測試全部通過 ✅
- [ ] Ruff 檢查零錯誤 ✅
- [ ] 請求驗證覆蓋率 100% ✅

### 功能指標  
- [ ] 200字元最小長度驗證 ✅
- [ ] 語言參數白名單驗證 ✅
- [ ] 超時錯誤正確處理 ✅
- [ ] 限速錯誤正確處理 ✅
- [ ] 統一錯誤響應格式 ✅

### 監控指標
- [ ] 驗證錯誤監控事件 ✅
- [ ] 錯誤分類統計 ✅
- [ ] 響應時間無顯著影響 ✅

---

## 🔄 風險評估與緩解

### 低風險項目
- **Pydantic 驗證器**: 成熟且穩定的方案
- **錯誤處理增強**: 不影響現有成功流程
- **監控集成**: 現有監控系統已完善

### 緩解策略
1. **漸進式部署**: 先在開發環境驗證
2. **回滾方案**: 保留手動驗證作為備用
3. **監控警報**: 設置驗證錯誤率警報
4. **文檔更新**: 更新API文檔說明驗證規則

---

## 📚 相關文件

### 修改文件清單
- `src/api/v1/index_cal_and_gap_analysis.py` - 主要實作
- `src/models/response.py` - 錯誤處理增強  
- `src/core/monitoring_service.py` - 監控集成 (如需要)

### 測試文件
- `test/integration/test_gap_analysis_v2_integration_complete.py` - 驗證目標
- `test/integration/test_gap_analysis_v2_api.py` - 備用測試

### 設計文件  
- `docs/issues/index-cal-and-gap-analysis-refactor/test-validation-report.md` - 問題分析
- 本文檔 - 實作指南

---

## 💬 結語

根據深入的架構分析，測試團隊的修復工作**極其成功**，將整合測試通過率從 7.1% 提升到 64.3%，提升了 827%。剩餘的 5 個測試失敗正確地指出了 API 層面缺少的輸入驗證功能。

**推薦實作方案**是使用 Pydantic 驗證器，因為：
- ✅ 聲明式驗證，代碼簡潔 
- ✅ 自動生成 OpenAPI 文檔
- ✅ 與 FastAPI 深度集成
- ✅ 提供詳細的錯誤信息
- ✅ 支持複雜驗證邏輯

實作完成後，預期整合測試將達到 **100% 通過率**，完全解決當前的API驗證問題。

---

**預估完成時間**: 2-4 小時  
**風險等級**: 低  
**優先級**: 高 (阻塞測試完成)  
**實作者**: API 開發團隊  
**驗證者**: 測試團隊