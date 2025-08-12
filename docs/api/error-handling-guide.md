# API 錯誤處理開發者指南

## 概述

本指南說明如何在 Azure Container API 專案中正確使用統一錯誤處理系統。該系統基於裝飾器模式，提供自動錯誤分類、監控整合和一致的回應格式。

## 🎯 核心原則

### 1. 統一錯誤處理
- 所有 API 端點必須使用 `@handle_api_errors` 裝飾器
- 錯誤處理邏輯集中在 `ErrorHandlerFactory` 中
- 回應格式符合 `UnifiedResponse` 標準

### 2. 自動錯誤分類
- 系統自動將異常映射到適當的 HTTP 狀態碼
- 統一的錯誤碼用於前端處理
- 輕量級監控自動記錄錯誤事件

### 3. 開發效率優先
- 開發者只需專注業務邏輯
- 錯誤處理完全自動化
- 新端點錯誤處理時間從 2 小時減少到 10 分鐘

## 📚 錯誤碼參考

### 驗證錯誤 (422)
| 錯誤碼 | 描述 | 觸發條件 |
|--------|------|----------|
| `VALIDATION_ERROR` | 通用驗證錯誤 | 輸入資料格式不正確 |
| `TEXT_TOO_SHORT` | 文字長度不足 | 履歷或職缺描述少於 200 字元 |
| `INVALID_LANGUAGE` | 不支援的語言 | 語言代碼不在支援列表中 |

### 認證錯誤 (401/403)
| 錯誤碼 | 描述 | 觸發條件 |
|--------|------|----------|
| `AUTH_TOKEN_INVALID` | 認證令牌無效 | API Key 錯誤或過期 |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 權限不足 | 缺少執行操作的權限 |

### 外部服務錯誤 (429/502/503/504)
| 錯誤碼 | 描述 | 觸發條件 |
|--------|------|----------|
| `EXTERNAL_RATE_LIMIT_EXCEEDED` | 速率限制超出 | Azure OpenAI API 限制 |
| `EXTERNAL_SERVICE_UNAVAILABLE` | 外部服務不可用 | Azure OpenAI 服務中斷 |
| `EXTERNAL_SERVICE_TIMEOUT` | 外部服務超時 | 請求超過 30 秒限制 |

### 系統錯誤 (500)
| 錯誤碼 | 描述 | 觸發條件 |
|--------|------|----------|
| `SYSTEM_INTERNAL_ERROR` | 系統內部錯誤 | 未預期的異常 |
| `DATABASE_ERROR` | 資料庫錯誤 | 課程搜尋資料庫連線問題 |

## 🛠️ 實作指南

### 標準端點實作

```python
from fastapi import APIRouter, Depends
from src.decorators.error_handler import handle_api_errors
from src.models.response import UnifiedResponse, create_success_response

router = APIRouter()

@handle_api_errors(api_name="your_service_name")
@router.post("/your-endpoint", response_model=UnifiedResponse)
async def your_endpoint(
    request: YourRequestModel,
    settings: Settings = Depends(get_settings)
) -> UnifiedResponse:
    """
    您的端點功能說明。
    
    Args:
        request: 請求模型
        settings: 應用程式設定
        
    Returns:
        UnifiedResponse: 統一格式回應
    """
    # 1. 業務邏輯實作
    result = await your_service.process(request)
    
    # 2. 回傳成功回應
    return create_success_response(result.model_dump())
```

### 特殊回應格式 (如 TailoringResponse)

```python
from src.decorators.error_handler import handle_tailor_resume_errors

@handle_tailor_resume_errors(api_name="special_endpoint")
@router.post("/special-endpoint", response_model=SpecialResponse)
async def special_endpoint(request: RequestModel) -> SpecialResponse:
    """處理需要特殊回應格式的端點"""
    result = await service.process(request)
    
    return SpecialResponse(
        success=True,
        data=result,
        error=ErrorInfo(),
        warning=WarningInfo()
    )
```

## 🚫 反模式 - 避免這些做法

### ❌ 手動錯誤處理
```python
# 不要這樣做
@router.post("/endpoint")
async def bad_endpoint(request: RequestModel):
    try:
        result = await service.process(request)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error")
```

### ❌ 不一致的回應格式
```python
# 不要這樣做
@router.post("/endpoint")
async def bad_endpoint(request: RequestModel):
    try:
        result = await service.process(request)
        return {"status": "ok", "result": result}  # 格式不一致
    except Exception:
        return {"status": "error", "message": "Failed"}  # 格式不一致
```

### ❌ 直接使用 OpenAI 客戶端
```python
# 不要這樣做
from openai import AsyncAzureOpenAI

async def bad_endpoint():
    client = AsyncAzureOpenAI(...)  # 應該使用 LLM Factory
    response = await client.chat.completions.create(...)
```

## ✅ 最佳實踐

### 1. 使用 LLM Factory
```python
from src.services.llm_factory import get_llm_client

# 正確做法
client = get_llm_client(api_name="your_service")
response = await client.chat.completions.create(...)
```

### 2. 適當的異常拋出
```python
from src.services.exceptions import ValidationError, RateLimitError

# 業務邏輯中拋出適當的異常
if len(text) < 200:
    raise ValidationError("Text must be at least 200 characters")

if rate_limited:
    raise RateLimitError("API rate limit exceeded")
```

### 3. 監控事件記錄
```python
from src.core.monitoring_logger import get_business_logger

logger = get_business_logger()

# 記錄重要業務事件
logger.info(f"Processing completed: {len(results)} items processed")
```

## 🔍 監控與除錯

### 錯誤追蹤儀表板
訪問 `/api/v1/monitoring/error-dashboard` 查看：
- 錯誤統計和趨勢
- 效能指標
- 最近錯誤範例

### 開發環境除錯
```bash
# 檢查錯誤詳細資訊
curl -H "X-API-Key: your-key" \
  http://localhost:8000/api/v1/monitoring/error-stats/VALIDATION_ERROR

# 重置監控統計 (僅開發環境)
curl -X POST -H "X-API-Key: your-key" \
  http://localhost:8000/api/v1/monitoring/reset-stats
```

### 日誌查看
```bash
# 查看業務事件日誌
tail -f logs/business_events.log

# 查看應用程式日誌
tail -f logs/app.log
```

## 📋 檢查清單

### 新端點開發
- [ ] 使用 `@handle_api_errors` 裝飾器
- [ ] 使用 `UnifiedResponse` 格式
- [ ] 通過 LLM Factory 調用 AI 服務
- [ ] 拋出適當的自定義異常
- [ ] 記錄重要業務事件
- [ ] 通過 Ruff 程式碼品質檢查

### 部署前檢查
- [ ] 所有端點使用統一錯誤處理
- [ ] 錯誤回應格式一致
- [ ] 監控整合正常運作
- [ ] 無手動錯誤處理殘留
- [ ] 測試覆蓋關鍵錯誤場景

## 📞 支援

### 開發問題
- 查看 `src/services/error_handler_factory.py` 了解錯誤處理邏輯
- 參考 `src/api/v1/keyword_extraction.py` 作為實作範例
- 檢查 `src/constants/error_codes.py` 獲取完整錯誤碼列表

### 效能問題
- 使用 `/api/v1/monitoring/performance-summary` 分析效能
- 檢查輕量級監控統計
- 查看 `src/middleware/lightweight_monitoring.py` 了解監控機制

### 生產問題
- 檢查 Azure Container Apps 日誌
- 使用錯誤追蹤儀表板分析趨勢
- 聯繫系統管理員進行深度分析

---

**文檔版本**: 1.0.0  
**最後更新**: 2025-08-12  
**維護者**: Claude Code + Development Team