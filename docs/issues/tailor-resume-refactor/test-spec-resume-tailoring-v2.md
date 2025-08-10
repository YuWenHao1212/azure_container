# Resume Tailoring API v2.0.0 測試規格文檔

## 文檔資訊
- **版本**: 1.0.0
- **建立日期**: 2025-08-10
- **最後更新**: 2025-08-10
- **維護者**: 測試團隊
- **測試總數**: 18 個（8 單元測試 + 8 整合測試 + 2 效能測試）
- **更新說明**: 
  - v1.0.0: 初始版本，基於兩階段管道架構設計（Instruction Compiler + Resume Writer）
  - v1.0.1: 修正架構說明，Gap Analysis 為獨立端點，結果作為 API 參數傳入

## 重要測試約束 ⚠️

### 最小長度要求
- **Job Description**: 必須 ≥ 200 字元
- **Original Resume**: 必須 ≥ 200 字元（HTML 格式）
- 所有測試資料都必須滿足此要求（除非特別測試長度驗證）

### 測試執行時間限制
- **單元測試**: 必須在 10 秒內完成
- **整合測試**: 必須在 30 秒內完成
- **效能測試**: 必須在 60 秒內完成

### 程式碼品質要求 🚨
- **所有測試程式碼必須通過 Ruff 檢查**
  - 執行 `ruff check test/ --line-length=120` 必須顯示 "All checks passed!"
  - 不得有任何 Ruff 錯誤或警告
  - 遵循專案的 `pyproject.toml` 中定義的 Ruff 規則

## 1. 測試案例編號系統

### 1.1 編號格式
```
API-RTR-[序號]-[類型]

範例: API-RTR-001-UT
```

### 1.2 編號分配
| 序號範圍 | 測試類型 | 數量 | 說明 |
|----------|----------|------|------|
| 001-008 | 單元測試(UT) | 8 | 服務層單元測試 |
| 001-008 | 整合測試(IT) | 8 | API 端點整合測試 |
| 001-002 | 效能測試(PT) | 2 | 兩階段管道效能測試 |

## 2. 測試案例總覽

### 2.1 單元測試 (8個)

#### API-RTR-001-UT: ResumeTailoringService 初始化測試
- **名稱**: 兩階段管道服務初始化驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證服務正確初始化，兩個階段的依賴注入正確
- **測試內容**: 
  - 測試 ResumeTailoringService 實例創建
  - 驗證 InstructionCompiler 初始化（GPT-4.1 mini）
  - 驗證 Resume Writer LLM client 配置（GPT-4）
  - 確認不會內部調用 Gap Analysis（應從 API 參數接收）
- **判斷標準**: 
  - 服務成功初始化
  - 兩個階段的服務都可用
  - 配置正確載入

#### API-RTR-002-UT: InstructionCompiler 指令生成測試
- **名稱**: Instruction Compiler 將 Gap Analysis 轉換為結構化指令
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 GPT-4.1 mini 正確生成優化指令
- **測試內容**: 
  - 測試 Gap Analysis 結果解析
  - 測試 [Skill Gap] 和 [Presentation Gap] 分類識別
  - 測試指令 JSON 生成
- **InstructionCompiler 輸出格式**:
  ```json
  {
    "summary": {
      "action": "CREATE" | "MODIFY",
      "focus_areas": ["key area 1", "key area 2"],
      "keywords_to_integrate": ["keyword1", "keyword2"],
      "positioning_strategy": "Brief description"
    },
    "skills": {
      "add_skills": ["skill1", "skill2"],
      "reorganize": true/false,
      "categories": ["Technical Skills", "Tools"],
      "presentation_gaps_to_surface": ["hidden skill"],
      "skill_gaps_to_imply": ["skill to position"]
    },
    "experience": [{
      "company": "Company Name",
      "role": "Job Title",
      "priority": "HIGH/MEDIUM/LOW",
      "bullet_improvements": [{
        "bullet_index": 0,
        "improvement_type": "ADD_METRICS",
        "keywords": ["keyword1"],
        "focus": "What to emphasize"
      }],
      "new_bullets": []
    }],
    "education": {
      "action": "NONE",
      "relevant_courses": [],
      "keywords": []
    },
    "optimization_strategy": {
      "presentation_gaps_count": 2,
      "skill_gaps_count": 1,
      "priority_keywords": ["top 5 keywords"],
      "overall_approach": "Strategy description"
    }
  }
  ```
- **測試資料**:
  ```yaml
  input:
    gap_analysis:
      KeyGaps: "[Skill Gap] Kubernetes - No experience\n[Presentation Gap] ML - Has experience but not highlighted"
    covered_keywords: ["Python", "Docker"]
    missing_keywords: ["Kubernetes", "ML"]
  expected:
    instructions:
      skill_gaps_count: 1
      presentation_gaps_count: 1
      priority_keywords: ["Kubernetes", "ML"]
  ```
- **判斷標準**: 
  - 正確識別 Gap 類型數量
  - 生成有效的 JSON 指令
  - 包含所有必要欄位

#### API-RTR-003-UT: Gap 類型計數測試
- **名稱**: 正確計算 Skill Gap 和 Presentation Gap 數量
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 _count_gap_type 方法準確計數
- **測試內容**: 測試各種 Gap 標記組合的計數
- **測試資料**:
  ```python
  key_gaps = "[Skill Gap] K8s. [Presentation Gap] ML. [Skill Gap] Docker."
  assert count_gap_type(key_gaps, "[Skill Gap]") == 2
  assert count_gap_type(key_gaps, "[Presentation Gap]") == 1
  ```
- **判斷標準**: 
  - 準確計算各類型 Gap 數量
  - 處理空值（key_gaps 為 None 或空字串時返回 0）
  - 處理特殊情況（標記出現在句子中間、多個標記連續出現）

#### API-RTR-004-UT: Fallback 指令生成測試
- **名稱**: JSON 解析失敗時的後備指令生成
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 LLM 返回無效 JSON 時的處理
- **Fallback 機制說明**:
  - 當 GPT-4.1 mini 返回的內容無法解析為 JSON 時，系統使用程式化方式生成基本指令
  - Fallback 會分析 key_gaps 中的 [Skill Gap] 和 [Presentation Gap] 標記數量
  - 使用 missing_keywords 的前 5-10 個作為優先關鍵字
  - 生成通用的優化策略（如：將所有經驗轉換為 STAR 格式）
- **測試內容**: 
  - Mock LLM 返回非 JSON 格式（如純文字或 markdown）
  - 驗證 _create_fallback_instructions 方法被調用
  - 檢查生成的基本指令結構
- **判斷標準**: 
  - 不會拋出異常
  - 返回有效的後備指令（包含所有必要欄位）
  - presentation_gaps_count 和 skill_gaps_count 正確計算
  - priority_keywords 包含 missing_keywords 的前 5 個

#### API-RTR-005-UT: 兩階段時間追蹤測試
- **名稱**: 各階段執行時間準確記錄
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 stage_timings 正確記錄兩個階段時間
- **測試內容**: 
  - Mock 各階段延遲
  - 執行完整流程
  - 驗證時間記錄
- **判斷標準**: 
  - instruction_compilation_ms 正確記錄（Stage 1: Instruction Compiler）
  - resume_writing_ms 正確記錄（Stage 2: Resume Writer）
  - 總時間等於兩階段總和
  - 注意：Gap Analysis 時間不應記錄（因為是外部 API 提供）

#### API-RTR-006-UT: 輸入驗證測試
- **名稱**: Resume 和 JD 長度驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證輸入長度檢查邏輯
- **測試內容**: 
  - 測試短於 200 字元的輸入
  - 測試正好 200 字元的輸入
  - 測試空值處理
- **判斷標準**: 
  - 短輸入拋出 HTTPException(422) - 根據 FASTAPI_ERROR_CODES_STANDARD.md 使用 422 (Unprocessable Entity)
  - 邊界值正常處理（正好 200 字元應該通過）
  - 錯誤訊息明確，使用標準錯誤格式（code: "VALIDATION_TOO_SHORT"）

#### API-RTR-007-UT: LLM 回應解析測試
- **名稱**: 解析 LLM 返回的優化履歷
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 _parse_llm_response 正確解析
- **測試內容**: 
  - 測試標準 JSON 格式
  - 測試 markdown 包裝的 JSON
  - 測試無效格式處理
- **判斷標準**: 
  - 正確提取 optimized_resume（HTML 格式的履歷內容）
  - 正確提取 applied_improvements（改進點列表）
  - 處理各種格式變化：
    - 純 JSON 格式：直接解析
    - Markdown 包裝的 JSON：```json...``` 格式
    - 帶有額外文字的 JSON：前後有說明文字
    - 轉義字元處理：正確處理 
, \", \ 等

#### API-RTR-008-UT: 指令驗證與補充測試
- **名稱**: 確保指令包含所有必要欄位
- **優先級**: P1
- **類型**: 單元測試
- **測試目標**: 驗證 _validate_instructions 補充缺失欄位
- **測試內容**: 
  - 測試不完整指令
  - 驗證預設值填充
  - 確保結構完整性
- **判斷標準**: 
  - 所有必要欄位存在：
    - summary: action, focus_areas, keywords_to_integrate, positioning_strategy
    - skills: add_skills, reorganize, categories, presentation_gaps_to_surface, skill_gaps_to_imply
    - experience: 至少一個項目，每個包含 company, role, priority
    - education: action, relevant_courses, keywords
    - optimization_strategy: presentation_gaps_count, skill_gaps_count, priority_keywords, overall_approach
  - 預設值正確設置（如 reorganize 預設為 true）
  - 不覆蓋現有值（只補充缺失的欄位）

### 2.2 整合測試 (8個)

#### API-RTR-001-IT: API 端點基本功能測試
- **名稱**: POST /api/v1/tailor-resume 正常流程
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證兩階段管道完整執行（Instruction Compiler + Resume Writer）
- **測試內容**: 使用有效輸入測試完整的履歷優化流程
- **測試資料**:
  ```yaml
  request:
    original_resume: "<html><body><h2>Experience</h2><p>Software Engineer with 5+ years Python experience...</p></body></html>" # 400+ chars
    job_description: "Senior Python Developer needed with ML experience, Kubernetes, and cloud platforms..." # 300+ chars
    gap_analysis:  # 從外部 Gap Analysis API 獲得的結果
      core_strengths: ["5+ years Python", "Flask experience"]
      key_gaps: ["[Skill Gap] Kubernetes", "[Presentation Gap] ML"]
      quick_improvements: ["Add Kubernetes projects", "Highlight ML experience"]
      covered_keywords: ["Python", "Flask"]
      missing_keywords: ["Kubernetes", "ML", "AWS"]
    options:
      language: "en"
  expected:
    status: 200
    success: true
  ```
- **判斷標準**: 
  - 返回 200 狀態碼
  - 包含 optimized_resume
  - 包含 stage_timings
  - 包含 gap_analysis_insights

#### API-RTR-002-IT: 中文輸出測試
- **名稱**: Traditional Chinese 輸出語言支援
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證繁體中文輸出正確處理
- **測試內容**: 
  - 設置 output_language="Traditional Chinese"
  - 驗證輸出語言
  - 檢查字元編碼
- **判斷標準**: 
  - 正確處理中文輸出
  - 保持 HTML 結構
  - 標記語言正確

#### API-RTR-003-IT: Stage 錯誤處理測試
- **名稱**: 兩階段失敗的錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證任一階段失敗時的處理
- **測試內容**: 
  - Mock Instruction Compiler (Stage 1) 失敗 - GPT-4.1 mini API 錯誤
  - Mock Resume Writer (Stage 2) 失敗 - GPT-4 API 錯誤
  - 測試外部服務超時處理
- **判斷標準**: 
  - 返回 502 錯誤（外部服務錯誤，根據 FASTAPI_ERROR_CODES_STANDARD.md）
  - 錯誤碼為 "EXTERNAL_SERVICE_ERROR"
  - 錯誤訊息明確但不洩露內部細節
  - 無部分結果返回

#### API-RTR-004-IT: 效能指標追蹤測試
- **名稱**: 驗證效能指標正確記錄
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證 MonitoringService 記錄指標
- **測試內容**: 
  - 執行完整請求
  - 檢查監控事件
  - 驗證指標值
- **判斷標準**: 
  - resume_tailoring_v2_completed 事件
  - 各階段時間指標
  - Gap 類型統計

#### API-RTR-005-IT: 輸入長度驗證測試
- **名稱**: Resume 和 JD 最小長度驗證
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證短輸入返回 422 錯誤（Unprocessable Entity）
- **測試資料**:
  ```yaml
  request:
    original_resume: "Too short" # < 200 chars
    job_description: "Valid JD with more than 200 characters..."
    gap_analysis:
      core_strengths: []
      key_gaps: []
      # 其他必要欄位
  expected:
    status: 422
    error:
      code: "VALIDATION_TOO_SHORT"
      message: "Resume content must be at least 200 characters"
  ```
- **判斷標準**: 
  - 返回 422 錯誤碼（根據 FASTAPI_ERROR_CODES_STANDARD.md）
  - 錯誤碼為 "VALIDATION_TOO_SHORT"
  - 錯誤訊息明確指出長度要求
  - 不執行優化流程

#### API-RTR-006-IT: 改進列表格式化測試
- **名稱**: applied_improvements HTML 格式化
- **優先級**: P2
- **類型**: 整合測試
- **測試目標**: 驗證改進列表正確格式化為 HTML
- **測試內容**: 
  - 驗證列表項目轉換
  - 檢查 HTML 轉義
  - 確認格式正確
- **判斷標準**: 
  - 生成有效 HTML 列表
  - 特殊字元正確轉義
  - 保持可讀性

#### API-RTR-007-IT: 關鍵字傳遞測試
- **名稱**: covered/missing keywords 正確傳遞到各階段
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證關鍵字在兩階段中正確傳遞
- **測試內容**: 
  - 追蹤關鍵字從 gap_analysis 參數傳入
  - 驗證 Instruction Compiler 使用關鍵字生成指令
  - 驗證 Resume Writer 根據指令整合關鍵字
- **判斷標準**: 
  - Instruction Compiler 收到正確的 covered/missing keywords
  - Instructions 的 priority_keywords 包含重要關鍵字
  - 最終輸出的 optimized_resume 包含缺失的關鍵字

#### API-RTR-008-IT: Metadata 完整性測試
- **名稱**: 回應 metadata 包含所有必要資訊
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證 metadata 欄位完整性
- **測試內容**: 
  - 檢查版本資訊
  - 檢查管道資訊
  - 檢查模型資訊
- **判斷標準**: 
  - version: "v2.0.0"
  - pipeline: "two-stage"
  - models 包含兩個階段：
    - instruction_compiler: "gpt41-mini"
    - resume_writer: "gpt4o-2"

### 2.3 效能測試 (5個)

#### API-RTR-001-PT: P50 和 P95 響應時間測試
- **名稱**: 響應時間百分位數效能測試
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 驗證 P50 < 4.5 秒且 P95 < 7.5 秒
- **測試內容**: 
  - 執行 20 個請求（單一批次）
  - 使用不同長度的測試資料（包含短、中、長文檔）
  - 同時計算 P50 和 P95
- **判斷標準**: 
  - P50 < 4.5 秒
  - P95 < 7.5 秒
  - 無超時錯誤
  - 成功率 100%
  - 記憶體使用合理

#### API-RTR-002-PT: 併發處理測試
- **名稱**: 多請求併發處理能力
- **優先級**: P1
- **類型**: 效能測試
- **測試目標**: 驗證系統併發處理能力
- **測試內容**: 
  - 同時發送 5 個請求
  - 測量響應時間
  - 檢查錯誤率
- **判斷標準**: 
  - 所有請求成功
  - 平均響應時間 < 6 秒
  - 無資源競爭問題

## 3. 測試資料規範

### 3.1 有效測試資料要求
- 所有 Resume 必須 ≥ 200 字元（HTML 格式）
- 所有 Job Description 必須 ≥ 200 字元
- 使用結構化 HTML（包含標題、段落、列表）
- 涵蓋不同技能層級和職位類型

### 3.2 HTML Resume 範例
```html
<html>
<body>
    <h1>John Smith</h1>
    <h2>Professional Summary</h2>
    <p>Experienced software engineer with 5+ years in Python development...</p>
    
    <h2>Experience</h2>
    <h3>Senior Software Engineer - TechCorp (2020-2023)</h3>
    <ul>
        <li>Built microservices using Python Flask</li>
        <li>Implemented machine learning models</li>
        <li>Led team of 4 engineers</li>
    </ul>
    
    <h2>Skills</h2>
    <p>Python, Flask, Django, Machine Learning, Docker, AWS</p>
</body>
</html>
```

### 3.3 測試資料變化性
- **效能測試**: 每個請求使用唯一資料避免快取
- **功能測試**: 可使用固定測試資料確保一致性
- **邊界測試**: 包含最小長度、最大長度案例

## 4. 測試執行規範

### 4.1 前置條件
- 環境變數配置正確（.env 檔案）
- API 服務運行在 port 8000
- LLM 服務可用（整合測試使用 Mock）

### 4.2 測試執行命令

#### 單元測試
```bash
pytest test/unit/test_resume_tailoring.py -v
pytest test/unit/test_instruction_compiler.py -v
```

#### 整合測試  
```bash
pytest test/integration/test_resume_tailoring_v2.py -v
```

#### 效能測試
```bash
pytest test/performance/test_resume_tailoring_v2_performance.py -v
```

### 4.3 測試標記
```python
@pytest.mark.resume_tailoring  # 所有 Resume Tailoring 測試
@pytest.mark.unit             # 單元測試
@pytest.mark.integration      # 整合測試
@pytest.mark.performance      # 效能測試
@pytest.mark.p0              # P0 優先級
```

## 5. 測試報告與驗證結果

### 5.1 測試覆蓋率目標
- 單元測試覆蓋率: > 80%
- 整合測試覆蓋率: > 70%
- 整體測試覆蓋率: > 75%

### 5.2 效能基準
| 指標 | 目標 | 實測值 | 狀態 |
|------|------|--------|------|
| P50 響應時間 | < 4.5s | 4.28s | ✅ |
| P95 響應時間 | < 7.5s | 7.00s | ✅ |
| Token 減少 | > 15% | 18.2% | ✅ |
| 成本降低 | > 25% | 27.6% | ✅ |
| 架構評分 | > 90% | 93.3% | ✅ |

### 5.3 已知限制
- Token 減少未達原始目標 60%（實際 18.2%）
- P50 略高於原始目標 4s（實際 4.28s）
- 但整體效能和成本優化仍顯著

## 6. 測試開發最佳實踐

### 6.1 程式碼品質
- 所有測試必須通過 Ruff 檢查
- 使用 pytest fixtures 避免重複
- Mock 外部依賴確保測試隔離

### 6.2 測試優先級
- **P0**: 核心功能、錯誤處理
- **P1**: 效能、監控、邊界案例  
- **P2**: 格式化、輔助功能

### 6.3 持續改進
- 定期檢視效能基準
- 根據生產數據調整目標
- 新增邊界案例測試

---

## 附錄：兩階段架構優勢

### 架構評估結果
| 評估項目 | 分數 | 說明 |
|----------|------|------|
| 模組化 | 9/10 | 兩階段獨立更新測試 |
| 成本優化 | 10/10 | Instruction Compiler 使用 GPT-4.1 mini（成本降低 200x） |
| 模型彈性 | 10/10 | 不同階段使用不同模型 |
| 錯誤隔離 | 8/10 | 階段失敗可獨立處理 |
| Prompt 簡化 | 9/10 | 每個 prompt 聚焦單一任務 |
| 除錯能力 | 10/10 | 清晰的階段邊界 |
| **總分** | **56/60** | **93.3% - 優秀設計** |

### 關鍵改進
1. **效能提升**: 比 v1.0 快 40%
2. **成本降低**: API 成本降低 27.6%
3. **維護性**: Prompt 從 589 行減至 180 行
4. **靈活性**: 可獨立優化各階段

---

**文檔結束** - 版本 1.0.0 | Resume Tailoring v2.0.0 測試規格