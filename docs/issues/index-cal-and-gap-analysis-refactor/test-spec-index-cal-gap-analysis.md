# Index Calculation and Gap Analysis API 測試規格文檔

## 文檔資訊
- **版本**: 1.0.1
- **建立日期**: 2025-08-03
- **最後更新**: 2025-08-03
- **維護者**: 測試團隊
- **測試總數**: 43 個（原 50 個，移除 7 個基礎設施相關測試）

## 重要測試約束 ⚠️

### 最小長度要求
- **Job Description**: 必須 ≥ 200 字元
- **Resume**: 必須 ≥ 200 字元（建議使用 HTML 格式）
- 所有測試資料都必須滿足此要求（除非特別測試長度驗證）

### 測試執行時間限制
- **單元測試 + 整合測試**: 必須在 20 秒內完成
- **效能測試 + 端對端測試**: 必須在 90 秒內完成

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
| 001-014 | 整合測試(IT) | 14 | API 端點整合測試 |
| 001-005 | 效能測試(PT) | 5 | 效能和負載測試 |
| 001-004 | 端對端測試(E2E) | 4 | 完整流程測試 |

## 2. 測試案例總覽

### 2.1 單元測試 (20個)

#### API-GAP-001-UT: CombinedAnalysisServiceV2 初始化測試
- **名稱**: 統一分析服務初始化驗證
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證服務正確初始化，依賴注入正確
- **前置條件**: 環境變數配置正確
- **測試資料**: 
  ```yaml
  input:
    enable_partial_results: true
    cache_ttl_minutes: 60
  expected:
    service_initialized: true
    dependencies_injected: true
  ```

#### API-GAP-002-UT: ResourcePoolManager 初始化測試
- **名稱**: 資源池管理器初始化和預建立
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證資源池預建立最小數量客戶端
- **測試步驟**:
  1. 初始化 ResourcePoolManager(min_size=2, max_size=10)
  2. 呼叫 initialize()
  3. 驗證池中有 2 個預建立的客戶端

#### API-GAP-003-UT: 資源池獲取客戶端測試
- **名稱**: 從資源池獲取和歸還客戶端
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證客戶端正確獲取和歸還
- **測試步驟**:
  1. 使用 get_client() context manager
  2. 驗證獲得有效客戶端
  3. 退出 context 後驗證客戶端歸還

#### API-GAP-004-UT: 資源池達到上限測試
- **名稱**: 資源池達到最大容量時的行為
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證達到 max_size 時等待可用客戶端

#### API-GAP-005-UT: 並行執行 Phase 1 測試
- **名稱**: Phase 1 並行 embedding 生成
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 resume 和 JD embedding 並行生成
- **測試資料**:
  ```yaml
  input:
    resume: "<h3>Senior Software Engineer</h3><p>10+ years of experience in full-stack development, specializing in <strong>Python</strong>, <strong>FastAPI</strong>, and microservices architecture.</p><ul><li>Led multiple teams in delivering scalable enterprise solutions</li><li>Expertise in cloud technologies (AWS, Azure)</li><li>Containerization (Docker, Kubernetes)</li><li>DevOps practices</li></ul><p>Strong background in system design and performance optimization.</p>" # 400+ chars HTML
    job_description: "We are seeking a Senior Python Developer with 8+ years of experience to join our growing team. The ideal candidate will have strong expertise in FastAPI, microservices, and cloud platforms. Required skills include Python, FastAPI, Docker, Kubernetes, AWS/Azure, CI/CD, and database design. Experience with React and frontend technologies is a plus." # 350+ chars
  ```

#### API-GAP-006-UT: 並行執行 Phase 2 測試
- **名稱**: Phase 2 Index 計算和 Gap 前置準備並行
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Index 計算與 Gap context 準備並行執行

#### API-GAP-007-UT: 並行執行 Phase 3 測試
- **名稱**: Phase 3 Gap Analysis 使用 Index 結果
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Gap Analysis 正確接收和使用 Index 結果

#### API-GAP-008-UT: AdaptiveRetryStrategy 初始化測試
- **名稱**: 自適應重試策略配置驗證
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證不同錯誤類型的重試配置正確

#### API-GAP-009-UT: 空欄位錯誤重試測試
- **名稱**: empty_fields 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證空欄位錯誤使用線性退避，最多 2 次重試

#### API-GAP-010-UT: 超時錯誤重試測試
- **名稱**: timeout 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證超時錯誤使用指數退避，基礎延遲 0.5 秒

#### API-GAP-011-UT: 速率限制錯誤重試測試
- **名稱**: rate_limit 錯誤類型重試行為
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證速率限制錯誤使用指數退避，基礎延遲 5 秒

#### API-GAP-012-UT: 部分結果處理測試
- **名稱**: Gap Analysis 失敗時返回 Index 結果
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證啟用部分結果時，Gap 失敗仍返回 Index 結果

#### API-GAP-013-UT: 完全失敗處理測試
- **名稱**: Index 和 Gap 都失敗的處理
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證兩個服務都失敗時正確拋出錯誤

#### API-GAP-014-UT: 服務依賴驗證測試
- **名稱**: Gap Analysis 接收 Index 結果依賴
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 matched_keywords 和 missing_keywords 正確傳遞

#### API-GAP-015-UT: 關鍵字覆蓋計算測試
- **名稱**: 關鍵字匹配結果傳遞給 Gap Analysis
- **優先級**: P0
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 covered_keywords 和 missed_keywords 正確計算和傳遞

#### API-GAP-016-UT: 錯誤分類器測試
- **名稱**: 錯誤類型分類邏輯驗證
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 _classify_gap_error 正確識別錯誤類型

#### API-GAP-017-UT: 統計追蹤測試
- **名稱**: 服務統計資訊追蹤
- **優先級**: P2
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 total_requests、partial_successes 等統計正確更新

#### API-GAP-018-UT: HTML 文本處理差異測試
- **名稱**: Embedding 和 LLM 的差異化文本處理
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Embedding 使用清理文本，LLM 保留 HTML 結構

#### API-GAP-019-UT: TaskGroup 異常處理測試
- **名稱**: Python 3.11 TaskGroup ExceptionGroup 處理
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證並行任務失敗時的異常聚合處理

#### API-GAP-020-UT: 服務清理測試
- **名稱**: 異常時的資源清理驗證
- **優先級**: P1
- **類型**: 單元測試
- **需求編號**: REQ-004
- **測試目標**: 驗證錯誤發生時資源池客戶端正確歸還

### 2.2 整合測試 (14個)

#### API-GAP-001-IT: API 端點基本功能測試
- **名稱**: POST /api/v1/index-cal-and-gap-analysis 正常流程
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 API 端點正常運作，回應格式正確
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
    data:
      raw_similarity_percentage: number
      similarity_percentage: number
      keyword_coverage: object
      gap_analysis: object
  ```

#### API-GAP-002-IT: JD 長度驗證測試
- **名稱**: Job Description < 200 字元錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 JD 少於 200 字元時返回 400 錯誤
- **測試資料**:
  ```yaml
  request:
    resume: "<section><h2>Senior Software Engineer</h2><p>Extensive experience in <em>full-stack development</em>, cloud architecture, and team leadership.</p><h3>Skills</h3><ul><li>Multiple programming languages</li><li>Modern frameworks</li><li>Cloud architecture</li></ul><p>Strong problem-solving skills and proven track record of delivering quality software solutions.</p></section>" # 350+ chars HTML
    job_description: "Looking for Python developer" # 只有 29 字元
    keywords: ["Python"]
  expected:
    status: 400
    error:
      code: "TEXT_TOO_SHORT"
      message: "Job description must be at least 200 characters"
  ```

#### API-GAP-003-IT: Resume 長度驗證測試
- **名稱**: Resume < 200 字元錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Resume 少於 200 字元時返回 400 錯誤
- **測試資料**:
  ```yaml
  request:
    resume: "Software developer" # 只有 18 字元
    job_description: "We are seeking an experienced Senior Software Engineer to join our dynamic team. The ideal candidate will have 5+ years of experience in software development, strong programming skills in Python and JavaScript, and expertise in cloud technologies. Must be proficient in modern development practices." # 300+ chars
    keywords: ["Python", "JavaScript"]
  expected:
    status: 400
    error:
      code: "TEXT_TOO_SHORT"
      message: "Resume must be at least 200 characters"
  ```

#### API-GAP-004-IT: 邊界長度測試
- **名稱**: JD 和 Resume 正好 200 字元測試
- **優先級**: P1
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證正好 200 字元時正常處理
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

#### API-GAP-005-IT: 關鍵字參數驗證測試
- **名稱**: keywords 參數格式驗證
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 keywords 支援陣列和逗號分隔字串
- **測試步驟**:
  1. 測試陣列格式：["Python", "Docker", "AWS"]
  2. 測試逗號分隔："Python,Docker,AWS"
  3. 驗證兩種格式產生相同結果

#### API-GAP-006-IT: 語言參數驗證測試
- **名稱**: language 參數驗證（只測試參數傳遞）
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證只接受 "en" 和 "zh-TW"，其他值返回錯誤
- **測試資料**:
  ```yaml
  invalid_languages: ["fr", "ja", "ko", "es", "de"]
  expected:
    status: 400
    error:
      code: "INVALID_LANGUAGE"
  ```

#### API-GAP-007-IT: Bubble.io 回應格式驗證
- **名稱**: 回應格式符合 Bubble.io 固定 schema
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證回應包含所有必要欄位且格式正確
- **驗證項目**:
  - success: boolean
  - data: object (包含所有必要子欄位)
  - error: object (code, message, details)
  - timestamp: ISO 8601 格式

#### API-GAP-008-IT: Feature Flag 測試
- **名稱**: USE_V2_IMPLEMENTATION Feature Flag 驗證
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Feature Flag 控制 V2 實作啟用
- **測試步驟**:
  1. 設定 USE_V2_IMPLEMENTATION=true
  2. 發送請求
  3. 驗證使用 V2 服務（透過回應時間或監控事件）

#### API-GAP-009-IT: 部分失敗處理測試
- **名稱**: Gap Analysis 失敗時的部分結果返回
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證啟用部分結果時，Gap 失敗仍返回 Index 結果
- **測試方法**: Mock Gap Analysis 服務失敗

#### API-GAP-010-IT: 服務超時處理測試
- **名稱**: 外部服務超時的錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 Azure OpenAI 超時時的重試和錯誤處理

#### API-GAP-011-IT: 速率限制錯誤處理測試
- **名稱**: Azure OpenAI 速率限制處理
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證遇到速率限制時的重試策略

#### API-GAP-012-IT: 處理時間元數據測試
- **名稱**: 回應包含處理時間分解
- **優先級**: P1
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 V2 回應包含 processing_time_ms 和 service_timings

#### API-GAP-013-IT: 大文檔處理測試
- **名稱**: 處理大型 JD 和 Resume
- **優先級**: P1
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證處理 10KB、20KB、30KB 文檔的能力

#### API-GAP-014-IT: 認證機制測試
- **名稱**: API Key 認證驗證
- **優先級**: P0
- **類型**: 整合測試
- **需求編號**: REQ-004
- **測試目標**: 驗證支援 Header (X-API-Key) 和 Query (?code=) 認證

### 2.3 效能測試 (5個)

#### API-GAP-001-PT: P50 響應時間測試
- **名稱**: 中位數響應時間 < 2 秒驗證
- **優先級**: P0
- **類型**: 效能測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 P50 響應時間符合目標
- **測試配置**:
  - 持續時間: 60 秒
  - 請求率: 10 QPS
  - 預期: P50 < 2000ms
- **重要注意事項**:
  - ⚠️ **必須關閉資源池快取**：測試真實 API 效能時，必須設定 `RESOURCE_POOL_ENABLED=false`
  - ⚠️ **使用唯一測試資料**：每個請求必須使用不同的 JD/Resume 組合，避免資源池重用
  - 建議方法：在測試資料中加入時間戳或請求 ID 確保唯一性

#### API-GAP-002-PT: P95 響應時間測試
- **名稱**: 95 百分位響應時間 < 4 秒驗證
- **優先級**: P0
- **類型**: 效能測試
- **需求編號**: REQ-004
- **測試目標**: 驗證 P95 響應時間符合目標
- **測試配置**:
  - 持續時間: 60 秒
  - 請求率: 10 QPS
  - 預期: P95 < 4000ms
- **重要注意事項**:
  - ⚠️ **同 API-GAP-001-PT**：必須關閉資源池快取並使用唯一測試資料

#### API-GAP-003-PT: 資源池重用率測試
- **名稱**: 資源池客戶端重用率 > 80%
- **優先級**: P0
- **類型**: 效能測試
- **需求編號**: REQ-004
- **測試目標**: 驗證資源池有效減少初始化開銷
- **測試方法**:
  1. 發送 100 個請求
  2. 檢查資源池統計
  3. 驗證 reuse_rate > 80%
- **注意事項**:
  - 此測試需要開啟資源池功能
  - 可使用重複的測試資料（測試重用效果）

#### API-GAP-004-PT: API 呼叫減少驗證
- **名稱**: 共享 Embedding 減少 API 呼叫 40-50%
- **優先級**: P0
- **類型**: 效能測試
- **需求編號**: REQ-004
- **測試目標**: 驗證相同輸入的重複請求減少 API 呼叫
- **測試方法**:
  1. 發送相同請求 10 次
  2. 監控 Azure OpenAI API 呼叫數
  3. 驗證減少 40% 以上
- **注意事項**:
  - 此測試專門驗證資源池效果
  - 必須使用完全相同的測試資料

#### API-GAP-005-PT: 資源池擴展測試
- **名稱**: 資源池動態擴展效能
- **優先級**: P2
- **類型**: 效能測試
- **需求編號**: REQ-004
- **測試目標**: 驗證資源池從 min_size 擴展到 max_size 的效能
- **注意事項**:
  - 使用不同的測試資料觸發資源池擴展
  - 每個請求使用不同 ID 確保不會被資源池重用

### 2.4 端對端測試 (4個)

#### API-GAP-001-E2E: 完整工作流程測試
- **名稱**: 從請求到回應的完整流程驗證
- **優先級**: P0
- **類型**: 端對端測試
- **需求編號**: REQ-004
- **測試目標**: 使用真實數據驗證完整工作流程
- **測試資料**: 使用實際的履歷和職缺描述（各 500+ 字元）

#### API-GAP-002-E2E: 輕量級監控整合測試
- **名稱**: LIGHTWEIGHT_MONITORING=true 監控驗證
- **優先級**: P1
- **類型**: 端對端測試
- **需求編號**: REQ-004
- **測試目標**: 驗證輕量級監控正確記錄關鍵指標
- **驗證項目**:
  - IndexCalAndGapAnalysisV2Completed 事件
  - processing_time_ms 記錄
  - version: "v2" 標記

#### API-GAP-003-E2E: 部分結果支援驗證
- **名稱**: 實際場景的部分結果功能
- **優先級**: P1
- **類型**: 端對端測試
- **需求編號**: REQ-004
- **測試目標**: 驗證生產環境中部分失敗時的行為

#### API-GAP-004-E2E: 真實數據綜合測試
- **名稱**: 使用多樣化真實數據的綜合測試
- **優先級**: P1
- **類型**: 端對端測試
- **需求編號**: REQ-004
- **測試目標**: 驗證各種真實履歷和職缺的處理
- **測試資料類型**:
  - 技術職位（軟體工程師、資料科學家）
  - 不同經驗層級（初級、中級、高級）
  - 不同長度（200-3000 字元）

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
- Azure OpenAI 服務可用

### 4.2 測試指令
```bash
# 執行所有 Gap Analysis 測試
pytest tests/test_gap_analysis/ -v

# 執行特定類型測試
pytest tests/unit/test_gap_analysis_unit.py -v
pytest tests/integration/test_gap_analysis_integration.py -v
pytest tests/performance/test_gap_analysis_performance.py -v
pytest tests/e2e/test_gap_analysis_e2e.py -v

# 執行特定測試案例
pytest tests/unit/test_gap_analysis_unit.py::test_API_GAP_001_UT -v
```

### 4.3 測試標記
```python
@pytest.mark.gap_analysis  # 所有 Gap Analysis 測試
@pytest.mark.unit          # 單元測試
@pytest.mark.integration   # 整合測試
@pytest.mark.performance   # 效能測試
@pytest.mark.e2e          # 端對端測試
@pytest.mark.p0           # P0 優先級
```

## 5. 測試報告

### 5.1 測試覆蓋率目標
- 單元測試覆蓋率: > 90%
- 整合測試覆蓋率: > 85%
- 整體測試覆蓋率: > 88%

### 5.2 測試結果報告
測試執行後應生成包含以下資訊的報告：
- 執行的測試案例數量
- 成功/失敗/跳過的數量
- 執行時間
- 失敗測試的詳細資訊
- 效能測試的統計數據

---

**文檔結束**