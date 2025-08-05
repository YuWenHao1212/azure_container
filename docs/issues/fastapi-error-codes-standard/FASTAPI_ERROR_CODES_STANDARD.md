# FastAPI 錯誤碼標準規範

本文件定義了專案中所有 FastAPI 端點應遵循的標準錯誤碼和錯誤處理模式。

## 📋 目錄

- [HTTP 狀態碼對照表](#http-狀態碼對照表)
- [錯誤響應格式](#錯誤響應格式)
- [業務錯誤碼](#業務錯誤碼)
- [實作指南](#實作指南)
- [測試規範](#測試規範)
- [最佳實踐](#最佳實踐)

## HTTP 狀態碼對照表

### 2xx 成功狀態碼
| 狀態碼 | 含義 | 使用場景 | 實作範例 |
|--------|------|----------|----------|
| 200 | OK | 成功處理請求 | 資料查詢、計算結果 |
| 201 | Created | 成功創建資源 | 新增用戶、創建記錄 |
| 202 | Accepted | 請求已接受，異步處理中 | 長時間運行的任務 |
| 204 | No Content | 成功處理但無內容返回 | 刪除操作、更新操作 |

### 4xx 客戶端錯誤狀態碼
| 狀態碼 | 含義 | 使用場景 | 觸發條件 | 實作重點 |
|--------|------|----------|----------|----------|
| **400** | Bad Request | 請求格式錯誤 | 無效JSON、參數類型錯誤 | 詳細說明格式要求 |
| **401** | Unauthorized | 認證失敗 | 缺少token、token過期 | 不透露用戶是否存在 |
| **403** | Forbidden | 權限不足 | 角色權限不夠、資源禁止存取 | 明確說明權限要求 |
| **404** | Not Found | 資源不存在 | 端點不存在、記錄不存在 | 避免資訊洩露 |
| **405** | Method Not Allowed | HTTP方法不支援 | 用POST存取GET端點 | 說明支援的方法 |
| **409** | Conflict | 資源衝突 | 重複創建、版本衝突 | 提供衝突解決建議 |
| **422** | Unprocessable Entity | 請求格式正確但語義錯誤 | 驗證失敗、業務規則違反 | 詳細驗證錯誤訊息 |
| **429** | Too Many Requests | 請求過於頻繁 | 超過速率限制 | 提供重試建議 |

### 5xx 伺服器錯誤狀態碼
| 狀態碼 | 含義 | 使用場景 | 觸發條件 | 實作重點 |
|--------|------|----------|----------|----------|
| **500** | Internal Server Error | 未預期的伺服器錯誤 | 程式異常、未捕獲異常 | 隱藏技術細節 |
| **502** | Bad Gateway | 上游服務錯誤 | 外部API錯誤、資料庫連線失敗 | 說明服務暫時不可用 |
| **503** | Service Unavailable | 服務暫時不可用 | 維護中、過載、依賴服務下線 | 提供重試時間建議 |
| **504** | Gateway Timeout | 上游服務超時 | 外部API超時、長時間查詢 | 建議重新嘗試 |

## 錯誤響應格式

### 統一錯誤響應結構

```json
{
  "success": false,
  "data": {},
  "error": {
    "has_error": true,
    "code": "ERROR_CODE",
    "message": "用戶友好的錯誤訊息",
    "details": "技術細節（僅開發環境）",
    "field_errors": {
      "field_name": ["具體的欄位錯誤訊息"]
    }
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "expected_minimum": 0,
    "actual_extracted": 0,
    "suggestion": ""
  },
  "timestamp": "2025-08-05T12:00:00.000000"
}
```

### 成功響應結構

```json
{
  "success": true,
  "data": {
    "實際的響應資料": "值"
  },
  "error": {
    "has_error": false,
    "code": "",
    "message": "",
    "details": ""
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "expected_minimum": 0,
    "actual_extracted": 0,
    "suggestion": ""
  },
  "timestamp": "2025-08-05T12:00:00.000000"
}
```

## 業務錯誤碼

### 驗證錯誤 (VALIDATION_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `VALIDATION_ERROR` | 422 | 通用驗證錯誤 | 欄位驗證失敗 |
| `VALIDATION_REQUIRED_FIELD` | 422 | 必填欄位缺失 | 缺少必要參數 |
| `VALIDATION_INVALID_FORMAT` | 422 | 格式不正確 | 電子郵件、電話號碼格式錯誤 |
| `VALIDATION_OUT_OF_RANGE` | 422 | 數值超出範圍 | 年齡、金額超出限制 |
| `VALIDATION_TOO_SHORT` | 422 | 內容過短 | 密碼、描述長度不足 |
| `VALIDATION_TOO_LONG` | 422 | 內容過長 | 文本超出最大長度限制 |

### 認證錯誤 (AUTH_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `AUTH_TOKEN_MISSING` | 401 | 缺少認證令牌 | 未提供 Authorization header |
| `AUTH_TOKEN_INVALID` | 401 | 無效的認證令牌 | Token 格式錯誤或損壞 |
| `AUTH_TOKEN_EXPIRED` | 401 | 認證令牌已過期 | Token 超過有效期 |
| `AUTH_CREDENTIALS_INVALID` | 401 | 認證憑證無效 | 用戶名密碼錯誤 |
| `AUTH_ACCOUNT_DISABLED` | 403 | 帳戶已停用 | 用戶帳戶被禁用 |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 403 | 權限不足 | 角色權限不夠 |

### 資源錯誤 (RESOURCE_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `RESOURCE_NOT_FOUND` | 404 | 資源不存在 | 查詢的記錄不存在 |
| `RESOURCE_ALREADY_EXISTS` | 409 | 資源已存在 | 嘗試創建重複資源 |
| `RESOURCE_CONFLICT` | 409 | 資源衝突 | 並發修改衝突 |
| `RESOURCE_LOCKED` | 423 | 資源被鎖定 | 資源正在被其他操作使用 |

### 業務邏輯錯誤 (BUSINESS_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `BUSINESS_RULE_VIOLATION` | 422 | 違反業務規則 | 不符合業務邏輯 |
| `BUSINESS_INSUFFICIENT_BALANCE` | 422 | 餘額不足 | 支付或扣款操作 |
| `BUSINESS_OPERATION_NOT_ALLOWED` | 403 | 操作不被允許 | 狀態不允許的操作 |
| `BUSINESS_QUOTA_EXCEEDED` | 429 | 超出配額限制 | 使用量超出限制 |

### 外部服務錯誤 (EXTERNAL_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `EXTERNAL_SERVICE_ERROR` | 502 | 外部服務錯誤 | 第三方API錯誤 |
| `EXTERNAL_SERVICE_UNAVAILABLE` | 503 | 外部服務不可用 | 第三方服務下線 |
| `EXTERNAL_SERVICE_TIMEOUT` | 504 | 外部服務超時 | 第三方API響應超時 |
| `EXTERNAL_RATE_LIMIT_EXCEEDED` | 429 | 外部服務速率限制 | Azure OpenAI 速率限制 |

### 系統錯誤 (SYSTEM_*)
| 錯誤碼 | HTTP狀態碼 | 描述 | 使用場景 |
|--------|------------|------|----------|
| `SYSTEM_INTERNAL_ERROR` | 500 | 系統內部錯誤 | 未預期的程式錯誤 |
| `SYSTEM_DATABASE_ERROR` | 500 | 資料庫錯誤 | 資料庫連線或查詢錯誤 |
| `SYSTEM_CONFIGURATION_ERROR` | 500 | 配置錯誤 | 系統配置問題 |
| `SYSTEM_MAINTENANCE` | 503 | 系統維護中 | 計劃性維護 |

## 實作指南

### 1. 錯誤處理中間件

```python
# src/middleware/error_handler.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from src.models.response import create_error_response
import logging

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):
    """全域異常處理器"""
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # 記錄未預期的錯誤
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    # 返回通用錯誤響應
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            code="SYSTEM_INTERNAL_ERROR",
            message="An unexpected error occurred",
            details="Please try again later"
        ).model_dump()
    )
```

### 2. 自定義異常類別

```python
# src/exceptions/custom_exceptions.py
from fastapi import HTTPException
from typing import Optional, Dict, Any

class ValidationException(HTTPException):
    """驗證異常"""
    def __init__(
        self, 
        message: str, 
        details: Optional[str] = None,
        field_errors: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=422,
            detail=create_error_response(
                code="VALIDATION_ERROR",
                message=message,
                details=details,
                field_errors=field_errors
            ).model_dump()
        )

class BusinessLogicException(HTTPException):
    """業務邏輯異常"""
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION"):
        super().__init__(
            status_code=422,
            detail=create_error_response(
                code=code,
                message=message
            ).model_dump()
        )

class ExternalServiceException(HTTPException):
    """外部服務異常"""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(
            status_code=status_code,
            detail=create_error_response(
                code="EXTERNAL_SERVICE_ERROR",
                message=message
            ).model_dump()
        )
```

### 3. 端點實作範例

```python
# src/api/v1/example.py
from fastapi import APIRouter, HTTPException, status
from src.exceptions.custom_exceptions import ValidationException, BusinessLogicException
from src.models.response import create_success_response, create_error_response

router = APIRouter()

@router.post("/users")
async def create_user(user_data: UserCreateRequest):
    try:
        # 驗證邏輯
        if len(user_data.password) < 8:
            raise ValidationException(
                message="Password must be at least 8 characters long",
                field_errors={"password": ["Must be at least 8 characters"]}
            )
        
        # 業務邏輯檢查
        if await user_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=create_error_response(
                    code="RESOURCE_ALREADY_EXISTS",
                    message="User with this email already exists"
                ).model_dump()
            )
        
        # 創建用戶
        user = await create_user_service(user_data)
        
        return create_success_response(
            data={"user_id": user.id, "email": user.email}
        )
        
    except ExternalServiceException:
        # 外部服務錯誤
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=create_error_response(
                code="EXTERNAL_SERVICE_UNAVAILABLE",
                message="User creation service is temporarily unavailable"
            ).model_dump()
        )
    
    except Exception as e:
        # 未預期錯誤
        logger.error(f"Unexpected error in create_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="SYSTEM_INTERNAL_ERROR",
                message="An unexpected error occurred"
            ).model_dump()
        )
```

## 測試規範

### 1. 成功情況測試

```python
def test_successful_operation(test_client):
    """測試成功操作"""
    response = test_client.post("/api/v1/users", json=valid_user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "user_id" in data["data"]
    assert data["error"]["has_error"] is False
```

### 2. 驗證錯誤測試

```python
def test_validation_error(test_client):
    """測試驗證錯誤"""
    invalid_data = {"email": "invalid-email", "password": "123"}
    response = test_client.post("/api/v1/users", json=invalid_data)
    
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["has_error"] is True
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "field_errors" in data["error"]
```

### 3. 認證錯誤測試

```python
def test_authentication_error(test_client):
    """測試認證錯誤"""
    response = test_client.get("/api/v1/protected-resource")
    
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTH_TOKEN_MISSING"
    assert "authentication" in data["error"]["message"].lower()
```

### 4. 外部服務錯誤測試

```python
def test_external_service_error(test_client):
    """測試外部服務錯誤"""
    with patch('src.services.external_service.call_api') as mock_call:
        mock_call.side_effect = ExternalServiceException("Service unavailable")
        
        response = test_client.post("/api/v1/process", json=valid_data)
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "EXTERNAL_SERVICE_UNAVAILABLE"
```

### 5. 測試覆蓋率要求

每個端點都應該測試以下錯誤情況：

- ✅ **400**: 無效請求格式
- ✅ **401**: 認證失敗（如適用）
- ✅ **403**: 權限不足（如適用）
- ✅ **404**: 資源不存在（如適用）
- ✅ **422**: 驗證錯誤
- ✅ **429**: 速率限制（如適用）
- ✅ **500**: 系統內部錯誤
- ✅ **502/503**: 外部服務錯誤（如適用）

## 最佳實踐

### 1. 錯誤訊息設計原則

#### ✅ 好的錯誤訊息
```json
{
  "error": {
    "code": "VALIDATION_TOO_SHORT",
    "message": "Resume content is too short. Minimum 10 characters required.",
    "field_errors": {
      "resume": ["Must be at least 10 characters long"]
    }
  }
}
```

#### ❌ 不好的錯誤訊息
```json
{
  "error": {
    "code": "ERROR",
    "message": "Invalid input",
    "details": "ValueError: len(resume) < 10"
  }
}
```

### 2. 安全考量

- **不要洩露敏感資訊**：避免在錯誤訊息中包含系統內部結構、SQL查詢、檔案路徑等
- **統一認證錯誤**：登入失敗時不要區分「用戶不存在」和「密碼錯誤」
- **記錄詳細日誌**：在後端記錄詳細錯誤資訊，但不傳給客戶端
- **限制錯誤訊息長度**：避免過長的錯誤訊息導致資訊洩露

### 3. 效能考量

- **快速失敗**：儘早驗證並返回錯誤，避免不必要的處理
- **異步錯誤處理**：對於可能耗時的錯誤處理，考慮異步處理
- **錯誤快取**：對於重複的驗證錯誤，考慮快取驗證結果

### 4. 監控和警報

```python
# 錯誤監控範例
@router.post("/api/v1/critical-operation")
async def critical_operation():
    try:
        result = await perform_operation()
        return create_success_response(data=result)
    except Exception as e:
        # 記錄錯誤並發送警報
        logger.error(f"Critical operation failed: {e}", extra={
            "operation": "critical_operation",
            "error_type": type(e).__name__,
            "user_id": get_current_user_id()
        })
        
        # 對於關鍵操作，發送即時警報
        if isinstance(e, CriticalSystemError):
            await send_alert(f"Critical system error: {e}")
        
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                code="SYSTEM_CRITICAL_ERROR",
                message="Critical operation failed"
            ).model_dump()
        )
```

## 實作檢查清單

### API 開發者檢查清單

- [ ] 每個端點都有明確的成功和失敗路徑
- [ ] 所有可能的錯誤情況都有對應的錯誤碼
- [ ] 錯誤訊息對用戶友好且具有指導性
- [ ] 敏感資訊不會在錯誤訊息中洩露
- [ ] 所有異常都被適當捕獲和處理
- [ ] 錯誤響應格式符合統一標準
- [ ] 關鍵錯誤有適當的監控和警報

### 測試工程師檢查清單

- [ ] 每個錯誤狀態碼都有對應的測試案例
- [ ] 測試涵蓋邊界條件和異常情況
- [ ] 驗證錯誤響應格式的一致性
- [ ] 測試外部服務失敗的處理
- [ ] 驗證錯誤訊息的準確性和有用性
- [ ] 測試併發情況下的錯誤處理

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-05  
**適用範圍**: Azure Container API 專案  
**維護者**: Azure Container API Team

**更新記錄**:
- 2025-08-05: 初始版本，建立完整錯誤碼標準