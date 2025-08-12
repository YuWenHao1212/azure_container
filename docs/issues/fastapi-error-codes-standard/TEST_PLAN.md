# 統一錯誤處理測試計畫

**版本**: 1.0.0  
**建立日期**: 2025-08-12  
**作者**: Azure Container API Team  
**相關文件**: [優化計畫](./ERROR_HANDLER_OPTIMIZATION_PLAN.md) | [實作指南](./ERROR_HANDLER_IMPLEMENTATION_GUIDE.md)

## 📋 測試範圍

### 測試目標
1. **功能正確性** - 確保錯誤處理邏輯正確
2. **向後兼容性** - 確保不影響現有 API 契約
3. **性能影響** - 驗證無顯著性能下降
4. **錯誤覆蓋** - 所有錯誤類型都被正確處理
5. **監控整合** - 確認錯誤被正確記錄和追蹤

### 測試層級
- **單元測試** - 測試各個組件
- **整合測試** - 測試端到端流程
- **性能測試** - 測試響應時間影響
- **回歸測試** - 確保現有功能正常

## 🧪 測試案例清單

### 1. Error Handler Factory 單元測試

#### 檔案: `test/unit/services/test_error_handler_factory.py`

```python
"""Error Handler Factory 單元測試"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.services.error_handler_factory import (
    ErrorHandlerFactory,
    get_error_handler_factory
)
from src.services.exceptions import (
    ValidationError,
    RateLimitError,
    ExternalServiceError,
    AuthenticationError
)
from src.constants.error_codes import ErrorCodes


class TestErrorHandlerFactory:
    """測試 Error Handler Factory"""
    
    @pytest.fixture
    def factory(self):
        """創建測試用的 factory"""
        return ErrorHandlerFactory()
    
    @pytest.fixture
    def context(self):
        """創建測試上下文"""
        return {
            "api_name": "test_api",
            "endpoint": "POST /test",
            "debug": False
        }
    
    def test_singleton_pattern(self):
        """測試單例模式"""
        factory1 = get_error_handler_factory()
        factory2 = get_error_handler_factory()
        assert factory1 is factory2
    
    def test_handle_validation_error(self, factory, context):
        """測試驗證錯誤處理"""
        exc = ValidationError("Invalid input: field is required")
        response = factory.handle_exception(exc, context)
        
        assert response["success"] is False
        assert response["error"]["has_error"] is True
        assert response["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert "Invalid input" in response["error"]["message"]
        assert response["error"]["details"] == ""  # debug=False
    
    def test_handle_rate_limit_error(self, factory, context):
        """測試速率限制錯誤處理"""
        exc = RateLimitError("Rate limit exceeded: 429")
        response = factory.handle_exception(exc, context)
        
        assert response["error"]["code"] == ErrorCodes.EXTERNAL_RATE_LIMIT_EXCEEDED
        assert "速率限制" in response["error"]["message"] or \
               "rate limit" in response["error"]["message"].lower()
    
    def test_handle_authentication_error(self, factory, context):
        """測試認證錯誤處理"""
        exc = AuthenticationError("Invalid token")
        response = factory.handle_exception(exc, context)
        
        assert response["error"]["code"] == ErrorCodes.AUTH_TOKEN_INVALID
        assert response["success"] is False
    
    def test_handle_timeout_error(self, factory, context):
        """測試超時錯誤處理"""
        exc = TimeoutError("Request timeout after 30s")
        response = factory.handle_exception(exc, context)
        
        assert response["error"]["code"] == ErrorCodes.EXTERNAL_SERVICE_TIMEOUT
    
    def test_handle_generic_exception(self, factory, context):
        """測試通用異常處理"""
        exc = Exception("Unexpected error")
        response = factory.handle_exception(exc, context)
        
        assert response["error"]["code"] == ErrorCodes.SYSTEM_INTERNAL_ERROR
        assert response["error"]["details"] == ""  # 不暴露詳情
    
    def test_debug_mode_includes_details(self, factory):
        """測試 debug 模式包含詳細資訊"""
        context = {"api_name": "test", "debug": True}
        exc = ValueError("Detailed error message")
        
        response = factory.handle_exception(exc, context)
        assert "ValueError" in response["error"]["details"]
        assert "Detailed error message" in response["error"]["details"]
    
    def test_field_errors_extraction(self, factory, context):
        """測試欄位錯誤提取"""
        exc = ValidationError("Validation failed")
        exc.field_errors = {
            "email": ["Invalid email format"],
            "password": ["Too short", "Missing special character"]
        }
        
        response = factory.handle_exception(exc, context)
        assert response["error"]["field_errors"] == exc.field_errors
    
    @patch('src.services.error_handler_factory.logger')
    def test_error_logging(self, mock_logger, factory, context):
        """測試錯誤日誌記錄"""
        exc = ValueError("Test error")
        factory.handle_exception(exc, context)
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "VALIDATION_ERROR" in call_args[0][0]
    
    @patch('src.services.error_handler_factory.get_monitoring_service')
    def test_monitoring_integration(self, mock_monitoring, factory, context):
        """測試監控整合"""
        mock_service = Mock()
        mock_monitoring.return_value = mock_service
        
        factory = ErrorHandlerFactory()
        exc = RateLimitError("Rate limit")
        factory.handle_exception(exc, context)
        
        mock_service.track_error.assert_called_once()
```

### 2. 錯誤處理裝飾器測試

#### 檔案: `test/unit/decorators/test_error_handler.py`

```python
"""錯誤處理裝飾器測試"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi import HTTPException, Request

from src.decorators.error_handler import handle_api_errors


class TestErrorHandlerDecorator:
    """測試錯誤處理裝飾器"""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """測試成功執行不影響結果"""
        @handle_api_errors(api_name="test")
        async def test_func():
            return {"success": True}
        
        result = await test_func()
        assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_handles_exceptions(self):
        """測試異常處理"""
        @handle_api_errors(api_name="test")
        async def test_func():
            raise ValueError("Test error")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"]["code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_preserves_http_exceptions(self):
        """測試保留 HTTPException"""
        @handle_api_errors(api_name="test")
        async def test_func():
            raise HTTPException(status_code=404, detail="Not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_func()
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"
    
    @pytest.mark.asyncio
    async def test_timing_metrics(self):
        """測試執行時間追蹤"""
        with patch('src.decorators.error_handler.get_error_handler_factory') as mock:
            mock_factory = Mock()
            mock_service = Mock()
            mock_factory.monitoring_service = mock_service
            mock.return_value = mock_factory
            
            @handle_api_errors(api_name="test", enable_timing=True)
            async def test_func():
                await asyncio.sleep(0.1)
                return "success"
            
            await test_func()
            mock_service.track_metric.assert_called_once()
            
            call_args = mock_service.track_metric.call_args
            assert call_args[0][0] == "test_success_time"
            assert call_args[0][1] >= 100  # 至少 100ms
```

### 3. 端點整合測試

#### 檔案: `test/integration/test_unified_error_handling.py`

```python
"""統一錯誤處理整合測試"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from src.main import app


class TestUnifiedErrorHandling:
    """測試統一錯誤處理整合"""
    
    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        return TestClient(app)
    
    def test_validation_error_response_format(self, client):
        """測試驗證錯誤響應格式"""
        response = client.post(
            "/api/v1/extract-jd-keywords",
            json={"job_description": ""}  # 太短
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # 驗證統一格式
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["has_error"] is True
        assert data["error"]["code"] == "VALIDATION_TOO_SHORT"
        assert "timestamp" in data
    
    @patch('src.services.llm_factory.get_llm_client')
    def test_external_service_error(self, mock_llm, client):
        """測試外部服務錯誤"""
        mock_llm.side_effect = ExternalServiceError("Azure OpenAI unavailable")
        
        response = client.post(
            "/api/v1/extract-jd-keywords",
            json={"job_description": "Valid job description " * 20}
        )
        
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "EXTERNAL_SERVICE_UNAVAILABLE"
    
    def test_rate_limit_error(self, client):
        """測試速率限制錯誤"""
        # 模擬速率限制
        with patch('src.services.llm_factory.get_llm_client') as mock:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = RateLimitError("429")
            mock.return_value = mock_client
            
            response = client.post(
                "/api/v1/index-calculation",
                json={
                    "resume": "Test resume",
                    "job_description": "Test JD",
                    "keywords": ["Python", "FastAPI"]
                }
            )
            
            assert response.status_code == 429
            data = response.json()
            assert data["error"]["code"] == "EXTERNAL_RATE_LIMIT_EXCEEDED"
    
    def test_timeout_error(self, client):
        """測試超時錯誤"""
        with patch('src.services.keyword_extraction_v2.KeywordExtractionServiceV2.process') as mock:
            mock.side_effect = TimeoutError("Timeout after 30s")
            
            response = client.post(
                "/api/v1/extract-jd-keywords",
                json={"job_description": "Test JD " * 50}
            )
            
            assert response.status_code == 504
            data = response.json()
            assert data["error"]["code"] == "EXTERNAL_SERVICE_TIMEOUT"
    
    def test_backward_compatibility(self, client):
        """測試向後兼容性"""
        # 測試現有客戶端仍能正常工作
        response = client.get("/api/v1/prompts/versions")
        
        if response.status_code != 200:
            # 錯誤響應應該保持相同格式
            data = response.json()
            assert "success" in data
            assert "error" in data
            assert "timestamp" in data
```

### 4. 性能測試

#### 檔案: `test/performance/test_error_handling_performance.py`

```python
"""錯誤處理性能測試"""
import pytest
import time
import asyncio
from statistics import mean, stdev

from src.services.error_handler_factory import ErrorHandlerFactory


class TestErrorHandlingPerformance:
    """測試錯誤處理性能影響"""
    
    @pytest.mark.asyncio
    async def test_error_handling_overhead(self):
        """測試錯誤處理開銷"""
        factory = ErrorHandlerFactory()
        context = {"api_name": "test", "debug": False}
        
        # 測試 100 次錯誤處理
        times = []
        for _ in range(100):
            exc = ValueError("Test error")
            start = time.perf_counter()
            factory.handle_exception(exc, context)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # 轉換為毫秒
        
        avg_time = mean(times)
        std_time = stdev(times)
        
        # 性能要求
        assert avg_time < 1.0  # 平均小於 1ms
        assert std_time < 0.5  # 標準差小於 0.5ms
        
        print(f"Error handling overhead: {avg_time:.3f}ms ± {std_time:.3f}ms")
    
    @pytest.mark.asyncio
    async def test_decorator_overhead(self):
        """測試裝飾器開銷"""
        # 無裝飾器
        async def plain_func():
            return {"result": "success"}
        
        # 有裝飾器
        @handle_api_errors(api_name="test", enable_monitoring=False)
        async def decorated_func():
            return {"result": "success"}
        
        # 測量無裝飾器執行時間
        plain_times = []
        for _ in range(100):
            start = time.perf_counter()
            await plain_func()
            plain_times.append((time.perf_counter() - start) * 1000)
        
        # 測量有裝飾器執行時間
        decorated_times = []
        for _ in range(100):
            start = time.perf_counter()
            await decorated_func()
            decorated_times.append((time.perf_counter() - start) * 1000)
        
        overhead = mean(decorated_times) - mean(plain_times)
        
        # 裝飾器開銷應該很小
        assert overhead < 0.1  # 小於 0.1ms
        
        print(f"Decorator overhead: {overhead:.3f}ms")
```

### 5. 回歸測試

#### 檔案: `test/regression/test_api_contracts.py`

```python
"""API 契約回歸測試"""
import pytest
from fastapi.testclient import TestClient
import json

from src.main import app


class TestAPIContracts:
    """確保 API 契約不被破壞"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_keyword_extraction_contract(self, client):
        """測試關鍵字提取 API 契約"""
        # 成功情況
        response = client.post(
            "/api/v1/extract-jd-keywords",
            json={
                "job_description": "We need a Python developer with FastAPI experience " * 10,
                "max_keywords": 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            # 驗證必要欄位
            assert "success" in data
            assert "data" in data
            assert "keywords" in data["data"]
            assert "keyword_count" in data["data"]
            assert "confidence_score" in data["data"]
        else:
            # 錯誤情況也要符合契約
            data = response.json()
            assert "success" in data
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]
    
    def test_error_response_contract(self, client):
        """測試錯誤響應契約"""
        # 故意觸發錯誤
        response = client.post(
            "/api/v1/index-calculation",
            json={}  # 缺少必要欄位
        )
        
        assert response.status_code in [400, 422]
        data = response.json()
        
        # 驗證錯誤響應結構
        assert data["success"] is False
        assert data["error"]["has_error"] is True
        assert len(data["error"]["code"]) > 0
        assert len(data["error"]["message"]) > 0
        assert "details" in data["error"]
        assert "field_errors" in data["error"]
```

## 📊 測試覆蓋率要求

### 單元測試覆蓋率
- Error Handler Factory: **>= 95%**
- Error Codes: **100%**
- Decorator: **>= 90%**
- Exceptions: **>= 85%**

### 整合測試覆蓋率
- 所有端點的錯誤場景: **100%**
- 錯誤碼使用: **>= 90%**
- 監控整合: **>= 80%**

### 錯誤類型覆蓋
每個端點必須測試：
- ✅ 400 Bad Request
- ✅ 401 Unauthorized (如適用)
- ✅ 403 Forbidden (如適用)
- ✅ 404 Not Found (如適用)
- ✅ 422 Unprocessable Entity
- ✅ 429 Too Many Requests
- ✅ 500 Internal Server Error
- ✅ 502 Bad Gateway
- ✅ 503 Service Unavailable
- ✅ 504 Gateway Timeout

## 🚀 測試執行計畫

### 測試執行順序
1. **單元測試** (必須先通過)
   ```bash
   pytest test/unit/services/test_error_handler_factory.py -v
   pytest test/unit/decorators/test_error_handler.py -v
   ```

2. **整合測試**
   ```bash
   pytest test/integration/test_unified_error_handling.py -v
   ```

3. **回歸測試**
   ```bash
   pytest test/regression/test_api_contracts.py -v
   ```

4. **性能測試**
   ```bash
   pytest test/performance/test_error_handling_performance.py -v
   ```

5. **完整測試套件**
   ```bash
   ./test/scripts/run_complete_test_suite.sh
   ```

### CI/CD 整合
```yaml
# .github/workflows/test.yml
- name: Run Error Handling Tests
  run: |
    pytest test/unit/services/test_error_handler_factory.py
    pytest test/unit/decorators/test_error_handler.py
    pytest test/integration/test_unified_error_handling.py
```

## 📈 測試指標

### 成功標準
- **所有測試通過**: 100%
- **無性能退化**: 響應時間增加 < 5%
- **無破壞性變更**: API 契約保持不變
- **錯誤覆蓋完整**: 所有錯誤類型都被測試

### 監控指標
- 測試執行時間
- 測試覆蓋率
- 錯誤處理延遲
- 記憶體使用

## 🐛 已知問題與風險

### 潛在問題
1. **並發測試可能失敗** - 使用 pytest-xdist 時注意
2. **模擬服務可能不準確** - 定期與真實服務測試
3. **性能測試環境差異** - 在相同環境執行

### 緩解措施
- 使用 fixture 隔離測試
- 定期執行端到端測試
- 在 CI 環境標準化測試

## 📝 測試文檔

### 測試報告模板
```markdown
## 測試執行報告

**日期**: YYYY-MM-DD
**版本**: X.X.X
**執行者**: Name

### 測試結果
- 單元測試: X/Y 通過
- 整合測試: X/Y 通過
- 性能測試: 符合/不符合標準
- 回歸測試: 通過/失敗

### 問題追蹤
- Issue #1: Description
- Issue #2: Description

### 建議
- 建議事項
```

## 🔄 更新記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-08-12 | 1.0.0 | 初始版本 |

---

**注意**: 測試計畫將隨實作進度更新。所有測試必須在部署前通過。