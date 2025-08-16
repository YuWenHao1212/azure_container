# Index Calculation and Gap Analysis API 測試規格文檔

## 文檔資訊
- **版本**: 1.0.11
- **建立日期**: 2025-08-03
- **最後更新**: 2025-08-15
- **維護者**: 測試團隊
- **測試總數**: 62 個（27 單元測試 + 31 整合測試 + 2 效能測試 + 2 E2E 測試）
- **更新說明**: 
  - v1.0.2: 新增效能測試快速執行指南
  - v1.0.3: 更新效能測試實作（平行執行、P95 20個樣本）
  - v1.0.4: 移除 API-GAP-004-E2E（與 001 功能重複）
  - v1.0.5: 效能測試重新分類 - 移除 3 個偽效能測試，移至整合測試 (PT: 5→2, IT: 14→17)
  - v1.0.6: 效能測試重新分類 - 移動 3 個測試至整合測試
  - v1.0.7: 新增錯誤處理測試案例 - 新增 10 個整合測試 (IT: 17→27)
  - v1.0.8: 合併效能測試 - 合併 API-GAP-001-PT 和 API-GAP-002-PT，同時計算 P50/P95 (PT: 2→1)
  - v1.0.9: 移除部分成功測試 - 刪除 API-GAP-003-E2E，與產品策略「完全失敗」一致 (E2E: 3→2)
  - v1.0.10: 新增 Resume Structure Analysis 測試案例 (UT: 20→25, IT: 27→30)
  - v1.0.11: 新增 Course Availability Check 測試案例 - 7 個單元測試 + 4 個整合測試 + 1 個效能測試 (UT: 25→27, IT: 30→31, PT: 1→2)

## 重要測試約束 ⚠️

### 最小長度要求
- **Job Description**: 必須 ≥ 200 字元
- **Resume**: 必須 ≥ 200 字元（建議使用 HTML 格式）
- 所有測試資料都必須滿足此要求（除非特別測試長度驗證）

### 測試執行時間限制
- **單元測試 + 整合測試**: 必須在 20 秒內完成
- **效能測試 + 端對端測試**: 必須在 90 秒內完成

### 程式碼品質要求 🚨
- **所有測試程式碼必須通過 Ruff 檢查**
  - 執行 `ruff check test/ --line-length=120` 必須顯示 "All checks passed!"
  - 不得有任何 Ruff 錯誤或警告
  - 遵循專案的 `pyproject.toml` 中定義的 Ruff 規則
- **撰寫測試前請先確認 Ruff 配置**
  - 確認 `pyproject.toml` 中的 `[tool.ruff.lint.per-file-ignores]` 設定
  - 測試檔案允許的例外：S101 (assert), RUF001/RUF002 (中文全形符號), S105 (測試密鑰)

## 1. 測試案例編號系統

### 1.1 編號格式
```
API-GAP-[序號]-[類型]

範例: API-GAP-001-UT
```

### 1.2 編號分配
| 序號範圍 | 測試類型 | 數量 | 說明 |
|----------|----------|------|------|
| 001-020 | 單元測試(UT) | 20 | 服務層單元測試 |
| 001-027 | 整合測試(IT) | 27 | API 端點整合測試（含錯誤處理） |
| 001-001 | 效能測試(PT) | 1 | 真實 Azure 服務效能測試 |
| 001-002 | 端對端測試(E2E) | 2 | 完整流程測試 |

**重要變更說明**:
- **效能測試重新分類**: API-GAP-003/004/005-PT 已移至整合測試 (API-GAP-015/017/016-IT)
- **分類原因**: 這些測試驗證 Python 應用層行為（資源池、快取），而非 Azure 服務效能
- **實際執行**: 效能測試現在只執行 1 個真實的 Azure OpenAI 效能測試 (同時計算 P50/P95)

## 2. 測試案例總覽

### 2.1 單元測試 (20個)

#### API-GAP-001-UT: CombinedAnalysisServiceV2 初始化測試
- **名稱**: 統一分析服務初始化驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證服務正確初始化，依賴注入正確
- **測試內容**: 測試服務實例創建、配置參數載入、依賴注入
- **測試資料**: 
  ```yaml
  input:
    enable_partial_results: true
    cache_ttl_minutes: 60
  expected:
    service_initialized: true
    dependencies_injected: true
  ```
- **判斷標準**: 
  - 服務成功初始化
  - 配置正確載入
  - 依賴服務可用

#### API-GAP-002-UT: ResourcePoolManager 初始化測試
- **名稱**: 資源池管理器初始化和預建立
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證資源池預建立最小數量客戶端
- **測試內容**: 初始化 ResourcePoolManager、呼叫 initialize()、驗證預建立客戶端
- **測試步驟**:
  1. 初始化 ResourcePoolManager(min_size=2, max_size=10)
  2. 呼叫 initialize()
  3. 驗證池中有 2 個預建立的客戶端
- **判斷標準**: 
  - 資源池正確初始化
  - 池中有正確數量的預建立客戶端
  - 客戶端狀態正常

#### API-GAP-003-UT: 資源池獲取客戶端測試
- **名稱**: 從資源池獲取和歸還客戶端
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證客戶端正確獲取和歸還
- **測試內容**: 使用 get_client() context manager、驗證客戶端有效性、確認歸還機制
- **測試步驟**:
  1. 使用 get_client() context manager
  2. 驗證獲得有效客戶端
  3. 退出 context 後驗證客戶端歸還
- **判斷標準**: 
  - 成功獲取有效客戶端
  - 客戶端可正常使用
  - 退出後客戶端正確歸還池中

#### API-GAP-004-UT: 資源池達到上限測試
- **名稱**: 資源池達到最大容量時的行為
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證達到 max_size 時等待可用客戶端
- **測試內容**: 填滿資源池、嘗試獲取額外客戶端、驗證等待行為
- **判斷標準**: 
  - 資源池達到上限時阻塞
  - 客戶端釋放後可繼續獲取
  - 無資源洩漏

#### API-GAP-005-UT: 並行執行 Phase 1 測試
- **名稱**: Phase 1 並行 embedding 生成
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 resume 和 JD embedding 並行生成
- **測試內容**: 測試 TaskGroup 並行執行 resume 和 JD embedding 生成
- **測試資料**:
  ```yaml
  input:
    resume: "<h3>Senior Software Engineer</h3><p>10+ years of experience in full-stack development, specializing in <strong>Python</strong>, <strong>FastAPI</strong>, and microservices architecture.</p><ul><li>Led multiple teams in delivering scalable enterprise solutions</li><li>Expertise in cloud technologies (AWS, Azure)</li><li>Containerization (Docker, Kubernetes)</li><li>DevOps practices</li></ul><p>Strong background in system design and performance optimization.</p>" # 400+ chars HTML
    job_description: "We are seeking a Senior Python Developer with 8+ years of experience to join our growing team. The ideal candidate will have strong expertise in FastAPI, microservices, and cloud platforms. Required skills include Python, FastAPI, Docker, Kubernetes, AWS/Azure, CI/CD, and database design. Experience with React and frontend technologies is a plus." # 350+ chars
  ```
- **判斷標準**: 
  - 兩個 embedding 任務並行執行
  - 執行時間小於串行執行
  - 結果正確返回

#### API-GAP-006-UT: 並行執行 Phase 2 測試
- **名稱**: Phase 2 Index 計算和 Gap 前置準備並行
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 Index 計算與 Gap context 準備並行執行
- **測試內容**: 測試 Index 計算和 Gap Analysis 前置準備的並行處理
- **判斷標準**: 
  - 兩個任務並行執行
  - 正確傳遞依賴數據
  - 無競爭條件

#### API-GAP-007-UT: 並行執行 Phase 3 測試
- **名稱**: Phase 3 Gap Analysis 使用 Index 結果
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 Gap Analysis 正確接收和使用 Index 結果
- **測試內容**: 測試 Gap Analysis 接收 Index 結果並正確處理
- **判斷標準**: 
  - 正確接收 matched_keywords
  - 正確接收 missing_keywords
  - Gap Analysis 結果包含關鍵字資訊

#### API-GAP-008-UT: AdaptiveRetryStrategy 初始化測試
- **名稱**: 自適應重試策略配置驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證不同錯誤類型的重試配置正確
- **測試內容**: 測試各種錯誤類型的重試策略配置
- **測試方法**:
  1. 初始化 AdaptiveRetryStrategy
  2. 檢查各錯誤類型的配置值
  3. 驗證策略物件正確創建
- **判斷標準**: 
  - empty_fields: 最多 2 次重試，線性退避，1 秒延遲
  - timeout: 最多 1 次重試，指數退避，0.5 秒基礎延遲
  - rate_limit: 最多 3 次重試，指數退避，5 秒基礎延遲，最大 20 秒
  - validation: 不重試（0 次）
  - general: 最多 2 次重試，線性退避，1 秒延遲

#### API-GAP-009-UT: 空欄位錯誤重試測試 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-019-UT (通用重試機制錯誤分類)
- **名稱**: empty_fields 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 Gap Analysis 回應中空欄位錯誤的重試行為
- **測試內容**: 模擬 Gap Analysis 回應中 CoreStrengths、KeyGaps 等必要欄位為空的情況，驗證重試邏輯
- **測試方法**:
  1. 模擬 Gap Analysis 服務返回空欄位響應
  2. 觸發 "Empty fields detected" 錯誤
  3. 驗證重試配置和行為
- **判斷標準**: 
  - 最多重試 2 次
  - 使用線性退避策略 (0.1秒基礎延遲)
  - 重試成功後返回正確結果

#### API-GAP-010-UT: 超時錯誤重試測試 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-017-UT (通用外部服務錯誤分類)
- **名稱**: timeout 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證超時錯誤使用指數退避，基礎延遲 0.5 秒
- **測試內容**: 模擬超時錯誤，驗證重試策略
- **判斷標準**: 
  - 最多重試 1 次
  - 使用指數退避策略
  - 基礎延遲 0.5 秒

#### API-GAP-011-UT: 速率限制錯誤重試測試 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERR-017-UT (通用外部服務錯誤分類)
- **名稱**: rate_limit 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證速率限制錯誤使用指數退避，基礎延遲 5 秒
- **測試內容**: 模擬速率限制錯誤，驗證重試行為
- **判斷標準**: 
  - 最多重試 3 次
  - 使用指數退避策略
  - 基礎延遲 5 秒，最大 20 秒

#### API-GAP-012-UT: Gap Analysis 失敗處理測試
- **名稱**: Gap Analysis 失敗時整個 API 失敗
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 Gap Analysis 失敗時整個 API 應該失敗，而不是返回部分結果
- **測試內容**: 模擬 Gap Analysis 服務失敗，驗證 API 正確拋出錯誤
- **設計理由**: 根據產品需求，Gap Analysis 是核心功能，失敗時應該讓整個 API 失敗，確保用戶得到完整且有意義的結果
- **判斷標準**: 
  - Gap Analysis 失敗時拋出相應錯誤
  - 不返回部分結果 (disable partial results)
  - **錯誤規格明確定義**：
    - HTTP 狀態碼：502 (Bad Gateway - 外部服務錯誤)
    - Error Code："EXTERNAL_SERVICE_ERROR" 
    - Error Message："Gap Analysis service is temporarily unavailable"
    - **與 API-GAP-013-UT 差異**：
      - API-GAP-012-UT：只有 Gap Analysis 失敗 → 502 錯誤
      - API-GAP-013-UT：Index + Gap 都失敗 → BaseExceptionGroup + 500 錯誤

#### API-GAP-013-UT: 完全失敗處理測試
- **名稱**: Index 和 Gap 都失敗的處理
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證兩個服務都失敗時正確拋出錯誤
- **測試內容**: 模擬 Index 和 Gap Analysis 都失敗
- **判斷標準**: 
  - 拋出 BaseExceptionGroup 類型錯誤 (Python 3.11+ 的異常組)
  - 錯誤組包含兩個子錯誤：Index 計算錯誤和 Gap Analysis 錯誤
  - 錯誤訊息明確標示兩個服務的失敗原因
  - HTTP 狀態碼為 500 (內部伺服器錯誤)
  - 無部分結果返回

#### API-GAP-014-UT: 服務依賴驗證測試
- **名稱**: Gap Analysis 接收 Index 結果依賴
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 matched_keywords 和 missing_keywords 正確傳遞
- **測試內容**: 驗證 Index 結果正確傳遞給 Gap Analysis
- **判斷標準**: 
  - matched_keywords 正確傳遞
  - missing_keywords 正確傳遞
  - Gap Analysis 使用這些資訊

#### API-GAP-015-UT: 關鍵字覆蓋計算測試
- **名稱**: 關鍵字匹配結果傳遞給 Gap Analysis
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 covered_keywords 和 missed_keywords 正確計算和傳遞
- **測試內容**: 測試關鍵字覆蓋率計算邏輯
- **判斷標準**: 
  - 覆蓋率計算準確
  - 關鍵字分類正確
  - 大小寫不敏感匹配

#### API-GAP-016-UT: 錯誤分類器測試
- **名稱**: 錯誤類型分類邏輯驗證
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 _classify_gap_error 正確識別錯誤類型
- **測試內容**: 測試各種錯誤類型的分類邏輯
- **判斷標準**: 
  - 正確識別各種錯誤類型
  - 返回對應的錯誤分類
  - 未知錯誤歸類為 general

#### API-GAP-017-UT: 統計追蹤測試
- **名稱**: 服務統計資訊追蹤
- **優先級**: P2
- **類型**: 單元測試
- **測試目標**: 驗證 total_requests、partial_successes 等統計正確更新
- **測試內容**: 測試服務統計資訊的收集和更新
- **判斷標準**: 
  - 請求計數正確增加
  - 成功/失敗統計準確
  - 處理時間記錄正確

#### API-GAP-018-UT: HTML 文本處理差異測試
- **名稱**: Embedding 和 LLM 的差異化文本處理
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 Embedding 使用清理文本，LLM 保留 HTML 結構
- **測試內容**: 測試 HTML 內容的差異化處理
- **判斷標準**: 
  - Embedding 接收純文字
  - LLM 接收完整 HTML
  - 處理結果符合預期

#### API-GAP-019-UT: TaskGroup 異常處理測試
- **名稱**: Python 3.11 TaskGroup ExceptionGroup 處理
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證並行任務失敗時的異常聚合處理
- **測試內容**: 測試 TaskGroup 中多個任務失敗的處理
- **判斷標準**: 
  - ExceptionGroup 正確聚合錯誤
  - 可存取所有子異常
  - 錯誤訊息清晰

#### API-GAP-020-UT: 服務清理測試
- **名稱**: 異常時的資源清理驗證
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證錯誤發生時資源池客戶端正確歸還
- **測試內容**: 測試異常情況下的資源清理
- **判斷標準**: 
  - 客戶端正確歸還資源池
  - 無資源洩漏
  - 資源池狀態正常

### 2.2 整合測試 (31個)

#### API-GAP-001-IT: API 端點基本功能測試
- **名稱**: POST /api/v1/index-cal-and-gap-analysis 正常流程
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 API 端點正常運作，回應格式正確
- **測試內容**: 使用有效輸入測試完整的 API 流程
- **測試資料**:
  ```yaml
  request:
    resume: "<div><h2>Full Stack Developer</h2><p><strong>8+ years</strong> in software development</p><h3>Expertise</h3><ul><li>Python, FastAPI, Django</li><li>React, JavaScript</li><li>Microservices architecture</li><li>RESTful APIs</li></ul><h3>Cloud & DevOps</h3><ul><li>AWS, Azure</li><li>Docker, Kubernetes</li><li>CI/CD pipelines</li></ul><p>Led development teams and delivered enterprise-scale applications.</p></div>" # 380+ chars HTML
    job_description: "Looking for a Senior Full Stack Developer to join our innovative team. Must have 5+ years of experience with Python, FastAPI, and modern JavaScript frameworks. Required skills include Docker, Kubernetes, AWS, microservices, and database design. Experience with machine learning and data engineering is highly valued." # 320+ chars
    keywords: ["Python", "FastAPI", "React", "Docker", "Kubernetes", "AWS", "Microservices"]
    language: "en"
  expected:
    status: 200
    success: true
  ```
- **判斷標準**: 
  - 返回 200 狀態碼
  - **必要欄位**完整包含：
    - `success`: boolean (true)
    - `data.index_calculation`: object (匹配指數結果)
    - `data.gap_analysis`: object (差距分析結果)
    - `data.processing_time_ms`: number (處理時間)
    - `timestamp`: string (ISO格式時間戳)
  - 計算結果合理 (匹配指數 0-100，差距分析包含 CoreStrengths 和 KeyGaps)

#### API-GAP-002-IT: JD 長度驗證測試
- **名稱**: Job Description < 200 字元錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 JD 少於 200 字元時返回 422 錯誤 (Pydantic 驗證錯誤)
- **測試內容**: 測試短 Job Description 的錯誤處理
- **錯誤代碼說明**: 使用 422 因為這是 Pydantic 模型驗證失敗，請求格式正確但內容不符合驗證規則
- **判斷標準**: 
  - 返回 422 錯誤碼 (Unprocessable Entity)
  - 錯誤訊息明確指出 "Job description must be at least 200 characters"
  - 錯誤代碼為 VALIDATION_ERROR (統一驗證錯誤碼)

#### API-GAP-003-IT: Resume 長度驗證測試
- **名稱**: Resume < 200 字元錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 Resume 少於 200 字元時返回 422 錯誤 (Pydantic 驗證錯誤)
- **測試內容**: 測試短 Resume 的錯誤處理
- **測試資料**:
  ```yaml
  request:
    resume: "Software developer" # 只有 18 字元
    job_description: "We are seeking an experienced Senior Software Engineer to join our dynamic team. The ideal candidate will have 5+ years of experience in software development, strong programming skills in Python and JavaScript, and expertise in cloud technologies. Must be proficient in modern development practices." # 300+ chars
    keywords: ["Python", "JavaScript"]
  expected:
    status: 422
    error:
      code: "VALIDATION_ERROR"
      message: "Resume must be at least 200 characters"
  ```
- **錯誤代碼說明**: 使用 422 因為這是 Pydantic 模型驗證失敗，明確標示為 Resume 長度不足
- **判斷標準**: 
  - 返回 422 錯誤碼 (Unprocessable Entity)
  - 錯誤訊息明確指出 "Resume must be at least 200 characters"
  - 錯誤代碼為 VALIDATION_ERROR，詳細說明為 Resume 長度不足

#### API-GAP-004-IT: 邊界長度測試
- **名稱**: JD 和 Resume 正好 200 字元測試
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證正好 200 字元時正常處理
- **測試內容**: 測試邊界長度的處理
- **測試資料**:
  ```yaml
  request:
    resume: "Senior Software Engineer with 10 years of experience in full-stack development. Expert in Python, JavaScript, and cloud technologies. Strong leadership and communication skills. Proven track record.." # 正好 200 字元
    job_description: "Looking for Senior Developer with Python and JavaScript expertise. Must have experience with cloud platforms, databases, and modern frameworks. Team collaboration and problem solving skills required." # 正好 200 字元
    keywords: ["Python", "JavaScript", "Cloud"]
  expected:
    status: 200
    success: true
  ```
- **判斷標準**: 
  - 返回 200 狀態碼
  - 成功處理請求
  - 返回完整結果

#### API-GAP-005-IT: 關鍵字參數驗證測試
- **名稱**: keywords 參數格式驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 keywords 支援陣列和逗號分隔字串
- **測試內容**: 測試不同關鍵字格式的處理
- **測試步驟**:
  1. 測試陣列格式：["Python", "Docker", "AWS"]
  2. 測試逗號分隔："Python,Docker,AWS"
  3. 驗證兩種格式產生相同結果
- **判斷標準**: 
  - 陣列格式正常處理
  - 字串格式正常處理
  - 兩種格式結果一致

#### API-GAP-006-IT: 語言參數驗證測試
- **名稱**: language 參數驗證（只測試參數傳遞）
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證只接受 "en" 和 "zh-TW"，其他值返回錯誤
- **測試內容**: 測試無效語言參數的處理
- **測試資料**:
  ```yaml
  invalid_languages: ["fr", "ja", "ko", "es", "de"]
  expected:
    status: 422
    error:
      code: "VALIDATION_ERROR"
      message: "Unsupported language: {language}. Supported: en, zh-TW"
  ```
- **判斷標準**: 
  - 無效語言返回 422 (Pydantic 模型驗證使用 422 狀態碼) 
  - 錯誤代碼為 INVALID_LANGUAGE 
  - 錯誤訊息清晰

#### API-GAP-007-IT: Bubble.io 回應格式驗證
- **名稱**: 回應格式符合 Bubble.io 固定 schema
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證回應包含所有必要欄位且格式正確
- **測試內容**: 驗證 API 回應符合固定 schema
- **判斷標準**: 
  - success 欄位存在且為 boolean
  - data 欄位包含所有必要子欄位
  - timestamp 為 ISO 8601 格式

#### API-GAP-008-IT: Feature Flag 測試
- **名稱**: USE_V2_IMPLEMENTATION Feature Flag 驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 Feature Flag 控制 V2 實作啟用
- **測試內容**: 測試 Feature Flag 對服務行為的影響
- **測試步驟**:
  1. 設定 USE_V2_IMPLEMENTATION=true
  2. 發送請求
  3. 驗證使用 V2 服務（透過回應時間或監控事件）
- **判斷標準**: 
  - V2 服務正確啟用
  - 回應包含 V2 特定欄位
  - 監控事件記錄 V2 使用

#### API-GAP-009-IT: 完整失敗處理測試 
- **名稱**: Gap Analysis 失敗時的完整失敗策略
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證任一服務失敗時，整個 API 請求失敗
- **測試內容**: Mock Gap Analysis 失敗，驗證完整失敗處理
- **判斷標準**: 
  - API 回應狀態碼 502 (External Service Error)
  - 不返回部分結果 
  - 錯誤訊息明確指出失敗原因

#### API-GAP-010-IT: 服務超時處理測試
- **名稱**: 外部服務超時的錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 Azure OpenAI 超時時的重試和錯誤處理
- **測試內容**: Mock 服務超時，驗證重試機制
- **判斷標準**: 
  - 重試 1 次後成功或失敗
  - 超時錯誤返回 504
  - 錯誤訊息清晰

#### API-GAP-011-IT: 速率限制錯誤處理測試
- **名稱**: Azure OpenAI 速率限制處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證遇到速率限制時的重試策略
- **測試內容**: Mock 速率限制錯誤，驗證重試行為
- **判斷標準**: 
  - 返回 429 錯誤碼
  - 重試使用指數退避
  - 包含 Retry-After 資訊

#### API-GAP-012-IT: 處理時間元數據測試
- **名稱**: 回應包含處理時間分解
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證 V2 回應包含 processing_time_ms 和 service_timings
- **測試內容**: 驗證回應包含詳細的時間分析
- **判斷標準**: 
  - processing_time_ms 存在且合理
  - service_timings 包含各階段時間
  - 時間加總正確

#### API-GAP-013-IT: 大文檔處理測試
- **名稱**: 處理大型 JD 和 Resume
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證處理 10KB、20KB、30KB 文檔的能力
- **測試內容**: 使用不同大小的文檔測試處理能力
- **判斷標準**: 
  - 成功處理不超時
  - 記憶體使用合理
  - 處理時間符合預期

#### API-GAP-014-IT: 認證機制測試
- **名穨**: API Key 認證驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證支援 Header (X-API-Key) 和 Query (?code=) 認證
- **測試內容**: 測試不同認證方式
- **判斷標準**: 
  - Header 認證成功
  - Query 參數認證成功
  - 無效 key 返回 401

#### API-GAP-015-IT: 資源池重用率測試
- **名稱**: 資源池客戶端重用率 > 80%
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證資源池有效減少初始化開銷
- **測試方法**:
  1. Mock LLM 和 Embedding 服務
  2. 發送 100 個請求
  3. 檢查資源池統計
  4. 驗證 reuse_rate > 80%
- **注意事項**:
  - 此測試需要開啟資源池功能
  - 使用重複的測試資料來測試重用效果
  - Mock 服務避免真實 API 調用延遲
- **原始編號**: 原為 API-GAP-003-PT

#### API-GAP-016-IT: 資源池擴展測試
- **名稱**: 資源池動態擴展功能
- **優先級**: P2
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證資源池從 min_size 擴展到 max_size 的功能
- **測試方法**:
  1. Mock LLM 和 Embedding 服務
  2. 初始化資源池 (min_size=2, max_size=10)
  3. 並發發送 10 個請求
  4. 驗證資源池動態擴展到所需大小
  5. 驗證所有請求都成功處理
- **注意事項**:
  - 使用不同的測試資料觸發資源池擴展
  - 每個請求使用不同 ID 確保不會被資源池重用
  - Mock 服務避免真實 API 調用延遲
- **原始編號**: 原為 API-GAP-005-PT

#### API-GAP-017-IT: API 呼叫減少驗證
- **名稱**: 共享 Embedding 減少 API 呼叫 40-50%
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證相同輸入的重複請求減少 API 呼叫
- **測試方法**:
  1. Mock LLM 和 Embedding 服務，追蹤調用次數
  2. 發送相同請求 10 次
  3. 驗證 Embedding API 只被調用 1 次（或極少次數）
  4. 驗證快取命中率 > 80%
  5. 確認 API 呼叫減少 40% 以上
- **注意事項**:
  - 此測試專門驗證資源池快取效果
  - 必須使用完全相同的測試資料
  - Mock 服務需要準確追蹤調用計數
- **原始編號**: 原為 API-GAP-004-PT

#### API-GAP-018-IT: Rate Limit 重試策略測試
- **名稱**: Azure OpenAI 限流錯誤重試行為驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證遇到 429 錯誤時使用指數退避策略
- **測試內容**: Mock 429 錯誤，驗證重試行為和延遲時間
- **判斷標準**: 
  - 重試使用指數退避 (3s, 6s, 12s)
  - 最大延遲不超過 20 秒
  - 第 4 次失敗後拋出錯誤

#### API-GAP-019-IT: Retry-After Header 處理測試
- **名稱**: Azure OpenAI Retry-After 標頭優先使用驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證系統優先使用 Retry-After header 但限制在 20 秒內
- **測試內容**: Mock Retry-After header，驗證上限處理
- **判斷標準**: 
  - Retry-After > 20s 時使用 20s
  - Retry-After < 20s 時使用實際值
  - 日誌顯示 "capped at 20s"

#### API-GAP-020-IT: 超時錯誤快速重試測試
- **名稱**: 請求超時錯誤的快速重試行為
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證超時錯誤只重試 1 次，延遲 0.5 秒
- **測試內容**: Mock TimeoutError，驗證快速重試
- **判斷標準**: 
  - 只重試 1 次
  - 延遲時間約 0.5 秒
  - 第二次成功後正常返回

#### API-GAP-021-IT: 一般錯誤重試測試
- **名稱**: 一般服務錯誤的線性退避重試
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證一般錯誤重試 2 次，線性退避 1 秒
- **測試內容**: Mock 一般 Exception，驗證重試行為
- **判斷標準**: 
  - 重試 2 次（初始 + 1 次重試）
  - 線性退避 1 秒
  - 第 2 次失敗後拋出錯誤

#### API-GAP-022-IT: 驗證錯誤無重試測試
- **名稱**: 輸入驗證錯誤不觸發重試機制
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 ValueError（400 錯誤）立即失敗，不重試
- **測試內容**: Mock ValueError，驗證不重試
- **判斷標準**: 
  - 不重試，立即返回錯誤
  - 只有 1 次服務調用
  - 返回 400 錯誤碼

#### API-GAP-023-IT: 無部分結果測試
- **名稱**: 任何失敗都返回完全失敗（無部分結果）
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 Gap Analysis 失敗時不返回 Index 結果
- **測試內容**: Mock Gap Analysis 失敗，驗證無部分結果
- **判斷標準**: 
  - 整個請求失敗
  - 無部分資料返回
  - 錯誤訊息完整

#### API-GAP-024-IT: Retry-After 上限測試
- **名稱**: Retry-After 值超過 20 秒時的處理
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證系統將過長的 Retry-After 限制在 20 秒
- **測試內容**: 測試不同 Retry-After 值的處理
- **判斷標準**: 
  - 60s → 使用 20s
  - 15s → 使用 15s
  - -1 → 使用預設策略

#### API-GAP-025-IT: 錯誤分類器準確性測試
- **名稱**: 錯誤類型分類邏輯的完整驗證
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證各種錯誤被正確分類
- **測試內容**: 測試各種錯誤類型的分類
- **判斷標準**: 
  - TimeoutError → "timeout"
  - ValueError → "validation"
  - "rate limit" → "rate_limit"

#### API-GAP-026-IT: 重試統計追蹤測試
- **名稱**: AdaptiveRetryStrategy 統計資訊正確性
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 驗證重試統計正確記錄和計算
- **測試內容**: 驗證統計資訊的收集和計算
- **判斷標準**: 
  - retry_stats 計數正確
  - 成功率計算準確
  - get_stats() 返回完整

#### API-GAP-027-IT: 指數退避計算正確性測試
- **名稱**: 指數退避延遲時間計算驗證
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 驗證指數退避公式正確實作
- **測試內容**: 驗證指數退避計算邏輯
- **判斷標準**: 
  - 3 * (2^n) 公式正確
  - 最大延遲 20 秒限制
  - 計算結果準確

### 2.3 效能測試 (1個)

#### API-GAP-001-PT: 響應時間效能測試 + 關鍵字一致性驗證 (P50/P95)
- **名稱**: 驗證響應時間 SLA 並同時檢查關鍵字處理正確性
- **優先級**: P0
- **類型**: 效能測試（整合功能驗證）
- **測試目標**: 
  - 驗證 P50 < 20秒 和 P95 < 30秒 的 SLA 要求
  - 確保每個請求的關鍵字輸入輸出一致性
- **測試內容**: 
  - 使用唯一測試資料執行 20 個平行請求
  - 關閉資源池快取以測試真實效能
  - 計算完整響應時間分布
  - **新增**：每個請求同時驗證 `len(input_keywords) == len(covered) + len(missed)`
  - **新增**：確保 `set(input_keywords) == set(covered) ∪ set(missed)`
- **合併理由**: 
  - 整合原 API-GAP-001-PT、API-GAP-002-PT 和 API-IC-001-PT
  - 避免重複 API 調用，提高測試效率
  - 同時驗證效能和功能正確性
- **判斷標準**: 
  - **效能標準**：
    - P50 < 20 秒 (中位數響應時間)
    - P95 < 30 秒 (95百分位響應時間) 
    - 成功率 > 95%
    - 無 timeout 錯誤
  - **功能標準**：
    - 所有 20 個請求都滿足：輸出關鍵字 (covered + missed) = 輸入關鍵字列表
    - 無額外或遺失的關鍵字
    - 大小寫處理正確
  - 預估執行時間 < 80 秒

#### ~~API-GAP-002-PT: P95 響應時間測試~~ [已合併]
- **狀態**: ✅ 已合併至 API-GAP-001-PT
- **合併原因**: 與 API-GAP-001-PT 測試邏輯相同，合併後可同時計算 P50 和 P95，提高測試效率

#### API-GAP-003-PT: 資源池重用率測試 [已刪除]
- **狀態**: ❌ 已刪除 - 移至 API-GAP-015-IT
- **刪除原因**: 此測試驗證 Python 應用層行為，而非 Azure 服務性能，更適合作為整合測試
- **參考**: 請見 API-GAP-015-IT

#### API-GAP-004-PT: API 呼叫減少驗證 [已刪除]
- **狀態**: ❌ 已刪除 - 移至 API-GAP-017-IT
- **刪除原因**: 此測試驗證 Python 應用層的快取機制和資源池效果，而非 Azure 服務性能，更適合作為整合測試
- **參考**: 請見 API-GAP-017-IT

#### API-GAP-005-PT: 資源池擴展測試 [已刪除]
- **狀態**: ❌ 已刪除 - 移至 API-GAP-016-IT
- **刪除原因**: 此測試驗證 Python 應用層資源池擴展行為，而非 Azure 服務性能，更適合作為整合測試
- **參考**: 請見 API-GAP-016-IT

### 2.4 端對端測試 (2個)

#### API-GAP-001-E2E: 完整工作流程測試
- **名稱**: 從請求到回應的完整流程驗證
- **優先級**: P0
- **類型**: E2E測試
- **測試目標**: 使用真實 Azure API 驗證完整工作流程
- **測試內容**: 使用實際的履歷和職缺描述（各 500+ 字元）執行完整的差距分析流程
- **驗證項目**:
  - API 回應成功 (HTTP 200)
  - **核心欄位驗證**（簡化為三個必要欄位）：
    - `data.raw_similarity_percentage`: number (0-100) - 相似度分數
    - `data.keyword_coverage`: object - 關鍵字覆蓋資訊
    - `data.gap_analysis`: object - 差距分析結果
  - **實際處理時間測量**: 測試會記錄真實的 API 呼叫時間（預期 12-20 秒）
- **測試輸出摘要**:
  - 相似度分數：顯示實際的 similarity_percentage 值
  - 實際處理時間：測量並顯示真實的 API 處理時間
  - 核心欄位驗證：檢查三個必要欄位是否存在且有值 

### 回應範例

```json
{
  "success": true,
  "data": {
    "raw_similarity_percentage": 68,
    "similarity_percentage": 78,
    "keyword_coverage": {
      "total_keywords": 8,
      "covered_count": 3,
      "coverage_percentage": 38,
      "covered_keywords": ["Python", "FastAPI", "Docker"],
      "missed_keywords": ["React", "Kubernetes", "AWS", "CI/CD", "DevOps"]
    },
    "gap_analysis": {
      "CoreStrengths": "<ol><li>Strong Python backend expertise with FastAPI framework</li><li>8+ years of software engineering experience exceeding requirements</li><li>Leadership experience managing development teams</li></ol>",
      "KeyGaps": "<ol><li>Missing React frontend development experience</li><li>No demonstrated Kubernetes container orchestration skills</li><li>Lack of AWS cloud platform experience</li><li>No mention of CI/CD pipeline implementation</li></ol>",
      "QuickImprovements": "<ol><li>Add specific React projects or mention any frontend JavaScript experience</li><li>Include Docker experience and mention any container-related work</li><li>Highlight any cloud platform experience (Azure, GCP) as transferable skills</li><li>Add any automation or deployment pipeline experience</li></ol>",
      "OverallAssessment": "<p>The candidate shows strong backend development skills with 60% higher experience than required. However, significant gaps exist in frontend (React), DevOps (Kubernetes, CI/CD), and cloud (AWS) technologies. With a 38% keyword match, the candidate would need 3-6 months of focused learning to become competitive. Immediate resume improvements and highlighting transferable skills could increase match to 50-60%. Currently positioned as a backend specialist rather than full-stack developer.</p>",
      "SkillSearchQueries": [
        {
          "skill_name": "React",
          "skill_category": "TECHNICAL",
          "description": "Frontend framework for building interactive user interfaces required for full-stack role"
        },
        {
          "skill_name": "Kubernetes",
          "skill_category": "TECHNICAL",
          "description": "Container orchestration platform essential for modern DevOps practices"
        },
        {
          "skill_name": "AWS",
          "skill_category": "TECHNICAL",
          "description": "Cloud platform knowledge required for deploying and managing applications"
        }
      ]
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-08-03T10:30:00.000Z"
}
```



#### API-GAP-002-E2E: 輕量級監控整合測試

- **名稱**: LIGHTWEIGHT_MONITORING=true 監控驗證
- **優先級**: P1
- **類型**: E2E測試
- **測試目標**: 驗證輕量級監控在真實環境的整合
- **測試內容**: 啟用輕量級監控，執行請求並驗證監控事件
- **判斷標準**: 
  - IndexCalAndGapAnalysisV2Completed 事件被記錄
  - processing_time_ms 正確記錄
  - version: "v2" 標記存在

#### ~~API-GAP-003-E2E: 部分結果支援驗證~~ [已刪除]
- **狀態**: ❌ **已刪除** - 與產品策略矛盾
- **刪除原因**: 產品需求已確定為「要嘛就全失敗 要嘛就都成功，不需要partial successful」
- **產品策略**: 任一服務失敗時，整個 API 必須失敗，確保用戶得到完整且有意義的結果
- **替代測試**: 請參考 API-GAP-009-IT (完整失敗處理測試) 和 API-GAP-012-UT (Gap Analysis 失敗處理)
- **影響**: E2E 測試數量從 3 個減少為 2 個

## 3. 測試資料規範

### 3.1 有效測試資料要求
- 所有 Resume 和 Job Description 必須 ≥ 200 字元
- Resume 建議使用 HTML 格式（包含標題、段落、列表等結構化元素）
- 使用真實且有意義的內容
- 涵蓋不同職位類型和經驗層級

### 3.2 HTML 格式範例
```html
<!-- Resume HTML 範例 -->
<article>
  <h1>John Doe - Senior Software Engineer</h1>
  <section>
    <h2>Professional Summary</h2>
    <p>Experienced software engineer with <strong>10+ years</strong> in building scalable applications.</p>
  </section>
  <section>
    <h2>Technical Skills</h2>
    <ul>
      <li>Programming: Python, JavaScript, Go</li>
      <li>Frameworks: FastAPI, React, Django</li>
      <li>Cloud: AWS, Azure, GCP</li>
    </ul>
  </section>
</article>
```

### 3.3 無效測試資料
- 少於 200 字元的文本（用於驗證錯誤處理）
- 空字串或純空白
- 非文字內容（數字、符號）

### 3.4 邊界測試資料
- 正好 200 字元的文本
- 接近但不足 200 字元（如 199 字元）
- 極長文本（30KB）

### 3.5 效能測試的快取考量

#### 避免快取影響真實效能測試
1. **P50/P95 響應時間測試**
   - 必須關閉資源池快取：`RESOURCE_POOL_ENABLED=false`
   - 每個請求使用完全不同的測試資料
   - 建議加入時間戳或 UUID 確保唯一性

2. **高並發負載測試**
   - 使用請求 ID 區分不同請求
   - 避免使用循環的測試資料模式
   - 關鍵字應有足夠的變化性（不只是 `Skill{id % 10}`）

3. **資源池效能測試**
   - API-GAP-003-PT 和 API-GAP-004-PT 需要開啟資源池
   - 這些測試專門驗證資源池效果

#### 測試資料準備策略
```python
# 錯誤示範：容易被快取命中
for i in range(600):
    data = test_cases[i % 3]  # 只有 3 種不同資料
    
# 正確示範：確保唯一性
for i in range(600):
    data = {
        "resume": f"{base_resume} - Request {i} - {time.time_ns()}",
        "jd": f"{base_jd} - Request {i} - {uuid.uuid4()}",
        "keywords": generate_random_keywords(seed=i)
    }
```

## 4. 測試執行規範

### 4.1 前置條件
- 環境變數配置正確（.env 檔案）
- API 服務運行在 port 8000
- Azure OpenAI 服務可用（效能測試和 E2E 測試需要）

### 4.2 測試腳本總覽

本專案提供兩個主要測試腳本：

1. **Mock 測試腳本** (`run_index_cal_gap_analysis_unit_integration.sh`)
   - 執行 **單元測試 + 整合測試** (37 個測試: 20 UT + 27 IT)
   - 使用 **Mock 服務**，不需要 Azure OpenAI API
   - 執行時間：< 20 秒
   - 適合開發過程中的快速驗證

2. **真實 API 測試腳本** (`run_index_cal_gap_analysis_real_api_perf_e2e.sh`)
   - 執行 **效能測試 + E2E 測試** (3 個測試: 1 PT + 2 E2E)
   - 使用 **真實 Azure OpenAI API**，會產生費用
   - 執行時間：< 90 秒
   - 適合完整驗證和效能測試

### 4.3 Mock 測試執行（推薦用於開發）

#### 基本用法
```bash
# 執行所有 47 個 Mock 測試（20 UT + 27 IT）
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 只執行單元測試 (20 個)
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --stage unit

# 只執行整合測試 (27 個)
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --stage integration

# 詳細輸出模式
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --verbose
```

#### Mock 測試優勢
- ✅ **無需 API 費用**：完全使用 Mock 服務
- ✅ **執行快速**：所有測試在 20 秒內完成
- ✅ **穩定結果**：不受網路或 API 限制影響
- ✅ **開發友好**：適合 TDD 和快速迭代

### 4.4 真實 API 測試執行（用於完整驗證）

#### 基本用法
```bash
# 執行所有 3 個真實 API 測試（1 PT + 2 E2E）
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh

# 只執行效能測試 (1 個)
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --stage performance

# 只執行 E2E 測試 (3 個)
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --stage e2e

# 背景執行（長時間測試）
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --background
```

#### 效能測試快速執行

##### 執行特定效能測試
```bash
# P50 測試 (中位數響應時間)
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test p50
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test API-GAP-001-PT

# API-GAP-001-PT 整合測試 (P50/P95 + 關鍵字一致性)
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test API-GAP-001-PT

# 同時執行 P50 和 P95 (已整合到 API-GAP-001-PT)
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test "p50,p95"
```

##### 進階選項
```bash
# 詳細輸出模式
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test "p50,p95" --verbose

# 背景執行（推薦用於效能測試）
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --perf-test "p50,p95" --background

# 查看背景執行狀態
tail -f test/logs/test_suite_real_api_perf_e2e_*.log
```

#### 效能測試注意事項
1. **真實 API 測試**：效能測試使用真實的 Azure OpenAI API，會產生實際費用
5. **測試目標**（✅ 調整為符合真實 LLM API）：
   - ✅ API-GAP-001-PT: 響應時間效能測試 (P50/P95): 目標約 80-90 秒
   - ⚠️ **已遷移**: API-GAP-003/004/005-PT 已移至整合測試 (API-GAP-015/016/017-IT)
   - ✅ **整合測試驗證**: 資源池功能現由整合測試驗證，使用 Mock 服務，節省成本

### 4.5 測試腳本進階用法

#### Mock 測試腳本進階用法
```bash
# 執行單元測試和整合測試（預設行為）
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 詳細輸出模式
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --verbose

# 查看幫助資訊
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --help
```

#### 真實 API 測試腳本進階用法
```bash
# 執行效能測試和 E2E 測試（預設行為）
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh

# 背景執行所有測試
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --background

# 查看幫助資訊
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --help
```

#### 除錯與監控
```bash
# Mock 測試詳細輸出
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --verbose

# 真實 API 測試詳細輸出
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --verbose

# 背景執行並監控
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --background
tail -f test/logs/test_suite_real_api_perf_e2e_*.log

# 查看最新測試結果
ls -lt test/logs/*.log | head -10
```

#### 測試結果分析
```bash
# 查看最新的效能測試結果
cat test/logs/performance_API-GAP-001-PT_*.json | jq '.'

# 查看整合測試結果
ls -la test/logs/test_suite_unit_integration_*.log

# 查看真實 API 測試結果  
ls -la test/logs/test_suite_real_api_perf_e2e_*.log

# 統計測試執行時間趨勢
grep "p50_time_s" test/logs/performance_API-GAP-001-PT_*.json
```

### 4.6 測試執行最佳實踐

#### 推薦執行順序
```bash
# 1. 開發階段：快速驗證（Mock 測試）
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh

# 2. 提交前：完整驗證（真實 API 測試）
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh

# 3. 效能評估：只執行效能測試
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --stage performance
```

#### 測試執行優化技巧
1. **Mock 測試優勢**：
   - 37 個測試在 20 秒內完成
   - 無 API 費用和網路延遲
   - 適合頻繁執行和 CI/CD

2. **真實 API 測試注意事項**：
   - API-GAP-001-PT：20 個請求平行執行，同時計算 P50/P95 並驗證關鍵字，約 80-90 秒
   - 使用真實 Azure OpenAI API，會產生費用

3. **資源池功能測試**：
   - API-GAP-015/016/017-IT 已移至整合測試
   - 使用 Mock 服務，快速驗證功能正確性
   - 不再需要大量真實 API 調用

#### 常見問題排除
```bash
# Mock 測試失敗
./test/scripts/run_index_cal_gap_analysis_unit_integration.sh --verbose

# 真實 API 測試超時
# 檢查網路連接和 API 配額
./test/scripts/run_index_cal_gap_analysis_real_api_perf_e2e.sh --verbose

# API 速率限制問題
# 減少併發數或增加請求間隔
export MAX_WORKERS=3  # 預設為 5

# 查看測試日誌
tail -100 test/logs/test_suite_*.log
```

### 4.7 測試標記
```python
@pytest.mark.gap_analysis  # 所有 Gap Analysis 測試
@pytest.mark.unit          # 單元測試
@pytest.mark.integration   # 整合測試
@pytest.mark.performance   # 效能測試
@pytest.mark.e2e          # 端對端測試
@pytest.mark.p0           # P0 優先級
```

## 5. 測試報告與驗證結果

### 5.1 測試覆蓋率目標（✅ 已達成）
- ✅ 單元測試覆蓋率: 100% (20/20 測試通過)
- ✅ 整合測試覆蓋率: 100% (17/17 測試通過)
- ✅ 整體測試覆蓋率: 100% (37/37 Mock 測試通過)

### 5.2 測試結果報告（✅ 已驗證）
測試執行後已生成包含以下資訊的報告：
- ✅ 執行的測試案例數量: 37 個 (20 UT + 17 IT)
- ✅ 成功/失敗/跳過的數量: 37 通過 / 0 失敗 / 0 跳過
- ✅ 執行時間: 28 秒 (符合 < 30 秒的目標)
- ✅ 失敗測試的詳細資訊: 無（所有測試通過）
- ✅ 效能測試的統計數據: 已實作完成，支援 JSON 格式輸出

## 6. 測試開發最佳實踐

### 6.1 程式碼品質標準 (Ruff)

#### 強制要求
1. **測試前檢查**: 撰寫測試程式碼前，先執行 `ruff check test/`
2. **提交前檢查**: 提交程式碼前，必須執行並通過：
   ```bash
   ruff check test/ --line-length=120
   # 必須顯示 "All checks passed!"
   ```
3. **自動修復**: 使用 `ruff check test/ --fix` 自動修復可修復的問題

#### Ruff 配置說明
```toml
# pyproject.toml 中的測試相關設定
[tool.ruff.lint.per-file-ignores]
"test/**/*.py" = [
    "E501",    # 行長度（已在全域設定為 120）
    "F401",    # 未使用的 import（測試中可能需要）
    "SIM117",  # 多重 with 語句（Python 3.11 支援）
    "S101",    # assert 使用（測試必需）
    "RUF001",  # 全形符號（中文測試資料）
    "RUF002",  # 全形符號在 docstring（中文說明）
    "S105"     # 硬編碼密鑰（測試環境可接受）
]
```

### 6.2 測試撰寫規範

#### 程式碼風格
1. **Import 排序**: 使用 isort 規則，Ruff 會自動處理
2. **型別註解**: 使用 Python 3.10+ 語法（`X | None` 而非 `Optional[X]`）
3. **未使用變數**: 使用 `_` 表示故意不使用的變數
4. **類別屬性**: 可變類別屬性需加上 `ClassVar` 註解

#### 測試結構
1. **測試函數命名**: `test_<功能>_<場景>_<預期結果>`
2. **測試類別**: 按功能模組組織測試類別
3. **Fixture 使用**: 善用 pytest fixtures 避免重複程式碼
4. **測試隔離**: 每個測試必須獨立，不依賴其他測試

### 6.3 開發流程

1. **撰寫測試前**
   ```bash
   # 確認 Ruff 設定
   cat pyproject.toml | grep -A 10 "tool.ruff"
   
   # 檢查現有程式碼品質
   ruff check test/
   ```

2. **撰寫測試時**
   - 遵循 AAA 模式（Arrange, Act, Assert）
   - 使用有意義的測試資料
   - 加入適當的錯誤訊息

3. **完成測試後**
   ```bash
   # 執行 Ruff 檢查
   ruff check test/<your_test_file>.py --line-length=120
   
   # 自動修復問題
   ruff check test/<your_test_file>.py --fix
   
   # 執行測試
   pytest test/<your_test_file>.py -v
   ```

4. **提交前檢查清單**
   - [ ] 所有測試通過
   - [ ] Ruff 檢查無錯誤
   - [ ] 測試覆蓋率符合要求
   - [ ] 測試執行時間符合限制
   - [ ] 測試資料符合最小長度要求

---

## 附錄：測試驗證結果

### 最新驗證結果 (2025-08-05)

#### Mock 測試驗證 ✅
```
執行日期: 2025-08-05 10:52:44
測試總數: 37 個測試案例 (20 Unit + 17 Integration)
執行環境: Python 3.11.8
總執行時間: 28s

測試摘要:
總測試數: 37 / 37
通過: 37 (100%)
失敗: 0
跳過: 0

測試類型統計:
單元測試 (Unit): 20/20 (100%) - 規格要求: 20
整合測試 (Integration): 17/17 (100%) - 規格要求: 17

優先級統計:
P0 (Critical): 23/23 (100%)
P1 (Important): 8/8 (100%)
P2 (Nice to have): 3/3 (100%)

結果: 🎉 所有 37 個 Unit & Integration 測試全部通過！
```

#### 真實 API 測試實作 ✅
```
實作狀態: 已完成實作
測試範圍: 3 個測試 (1 Performance + 2 E2E)
支援功能:
- ✅ P50/P95 + 關鍵字一致性整合測試 (API-GAP-001-PT)  
- ✅ E2E 完整流程測試 (API-GAP-001-E2E)
- ✅ 輕量級監控測試 (API-GAP-002-E2E)
- ❌ ~~部分結果支援測試 (API-GAP-003-E2E)~~ - 已刪除，與產品策略矛盾
- ✅ 背景執行模式
- ✅ 具體效能測試選項 (--perf-test)
```

### 測試腳本使用統計

#### Mock 測試腳本 (`run_index_cal_gap_analysis_unit_integration.sh`)
- ✅ **完全驗證**: 所有 37 個測試 100% 通過
- ✅ **穩定性能**: 執行時間穩定在 28-30 秒
- ✅ **無成本**: 使用 Mock 服務，無 API 費用
- ✅ **開發友好**: 適合頻繁執行和 CI/CD

#### 真實 API 測試腳本 (`run_index_cal_gap_analysis_real_api_perf_e2e.sh`)
- ✅ **完整實作**: 收含所有 5 個真實 API 測試
- ✅ **效能測試**: P50/P95 效能測試完整實作
- ✅ **背景執行**: 支援長時間測試的背景執行
- ✅ **精確控制**: 支援特定測試選擇執行

---

## 錯誤碼對照表

### 標準 HTTP 錯誤碼 vs Gap Analysis 實作對照

| 錯誤類型 | 標準建議狀態碼 | Gap Analysis 實作 | 符合性 | 相關測試案例 |
|---------|----------------|-------------------|--------|-------------|
| **請求格式錯誤** | 400 Bad Request | 400 Bad Request | ✅ 符合 | API-GAP-002-IT, API-GAP-003-IT |
| **文字太短** | 422 Unprocessable Entity (Pydantic驗證) | 422 Unprocessable Entity | ✅ 符合 | API-GAP-002-IT, API-GAP-003-IT |
| **無效語言** | 422 Unprocessable Entity (Pydantic驗證) | 422 Unprocessable Entity | ✅ 符合 | API-GAP-006-IT |
| **JSON 解析錯誤** | 400 Bad Request | 422 Unprocessable Entity | ❌ 不符 | (需要調整) |
| **認證失敗** | 401 Unauthorized | 401 Unauthorized | ✅ 符合 | API-GAP-014-IT |
| **權限不足** | 403 Forbidden | 403 Forbidden | ✅ 符合 | (預留) |
| **驗證錯誤** | 422 Unprocessable Entity | 422 Unprocessable Entity | ✅ 符合 | API-GAP-022-IT |
| **速率限制** | 429 Too Many Requests | 429 Too Many Requests | ✅ 符合 | API-GAP-011-IT, API-GAP-019-IT |
| **服務錯誤** | 500 Internal Server Error | 500 Internal Server Error | ✅ 符合 | API-GAP-021-IT |
| **外部服務錯誤** | 502 Bad Gateway | 502 Bad Gateway | ✅ 符合 | (預留) |
| **服務不可用** | 503 Service Unavailable | 503 Service Unavailable | ✅ 符合 | (預留) |
| **請求超時** | 504 Gateway Timeout | 504 Gateway Timeout | ✅ 符合 | API-GAP-020-IT |

### 錯誤處理機制對照

| 錯誤處理機制 | Index Calculation V2 | Gap Analysis | 差異說明 |
|-------------|---------------------|--------------|----------|
| **認證錯誤處理** | 自定義 `AuthenticationError` 保留原始狀態碼 | 待實作 | Gap Analysis 需要相同處理 |
| **外部服務錯誤** | 自定義 `ExternalServiceError` → 502 | 待實作 | Gap Analysis 需要相同處理 |
| **JSON 解析錯誤** | 特殊處理返回 400 | 返回 422 | Gap Analysis 需要調整為 400 |
| **重試機制** | 使用統一重試策略 | 使用 AdaptiveRetryStrategy | 實作方式不同但功能相似 |
| **錯誤分類** | 按 HTTP 狀態碼分類 | 按錯誤類型分類（timeout, rate_limit等） | 分類維度不同 |

### 建議調整項目

1. **JSON 解析錯誤** (高優先級)
   - 當前：422 Unprocessable Entity
   - 建議：400 Bad Request
   - 原因：JSON 格式錯誤屬於請求格式問題，應返回 400

2. **認證錯誤處理** (中優先級)
   - 當前：可能統一返回某個錯誤碼
   - 建議：實作類似 `AuthenticationError` 的機制，保留原始 401/403 狀態碼
   - 相關測試：需要新增測試案例

3. **外部服務錯誤** (中優先級)
   - 當前：可能返回 500
   - 建議：返回 502 Bad Gateway
   - 原因：明確區分內部錯誤和外部依賴錯誤

## 6. Resume Structure Analysis 測試案例 (V4)

### 6.1 單元測試 (RS-xxx-UT)

#### RS-001-UT: 基本結構分析測試
- **名稱**: Resume Structure Analyzer 基本功能驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證履歷結構識別的核心功能
- **測試內容**: 測試識別標準履歷區段（Summary、Skills、Experience、Education等）
- **判斷標準**: 
  - 正確識別存在的區段標題
  - 不存在的區段返回 null
  - 自訂區段列表正確

#### RS-002-UT: Prompt 模板驗證測試
- **名稱**: Prompt 配置載入和格式驗證
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 prompt 模板正確載入和格式化
- **測試內容**: 測試 prompt 模板結構、佔位符、fallback 機制
- **判斷標準**: 
  - system prompt 存在且格式正確
  - user prompt 包含 {resume_html} 佔位符
  - fallback prompt 可正常使用

#### RS-003-UT: JSON 解析驗證測試
- **名稱**: LLM 回應 JSON 解析和錯誤處理
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 JSON 解析邏輯和錯誤處理
- **測試內容**: 測試不同格式的 JSON 回應（含 markdown code block）
- **判斷標準**: 
  - 正確解析標準 JSON
  - 處理 ```json 包裝的內容
  - 格式錯誤時拋出 JSONDecodeError

#### RS-004-UT: 重試機制測試
- **名稱**: 3 次重試機制與延遲策略驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證失敗時的重試邏輯
- **測試內容**: 模擬失敗場景，驗證重試次數和延遲
- **判斷標準**: 
  - 最多重試 3 次
  - 重試延遲 500ms
  - 第 3 次成功時返回結果

#### RS-005-UT: Fallback 結構測試
- **名稱**: 完全失敗時的 fallback 結構生成
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證所有重試失敗後的 fallback 機制
- **測試內容**: 模擬持續失敗，驗證 fallback 結構
- **判斷標準**: 
  - 3 次重試都失敗後啟動 fallback
  - 返回預設結構（基本區段）
  - metadata 顯示 unknown/0 值

### 6.2 整合測試 (RS-xxx-IT)

#### RS-001-IT: 並行執行時間測試
- **名稱**: Parallel Execution Timing 驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證並行任務執行時間，確保結構分析不增加延遲
- **測試內容**: 模擬不同服務執行時間，驗證並行執行
- **判斷標準**: 
  - 總時間不超過最長任務時間 + 額外開銷
  - 結構分析（2s）與 Keywords/Embeddings 並行
  - resume_structure 欄位正確返回

#### RS-002-IT: API 回應格式測試
- **名稱**: API Response Format 驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 API 回應包含正確的結構欄位
- **測試內容**: 測試有/無結構資料的回應格式
- **判斷標準**: 
  - IndexCalAndGapAnalysisData 模型接受 resume_structure
  - standard_sections 包含所有標準區段
  - 向後相容：無結構時仍可正常回應

#### RS-003-IT: 錯誤處理流程測試
- **名稱**: Error Handling and Fallback 驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 測試錯誤恢復和 fallback 機制
- **測試內容**: 模擬結構分析服務失敗，驗證 fallback
- **判斷標準**: 
  - 服務失敗時使用 fallback 結構
  - 其他服務正常運作不受影響
  - fallback 結構包含基本欄位

#### RS-004-IT: 功能開關行為測試
- **名稱**: Feature Flag Enable/Disable 驗證
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 測試 ENABLE_RESUME_STRUCTURE_ANALYSIS 功能開關
- **測試內容**: 測試開啟/關閉功能的不同行為
- **判斷標準**: 
  - 開啟時：回應包含 resume_structure
  - 關閉時：回應不包含 resume_structure
  - 開關狀態不影響其他功能

#### RS-005-IT: 端對端 Mock 流程測試
- **名稱**: End-to-End Mock Flow 完整驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 完整流程與 mock 服務測試
- **測試內容**: 使用完整 mock 資料驗證所有元件整合
- **判斷標準**: 
  - 所有服務回應正確整合
  - metadata 包含 structure_analysis_enabled
  - 完整回應結構包含所有必要欄位

### 6.3 測試實作位置

- **單元測試**: `test/unit/test_resume_structure_analyzer.py`
- **整合測試**: `test/integration/test_resume_structure_integration.py`

### 6.4 測試執行指令

```bash
# 執行單元測試
pytest test/unit/test_resume_structure_analyzer.py -v

# 執行整合測試  
pytest test/integration/test_resume_structure_integration.py -v

# 執行特定測試
pytest test/unit/test_resume_structure_analyzer.py::TestResumeStructureAnalyzer::test_RS_001_UT_basic_structure_analysis -v
```

## 7. Course Availability Check 測試案例

### 7.1 單元測試 (CA-xxx-UT)

#### CA-001-UT: 批量 Embedding 生成測試
- **名稱**: Batch Embedding Generation
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證批量生成 embeddings 功能
- **測試內容**: Mock embedding service，測試 3-6 個技能的批量處理
- **判斷標準**:
  - 一次 API 呼叫生成所有 embeddings
  - 返回數量與輸入一致
  - 處理空列表不報錯
  - 正確應用 SKILL/FIELD 差異化文本策略

#### CA-002-UT: 單一技能查詢測試
- **名稱**: Single Skill Query Execution
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證單一技能的資料庫查詢
- **測試內容**: Mock 資料庫連線，測試 SQL 查詢邏輯與優先排序
- **判斷標準**:
  - 正確返回 has_courses 布林值
  - course_count 不超過 10
  - 查詢超時拋出 TimeoutError
  - 使用正確的相似度閾值（SKILL: 0.30, FIELD: 0.25）

#### CA-003-UT: 快取機制測試
- **名稱**: Popular Skills Cache Mechanism
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證熱門技能快取
- **測試內容**: 測試快取命中與未命中場景
- **判斷標準**:
  - 熱門技能直接返回快取結果
  - 未快取技能進入查詢流程
  - 快取命中率統計正確
  - Python, JavaScript 等熱門技能在快取中

#### CA-004-UT: 錯誤處理測試
- **名稱**: Graceful Degradation Error Handling
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 Graceful Degradation 機制
- **測試內容**: 模擬各種錯誤場景
- **判斷標準**:
  - 單一失敗不影響其他技能
  - 失敗技能標記為 false/0
  - 發送正確的錯誤告警
  - 系統整體失敗時所有技能標記為 false

#### CA-005-UT: 並行處理測試
- **名稱**: Parallel Processing with asyncio.gather
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 asyncio.gather 並行執行
- **測試內容**: 測試 3-6 個技能的並行查詢
- **判斷標準**:
  - 所有查詢並行執行
  - 單一異常不影響其他
  - return_exceptions=True 正確處理
  - 執行時間明顯少於串行處理

#### CA-006-UT: 空技能列表處理測試
- **名稱**: Empty Skill List Handling
- **優先級**: P2
- **類型**: 單元測試
- **測試目標**: 驗證空列表輸入的處理
- **測試內容**: 傳入空的技能查詢列表
- **判斷標準**:
  - 返回空列表而非錯誤
  - 不呼叫 embedding 或資料庫服務
  - 快速返回（< 10ms）
  - 不產生任何錯誤日誌

#### CA-007-UT: 超時處理測試
- **名稱**: Timeout Handling Test
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證查詢超時的處理機制
- **測試內容**: 模擬資料庫查詢超時（> 1秒）
- **判斷標準**:
  - 正確捕獲 TimeoutError
  - 超時的技能標記為 unavailable
  - 記錄警告日誌
  - 不影響其他技能的查詢

### 7.2 整合測試 (CA-xxx-IT)

#### CA-001-IT: API 整合測試
- **名稱**: Gap Analysis Integration
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證與 Gap Analysis 的整合
- **測試內容**: Mock 完整 API 流程，驗證結果增強
- **測試資料**:
  - Rust (SKILL): Systems programming language
  - Quantum Computing (FIELD): Quantum algorithms
- **判斷標準**:
  - SkillSearchQueries 包含新欄位 (has_available_courses, course_count)
  - 數值合理（0-10）
  - 包含 preferred_count 和 other_count 分解

#### CA-002-IT: 並行處理與差異化策略測試
- **名稱**: Parallel Processing and Category Differentiation
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 SKILL/FIELD 差異化處理
- **測試內容**: 測試不同類別的 embedding 文本生成
- **判斷標準**:
  - SKILL 類別包含 "course project certificate" 關鍵詞
  - FIELD 類別包含 "specialization degree" 關鍵詞
  - 並行處理多個技能
  - 正確應用不同的相似度閾值

#### CA-003-IT: 優雅降級測試
- **名稱**: Graceful Degradation on Service Failure
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證服務失敗時的恢復
- **測試內容**: 模擬 Embedding/DB 服務失敗
- **判斷標準**:
  - 主 API 繼續運作
  - 技能標記為 false
  - 錯誤告警正確發送
  - 不中斷主要 Gap Analysis 流程

#### CA-004-IT: 資料庫連線失敗測試
- **名稱**: Database Connection Failure Handling
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證資料庫連線失敗的處理
- **測試內容**: Mock connection pool 拋出異常
- **判斷標準**:
  - 服務不崩潰
  - 返回 false/0 作為預設值
  - 正確記錄錯誤日誌
  - Graceful degradation 機制啟動

### 7.3 效能測試 (CA-xxx-PT)

#### CA-001-PT: 6 技能效能測試
- **名稱**: 6-Skill Performance Test
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 測試 6 個技能並行查詢的效能表現
- **測試內容**:
  - 固定 6 個技能（3 SKILL + 3 FIELD 類別）
  - 連續執行 20 次迭代
  - 每次迭代都是 6 個技能的並行查詢
  - 計算 P50、P95、平均值等統計數據
- **測試資料**: 真實存在的技能（Python, Docker, React, Machine Learning, Data Science, Cloud Computing）
- **判斷標準**:
  - P50 < 500ms（使用真實 API）
  - P95 < 1000ms（使用真實 API）
  - 生成詳細 JSON 報告

### 7.4 測試實作位置

```
test/
├── unit/
│   └── services/
│       └── test_course_availability.py         # 7 個單元測試
└── integration/
    └── test_course_availability_integration.py # 4 個整合測試
└── performance/
    └── test_course_availability_performance.py  # 3 個效能測試（已修復）
```

### 7.5 測試執行指令

```bash
# 執行所有課程可用性測試
pytest test/unit/services/test_course_availability.py -v
pytest tests/integration/test_course_availability_integration.py -v

# 執行特定測試
pytest test/unit/services/test_course_availability.py::TestCourseAvailability::test_CA_001_UT_batch_embedding_generation -v

# 執行效能測試
./test/scripts/run_course_availability_performance.sh

# 執行特定效能測試
pytest test/performance/test_course_availability_performance.py::TestCourseAvailabilityPerformance::test_CA_001_PT_progressive_performance -v

# 執行真實 API 測試（需要 API keys）
pytest test/performance/test_course_availability_performance.py -m real_api -v
pytest test/performance/test_course_availability_performance.py -v --real-api
```

---

**文檔結束** - 版本 1.0.11 | 所有測試已完成驗證 ✅ | 新增課程可用性檢查測試規格