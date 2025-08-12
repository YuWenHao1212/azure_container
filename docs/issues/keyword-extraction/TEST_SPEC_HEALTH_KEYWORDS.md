# 健康檢查與關鍵字提取測試規格文檔

## 文檔資訊
- **版本**: 3.2.0
- **建立日期**: 2025-08-06
- **最後更新**: 2025-08-06
- **維護者**: 測試團隊
- **範圍**: API層健康檢查(HLT)與關鍵字提取(KW)測試
- **說明**: 服務層測試已移至 service-module-refactor/TEST_SPEC_SERVICE_MODULES.md

## 測試執行指南

### 快速開始
```bash
# 執行完整 Mock 測試套件（推薦開發使用）- 19 個測試
./test/scripts/run_health_keyword_unit_integration.sh

# 執行真實 API 效能測試（會產生費用）- 1 個測試
./test/scripts/run_health_keyword_real_api_perf.sh
```

### Mock 測試（單元測試 + 整合測試）
```bash
# 執行完整 Mock 測試套件 - 19 個測試（約 15 秒）
./test/scripts/run_health_keyword_unit_integration.sh

# 執行單元測試 - 8 個測試
./test/scripts/run_health_keyword_unit_integration.sh --stage unit

# 執行整合測試 - 11 個測試  
./test/scripts/run_health_keyword_unit_integration.sh --stage integration

# 背景執行（適合長時間測試）
./test/scripts/run_health_keyword_unit_integration.sh --background
```

### 真實 API 測試（效能測試）
```bash
# 執行效能測試 - 1 個測試（25 個請求樣本）
./test/scripts/run_health_keyword_real_api_perf.sh

# 背景執行
./test/scripts/run_health_keyword_real_api_perf.sh --background

# 執行特定效能測試
./test/scripts/run_health_keyword_real_api_perf.sh --perf-test keyword
```

### 注意事項
- **Mock 測試**：適合開發階段快速驗證（約 15 秒）
- **真實 API 測試**：會產生 Azure OpenAI API 費用（約 40-60 秒）
- **效能測試配置**：使用 25 個樣本（5 個測試案例 × 5 個請求）計算 P50/P95
- **P50 目標**：< 3500ms
- **P95 目標**：< 4500ms

## 變更歷史
| 版本 | 日期 | 變更內容 | 修改者 |
|------|------|----------|--------|
| 3.2.0 | 2025-08-06 | 新增測試執行指南，更新 P50/P95 目標值 | 測試團隊 |
| 3.1.0 | 2025-08-06 | 分離服務層測試至獨立文檔 | 測試團隊 |
| 3.0.0 | 2025-08-06 | 重新編號系統，分離API層與服務層測試 | 測試團隊 |

## 1. 測試編號系統重組

### 1.1 編號格式
```
[類別]-[模組]-[序號]-[類型]

範例: API-HLT-001-UT
      SVC-LD-001-UT
```

### 1.2 模組代碼定義

| 代碼 | 模組 | 說明 | 編號範圍 |
|------|------|------|----------|
| **API層模組** |
| HLT | Health | 健康檢查端點 | 001-099 (UT), 101-199 (IT) |
| KW | Keywords | 關鍵字提取API | 001-099 (UT), 101-199 (IT), 201-299 (PT) |
**註**: 服務層模組 (SVC-LD, SVC-PM, SVC-KW, SVC-LLM) 已移至 [TEST_SPEC_SERVICE_MODULES.md](../service-module-refactor/TEST_SPEC_SERVICE_MODULES.md)

### 1.3 測試類型
- **UT**: Unit Test (單元測試)
- **IT**: Integration Test (整合測試)
- **PT**: Performance Test (效能測試)
- **E2E**: End-to-End Test (端對端測試)

## 2. 測試編號對照表

### 2.1 總覽統計
- **健康檢查模組**: 3個測試（2個單元 + 1個整合）
- **關鍵字提取API**: 13個測試（3個單元 + 10個整合）**[原16個，移除3個]**
- **總計Mock測試**: 16個測試 (5 UT + 11 IT) **[原19個]**
- **效能測試**: 1個測試 (獨立執行，Real API)
- **移除測試**: API-KW-002/003/004-UT（合併至ERROR_HANDLER）

**註**: 服務層74個測試已移至 [TEST_SPEC_SERVICE_MODULES.md](../service-module-refactor/TEST_SPEC_SERVICE_MODULES.md)

### 2.2 詳細對照表

| 原編號 | 新編號 | 測試名稱 | 層級 | 檔案位置 |
|--------|--------|----------|------|----------|
| **健康檢查 (HLT)** |||||
| API-HLT-001~009-UT | **API-HLT-001~002-UT** | 健康檢查端點單元測試 | API | test/unit/test_health.py |
| API-HLT-010-IT | **API-HLT-101-IT** | 健康檢查整合測試 | API | test/integration/test_health_integration.py |
| **關鍵字提取API (KW)** |||||
| API-KW-101~110-UT | **API-KW-001~006-UT** | 基礎功能單元測試 | API | test/unit/test_keyword_extraction.py |
| API-KW-111-IT | **API-KW-101-IT** | Azure OpenAI整合 | API | test/integration/test_azure_openai_integration.py |
| API-KW-301~314-IT | **API-KW-102~110-IT** | 語言檢測整合測試 | API | test/integration/test_keyword_extraction_language.py |
| API-KW-315-PT | **API-KW-201-PT** | 關鍵字提取效能 | API | test/performance/test_keyword_extraction_performance_simple.py |


## 3. 健康檢查模組 (HLT)

### 3.1 單元測試 (API-HLT-001-UT, API-HLT-002-UT)

#### API-HLT-001-UT: 健康檢查端點完整驗證
- **名稱**: 健康檢查端點回應與格式驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 單一請求驗證所有健康檢查功能
- **測試內容**: 發送 GET 請求至 /health
- **判斷標準** (全部必須通過): 
  - ✅ HTTP 200 狀態碼
  - ✅ 回應包含 "status": "healthy"
  - ✅ 包含所有必要欄位: status, timestamp, version, environment
  - ✅ 各欄位類型正確 (string/datetime)
  - ✅ version 欄位值等於 settings.VERSION
  - ✅ timestamp 符合 ISO 8601 格式
  - ✅ 不需要認證 (無 API Key 也能訪問)
  - ✅ 包含 CORS headers (Access-Control-Allow-Origin)

#### API-HLT-002-UT: HTTP 方法限制驗證
- **名稱**: 健康檢查只接受 GET 方法
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證非 GET 方法被正確拒絕
- **測試內容**: 使用 POST, PUT, DELETE 方法請求 /health
- **判斷標準**: 
  - ✅ 所有非 GET 方法返回 405 Method Not Allowed
  - ✅ 錯誤回應格式正確 (接受 FastAPI 標準格式 `{"detail": "..."}` 或自定義格式 `{"error": {...}}`)
- **實作細節**: 測試能容忍不同的錯誤回應格式，因為 FastAPI 可能回傳標準或自定義錯誤格式

### 3.2 整合測試 (API-HLT-101-IT)

#### API-HLT-101-IT: 健康檢查整合測試
- **名稱**: 健康檢查含依賴服務狀態
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證健康檢查能正確反映外部服務狀態
- **測試內容**: 整合實際服務依賴
- **判斷標準**: 
  - 能正確顯示各服務狀態
  - 整體狀態邏輯正確
- **狀態**: ✅ 已實作

## 4. 關鍵字提取API層 (KW)

### 4.1 單元測試 (API-KW-001~006-UT)
**註**: 單元測試使用 Mock Azure OpenAI 服務，不會實際調用外部 API

#### API-KW-001-UT: 關鍵字提取成功路徑完整驗證
- **名稱**: JD 關鍵字提取正常流程與格式驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 單一請求驗證所有成功路徑功能
- **測試內容**: 發送有效英文JD (>200字元) 至 /api/v1/extract-jd-keywords
- **判斷標準** (全部必須通過):
  - ✅ HTTP 200 狀態碼
  - ✅ success = true
  - ✅ 返回 keywords 陣列 (非空)
  - ✅ 關鍵字數量符合預期 (1-30個)
  - ✅ 包含所有必要欄位: keywords, detected_language, prompt_version
  - ✅ detected_language = "en" (英文JD)
  - ✅ prompt_version 包含版本資訊
  - ✅ 每個關鍵字為非空字串
  - ✅ warning.has_warning = false (正常情況)

#### API-KW-002-UT: 驗證錯誤處理 - 描述過短 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-016-UT (通用驗證錯誤處理)
- **名稱**: JD 過短驗證錯誤
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 JD 少於 200 字元的錯誤處理
- **測試內容**: 發送 < 200 字元的 job_description
- **判斷標準**:
  - ✅ HTTP 422 (Unprocessable Entity)
  - ✅ error.code = "VALIDATION_ERROR"
  - ✅ error.message 包含 "輸入參數驗證失敗"
  - ✅ error.details 包含 "Job description must be at least 200 characters"

#### API-KW-003-UT: 驗證錯誤處理 - max_keywords 無效 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-016-UT (通用驗證錯誤處理)
- **名稱**: max_keywords 參數驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 max_keywords 範圍檢查
- **測試內容**: 測試 max_keywords < 5 或 > 25 (實際 API 限制)
- **判斷標準**:
  - ✅ HTTP 422 (Unprocessable Entity)
  - ✅ error.code = "VALIDATION_ERROR"
  - ✅ error.details 包含 "greater than or equal to 5" (< 5 時，Pydantic V2 格式)
  - ✅ error.details 包含 "less than or equal to 25" (> 25 時，實際 API 限制)
- **實作細節**: 
  - API 實際限制為 25，不是文檔中的 30 (見 `src/models/keyword_extraction.py:23`)
  - 使用 Pydantic V2 驗證訊息格式，支援部分字串匹配而非完整訊息匹配

#### API-KW-004-UT: 外部服務錯誤處理 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-017-UT (通用外部服務錯誤分類)
- **名稱**: Azure OpenAI 服務錯誤處理
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證外部服務錯誤的處理
- **測試內容**: Mock 各種 Azure OpenAI 錯誤
- **判斷標準**:
  - **速率限制錯誤**:
    - ✅ HTTP 429 (Too Many Requests)
    - ✅ error.code = "EXTERNAL_RATE_LIMIT_EXCEEDED"
    - ✅ 包含重試建議
  - **服務超時**:
    - ✅ HTTP 504 (Gateway Timeout)
    - ✅ error.code = "EXTERNAL_SERVICE_TIMEOUT"
    - ✅ 建議稍後重試

#### API-KW-005-UT: 繁體中文支援驗證
- **名稱**: 繁體中文 JD 處理
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證繁體中文完整支援
- **測試內容**: 發送繁體中文JD (>200字元)
- **判斷標準** (全部必須通過):
  - ✅ HTTP 200 狀態碼
  - ✅ detected_language = "zh-TW"
  - ✅ prompt_version 包含 "zh-TW"
  - ✅ 返回相關中文關鍵字
  - ✅ 關鍵字符合中文技能詞彙

#### API-KW-006-UT: 邊界測試與品質警告
- **名稱**: 邊界條件與品質檢查
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證邊界條件處理與品質警告機制
- **測試內容**: 測試各種邊界情況
- **判斷標準**:
  - **超長JD** (3000字元):
    - ✅ HTTP 200 (正常處理)
    - ✅ 不超時 (< 3秒)
    - ✅ 返回合理數量關鍵字 (10-30個)
  - **低品質關鍵字**:
    - ✅ HTTP 200
    - ✅ warning.has_warning = true
    - ✅ warning.message 包含品質提示
    - ✅ warning.suggestion 提供改進建議

### 4.2 整合測試 (API-KW-101~111-IT)
**註**: 整合測試使用 Mock Azure OpenAI 服務，不會實際調用外部 API

#### API-KW-101-IT: Azure OpenAI 整合
- **名稱**: 關鍵字提取 API 整合測試
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證與 Azure OpenAI 的整合
- **測試內容**: 使用 Mock Azure OpenAI 服務測試
- **判斷標準**: 成功返回關鍵字

#### API-KW-102-IT: 英文 JD 使用英文 prompt
- **名稱**: 端到端驗證英文職缺使用英文 prompt
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證語言檢測與prompt選擇
- **測試內容**: 發送英文JD
- **判斷標準**: 
  - detected_language="en"
  - prompt_version 包含 "en"

#### API-KW-103-IT: 繁中 JD 使用繁中 prompt
- **名稱**: 端到端驗證繁中職缺使用繁中 prompt
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證繁中語言處理
- **測試內容**: 發送繁體中文JD
- **判斷標準**: 
  - detected_language="zh-TW"
  - prompt_version 包含 "zh-TW"

#### API-KW-104-IT: 混合語言（>20%繁中）
- **名稱**: 混合語言正確選擇 prompt
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證混合語言閾值處理
- **測試內容**: 發送混合語言JD（繁中>20%）
- **判斷標準**: 
  - detected_language="zh-TW"
  - 使用繁中 prompt

#### API-KW-105-IT: 混合語言（<20%繁中）
- **名稱**: 混合語言低於閾值時使用英文 prompt
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證混合語言閾值處理
- **測試內容**: 發送混合語言JD（繁中<20%）
- **判斷標準**: 
  - detected_language="en"
  - prompt_version 包含 "en"

#### API-KW-106-IT: 拒絕簡體中文
- **名稱**: API 正確拒絕簡體中文內容
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證簡體中文檢測和拒絕機制
- **測試內容**: 發送純簡體中文 JD
- **判斷標準**: 
  - HTTP 422
  - error.code="UNSUPPORTED_LANGUAGE"
  - 錯誤訊息包含語言檢測結果

#### API-KW-107-IT: 拒絕日文
- **名稱**: API 正確拒絕日文內容
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證日文檢測和拒絕機制
- **測試內容**: 發送純日文 JD
- **判斷標準**: 
  - HTTP 422
  - error.code="UNSUPPORTED_LANGUAGE"

#### API-KW-108-IT: 拒絕韓文
- **名稱**: API 正確拒絕韓文內容
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證韓文檢測和拒絕機制
- **測試內容**: 發送純韓文 JD
- **判斷標準**: 
  - HTTP 422
  - error.code="UNSUPPORTED_LANGUAGE"

#### API-KW-109-IT: 拒絕混合不支援語言並返回詳細錯誤
- **名稱**: 混合不支援語言的詳細錯誤回應
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證混合語言檢測和完整錯誤回應
- **測試內容**: 發送包含多種不支援語言的混合內容
- **判斷標準**: 
  - HTTP 422
  - error.code="UNSUPPORTED_LANGUAGE"
  - 錯誤回應包含完整結構
  - 錯誤包含語言組成分析詳情

#### API-KW-110-IT: 語言參數覆蓋測試
- **名稱**: 明確指定 language 參數時的 API 行為
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證語言參數覆蓋自動檢測
- **測試內容**: 指定 language 參數
- **判斷標準**: 使用指定語言的 prompt

### 4.3 效能測試 (API-KW-201-PT)
**註**: 效能測試使用真實的 Azure OpenAI API 來測試實際效能，通過 LLM Factory (`get_llm_client`) 調用

#### API-KW-201-PT: 關鍵字提取效能
- **名稱**: 關鍵字提取回應時間測試
- **優先級**: P1
- **類型**: 效能測試
- **測試目標**: 驗證API效能符合要求
- **測試內容**: 執行30次請求，計算響應時間
- **判斷標準**: 
  - P50 < 3.5秒
  - P95 < 4.5秒
  - 成功率 > 95%

## 5. 測試套件執行

### 5.1 測試檔案對應

| 測試套件 | 檔案路徑 | 測試數量 |
|---------|----------|----------|
| 健康檢查單元測試 | test/unit/test_health.py | 2 |
| 健康檢查整合測試 | test/integration/test_health_integration.py | 1 |
| 關鍵字提取單元測試 | test/unit/test_keyword_extraction.py | 6 |
| 關鍵字提取整合測試 | test/integration/test_keyword_extraction_language.py | 9 |
| Azure OpenAI整合 | test/integration/test_azure_openai_integration.py | 1 |
| 關鍵字提取效能 | test/performance/test_keyword_extraction_performance_simple.py | 1 |
| **總計API層** | | **20** |

### 5.2 執行指令

```bash
# 執行健康檢查測試
pytest test/unit/test_health.py -v
pytest test/integration/test_health_integration.py -v

# 執行關鍵字提取API層測試
pytest test/unit/test_keyword_extraction.py -v
pytest test/integration/test_keyword_extraction_language.py -v
pytest test/performance/test_keyword_extraction_performance_simple.py -v

# 執行完整測試套件
./test/scripts/run_complete_test_suite.sh --include-performance
```

## 6. 測試統計摘要

### 6.1 按層級統計

| 層級 | 單元測試 | 整合測試 | 效能測試 | 總計 |
|------|----------|----------|----------|------|
| API層 - 健康檢查 | 2 | 1 | 0 | 3 |
| API層 - 關鍵字提取 | 6 | 10 | 1 | 17 |
| **總計** | **8** | **11** | **1** | **20** |

### 6.2 按功能統計

| 功能模組 | 測試數量 | 類型分佈 |
|----------|----------|----------|
| 健康檢查 | 3 | 2 UT + 1 IT |
| 關鍵字提取 | 17 | 6 UT + 10 IT + 1 PT |
| **總計** | **20** | 8 UT + 11 IT + 1 PT |

**註**: 服務層測試統計請參考 [TEST_SPEC_SERVICE_MODULES.md](../service-module-refactor/TEST_SPEC_SERVICE_MODULES.md)

## 7. 注意事項

1. **編號一致性**: 所有測試案例編號已根據新系統重新編排
2. **層級分離**: 明確區分API層測試(使用TestClient)與服務層測試(直接調用服務)
3. **檔案組織**: 部分測試需要從原檔案遷移到新的對應檔案
4. **向後相容**: 保留原編號對照，便於追溯
5. **API 調用規範**: 
   - **UT (單元測試)**: 使用 Mock Azure OpenAI 服務，不產生實際 API 調用成本
   - **IT (整合測試)**: 使用 Mock Azure OpenAI 服務，測試服務間整合但不調用真實 API
   - **PT (效能測試)**: 使用真實 Azure OpenAI API，必須通過 LLM Factory (`get_llm_client`) 調用
   - **禁止模式**: 直接使用 `get_azure_openai_client()` 或 OpenAI SDK，會導致 deployment 錯誤
   - **參考經驗**: index-calculation-v2 和 gap-analysis-v2 重構中的 Real API vs Mock 最佳實踐

---

**文檔維護**: 
- 定期審查測試覆蓋率
- 新增測試時遵循編號規範
- 更新對照表以保持同步