# Index Calculation V2 測試規格文檔

## 1. 測試概述

### 1.1 測試目標
- 驗證 Index Calculation V2 所有功能符合技術規格要求
- 確保效能指標達到預定目標（P95 < 2秒）
- 驗證錯誤處理機制的完整性和正確性
- 確認 Bubble.io API Connector 相容性（固定 schema）
- 測試快取機制和並行處理的效果

### 1.2 測試範圍
本測試規格涵蓋 Index Calculation V2 的所有核心功能模組：
1. **服務架構** - 服務類別初始化與生命週期管理
2. **相似度計算** - Embedding 生成與 cosine similarity 計算
3. **關鍵字覆蓋** - 關鍵字匹配分析與統計
4. **快取機制** - LRU 快取與 TTL 管理
5. **並行處理** - Python 3.11 TaskGroup 的並發執行
6. **錯誤處理** - 各層級錯誤捕獲與降級策略
7. **監控統計** - 輕量級監控資料收集

## 2. 測試命名規範

### 2.1 測試 ID 格式
遵循專案統一格式：`API-[MODULE]-[NUMBER]-[TYPE]`

```
API-IC-XXX-YY
```

其中：
- `API` - 固定前綴，表示 API 相關測試
- `IC` - Index Calculation 模組代碼
- `XXX` - 三位數編號（001-999）
- `YY` - 測試類型：
  - `UT` - Unit Test（單元測試）
  - `IT` - Integration Test（整合測試）
  - `PT` - Performance Test（效能測試）

### 2.2 測試優先級定義
- **P0 (Critical)**: 核心功能測試，阻擋發布，必須 100% 通過
- **P1 (High)**: 重要功能測試，影響用戶體驗，應該通過
- **P2 (Medium)**: 次要功能測試，不影響主流程，建議通過
- **P3 (Low)**: 邊緣情況測試，用於提升健壯性

## 3. 單元測試規格 (Unit Tests)

### 3.1 服務架構測試

#### API-IC-001-UT: 服務初始化測試
- **優先級**: P0
- **測試目的**: 驗證 IndexCalculationServiceV2 能夠正確初始化，並確保所有依賴正確注入
- **測試方法**:
  1. 測試預設配置初始化
  2. 測試自訂配置初始化
  3. 驗證各種依賴的注入狀態
- **輸入資料**:
  - 預設配置
  - 自訂快取配置
  - 自訂並行處理配置
- **預期結果**: 
  - 服務成功初始化
  - 快取物件正確建立
  - 連線池正確建立
  - 監控元件正確初始化

#### API-IC-002-UT: 快取鍵生成測試
- **優先級**: P0
- **測試目的**: 驗證快取鍵生成的一致性和唯一性
- **測試方法**:
  1. 相同文本產生相同鍵
  2. 不同文本產生不同鍵
  3. HTML 標籤清理後的一致性
- **輸入資料**:
  - 純文本內容
  - HTML 格式內容
  - 空白字元變化
- **預期結果**: 
  - 相同內容產生相同 SHA256 hash
  - 不同內容產生不同 hash
  - HTML 清理後的相同內容產生相同 hash

### 3.2 快取機制測試

#### API-IC-003-UT: 快取 TTL 過期測試
- **優先級**: P1
- **測試目的**: 驗證快取項目的 TTL 過期機制正常運作
- **測試方法**:
  1. 設定短 TTL 測試過期
  2. 設定長 TTL 測試未過期
  3. 測試過期後的清理
- **輸入資料**:
  - TTL = 1 秒的快取項
  - TTL = 60 分鐘的快取項
- **預期結果**: 
  - 過期項目返回 None
  - 未過期項目正常返回資料
  - 過期項目被自動清理

#### API-IC-004-UT: 快取 LRU 淘汰測試
- **優先級**: P1
- **測試目的**: 驗證 LRU 淘汰策略在快取滿時正確運作
- **測試方法**:
  1. 填滿快取到上限
  2. 新增項目觸發淘汰
  3. 驗證最少使用的項目被移除
- **輸入資料**:
  - 快取大小 = 3
  - 連續加入 4 個項目
- **預期結果**: 
  - 第 4 個項目加入時，第 1 個項目被淘汰
  - 快取大小保持在限制內

### 3.3 核心功能測試

#### API-IC-005-UT: 相似度計算整合測試
- **優先級**: P2
- **測試目的**: 驗證整個相似度計算流程的正確性（主要測試 embedding 和 sigmoid 轉換的整合）
- **測試方法**:
  1. Mock Azure OpenAI embedding 服務
  2. 提供固定的 embedding 向量
  3. 驗證計算流程
- **輸入資料**:
  - Mock embeddings: [[0.1, 0.2, ...], [0.1, 0.2, ...]]
  - 履歷和職缺文本
- **預期結果**: 
  - 正確調用 embedding 服務
  - 正確執行 cosine similarity
  - 正確套用 sigmoid 轉換
- **備註**: Embedding 和 cosine similarity 本身是標準 NLP 函數，不需要單獨測試其數學正確性

#### API-IC-006-UT: Sigmoid 轉換參數一致性測試
- **優先級**: P1
- **測試目的**: 確保 sigmoid 轉換參數與 V1 保持一致（k=15.0, x0=0.373）
- **測試方法**:
  1. 驗證預設參數值
  2. 驗證 overflow 處理
  3. 驗證與 V1 輸出一致性
- **輸入資料**:
  - 測試預設參數: x0=0.373, k=15.0
  - 測試極端值: x=-100, x=100
- **預期結果**: 
  - 參數值與配置一致
  - 極端值不會造成 overflow
  - 輸出範圍始終在 [0, 1]
- **備註**: Sigmoid 函數的數學正確性是標準公式，重點是確保參數配置正確

#### API-IC-007-UT: 關鍵字覆蓋分析測試
- **優先級**: P0
- **測試目的**: 驗證關鍵字匹配邏輯的正確性（參考 index_calculation.py 的 analyze_keyword_coverage 函數）
- **測試方法**:
  1. 大小寫不敏感測試 (keyword_match_case_sensitive=False)
  2. 複數形式匹配測試 (enable_plural_matching=True)
  3. 字詞邊界匹配測試 (\b regex)
  4. 逗號分隔字串輸入測試
- **輸入資料**:
  ```python
  # 測試案例 1: 大小寫
  resume = "Python developer with API experience"
  keywords = ["python", "api", "DOCKER"]
  
  # 測試案例 2: 複數形式
  resume = "Strong skills in APIs and Python frameworks"
  keywords = ["API", "framework", "skill"]
  
  # 測試案例 3: 字詞邊界
  resume = "JavaScript developer"
  keywords = ["Java", "Script"]
  ```
- **預期結果**: 
  - 案例 1: covered=["python", "api"], missed=["DOCKER"]
  - 案例 2: covered=["API", "framework"], missed=["skill"] (因為 skills → skill)
  - 案例 3: covered=[], missed=["Java", "Script"] (字詞邊界)

#### API-IC-008-UT: TinyMCE HTML 清理測試
- **優先級**: P1
- **測試目的**: 驗證 TinyMCE 生成的 HTML 能正確清理（使用 text_processing.clean_html_text）
- **測試方法**:
  1. TinyMCE 典型輸出測試
  2. 巢狀標籤和屬性測試
  3. 特殊字元和實體測試
  4. 空白和換行處理
- **輸入資料**:
  ```html
  <!-- TinyMCE 典型輸出 -->
  <p>Python developer with <strong>5 years</strong> experience</p>
  <ul>
    <li>API development</li>
    <li>Docker &amp; Kubernetes</li>
  </ul>
  
  <!-- 特殊情況 -->
  <p>&nbsp;</p>
  <div style="color: red;">Important</div>
  ```
- **預期結果**: 
  - "Python developer with 5 years experience\nAPI development\nDocker & Kubernetes"
  - 保留文本結構，移除所有標籤和樣式
  - HTML 實體正確解碼

### 3.4 並行處理測試

#### API-IC-009-UT: TaskGroup 並行執行測試
- **優先級**: P0
- **測試目的**: 驗證 Python 3.11 TaskGroup 的並行執行正確性
- **測試方法**:
  1. 多任務並行執行
  2. 任務完成順序驗證
  3. 共享資源安全性
- **輸入資料**:
  - 5 個 embedding 生成任務
  - 共享快取物件
- **預期結果**: 
  - 所有任務成功完成
  - 執行時間 < 序列執行
  - 無競爭條件

#### API-IC-010-UT: TaskGroup 錯誤處理測試
- **優先級**: P1
- **測試目的**: 驗證 TaskGroup 的 ExceptionGroup 錯誤處理
- **測試方法**:
  1. 單一任務失敗
  2. 多任務失敗
  3. 部分任務失敗
- **輸入資料**:
  - 正常任務 + 失敗任務
  - 多個失敗任務
- **預期結果**: 
  - ExceptionGroup 捕獲所有錯誤
  - 可分別處理各錯誤
  - 正常任務結果保留

## 4. 整合測試規格 (Integration Tests)

### 4.1 API 端點測試

#### API-IC-101-IT: API 端點基本功能測試
- **優先級**: P0
- **測試目的**: 驗證 POST /api/v1/index-calculation 端點正常運作
- **測試方法**:
  1. 發送有效請求
  2. 驗證回應狀態碼
  3. 驗證回應格式
  4. 驗證 Bubble.io 固定 schema
- **輸入資料**:
  ```json
  {
    "resume": "Python developer with 5 years experience",
    "job_description": "Looking for Python developer",
    "keywords": ["Python", "API", "Docker"]
  }
  ```
- **預期結果**: 
  - HTTP 200 OK
  - 所有必填欄位存在
  - timing_breakdown 為空物件（生產環境）

#### API-IC-102-IT: 快取行為整合測試
- **優先級**: P0
- **測試目的**: 驗證快取在 API 層級的正確行為
- **測試方法**:
  1. 發送相同請求兩次
  2. 檢查 cache_hit 欄位
  3. 比較處理時間
- **輸入資料**:
  - 相同的履歷和職缺描述
  - 連續發送 3 次
- **預期結果**: 
  - 第 1 次：cache_hit = false
  - 第 2-3 次：cache_hit = true
  - Cache hit 時間 < 50ms

#### API-IC-103-IT: 輸入驗證測試
- **優先級**: P0
- **測試目的**: 驗證各種無效輸入的錯誤處理
- **測試方法**:
  1. 空履歷測試
  2. 過短文本測試 (< 100 字元)
  3. 超長文本測試 (> 500KB)
  4. 無效 JSON 格式
- **輸入資料**:
  - {"resume": "", ...}
  - {"resume": "short", ...}
  - {"resume": "x" * 600000, ...}
- **預期結果**: 
  - HTTP 400 Bad Request
  - 明確的錯誤訊息
  - 錯誤日誌記錄

### 4.2 外部服務整合測試

#### API-IC-104-IT: Azure OpenAI 服務失敗測試
- **優先級**: P0
- **測試目的**: 驗證 embedding 服務失敗時的錯誤處理
- **測試方法**:
  1. Mock Azure OpenAI 服務
  2. 模擬各種失敗情況
  3. 驗證重試機制
- **輸入資料**:
  - 模擬 429 Rate Limit
  - 模擬 500 Internal Error
  - 模擬網路超時
- **預期結果**: 
  - HTTP 503 Service Unavailable
  - 重試 3 次後失敗
  - 錯誤日誌儲存

#### API-IC-105-IT: 並發請求處理測試
- **優先級**: P1
- **測試目的**: 驗證高並發請求下的系統穩定性
- **測試方法**:
  1. 同時發送 10 個請求
  2. 不同內容避免快取
  3. 監控資源使用
- **輸入資料**:
  - 10 個不同的履歷/職缺組合
- **預期結果**: 
  - 所有請求成功 (100%)
  - 無競爭條件
  - 記憶體使用 < 2GB

#### API-IC-106-IT: 大文檔處理測試
- **優先級**: P1
- **測試目的**: 驗證大文檔的處理能力和效能
- **測試方法**:
  1. 測試 10KB 文檔（約 500 個中文字）
  2. 測試 20KB 文檔（約 1000 個中文字）
  3. 測試 30KB 文檔（約 2000 個中文字，實際上限）
- **輸入資料**:
  - 標準履歷 (10KB)
  - 詳細履歷 (20KB)
  - 最大履歷 (30KB)
- **預期結果**: 
  - 成功處理
  - P95 < 2秒
  - 無記憶體溢出

### 4.3 監控和統計測試

#### API-IC-107-IT: 服務統計端點測試
- **優先級**: P2
- **測試目的**: 驗證 GET /api/v1/index-calculation/stats 端點
- **測試方法**:
  1. 執行多個計算請求
  2. 調用統計端點
  3. 驗證統計資料正確性
- **輸入資料**:
  - GET /api/v1/index-calculation/stats
- **預期結果**: 
  - 正確的統計數據
  - cache_hit_rate 計算正確
  - average_processing_time 合理

#### API-IC-108-IT: 跨語言內容測試
- **優先級**: P1
- **測試目的**: 驗證中英文混合內容的處理
- **測試方法**:
  1. 純中文測試
  2. 純英文測試
  3. 中英混合測試
- **輸入資料**:
  - 中文履歷 + 英文職缺
  - 中英混合關鍵字
- **預期結果**: 
  - 正確處理
  - 無編碼錯誤
  - 相似度計算正確

## 5. 效能測試規格 (Performance Tests)

### 效能測試執行策略（2分鐘內完成）

#### 執行時間表
| 時間段 | 測試項目 | 說明 |
|---------|----------|------|
| 0:00-0:30 | 基準 + 快取測試（並行） | API-IC-201-PT 和 API-IC-202-PT |
| 0:30-1:30 | 負載測試 | API-IC-203-PT（主要測試） |
| 1:30-2:00 | 記憶體 + 快取限制（並行） | API-IC-204-PT 和 API-IC-205-PT |

#### 優化策略

1. **並行執行機制**
   ```bash
   # 使用 GNU parallel 或 Python multiprocessing
   parallel ::: \
     "pytest test_benchmark.py" \
     "pytest test_cache.py" \
     "pytest test_memory.py"
   ```

2. **樣本數量優化**
   - 使用統計抽樣確保 95% 信心區間
   - 基準測試：100 次（誤差範圍 ±10%）
   - 快取測試：50 次（足以驗證命中率）
   - 負載測試：60 秒漸進式加載

3. **測試資料預處理**
   ```python
   # 預先生成所有測試資料
   test_data = generate_test_data()
   cache_test_data_in_memory(test_data)
   ```

4. **快速指標收集**
   - 使用非阻塞 I/O
   - 即時計算百分位數
   - 延遲詳細報告生成

5. **失敗快速機制**
   ```python
   # 若基本指標不達標，立即中止
   if p95_response_time > 2000:  # ms
       fail_fast("Performance regression detected")
   ```

### 5.1 基準效能測試

#### API-IC-201-PT: 響應時間基準測試（30秒）
- **優先級**: P0
- **測試目的**: 建立效能基準並驗證是否達到目標
- **測試方法**:
  1. 使用標準測試資料集
  2. 執行 100 次請求（統計抽樣）
  3. 計算各百分位數
- **輸入資料**:
  - 小型文檔 (< 1KB)
  - 中型文檔 (1-10KB)
  - 大型文檔 (10-30KB)
- **預期結果**: 
  - P50 < 1000ms
  - P95 < 2000ms
  - P99 < 3000ms

#### API-IC-202-PT: 快取效能測試（30秒）
- **優先級**: P0
- **測試目的**: 驗證快取對效能的提升效果
- **測試方法**:
  1. 預熱 20 個常用查詢
  2. 執行 50 次混合查詢
  3. 比較 cache hit/miss 時間
- **輸入資料**:
  - 5 種不同內容
  - 混合新舊查詢
- **預期結果**: 
  - Cache hit < 50ms
  - Cache miss: 1-2秒
  - Hit rate > 60%

### 5.2 負載測試

#### API-IC-203-PT: 高並發負載測試（60秒）
- **優先級**: P0
- **測試目的**: 驗證系統在高負載下的穩定性
- **測試方法**:
  1. 使用 Locust（更快的啟動時間）
  2. 漸進式負載：0-30秒達到 50 QPS
  3. 維持 30 秒高負載
  4. 即時監控關鍵指標
- **輸入資料**:
  - 50 個並發用戶
  - 預生成的隨機內容池
- **預期結果**: 
  - 成功率 > 95%
  - 無記憶體洩漏跡象
  - CPU < 80%
  - P95 < 3秒

#### API-IC-204-PT: 記憶體使用效率測試（30秒）
- **優先級**: P1
- **測試目的**: 驗證記憶體使用效率和無洩漏
- **測試方法**:
  1. 快速執行 200 個不同請求
  2. 每 5 秒採樣記憶體使用
  3. 強制 GC 後檢查
- **輸入資料**:
  - 200 個唯一內容
  - 混合大小文檔
- **預期結果**: 
  - 峰值 < 2GB
  - GC 後回收 > 50%
  - 無明顯洩漏

#### API-IC-205-PT: 快取大小限制測試（30秒）
- **優先級**: P1
- **測試目的**: 驗證快取大小限制和 LRU 淘汰效率
- **測試方法**:
  1. 設定快取上限 100（加速測試）
  2. 快速加入 200 個項目
  3. 驗證 LRU 淘汰行為
- **輸入資料**:
  - 200 個預生成請求
- **預期結果**: 
  - 快取大小保持 100
  - 正確的 LRU 行為
  - 淘汰效能 < 10ms

## 6. 端對端測試規格 (End-to-End Tests)

### 6.1 完整流程測試

#### API-IC-301-E2E: 完整工作流程測試
- **優先級**: P0
- **測試目的**: 驗證從輸入到輸出的完整流程
- **測試方法**:
  1. 使用真實履歷資料
  2. 模擬完整使用情境
  3. 驗證所有功能
- **輸入資料**:
  - 真實文字履歷（純文字或 HTML 格式）
  - 真實職缺描述（純文字或 HTML 格式）
  - 實際關鍵字列表（陣列或逗號分隔字串）
- **預期結果**: 
  - 相似度分數合理
  - 關鍵字匹配正確
  - 回應格式符合 Bubble.io

#### API-IC-302-E2E: 錯誤恢復測試
- **優先級**: P1
- **測試目的**: 驗證系統的錯誤恢復和健壯性
- **測試方法**:
  1. 模擬各種錯誤
  2. 驗證恢復機制
  3. 確認不影響其他請求
- **輸入資料**:
  - 網路中斷
  - 服務暫時不可用
  - 快取失效
- **預期結果**: 
  - 錯誤被優雅處理
  - 系統自動恢復
  - 錯誤日誌完整

### 6.2 監控和可觀測性測試

#### API-IC-303-E2E: 監控和日誌整合測試
- **優先級**: P2
- **測試目的**: 驗證監控和日誌系統的完整性
- **測試方法**:
  1. 執行各種操作
  2. 檢查監控指標
  3. 驗證日誌記錄
- **輸入資料**:
  - 正常請求
  - 錯誤請求
  - 效能壓力
- **預期結果**: 
  - 所有指標被記錄
  - 錯誤日誌儲存到 Blob
  - /stats 端點資料正確

## 7. 測試資料集

### 7.1 標準測試資料
測試資料位於 `tests/fixtures/index_calculation/` 目錄：

#### 基本測試資料
- `standard_resumes.json` - 10 種典型履歷（涵蓋不同職位和經驗）
- `standard_job_descriptions.json` - 10 種典型職缺描述
- `standard_keywords.json` - 常用技能關鍵字列表

#### 邊界案例資料
- `edge_cases.json` - 包含：
  - 空內容
  - 特殊字元
  - 超長文本
  - HTML/Script 注入
  - 編碼問題

### 7.2 效能測試資料

#### 文檔大小分類
- **小型文檔** (< 1KB)：簡短履歷摘要（約 50-100 個中文字）
- **中型文檔** (1-10KB)：標準履歷（約 500-1000 個中文字）
- **大型文檔** (10-30KB)：詳細履歷（約 1500-2000 個中文字）

### 7.3 跨語言測試資料
- `chinese_resumes.json` - 純中文履歷
- `english_resumes.json` - 純英文履歷
- `mixed_language.json` - 中英混合內容

## 8. 測試環境要求

### 8.1 硬體要求
- **CPU**: 最低 2 核心，建議 4 核心以上
- **RAM**: 最低 4GB，建議 8GB 以上
- **儲存**: 10GB 可用空間
- **網路**: 穩定的網路連線 (Azure OpenAI 需要)

### 8.2 軟體要求
- **Python**: 3.11.8 (專案指定版本)
- **Docker**: 20.10+ (整合測試用)
- **測試框架**:
  - pytest >= 7.4.0
  - pytest-asyncio >= 0.21.0
  - pytest-cov >= 4.1.0
- **效能測試工具**:
  - locust >= 2.15.0 (負載測試)
  - memory-profiler >= 0.61.0 (記憶體分析)

### 8.3 環境變數設定
```bash
# 測試環境配置
export ENVIRONMENT=test
export INDEX_CALC_CACHE_ENABLED=true
export INDEX_CALC_CACHE_TTL_MINUTES=60
export LIGHTWEIGHT_MONITORING=true

# Azure OpenAI 配置
export AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com
export AZURE_OPENAI_API_KEY=test-key
```

## 9. 測試執行策略

### 9.1 執行順序
1. **單元測試** - 必須 100% 通過才能繼續
2. **整合測試** - 必須 100% 通過才能繼續
3. **效能測試** - 必須達到效能基準
4. **端對端測試** - P0 測試必須通過

### 9.2 執行命令
```bash
# 單元測試
pytest tests/unit/test_index_calculation_v2.py -v --cov=src.services.index_calculation_v2

# 整合測試
pytest tests/integration/test_index_calculation_v2_api.py -v

# 效能測試（2分鐘快速執行）
./test/scripts/run_index_calculation_v2_performance.sh

# 或分別執行：
# 基準和快取測試（並行，30秒）
pytest tests/performance/test_index_calculation_v2_benchmark.py -v &
pytest tests/performance/test_index_calculation_v2_cache.py -v &
wait

# 負載測試（60秒）
locust -f tests/performance/test_index_calculation_v2_load.py --headless -u 50 -r 10 -t 60s

# 其他效能測試（並行，30秒）
pytest tests/performance/test_index_calculation_v2_memory.py -v &
pytest tests/performance/test_index_calculation_v2_cache_limit.py -v &
wait

# 完整測試套件
./test/scripts/run_index_calculation_v2_tests.sh
```

### 9.3 通過標準
- **單元測試覆蓋率**: >= 90%
- **P0 測試**: 100% 通過
- **P1 測試**: >= 95% 通過
- **效能基準**: 符合技術規格要求

## 10. 測試報告要求

### 10.1 報告內容
每次測試執行必須產生以下報告：

1. **測試覆蓋率報告**
   - 程式碼覆蓋率
   - 分支覆蓋率
   - 未覆蓋程式碼分析

2. **測試結果摘要**
   - 通過/失敗統計
   - 各優先級通過率
   - 執行時間分析

3. **效能指標報告**
   - 響應時間分布 (P50/P95/P99)
   - 資源使用情況
   - 與基準的對比

4. **失敗分析**
   - 失敗測試詳情
   - 錯誤日誌
   - 修復建議

### 10.2 報告格式
```
Index Calculation V2 測試報告
================================
測試日期: YYYY-MM-DD
測試版本: v2.0.0
執行環境: [development/staging/production]

摘要:
- 總測試數: XXX
- 通過: XXX
- 失敗: XXX
- 通過率: XX%
- 覆蓋率: XX%

[詳細內容...]
```

## 11. 效能測試快速執行腳本

### 11.1 完整 2 分鐘測試腳本
```bash
#!/bin/bash
# run_index_calculation_v2_performance.sh
# 在 2 分鐘內完成所有效能測試

echo "=== Index Calculation V2 效能測試 (2分鐘) ==="
echo "開始時間: $(date)"

# 第一階段：基準和快取測試（30秒）
echo "\n[0:00-0:30] 執行基準和快取測試..."
(
    pytest tests/performance/test_ic_benchmark.py::test_response_time_baseline -v --tb=short &
    pytest tests/performance/test_ic_cache.py::test_cache_performance -v --tb=short &
    wait
) &
PHASE1_PID=$!

# 等待 30 秒
sleep 30
kill -0 $PHASE1_PID 2>/dev/null && kill -TERM $PHASE1_PID

# 第二階段：負載測試（60秒）
echo "\n[0:30-1:30] 執行高並發負載測試..."
locust -f tests/performance/test_ic_load.py \
    --headless \
    --users 50 \
    --spawn-rate 10 \
    --run-time 60s \
    --only-summary

# 第三階段：記憶體和快取限制測試（30秒）
echo "\n[1:30-2:00] 執行記憶體和快取限制測試..."
(
    pytest tests/performance/test_ic_memory.py::test_memory_efficiency -v --tb=short &
    pytest tests/performance/test_ic_cache_limit.py::test_lru_performance -v --tb=short &
    wait
) &
PHASE3_PID=$!

# 等待 30 秒
sleep 30
kill -0 $PHASE3_PID 2>/dev/null && kill -TERM $PHASE3_PID

echo "\n結束時間: $(date)"
echo "測試完成！請查看上方結果。"
```

### 11.2 測試結果快速驗證
```python
# tests/performance/quick_validate.py
import json
from datetime import datetime

def validate_2min_performance_results(results_file):
    """快速驗證 2 分鐘測試結果是否達標"""
    with open(results_file) as f:
        results = json.load(f)
    
    # 驗證核心指標
    checks = {
        "P50 < 1秒": results["p50"] < 1000,
        "P95 < 2秒": results["p95"] < 2000,
        "Cache Hit Rate > 60%": results["cache_hit_rate"] > 0.6,
        "成功率 > 95%": results["success_rate"] > 0.95,
        "記憶體 < 2GB": results["peak_memory_mb"] < 2048
    }
    
    print("\n=== 效能測試結果 (執行時間: 2分鐘) ===")
    all_passed = True
    for check, passed in checks.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{check}: {status}")
        all_passed &= passed
    
    return all_passed
```

## 12. 測試案例總結

### 12.1 測試分布統計

| 模組 | 單元測試 | 整合測試 | 效能測試 | 端對端測試 | 總計 |
|------|----------|----------|----------|------------|------|
| 服務架構 | 2 | - | - | - | 2 |
| 快取機制 | 2 | 1 | 2 | - | 5 |
| 核心功能 | 4 | 3 | 1 | 1 | 9 |
| 並行處理 | 2 | 1 | 1 | - | 4 |
| 錯誤處理 | - | 2 | - | 1 | 3 |
| 監控統計 | - | 1 | - | 1 | 2 |
| 跨語言支援 | - | 1 | - | - | 1 |
| **總計** | **10** | **8** | **5** | **3** | **26** |

### 12.2 優先級分布

| 優先級 | 測試數量 | 佔比 |
|----------|----------|------|
| P0 (Critical) | 12 | 46.2% |
| P1 (High) | 11 | 42.3% |
| P2 (Medium) | 3 | 11.5% |
| P3 (Low) | 0 | 0% |

### 12.3 測試覆蓋完整性

- ✅ **所有核心功能**均有對應測試案例
- ✅ **所有 API 端點**均有整合測試覆蓋
- ✅ **效能指標**均有對應的效能測試
- ✅ **錯誤情境**均有處理和恢復測試
- ✅ **Bubble.io 相容性**有專門測試驗證
- ✅ **2分鐘快速效能測試**確保快速回饋

---

**文檔版本**: 1.3.0  
**建立日期**: 2025-08-02  
**最後更新**: 2025-08-02  
**維護團隊**: Backend Team

### 更新記錄
- v1.3.0 (2025-08-02)
  - 根據現有實作調整測試範圍：
    - API-IC-005-UT：改為整合測試，降為 P2（NLP 函數本身不需測試）
    - API-IC-006-UT：改為參數一致性測試，改為 P1
    - API-IC-007-UT：明確定義複數形式和大小寫匹配邏輯
    - API-IC-008-UT：針對 TinyMCE 輸出格式測試
    - API-IC-301-E2E：明確輸入為文字格式，非 PDF
- v1.2.0 (2025-08-02)
  - 調整大文檔測試上限為 30KB（約 2000 個中文字）
  - 新增 2 分鐘快速效能測試執行策略
  - 優化負載測試時間從 5 分鐘縮短到 60 秒
  - 提供完整的測試執行腳本