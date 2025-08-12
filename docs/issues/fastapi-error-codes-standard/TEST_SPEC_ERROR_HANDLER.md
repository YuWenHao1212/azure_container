# 統一錯誤處理系統測試規格文檔

## 文檔資訊
- **版本**: 2.1.0
- **建立日期**: 2025-08-12
- **最後更新**: 2025-08-12
- **維護者**: 測試團隊
- **測試總數**: 30 個（20 單元測試 + 10 整合測試）
- **更新說明**: 
  - v2.1.0: 成為統一錯誤處理測試中心，新增 5 個通用錯誤測試，合併其他模組的重複測試
  - v2.0.0: 精簡版本，移除不必要的 PT 和 E2E，專注核心功能測試

## 測試理念
錯誤處理是 **service level** 功能，應專注於：
- **單元測試 (UT)**: 驗證核心組件邏輯正確性
- **整合測試 (IT)**: 驗證與 FastAPI 框架整合正確
- **不需要 PT/E2E**: 效能和端對端測試應在業務 API 層級進行

## 測試約束 ⚠️

### 程式碼品質要求
- 執行 `ruff check src/ test/ --line-length=120` 必須通過
- 測試執行時間：UT < 5秒，IT < 15秒
- 測試覆蓋率：核心邏輯 > 90%

## 1. 測試案例編號系統

```
ERR-[序號]-[類型]
範例: ERR-001-UT
```

## 2. 單元測試 (20個) - 核心邏輯驗證

### ERR-001-UT: 錯誤碼常數完整性
- **測試目標**: 驗證所有必要錯誤碼都已定義
- **測試內容**: ErrorCodes 類別常數檢查
- **判斷標準**: 
  - VALIDATION_ERROR 存在
  - AUTH_TOKEN_INVALID 存在
  - EXTERNAL_RATE_LIMIT_EXCEEDED 存在
  - SYSTEM_INTERNAL_ERROR 存在

### ERR-002-UT: 錯誤碼映射結構
- **測試目標**: 驗證 ERROR_CODE_MAPPING 結構完整
- **測試內容**: 每個錯誤碼的必要欄位
- **判斷標準**: 
  - 包含 message (中文)
  - 包含 message_en (英文)
  - 包含 status_code (400-599)

### ERR-003-UT: 多語言訊息取得
- **測試目標**: 驗證 get_error_message 函數
- **測試內容**: 中英文訊息切換
- **測試資料**:
  ```python
  ("VALIDATION_ERROR", "zh") → "輸入資料驗證失敗"
  ("VALIDATION_ERROR", "en") → "Input validation failed"
  ("UNKNOWN", "zh") → "未知錯誤"
  ```

### ERR-004-UT: HTTP 狀態碼映射
- **測試目標**: 驗證 get_status_code 函數
- **測試內容**: 錯誤碼到狀態碼的映射
- **測試案例**:
  - VALIDATION_ERROR → 422
  - AUTH_TOKEN_INVALID → 401
  - EXTERNAL_RATE_LIMIT_EXCEEDED → 429
  - SYSTEM_INTERNAL_ERROR → 500

### ERR-005-UT: Factory 單例模式
- **測試目標**: 驗證 ErrorHandlerFactory 單例實作
- **測試內容**: 多次呼叫 get_error_handler_factory()
- **判斷標準**: 返回相同實例 (id 相同)

### ERR-006-UT: 異常分類邏輯
- **測試目標**: 驗證 _classify_exception 方法
- **測試內容**: 不同異常類型的分類
- **測試案例**:
  ```python
  ValidationError → (VALIDATION_ERROR, 422)
  RateLimitError → (EXTERNAL_RATE_LIMIT_EXCEEDED, 429)
  AuthenticationError(401) → (AUTH_TOKEN_INVALID, 401)
  AuthenticationError(403) → (AUTH_INSUFFICIENT_PERMISSIONS, 403)
  Exception → (SYSTEM_INTERNAL_ERROR, 500)
  ```

### ERR-007-UT: ServiceError 增強
- **測試目標**: 驗證 ServiceError.to_response() 方法
- **測試內容**: error_code 和 status_code 屬性
- **判斷標準**: 
  - 屬性正確設定和讀取
  - to_response() 返回正確格式

### ERR-008-UT: 自定義訊息優先
- **測試目標**: 驗證訊息優先級邏輯
- **測試內容**: _get_error_message 方法
- **判斷標準**: 
  - 有 message 屬性時優先使用
  - 無 message 時使用預設
  - ValueError 特殊處理

### ERR-009-UT: 欄位錯誤提取
- **測試目標**: 驗證 ValidationError field_errors 處理
- **測試內容**: _extract_field_errors 方法
- **測試資料**:
  ```python
  ValidationError(field_errors={"resume": ["Too short"]})
  ```

### ERR-010-UT: 錯誤回應格式
- **測試目標**: 驗證 _create_error_response 結構
- **測試內容**: 回應格式完整性
- **必要欄位**:
  - success: false
  - error.has_error: true
  - error.code: 錯誤碼
  - error.message: 錯誤訊息
  - timestamp: ISO 格式

### ERR-011-UT: Debug 模式控制
- **測試目標**: 驗證 debug 模式詳細資訊顯示
- **測試內容**: _get_error_details 方法
- **判斷標準**: 
  - debug=true 顯示異常詳情
  - debug=false 返回空字串

### ERR-012-UT: 裝飾器保留函數元資料
- **測試目標**: 驗證 @functools.wraps 正確使用
- **測試內容**: 裝飾後函數的 __name__ 和 __doc__
- **判斷標準**: 原始函數元資料保留

### ERR-013-UT: HTTPException 透傳
- **測試目標**: 驗證 HTTPException 不被攔截
- **測試內容**: 裝飾器遇到 HTTPException 的行為
- **判斷標準**: HTTPException 直接 raise

### ERR-014-UT: 監控服務呼叫
- **測試目標**: 驗證錯誤送到監控系統
- **測試內容**: Mock monitoring_service.track_error
- **判斷標準**: 
  - track_error 被呼叫
  - 包含錯誤類型和訊息
  - 監控失敗不影響主流程

### ERR-015-UT: 完整處理流程
- **測試目標**: 驗證 handle_exception 端到端流程
- **測試內容**: 從異常到回應的完整路徑
- **驗證步驟**:
  1. 異常分類
  2. 訊息取得
  3. 監控記錄
  4. 回應生成

### ERR-016-UT: 通用驗證錯誤處理 [合併自其他模組]
- **測試目標**: 驗證通用輸入驗證錯誤的統一處理
- **測試內容**: 測試各種輸入驗證錯誤場景
- **合併來源**: INDEX_CALCULATION, HEALTH_KEYWORDS, RESUME_TAILORING
- **判斷標準**: 
  - 參數過短 (<200字元) → VALIDATION_ERROR
  - 參數類型錯誤 → VALIDATION_ERROR
  - 缺少必要參數 → VALIDATION_ERROR
  - 統一返回 422 狀態碼

### ERR-017-UT: 通用外部服務錯誤分類 [合併自其他模組]
- **測試目標**: 驗證外部服務錯誤的統一分類邏輯
- **測試內容**: 測試各種外部服務失敗場景
- **合併來源**: INDEX_CALCULATION, RESUME_TAILORING
- **判斷標準**: 
  - 429 錯誤 → EXTERNAL_RATE_LIMIT_EXCEEDED
  - 502 錯誤 → EXTERNAL_SERVICE_ERROR
  - 504 錯誤 → EXTERNAL_SERVICE_TIMEOUT
  - 正確的錯誤訊息格式

### ERR-018-UT: 通用語言檢測錯誤 [合併自 SERVICE_MODULES]
- **測試目標**: 驗證不支援語言的統一錯誤處理
- **測試內容**: 測試各種不支援語言的拒絕機制
- **合併來源**: SERVICE_MODULES (SVC-LD-006~009)
- **判斷標準**: 
  - 簡體中文 → UNSUPPORTED_LANGUAGE
  - 日文/韓文 → UNSUPPORTED_LANGUAGE
  - 統一返回 422 狀態碼
  - 包含檢測到的語言資訊

### ERR-019-UT: 通用重試機制錯誤分類 [合併自 GAP_ANALYSIS]
- **測試目標**: 驗證重試機制的錯誤分類邏輯
- **測試內容**: 測試哪些錯誤應該重試、哪些不應該
- **合併來源**: GAP_ANALYSIS (API-GAP-018~027)
- **判斷標準**: 
  - 暫時性錯誤 (429, 503) → 可重試
  - 永久性錯誤 (400, 422) → 不可重試
  - 超時錯誤 (408, 504) → 可重試
  - 認證錯誤 (401, 403) → 不可重試

### ERR-020-UT: 通用系統內部錯誤處理 [合併自其他模組]
- **測試目標**: 驗證未預期錯誤的統一處理
- **測試內容**: 測試各種未預期的系統錯誤
- **合併來源**: RESUME_TAILORING, INDEX_CALCULATION
- **判斷標準**: 
  - 未捕獲的 Exception → SYSTEM_INTERNAL_ERROR
  - 返回 500 狀態碼
  - 不洩露敏感資訊
  - 包含錯誤追蹤 ID

## 3. 整合測試 (10個) - FastAPI 整合驗證

### ERR-001-IT: 成功請求不受影響
- **測試目標**: 驗證裝飾器不影響正常請求
- **測試內容**: 使用 TestClient 測試成功請求
- **測試端點**: /api/v1/prompts/tasks
- **判斷標準**: 
  - 返回 200
  - 原始回應不變

### ERR-002-IT: ValidationError 處理
- **測試目標**: 驗證 422 驗證錯誤正確處理
- **測試內容**: 觸發 ValidationError
- **測試資料**: 無效的 task 參數
- **判斷標準**: 
  - 返回 422
  - error.code = "VALIDATION_ERROR"
  - 統一錯誤格式

### ERR-003-IT: 內部錯誤處理
- **測試目標**: 驗證 500 錯誤處理
- **測試內容**: Mock 內部異常
- **判斷標準**: 
  - 返回 500
  - error.code = "SYSTEM_INTERNAL_ERROR"
  - 不洩露 stack trace（非 debug 模式）

### ERR-004-IT: 認證錯誤處理
- **測試目標**: 驗證 401/403 錯誤
- **測試內容**: Mock AuthenticationError
- **測試案例**:
  - status_code=401 → AUTH_TOKEN_INVALID
  - status_code=403 → AUTH_INSUFFICIENT_PERMISSIONS

### ERR-005-IT: 速率限制錯誤
- **測試目標**: 驗證 429 錯誤處理
- **測試內容**: Mock RateLimitError
- **判斷標準**: 
  - 返回 429
  - error.code = "EXTERNAL_RATE_LIMIT_EXCEEDED"

### ERR-006-IT: 外部服務錯誤
- **測試目標**: 驗證 502/503 錯誤
- **測試內容**: Mock ExternalServiceError
- **判斷標準**: 
  - 返回正確狀態碼
  - error.code = "EXTERNAL_SERVICE_ERROR/UNAVAILABLE"

### ERR-007-IT: 欄位級錯誤
- **測試目標**: 驗證 field_errors 正確返回
- **測試內容**: ValidationError 包含 field_errors
- **判斷標準**: 
  - error.field_errors 包含欄位錯誤
  - 格式正確

### ERR-008-IT: 錯誤格式一致性
- **測試目標**: 驗證所有錯誤使用統一格式
- **測試內容**: 觸發多種錯誤類型
- **判斷標準**: 
  - 都包含 success, error, timestamp
  - error 結構一致

### ERR-009-IT: HTTPException 相容
- **測試目標**: 驗證與 FastAPI HTTPException 相容
- **測試內容**: 混用 HTTPException 和自定義錯誤
- **判斷標準**: 
  - HTTPException 正常處理
  - 自定義錯誤也正常處理

### ERR-010-IT: 並發請求隔離
- **測試目標**: 驗證並發錯誤互不干擾
- **測試內容**: 同時發送多個會失敗的請求
- **判斷標準**: 
  - 每個請求獨立處理
  - 錯誤訊息不混淆

## 4. 測試執行指南

### 4.1 執行命令
```bash
# 單元測試 (應在 5 秒內完成)
pytest test/unit/test_error_handler/ -v

# 整合測試 (應在 15 秒內完成)  
pytest test/integration/test_error_handler_integration/ -v

# 全部測試
pytest test/ -k "error_handler" -v

# 測試覆蓋率
pytest test/ -k "error_handler" --cov=src/constants --cov=src/services/error_handler_factory --cov=src/decorators
```

### 4.2 測試檔案結構
```
test/
├── unit/
│   └── test_error_handler/
│       ├── test_error_codes.py         # ERR-001-UT ~ ERR-004-UT
│       ├── test_error_handler_factory.py # ERR-005-UT ~ ERR-011-UT, ERR-015-UT
│       └── test_error_handler_decorator.py # ERR-012-UT ~ ERR-014-UT
└── integration/
    └── test_error_handler_integration/
        └── test_error_handler_api.py   # ERR-001-IT ~ ERR-010-IT
```

## 5. 測試資料最小集

### 必要測試資料
```python
# 最小測試集 - 涵蓋所有錯誤類型
TEST_CASES = {
    "validation": {"task": "invalid_task"},
    "auth_401": {"api_key": "invalid"},
    "auth_403": {"api_key": "valid_but_no_permission"},
    "rate_limit": {"requests": 100},  # 觸發限流
    "internal": Mock(side_effect=Exception("test")),
    "external": Mock(side_effect=ExternalServiceError())
}
```

## 6. 驗收標準

### 必須通過
- [ ] 所有 15 個單元測試通過
- [ ] 所有 10 個整合測試通過
- [ ] Ruff 檢查無錯誤
- [ ] 測試執行時間符合要求

### 品質指標
- [ ] 核心邏輯覆蓋率 > 90%
- [ ] 錯誤格式 100% 一致
- [ ] 無破壞性變更

## 7. 已知限制和假設

### 限制
1. 監控服務使用 Mock（單元測試）
2. 不測試真實 Azure OpenAI 錯誤（由業務 API 測試覆蓋）
3. 不測試效能影響（錯誤處理開銷極小）

### 假設
1. FastAPI 框架錯誤處理機制穩定
2. Python 異常機制可靠
3. 監控服務介面不會變更

---

**文檔結束** - 版本 2.0.0 | 精簡但完整的測試規格