# Resume Tailoring API 測試規格文檔

## 文檔資訊
- **版本**: 3.1.0
- **建立日期**: 2025-08-11
- **最後更新**: 2025-08-23
- **維護者**: 測試團隊
- **測試總數**: 13 個（原15個，移除2個重複錯誤處理測試）
- **Mock測試**: 10 個（6 UT + 4 IT，移除2個IT）
- **Real API測試**: 3 個效能測試（保持不變）
- **更新說明**: 
  - v3.1.0: 更新為支援平行 LLM 架構，調整資料模型和測試斷言
  - v1.1.0: 移除 API-TLR-523/524-IT，合併至ERROR_HANDLER
  - v1.0.0: 初始版本，基於 v2.1.0-simplified 混合 CSS 標記系統

## 重要測試約束 ⚠️

### 最小長度要求
- **Job Description**: 必須 ≥ 200 字元
- **Original Resume**: 必須 ≥ 200 字元（HTML 格式）
- 所有測試資料都必須滿足此要求（除非特別測試長度驗證）

### 測試執行時間限制
- **單元測試**: 必須在 5 秒內完成
- **整合測試**: 必須在 10 秒內完成  
- **效能測試**: 必須在 30 秒內完成

### 程式碼品質要求 🚨
- **所有測試程式碼必須通過 Ruff 檢查**
  - 執行 `ruff check test/ --line-length=120` 必須顯示 "All checks passed!"
  - 不得有任何 Ruff 錯誤或警告
  - 遵循專案的 `pyproject.toml` 中定義的 Ruff 規則

## v3.1.0 重要變更 ⚠️

### API 模型變更
1. **請求模型變更**：
   - `gap_analysis` → `original_index`：現在使用來自前一個 API 的完整結果
   - 保留 `options` 參數，支援語言和視覺標記選項

2. **回應模型變更**：
   - `applied_improvements`：從 HTML 字串改為字串列表格式
   - **新增 Keywords 模型**：包含 `kcr_*` 和 `kw_*` 前綴的詳細關鍵字指標
   - **新增 SimilarityMetrics**：包含 `SS_*` 前綴的相似度指標
   - **新增時間追蹤**：`llm1_processing_time_ms`、`llm2_processing_time_ms` 等

3. **測試資料調整**：
   - Mock 資料需使用新的模型格式
   - 斷言需檢查新的字段名稱

### 架構變更
- **平行 LLM 處理**：LLM1 (Core Optimizer) 和 LLM2 (Additional Manager) 並行執行
- **懶載入初始化**：服務使用 `get_tailoring_service()` 工廠函數避免匯入時錯誤
- **移除 fallback 機制**：服務錯誤時直接傳播異常，不使用估算值

## 1. 測試案例編號系統

### 1.1 編號格式
```
API-TLR-[序號]-[類型]

範例: API-TLR-501-UT
```

### 1.2 編號分配
| 序號範圍 | 測試類型 | 數量 | 說明 |
|----------|----------|------|------|
| 501-506 | 單元測試(UT) | 6 | 關鍵字處理與 Metrics 計算單元測試 |
| 507-512 | 單元測試(UT) | 6 | 關鍵字變體與邊界情況測試 |
| 521-526 | 整合測試(IT) | 6 | API 端點整合測試 |
| 541-543 | 效能測試(PT) | 3 | 關鍵字處理效能測試 |

## 2. 測試案例總覽

### 2.1 單元測試 (6個) - 關鍵字處理與 Metrics 計算相關測試



#### API-TLR-501-UT: 關鍵字檢測測試
- **名稱**: _detect_keywords_presence 基本功能驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證從 HTML 中正確檢測關鍵字
- **測試原因**: Resume Tailoring 需要追蹤關鍵字狀態變化，確保關鍵字檢測準確
- **測試內容**: 測試基本關鍵字在 HTML 內容中的檢測
- **測試資料**: 
  ```yaml
  input:
    html_content: "<p>Python developer with Django expertise</p>"
    keywords_to_check: ["Python", "Django", "React"]
  expected:
    found_keywords: ["Python", "Django"]
  ```
- **判斷標準**: 正確識別存在的關鍵字，不誤報不存在的關鍵字

#### API-TLR-502-UT: 關鍵字分類測試
- **名稱**: _categorize_keywords 四種狀態分類驗證
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證關鍵字分類為 still_covered、removed、newly_added、still_missing
- **測試原因**: 核心業務邏輯，用於生成警告和統計報告
- **測試內容**: 測試四種關鍵字狀態的完整分類邏輯
- **測試資料**:
  ```yaml
  input:
    originally_covered: ["Python", "Django", "Docker"]
    currently_covered: ["Python", "AWS", "React"]
    covered_keywords: ["Python", "Django", "Docker"]
    missing_keywords: ["AWS", "React", "Kubernetes"]
  expected:
    still_covered: ["Python"]
    removed: ["Django", "Docker"]
    newly_added: ["AWS", "React"]
    still_missing: ["Kubernetes"]
  ```
- **判斷標準**: 四種狀態分類準確，無關鍵字遺漏或錯分

#### API-TLR-503-UT: 關鍵字變體匹配測試
- **名稱**: 關鍵字變體智能匹配（防禦性設計）
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 CI/CD → CI-CD、Node.js → NodeJS 等變體匹配
- **測試原因**: LLM 不是 100% 可靠，防禦性設計避免格式差異導致追蹤失準
- **測試內容**: 測試常見技術術語的變體匹配
- **測試資料**:
  ```yaml
  input:
    html_content: "<p>Experience with CI/CD pipelines and Node.js</p>"
    keywords_to_check: ["CI-CD", "NodeJS", "CICD"]
  expected:
    found_keywords: ["CI-CD", "NodeJS", "CICD"]  # 全部匹配
  ```
- **判斷標準**: 變體匹配準確，不影響其他匹配邏輯

#### API-TLR-504-UT: 縮寫對應測試
- **名稱**: 專業術語縮寫匹配（容錯機制）
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證 ML ↔ Machine Learning 等縮寫雙向匹配
- **測試原因**: 確保縮寫和全稱都能被正確識別和追蹤
- **測試內容**: 測試內建縮寫對照表的雙向查詢
- **內建縮寫對應表**:
  ```python
  abbreviations = {
    "Machine Learning": ["ML"],
    "Artificial Intelligence": ["AI"], 
    "Natural Language Processing": ["NLP"],
    "Application Programming Interface": ["API"]
  }
  ```
- **判斷標準**: 縮寫和全稱雙向匹配正確

#### API-TLR-505-UT: Metrics 計算成功流程測試
- **名稱**: _calculate_metrics_after_optimization 成功流程
- **優先級**: P0
- **類型**: 單元測試
- **測試目標**: 驗證整合 IndexCalculationServiceV2 的正常流程
- **測試原因**: 確保真實 metrics 計算功能正常運作，不使用 fallback 估算值
- **測試內容**: 測試成功調用 IndexCalculationServiceV2 並計算 metrics
- **判斷標準**: IndexCalculationServiceV2 被正確調用，metrics 正確計算

#### API-TLR-506-UT: ServiceError 異常傳播測試
- **名稱**: IndexCalculationServiceV2 失敗時正確拋出異常
- **優先級**: P0
- **類型**: 單元測試  
- **測試目標**: 驗證服務失敗時異常正確傳播（不使用 fallback）
- **測試原因**: 確保移除 fallback 機制後，服務失敗時正確拋出異常
- **測試內容**: 測試 IndexCalculationServiceV2 拋出 ServiceError 時的處理
- **判斷標準**: ServiceError 正確傳播，不生成 fallback 結果

### 2.2 整合測試 (6個)

#### API-TLR-521-IT: 成功優化與關鍵字追蹤測試
- **名稱**: POST /api/v1/tailor-resume 正常流程
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證 API 端點正常運作，關鍵字追蹤功能正確
- **測試內容**: 使用有效輸入測試完整的 API 流程
- **測試資料** (v3.1.0 格式):
  ```yaml
  request:
    job_description: "Looking for Python developer..." # 300+ chars
    original_resume: "<html><body>Python developer...</body></html>" # 250+ chars
    original_index:  # 改自 gap_analysis
      core_strengths: ["Python", "Leadership"]
      key_gaps: ["[Skill Gap] Docker"]
      quick_improvements: ["Add Docker certification"]
      covered_keywords: ["Python", "Django"]
      missing_keywords: ["Docker", "Kubernetes"]
      coverage_percentage: 50
      similarity_percentage: 60
    options:
      language: "en"
      include_visual_markers: true
  expected:
    status: 200
    success: true
    data:
      Keywords:  # v3.1.0 新格式
        kcr_before: 50
        kcr_after: 80
        kcr_improvement: 30
        kw_after_covered: ["Python", "Docker"]
        kw_removed: ["Django"]
        newly_added: ["Docker"]
        kw_after_missed: ["Kubernetes"]
      similarity:  # v3.1.0 新格式
        SS_before: 60
        SS_after: 85
        SS_improvement: 25
      applied_improvements:  # 改為列表格式
        - "[Skill Gap] Added Docker containerization"
  ```
- **判斷標準**: 
  - 返回 200 狀態碼
  - keyword_tracking 欄位完整
  - 警告機制正確觸發

#### API-TLR-522-IT: 無關鍵字移除無警告測試
- **名稱**: 關鍵字全部保留時無警告
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證無關鍵字移除時不產生警告
- **測試內容**: 測試所有關鍵字都保留的情況
- **判斷標準**: 
  - has_warning 為 false
  - warning.message 為空
  - warning.details 為空陣列

#### API-TLR-523-IT: 輸入長度驗證測試 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERROR_HANDLER 測試套件 (ERR-016-UT 通用驗證錯誤處理)
- **名稱**: Resume 或 JD 太短的錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證長度驗證錯誤處理
- **測試內容**: 測試少於 200 字元的輸入
- **測試資料**:
  ```yaml
  request:
    job_description: "Short JD"  # < 200 chars
    original_resume: "<html><body>Short</body></html>"  # < 200 chars
  expected:
    status: 422  # 驗證錯誤
    success: false
    error:
      code: "VALIDATION_TOO_SHORT"
      message: "Resume must be at least 200 characters"
  ```
- **判斷標準**: 
  - 返回 422 狀態碼（驗證錯誤）
  - error.has_error 為 true
  - 錯誤碼為 VALIDATION_TOO_SHORT

#### API-TLR-524-IT: 外部服務錯誤處理測試 [已合併至ERROR_HANDLER]
- **狀態**: ⚠️ **已移除** - 合併至 ERROR_HANDLER 測試套件 (ERR-017-UT 通用外部服務錯誤分類)
- **名稱**: LLM 服務錯誤處理
- **優先級**: P0
- **類型**: 整合測試
- **測試目標**: 驗證外部服務錯誤的處理
- **測試內容**: Mock LLM 服務錯誤
- **錯誤碼標準**: 參考 FASTAPI_ERROR_CODES_STANDARD.md
- **判斷標準**: 
  - 錯誤碼為 EXTERNAL_RATE_LIMIT_EXCEEDED (429)
  - 錯誤碼為 EXTERNAL_SERVICE_ERROR (502)
  - 錯誤碼為 EXTERNAL_SERVICE_TIMEOUT (504)
  - 錯誤訊息清晰
  - 不返回部分結果

#### API-TLR-525-IT: 系統內部錯誤處理測試
- **名稱**: 意外錯誤的處理
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證系統內部錯誤處理
- **測試內容**: Mock 意外的 Exception
- **錯誤碼標準**: 參考 FASTAPI_ERROR_CODES_STANDARD.md
- **判斷標準**: 
  - 錯誤碼為 SYSTEM_INTERNAL_ERROR (500)
  - 錯誤訊息安全（不洩露敏感資訊）
  - 日誌記錄完整

#### API-TLR-526-IT: 覆蓋率統計測試
- **名稱**: 關鍵字覆蓋率統計驗證
- **優先級**: P1
- **類型**: 整合測試
- **測試目標**: 驗證覆蓋率統計的正確性
- **測試內容**: 測試 before/after 覆蓋率計算
- **判斷標準**: 
  - coverage.before 正確計算
  - coverage.after 反映實際變化
  - improvement 計算準確

### 2.3 效能測試 (3個)

#### API-TLR-541-PT: 關鍵字檢測效能測試
- **名稱**: 大量關鍵字檢測效能
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 驗證處理 30+ 關鍵字的效能
- **測試內容**: 使用 30 個關鍵字測試檢測效能
- **測試方法**:
  1. 準備包含多種技術的長履歷（10KB+）
  2. 準備 30+ 個關鍵字列表
  3. 執行 100 次迭代
  4. 計算 P50、P95 時間
- **判斷標準**: 
  - **P50 < 50ms**（30 個關鍵字）
  - **P95 < 100ms**
  - 無記憶體洩漏

#### API-TLR-542-PT: 關鍵字分類效能測試
- **名稱**: Python 後處理關鍵字分類效能
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 驗證 Python 關鍵字分類函數的效能
- **測試原因**:
  - 這不是 LLM 的分類，是 Python 後處理的分類邏輯
  - _categorize_keywords 函數需要比對兩個列表，分類成四種狀態
  - 確保 Python 處理不會成為整體 API 的效能瓶頸
- **測試內容**: 使用 50 個關鍵字測試分類效能
- **測試方法**:
  1. 準備 50 個關鍵字的測試資料
  2. 執行 1000 次迭代
  3. 計算統計數據
- **判斷標準**: 
  - **P50 < 10ms**
  - **P95 < 20ms**
  - 結果準確性 100%

#### API-TLR-543-PT: 完整 API 回應時間測試
- **名稱**: 端到端回應時間測試
- **優先級**: P0
- **類型**: 效能測試
- **測試目標**: 驗證完整 API 回應時間符合 SLA
- **測試內容**: 測試包含所有處理步驟的完整流程
- **測試方法**:
  1. Mock LLM 服務（Stage 1: 300ms, Stage 2: 2000ms）
  2. 執行 10 個請求
  3. 測量端到端時間
- **判斷標準**: 
  - **P50 < 4500ms**
  - **P95 < 7500ms**
  - **P99 < 8000ms**

## 3. 測試資料規範

### 3.1 有效測試資料要求
- 所有 Resume 和 Job Description 必須 ≥ 200 字元
- Resume 必須使用 HTML 格式
- 包含實際的職位描述和技能關鍵字
- 涵蓋不同產業和職位類型

### 3.2 HTML 格式範例
```html
<!-- Resume HTML 範例 -->
<div class="resume">
  <h1>John Doe</h1>
  <h2>Senior Software Engineer</h2>
  <section>
    <h3>Skills</h3>
    <ul>
      <li>Programming: Python, JavaScript, Go</li>
      <li>Frameworks: Django, FastAPI, React</li>
      <li>DevOps: Docker, Kubernetes, CI/CD</li>
    </ul>
  </section>
  <section>
    <h3>Experience</h3>
    <p>10+ years developing scalable web applications...</p>
  </section>
</div>
```

### 3.3 關鍵字測試資料集

#### 技術關鍵字集
```yaml
programming_languages: ["Python", "JavaScript", "Java", "C++", "C#", "Go"]
frameworks: ["Django", "FastAPI", "React", "Vue", "Angular", "Spring"]
devops: ["Docker", "Kubernetes", "CI/CD", "Jenkins", "GitLab CI"]
cloud: ["AWS", "Azure", "GCP", "CloudFormation", "Terraform"]
databases: ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch"]
```

#### 特殊字元關鍵字（硬編碼處理）
```python
# 實作中的特殊處理
special_langs = {
    "C++": [r"C\+\+", r"Cpp", r"CPP"],
    "C#": [r"C#", r"CSharp", r"C Sharp"],
    ".NET": [r"\.NET", r"dotnet", r"dot net"]
}
```

#### 變體匹配規則
```yaml
slash_variations:  # "/" 的變體
  "CI/CD": ["CI-CD", "CI CD", "CICD"]
  "TCP/IP": ["TCP-IP", "TCP IP"]
  
dot_variations:  # "." 的變體
  "Node.js": ["NodeJS", "Node JS", "nodejs"]
  "Vue.js": ["VueJS", "Vue JS", "vuejs"]
```

#### 內建縮寫對照表（雙向查詢）
```python
# 系統內建的縮寫對應字典
abbreviations = {
    "Machine Learning": ["ML"],
    "Artificial Intelligence": ["AI"],
    "Deep Learning": ["DL"],
    "Natural Language Processing": ["NLP"],
    "User Experience": ["UX"],
    "User Interface": ["UI"],
    "Application Programming Interface": ["API"],
    "Software Development Kit": ["SDK"],
    "Continuous Integration": ["CI"],
    "Continuous Deployment": ["CD"],
    "Continuous Delivery": ["CD"]
}

# 使用範例：
# 1. 關鍵字 "ML" → 也會匹配 "Machine Learning"
# 2. 關鍵字 "Machine Learning" → 也會匹配 "ML"
```

## 4. 測試執行規範

### 4.1 前置條件
- 環境變數配置正確（.env 檔案）
- API 服務運行在 port 8000
- 測試資料準備完成

### 4.2 測試執行命令

#### 單元測試執行
```bash
# 執行所有單元測試
pytest test/unit/test_resume_tailoring_keyword_tracking.py -v

# 執行特定測試
pytest test/unit/test_resume_tailoring_keyword_tracking.py::test_detect_keywords_presence_basic -v

# 顯示覆蓋率
pytest test/unit/test_resume_tailoring_keyword_tracking.py --cov=src.services.resume_tailoring
```

#### 整合測試執行
```bash
# 執行所有整合測試
pytest test/integration/test_resume_tailoring_api.py -v

# 執行特定測試類別
pytest test/integration/test_resume_tailoring_api.py::TestResumeTailoringAPI -v
```

#### 效能測試執行
```bash
# 執行所有效能測試
pytest test/performance/test_resume_tailoring_performance.py -v -s

# 執行特定效能測試
pytest test/performance/test_resume_tailoring_performance.py::test_keyword_detection_performance -v -s
```

### 4.3 測試標記
```python
@pytest.mark.resume_tailoring  # 所有 Resume Tailoring 測試
@pytest.mark.unit              # 單元測試
@pytest.mark.integration       # 整合測試
@pytest.mark.performance       # 效能測試
@pytest.mark.p0                # P0 優先級
```

### 4.4 測試執行時間要求
| 測試類型 | 目標時間 | 最大時間 |
|----------|----------|----------|
| 單元測試（6個） | < 3秒 | 6秒 |
| 整合測試（6個） | < 12秒| 18秒 |
| 效能測試（3個） | < 20秒 | 30秒 |
| **總計** | < 35秒 | 54秒 |

## 5. 測試報告與驗證結果

### 5.1 測試覆蓋率目標
- ✅ 單元測試覆蓋率: > 90%
- ✅ 整合測試覆蓋率: > 80%
- ✅ 關鍵功能覆蓋率: 100%

### 5.2 測試結果報告格式
測試執行後生成的報告應包含：
- 執行的測試案例數量
- 成功/失敗/跳過的數量
- 執行時間統計
- 失敗測試的詳細資訊
- 效能測試的 P50/P95 數據

### 5.3 關鍵指標監控
- **關鍵字檢測準確率**: > 99%
- **關鍵字分類準確率**: 100%
- **P50 回應時間**: < 2.5秒
- **P95 回應時間**: < 4.5秒
- **關鍵字處理開銷**: < 10ms

## 6. 測試開發最佳實踐

### 6.1 程式碼品質標準 (Ruff)

#### 強制要求
1. **測試前檢查**: 撰寫測試前執行 `ruff check test/`
2. **提交前檢查**: 必須通過 `ruff check test/ --line-length=120`
3. **自動修復**: 使用 `ruff check test/ --fix` 自動修復

#### Ruff 配置
```toml
# pyproject.toml 測試相關設定
[tool.ruff.lint.per-file-ignores]
"test/**/*.py" = [
    "S101",    # assert 使用（測試必需）
    "RUF001",  # 全形符號（中文測試資料）
    "RUF002",  # 全形符號在 docstring
    "S105"     # 硬編碼密鑰（測試環境）
]
```

### 6.2 測試撰寫規範

#### 測試結構
1. **AAA 模式**: Arrange, Act, Assert
2. **測試隔離**: 每個測試獨立執行
3. **Mock 使用**: 適當 Mock 外部依賴
4. **資料準備**: 使用 fixture 避免重複

#### 命名規範
- 測試函數: `test_<功能>_<場景>_<預期結果>`
- 測試類別: `Test<模組名稱>`
- Fixture: `<資源>_fixture`

### 6.3 開發流程

1. **撰寫測試前**
   ```bash
   # 檢查現有測試
   pytest test/unit/test_resume_tailoring*.py --collect-only
   
   # 確認 Ruff 設定
   ruff check test/ --show-settings
   ```

2. **撰寫測試時**
   - 先寫測試，再寫實作（TDD）
   - 每個測試專注單一功能
   - 使用有意義的測試資料

3. **完成測試後**
   ```bash
   # Ruff 檢查
   ruff check test/unit/test_resume_tailoring_keyword_tracking.py --line-length=120
   
   # 執行測試
   pytest test/unit/test_resume_tailoring_keyword_tracking.py -v
   
   # 覆蓋率檢查
   pytest test/unit/test_resume_tailoring_keyword_tracking.py --cov
   ```

## 7. 風險與緩解措施

### 7.1 技術風險
| 風險項目 | 影響程度 | 緩解措施 |
|----------|----------|----------|
| LLM 不遵循關鍵字格式 | 高 | 1. Prompt 明確指示<br>2. 後處理變體匹配 |
| 關鍵字檢測效能瓶頸 | 中 | 1. 正則表達式優化<br>2. 快取編譯模式 |
| 特殊字元處理錯誤 | 中 | 1. 完整轉義處理<br>2. 充分測試覆蓋 |

### 7.2 業務風險
| 風險項目 | 影響程度 | 緩解措施 |
|----------|----------|----------|
| 關鍵字被意外移除 | 高 | 1. 警告機制<br>2. 用戶確認流程 |
| ATS 相容性問題 | 高 | 1. 保持原始格式<br>2. 最小化修改 |

## 8. 未來優化建議

### 8.1 短期優化（1-2週）
1. **擴展縮寫對照表**: 增加更多行業術語
2. **同義詞支援**: Developer ↔ Engineer
3. **正則表達式快取**: 提升檢測效能

### 8.2 中期優化（1個月）
1. **機器學習相似度**: 使用 embedding 計算相似度
2. **動態匹配閾值**: 根據關鍵字類型調整
3. **A/B 測試框架**: 測試不同匹配策略

### 8.3 長期優化（3個月）
1. **專用關鍵字服務**: 獨立的關鍵字匹配微服務
2. **行業知識庫**: 建立行業特定關鍵字庫
3. **智能權重系統**: 關鍵字重要性自動評分

---

## 附錄：測試執行結果

### 最新測試結果 (2025-08-23)

#### ✅ v3.1.0 測試實作完成
```
狀態: 所有測試已更新支援 v3.1.0
測試總數: 13 個 (6 單元測試 + 4 整合測試 + 3 效能測試)
實作狀態: 已完成並通過

測試檔案狀態:
✅ test/unit/services/test_resume_tailoring_metrics.py (6 個測試)
✅ test/integration/test_resume_tailoring_api.py (4 個測試通過，2 個跳過)
✅ test/performance/test_resume_tailoring_performance.py (3 個測試)

v3.1.0 更新內容:
- 更新 mock 路徑支援懶載入模式
- 調整資料模型為 original_index
- 更新回應格式為新的 Keywords 和 SimilarityMetrics 模型
- applied_improvements 改為列表格式
```

#### 🎯 實作優先級
```
P0 優先級 (必須完成):
- API-TAILOR-017-UT: Metrics 計算成功流程
- API-TAILOR-018-UT: ServiceError 異常傳播
- API-TAILOR-019-IT: 成功優化與關鍵字追蹤
- API-TAILOR-024-IT: ServiceError 處理測試

P1 優先級 (後續完成):
- 其他單元測試 (013-016)
- 其他整合測試 (020-023)
- 所有效能測試 (025-027)
```

### Ruff 檢查結果 ✅
```bash
$ ruff check src/ test/ --line-length=120
All checks passed!
```

## 7.5. Fallback 機制移除相關測試 (2025-08-11 更新)

### 7.5.1 背景
在 2025-08-11 的更新中，我們移除了 Resume Tailoring 中的 fallback 機制，當 IndexCalculationServiceV2 失敗時，系統現在會返回明確的錯誤，而不是不準確的估算值（+20% similarity, +15% coverage）。

### 7.5.2 新增測試項目

#### 單元測試
- **API-TAILOR-013-UT**: _calculate_metrics_after_optimization 成功流程測試
  - 驗證 IndexCalculationServiceV2 整合正常
  - 確保 before metrics 來自 gap_analysis，after metrics 來自真實計算
  - 測試 metrics 計算的準確性

- **API-TAILOR-015-UT**: ServiceError 異常傳播測試  
  - 驗證服務失敗時 ServiceError 正確拋出
  - 確保不生成任何 fallback 結果
  - 測試錯誤處理的完整性

#### 整合測試更新
- **API-TAILOR-002-IT**: 更新為真實計算成功測試
  - 驗證完整 API 流程使用真實 metrics
  - 確保返回的 similarity.after 不是簡單的 +20 估算
  - 測試真實計算的 improvement 值

- **API-TAILOR-006-IT**: 更新為 ServiceError 處理測試
  - 驗證 API 層級正確處理 ServiceError
  - 確保返回 SERVICE_CALCULATION_ERROR 錯誤碼
  - 測試不返回任何部分結果

### 7.5.3 測試檔案位置
- **單元測試**: `test/unit/services/test_resume_tailoring_metrics.py` (新建)
- **整合測試**: `test/integration/test_resume_tailoring_api.py` (更新現有)

### 7.5.4 驗證結果
- ✅ 所有新增/更新的測試都通過
- ✅ ServiceError 正確傳播到 API 層級
- ✅ 不再使用不準確的 fallback 估算值
- ✅ 真實 metrics 計算正常運作

## 8. 測試實作狀態

### 8.1 測試檔案位置

| Test ID 範圍 | 類型 | 實作檔案 | 狀態 |
|-------------|------|----------|------|
| API-TLR-501-UT ~ API-TLR-506-UT | 單元測試 | test/unit/services/test_resume_tailoring_metrics.py | ✅ 已完成 |
| API-TLR-521-IT ~ API-TLR-526-IT | 整合測試 | test/integration/test_resume_tailoring_api.py | ✅ 已完成 |
| API-TLR-541-PT ~ API-TLR-543-PT | 效能測試 | test/performance/test_resume_tailoring_performance.py | ✅ 已完成 |

### 8.2 Test ID 標記狀態

所有測試都已按照 TEST_SPEC.md 標準實作，使用新的 API-TLR-XXX-YY 格式：

#### 單元測試 Test IDs (✅ 已實作)
- API-TLR-501-UT: test_detect_keywords_presence_basic
- API-TLR-502-UT: test_categorize_keywords_four_states
- API-TLR-503-UT: test_keyword_variant_matching
- API-TLR-504-UT: test_abbreviation_mapping
- API-TLR-505-UT: test_calculate_metrics_after_optimization_success
- API-TLR-506-UT: test_calculate_metrics_service_failure

#### 整合測試 Test IDs (✅ 已實作)
- API-TLR-521-IT: test_successful_tailoring_with_keyword_tracking
- API-TLR-522-IT: test_no_keywords_removed_no_warning
- API-TLR-523-IT: test_validation_error_too_short
- API-TLR-524-IT: test_external_service_error
- API-TLR-525-IT: test_system_internal_error
- API-TLR-526-IT: test_service_error_handling

#### 效能測試 Test IDs (✅ 已實作)
- API-TLR-541-PT: test_keyword_detection_performance
- API-TLR-542-PT: test_keyword_categorization_performance
- API-TLR-543-PT: test_full_api_response_time

### 8.3 關鍵教訓應用

按照 Gap Analysis V2 重構的經驗教訓，Resume Tailoring 測試實作：

1. **LLM Factory 使用** ✅
   - 所有 LLM 調用都通過 `get_llm_client` 
   - 不直接使用 OpenAI SDK
   - 使用正確的 API 名稱映射

2. **Test ID 標記** ✅
   - 每個測試方法都有 Test ID 註釋
   - 文檔字串中包含 Test ID
   - 遵循 `# Test ID: API-TAILOR-XXX-YY` 格式

3. **Mock 策略** ✅
   - 單元測試：完全 Mock 外部依賴
   - 整合測試：Mock LLM，保留內部邏輯
   - 效能測試：Mock LLM 回應時間模擬真實延遲

4. **防禦性設計** ✅
   - 關鍵字變體匹配處理 LLM 不一致性
   - 縮寫對應增強容錯性
   - 空值和邊界條件處理

---

**文檔結束** - 版本 1.0.0 | 測試規格與實作已完成 ✅

**實作完成摘要**：
1. ✅ 建立 `test/unit/services/test_resume_tailoring_metrics.py` - 6個單元測試
2. ✅ 更新 `test/integration/test_resume_tailoring_api.py` - 6個整合測試  
3. ✅ 建立 `test/performance/test_resume_tailoring_performance.py` - 3個效能測試
4. ✅ 更新 `pre_commit_check_advanced.py` 加入 Resume Tailoring 測試套件
5. ✅ 所有測試都使用新的 API-TLR-XXX-YY Test ID 格式

**測試統計總計**：
- **單元測試**: 6個 (API-TLR-501-UT ~ API-TLR-506-UT)
- **整合測試**: 6個 (API-TLR-521-IT ~ API-TLR-526-IT)  
- **效能測試**: 3個 (API-TLR-541-PT ~ API-TLR-543-PT)
- **總測試數**: 15個測試

**執行驗證**：
```bash
# 執行所有 Resume Tailoring 測試
python test/scripts/pre_commit_check_advanced.py --option resume-tailoring

# 或分別執行
pytest test/unit/services/test_resume_tailoring_metrics.py -v
pytest test/integration/test_resume_tailoring_api.py -v  
pytest test/performance/test_resume_tailoring_performance.py -v

# Ruff 檢查
ruff check test/unit/services/test_resume_tailoring_metrics.py --line-length=120
ruff check test/integration/test_resume_tailoring_api.py --line-length=120
ruff check test/performance/test_resume_tailoring_performance.py --line-length=120
```