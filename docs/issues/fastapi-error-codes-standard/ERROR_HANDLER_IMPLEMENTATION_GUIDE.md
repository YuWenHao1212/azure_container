# 統一錯誤處理實作指南

**版本**: 1.0.0  
**建立日期**: 2025-08-12  
**作者**: Azure Container API Team  
**相關計畫**: [ERROR_HANDLER_OPTIMIZATION_PLAN.md](./ERROR_HANDLER_OPTIMIZATION_PLAN.md)

## 📚 目錄

1. [核心組件實作](#核心組件實作)
2. [錯誤碼定義](#錯誤碼定義)
3. [裝飾器使用](#裝飾器使用)
4. [端點重構指南](#端點重構指南)
5. [測試策略](#測試策略)
6. [遷移路徑](#遷移路徑)

## 🏗️ 核心組件實作

### 1. Error Handler Factory

#### 檔案位置
`src/services/error_handler_factory.py`

#### 實作範例
```python
"""統一錯誤處理工廠模組"""
import logging
from typing import Any, Dict, Optional, Type
from datetime import datetime

from fastapi import HTTPException, status
from src.models.response import UnifiedResponse, ErrorDetail, WarningInfo
from src.services.monitoring import get_monitoring_service
from src.constants.error_codes import ErrorCodes, ERROR_CODE_MAPPING
from src.services.exceptions import (
    ServiceError,
    ValidationError,
    AuthenticationError,
    ExternalServiceError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class ErrorHandlerFactory:
    """
    統一的錯誤處理工廠
    
    負責：
    1. 異常分類和映射
    2. 錯誤響應生成
    3. 監控和日誌記錄
    4. 錯誤上下文管理
    """
    
    def __init__(self):
        """初始化錯誤處理工廠"""
        self.monitoring_service = get_monitoring_service()
        self._init_error_mappings()
    
    def _init_error_mappings(self):
        """初始化異常到錯誤碼的映射"""
        self.exception_mappings = {
            # Validation errors -> 422
            ValidationError: {
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_code": ErrorCodes.VALIDATION_ERROR,
            },
            ValueError: {
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "error_code": ErrorCodes.VALIDATION_ERROR,
            },
            
            # Authentication errors -> 401/403
            AuthenticationError: {
                "status_code": status.HTTP_401_UNAUTHORIZED,
                "error_code": ErrorCodes.AUTH_TOKEN_INVALID,
            },
            
            # Rate limit errors -> 429
            RateLimitError: {
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "error_code": ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED,
            },
            
            # External service errors -> 502/503
            ExternalServiceError: {
                "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                "error_code": ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE,
            },
            
            # Timeout errors -> 504
            TimeoutError: {
                "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
                "error_code": ErrorCodes.EXTERNAL_SERVICE_TIMEOUT,
            },
            
            # Default -> 500
            Exception: {
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error_code": ErrorCodes.SYSTEM_INTERNAL_ERROR,
            },
        }
    
    def handle_exception(
        self,
        exc: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        處理異常並返回統一格式的錯誤響應
        
        Args:
            exc: 捕獲的異常
            context: 錯誤上下文資訊
            
        Returns:
            統一格式的錯誤響應字典
        """
        # 1. 分類異常
        error_info = self._classify_exception(exc)
        
        # 2. 生成錯誤訊息
        error_message = self._get_error_message(exc, error_info["error_code"])
        
        # 3. 記錄和監控
        self._log_and_monitor(exc, error_info, context)
        
        # 4. 生成響應
        return self._create_error_response(
            error_code=error_info["error_code"],
            message=error_message,
            details=self._get_error_details(exc, context),
            field_errors=self._extract_field_errors(exc)
        )
    
    def _classify_exception(self, exc: Exception) -> Dict[str, Any]:
        """分類異常並返回對應的錯誤資訊"""
        # 從最具體到最通用的順序檢查
        for exc_type, error_info in self.exception_mappings.items():
            if isinstance(exc, exc_type):
                return error_info
        
        # 預設錯誤
        return self.exception_mappings[Exception]
    
    def _get_error_message(self, exc: Exception, error_code: str) -> str:
        """獲取用戶友好的錯誤訊息"""
        # 如果異常有自定義訊息，使用它
        if hasattr(exc, 'message'):
            return exc.message
        
        # 否則使用錯誤碼對應的標準訊息
        return ERROR_CODE_MAPPING.get(
            error_code,
            {}).get('message', str(exc)
        )
    
    def _get_error_details(
        self,
        exc: Exception,
        context: Dict[str, Any]
    ) -> str:
        """獲取錯誤詳情（僅開發環境）"""
        if context.get('debug', False):
            return f"{type(exc).__name__}: {str(exc)}"
        return ""
    
    def _extract_field_errors(self, exc: Exception) -> Dict[str, list]:
        """提取欄位級別的錯誤"""
        if hasattr(exc, 'field_errors'):
            return exc.field_errors
        return {}
    
    def _log_and_monitor(
        self,
        exc: Exception,
        error_info: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """記錄錯誤日誌並發送監控事件"""
        # 記錄日誌
        logger.error(
            f"API Error: {error_info['error_code']} - {exc}",
            extra={
                "error_code": error_info["error_code"],
                "status_code": error_info["status_code"],
                "api_name": context.get("api_name"),
                "endpoint": context.get("endpoint"),
            },
            exc_info=True
        )
        
        # 發送監控事件
        if self.monitoring_service:
            self.monitoring_service.track_error(
                error_type=type(exc).__name__,
                error_message=str(exc),
                endpoint=context.get("endpoint"),
                custom_properties={
                    "error_code": error_info["error_code"],
                    "status_code": error_info["status_code"],
                    "api_name": context.get("api_name"),
                }
            )
    
    def _create_error_response(
        self,
        error_code: str,
        message: str,
        details: str = "",
        field_errors: Dict[str, list] = None
    ) -> Dict[str, Any]:
        """創建統一格式的錯誤響應"""
        return {
            "success": False,
            "data": {},
            "error": {
                "has_error": True,
                "code": error_code,
                "message": message,
                "details": details,
                "field_errors": field_errors or {}
            },
            "warning": {
                "has_warning": False,
                "message": "",
                "expected_minimum": 0,
                "actual_extracted": 0,
                "suggestion": ""
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# 單例實例
_error_handler_factory = None


def get_error_handler_factory() -> ErrorHandlerFactory:
    """獲取錯誤處理工廠單例"""
    global _error_handler_factory
    if _error_handler_factory is None:
        _error_handler_factory = ErrorHandlerFactory()
    return _error_handler_factory
```

### 2. 錯誤處理裝飾器

#### 檔案位置
`src/decorators/error_handler.py`

#### 實作範例
```python
"""API 錯誤處理裝飾器"""
import functools
import time
from typing import Callable, Optional

from fastapi import HTTPException, Request
from src.services.error_handler_factory import get_error_handler_factory
from src.core.config import get_settings

settings = get_settings()


def handle_api_errors(
    api_name: str,
    enable_monitoring: bool = True,
    enable_timing: bool = True
):
    """
    統一的 API 錯誤處理裝飾器
    
    Args:
        api_name: API 名稱，用於監控和日誌
        enable_monitoring: 是否啟用監控
        enable_timing: 是否追蹤執行時間
        
    Example:
        @handle_api_errors(api_name="keyword_extraction")
        async def extract_keywords(request: Request):
            # 業務邏輯
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time() if enable_timing else None
            error_handler = get_error_handler_factory()
            
            # 提取請求資訊作為上下文
            context = {
                "api_name": api_name,
                "debug": settings.debug,
                "enable_monitoring": enable_monitoring,
            }
            
            # 尋找 Request 對象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                context.update({
                    "endpoint": f"{request.method} {request.url.path}",
                    "client_host": request.client.host if request.client else None,
                })
            
            try:
                # 執行原始函數
                result = await func(*args, **kwargs)
                
                # 記錄成功的執行時間
                if enable_timing and enable_monitoring:
                    execution_time = (time.time() - start_time) * 1000
                    error_handler.monitoring_service.track_metric(
                        f"{api_name}_success_time",
                        execution_time,
                        {"endpoint": context.get("endpoint")}
                    )
                
                return result
                
            except HTTPException:
                # HTTPException 直接拋出（已經是正確格式）
                raise
                
            except Exception as exc:
                # 處理所有其他異常
                error_response = error_handler.handle_exception(exc, context)
                
                # 獲取狀態碼
                error_info = error_handler._classify_exception(exc)
                status_code = error_info["status_code"]
                
                # 拋出 HTTPException
                raise HTTPException(
                    status_code=status_code,
                    detail=error_response
                )
        
        return wrapper
    return decorator
```

## 📋 錯誤碼定義

### 檔案位置
`src/constants/error_codes.py`

### 實作範例
```python
"""標準錯誤碼定義"""
from enum import Enum


class ErrorCodes:
    """錯誤碼常量"""
    
    # Validation Errors (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VALIDATION_REQUIRED_FIELD = "VALIDATION_REQUIRED_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_TOO_SHORT = "VALIDATION_TOO_SHORT"
    VALIDATION_TOO_LONG = "VALIDATION_TOO_LONG"
    VALIDATION_OUT_OF_RANGE = "VALIDATION_OUT_OF_RANGE"
    
    # Authentication Errors (401/403)
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_CREDENTIALS_INVALID = "AUTH_CREDENTIALS_INVALID"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    
    # Resource Errors (404/409)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # Business Logic Errors (422)
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    BUSINESS_OPERATION_NOT_ALLOWED = "BUSINESS_OPERATION_NOT_ALLOWED"
    
    # External Service Errors (502/503/504)
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_RATE_LIMIT_EXCEEDED = "EXTERNAL_RATE_LIMIT_EXCEEDED"
    
    # System Errors (500)
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"
    SYSTEM_DATABASE_ERROR = "SYSTEM_DATABASE_ERROR"
    SYSTEM_CONFIGURATION_ERROR = "SYSTEM_CONFIGURATION_ERROR"


# 錯誤碼到訊息的映射
ERROR_CODE_MAPPING = {
    ErrorCodes.VALIDATION_ERROR: {
        "message": "輸入資料驗證失敗",
        "message_en": "Input validation failed"
    },
    ErrorCodes.VALIDATION_REQUIRED_FIELD: {
        "message": "缺少必要欄位",
        "message_en": "Required field missing"
    },
    ErrorCodes.VALIDATION_TOO_SHORT: {
        "message": "內容長度不足",
        "message_en": "Content too short"
    },
    ErrorCodes.VALIDATION_TOO_LONG: {
        "message": "內容超過長度限制",
        "message_en": "Content exceeds maximum length"
    },
    ErrorCodes.AUTH_TOKEN_MISSING: {
        "message": "缺少認證令牌",
        "message_en": "Authentication token missing"
    },
    ErrorCodes.AUTH_TOKEN_INVALID: {
        "message": "無效的認證令牌",
        "message_en": "Invalid authentication token"
    },
    ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE: {
        "message": "外部服務暫時無法使用",
        "message_en": "External service temporarily unavailable"
    },
    ErrorCodes.EXTERNAL_SERVICE_TIMEOUT: {
        "message": "外部服務回應超時",
        "message_en": "External service timeout"
    },
    ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED: {
        "message": "超過 API 速率限制，請稍後再試",
        "message_en": "API rate limit exceeded, please try again later"
    },
    ErrorCodes.SYSTEM_INTERNAL_ERROR: {
        "message": "系統發生未預期錯誤",
        "message_en": "An unexpected error occurred"
    },
}
```

## 🔄 端點重構指南

### 重構前後對比

#### 原始代碼（冗長的錯誤處理）
```python
@router.post("/extract-jd-keywords")
async def extract_jd_keywords(request: KeywordExtractionRequest):
    try:
        # 業務邏輯
        result = await service.process(request)
        return create_success_response(data=result)
        
    except UnsupportedLanguageError as e:
        logger.warning(f"Unsupported language: {e}")
        error_response = create_error_response(
            code="UNSUPPORTED_LANGUAGE",
            message=f"不支援的語言: {e.detected_language}",
            details=f"Detected: {e.detected_language}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.dict()
        )
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        error_response = create_error_response(
            code="VALIDATION_ERROR",
            message="輸入參數驗證失敗",
            details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.dict()
        )
        
    except RateLimitError as e:
        # ... 更多錯誤處理
        
    except Exception as e:
        # ... 通用錯誤處理
```

#### 重構後（簡潔的錯誤處理）
```python
from src.decorators.error_handler import handle_api_errors

@router.post("/extract-jd-keywords")
@handle_api_errors(api_name="keyword_extraction")
async def extract_jd_keywords(request: KeywordExtractionRequest):
    # 只需專注於業務邏輯
    result = await service.process(request)
    return create_success_response(data=result)
```

### 重構步驟

1. **添加裝飾器**
   ```python
   @handle_api_errors(api_name="your_api_name")
   ```

2. **移除 try-except 區塊**
   - 保留業務邏輯
   - 移除所有錯誤處理代碼

3. **確保異常類型正確**
   - 使用標準異常類別
   - 添加必要的錯誤資訊

4. **測試驗證**
   - 執行單元測試
   - 驗證錯誤響應格式

## 🧪 測試策略

### 單元測試範例
```python
import pytest
from unittest.mock import Mock, patch
from src.services.error_handler_factory import ErrorHandlerFactory


class TestErrorHandlerFactory:
    """測試錯誤處理工廠"""
    
    def test_handle_validation_error(self):
        """測試驗證錯誤處理"""
        factory = ErrorHandlerFactory()
        exc = ValueError("Invalid input")
        context = {"api_name": "test", "debug": False}
        
        response = factory.handle_exception(exc, context)
        
        assert response["success"] is False
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["has_error"] is True
    
    def test_handle_rate_limit_error(self):
        """測試速率限制錯誤處理"""
        factory = ErrorHandlerFactory()
        exc = RateLimitError("Rate limit exceeded")
        context = {"api_name": "test", "debug": False}
        
        response = factory.handle_exception(exc, context)
        
        assert response["error"]["code"] == "EXTERNAL_RATE_LIMIT_EXCEEDED"
```

### 整合測試範例
```python
import pytest
from fastapi.testclient import TestClient


def test_api_error_handling(client: TestClient):
    """測試 API 錯誤處理"""
    # 發送無效請求
    response = client.post(
        "/api/v1/extract-jd-keywords",
        json={"job_description": ""}  # 太短
    )
    
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_TOO_SHORT"
```

## 🔄 遷移路徑

### Phase 1: 試點遷移（Day 1）
1. 選擇簡單端點（如 `/api/v1/prompts`）
2. 套用新的錯誤處理
3. 測試並驗證
4. 收集反饋

### Phase 2: 批量遷移（Day 2-3）
1. 遷移中等複雜度端點
2. 處理特殊情況
3. 更新測試案例

### Phase 3: 完成遷移（Day 4）
1. 遷移複雜端點
2. 處理 `resume_tailoring` 特殊格式
3. 全面測試

### 向後兼容性策略
```python
# 使用 feature flag 控制
if settings.USE_NEW_ERROR_HANDLER:
    @handle_api_errors(api_name="test")
    async def endpoint():
        pass
else:
    # 保留原始錯誤處理
    async def endpoint():
        try:
            # ...
        except:
            # ...
```

## 📝 最佳實踐

### DO ✅
- 使用標準異常類別
- 提供有意義的錯誤訊息
- 包含適當的錯誤上下文
- 記錄所有錯誤
- 測試錯誤場景

### DON'T ❌
- 不要暴露敏感資訊
- 不要忽略錯誤
- 不要使用通用錯誤訊息
- 不要混用新舊錯誤處理
- 不要跳過測試

## 🔗 相關資源

- [錯誤碼標準規範](./FASTAPI_ERROR_CODES_STANDARD.md)
- [優化計畫](./ERROR_HANDLER_OPTIMIZATION_PLAN.md)
- [測試計畫](./TEST_PLAN.md)
- [LLM Factory 參考實作](../../src/services/llm_factory.py)

---

**注意**: 本指南將隨實作進度持續更新。如有問題請聯繫開發團隊。