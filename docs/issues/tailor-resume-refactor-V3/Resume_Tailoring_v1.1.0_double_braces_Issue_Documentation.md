# Resume Tailoring v1.1.0 完整技術文檔

**文檔版本**: 1.0.0  
**建立日期**: 2025-08-29  
**作者**: WenHao + Claude Code  
**狀態**: 已部署生產環境 ✅

---

## 目錄

1. [執行摘要](#執行摘要)
2. [系統架構](#系統架構)
3. [問題分析與解決方案](#問題分析與解決方案)
4. [技術實施](#技術實施)
5. [Prompt 規範](#prompt-規範)
6. [測試與驗證](#測試與驗證)
7. [部署狀態](#部署狀態)
8. [未來建議](#未來建議)

---

## 執行摘要

Resume Tailoring v1.1.0 成功解決了 JSON 轉義問題並整合了 enhancement fields 功能。透過實施 SafePromptFormatter 解決方案，系統現在能穩定處理包含 JSON 範例的 prompt 模板，同時支援履歷增強功能。

### 關鍵成就
- ✅ 解決了 Production API 的 KeyError 問題
- ✅ 成功整合 `resume_enhancement_project` 和 `resume_enhancement_certification`
- ✅ 所有 240 個測試通過，系統穩定運行
- ✅ 處理時間維持在 7-8 秒內，效能良好

---

## 系統架構

### v1.1.0 雙 LLM 管線架構

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Request                           │
│  (Bubble API Connector / Direct API Call)                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│               ResumeTailoringServiceV31                      │
│                  (Python Pre-processor)                      │
├─────────────────────────────────────────────────────────────┤
│ • Parse original_index with enhancement fields               │
│ • Preprocess certifications by skill                         │
│ • Prepare parallel LLM bundles                               │
└──────────┬────────────────────────────────┬─────────────────┘
           │                                │
    Parallel Execution                      │
           │                                │
           ▼                                ▼
┌──────────────────────┐        ┌──────────────────────────┐
│   LLM1 (Core)        │        │   LLM2 (Additional)       │
│  v1.0.0-resume-core  │        │ v1.1.0-resume-additional │
├──────────────────────┤        ├──────────────────────────┤
│ • Professional Summary│        │ • Education (Enhanced)    │
│ • Core Competencies  │        │ • Projects (Personal)     │
│ • Experience         │        │ • Certifications (New)    │
│                      │        │ • Supplementary Details   │
└──────────┬───────────┘        └────────────┬─────────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 Python Post-processor                        │
├─────────────────────────────────────────────────────────────┤
│ • Merge sections from both LLMs                              │
│ • Apply CSS markers (opt-new, opt-modified)                  │
│ • Calculate metrics and validation                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                   Final Response
```

### 技術堆疊

| 層級 | 技術 | 版本 |
|------|------|------|
| API Framework | FastAPI | 0.104.1 |
| LLM Service | Azure OpenAI | GPT-4.1 |
| Prompt Format | YAML | - |
| Container | Docker | - |
| Deployment | Azure Container Apps | - |

---

## 問題分析與解決方案

### 問題：JSON 轉義衝突

#### 根本原因
YAML prompt 檔案中包含 JSON 格式範例，其中的大括號 `{}` 被 Python `str.format()` 誤認為模板變量占位符。

```python
# 問題示例
template = 'Example: {"name": "{user_name}"}'  
template.format(user_name="Bob")  # KeyError: '"name"'
```

### 解決方案：SafePromptFormatter

#### 實施的解決方案

```python
def safe_format(template: str, **kwargs) -> str:
    """
    Safe format function that handles JSON examples in prompts.
    
    Uses Unicode markers to temporarily replace double braces {{ }}
    to avoid conflicts with str.format().
    """
    # Unicode markers that won't conflict with any normal text
    LEFT_MARKER = '\u27EA'  # ⟪ (Mathematical Left Double Angle Bracket)
    RIGHT_MARKER = '\u27EB'  # ⟫ (Mathematical Right Double Angle Bracket)
    
    # Step 1: Replace {{ and }} with markers
    protected = template.replace('{{', LEFT_MARKER)
    protected = protected.replace('}}', RIGHT_MARKER)
    
    # Step 2: Apply normal str.format()
    formatted = protected.format(**kwargs)
    
    # Step 3: Restore original braces
    result = formatted.replace(LEFT_MARKER, '{').replace(RIGHT_MARKER, '}')
    
    return result
```

#### 解決方案優點
- ✅ 最小程式碼改動
- ✅ 不需修改 YAML 檔案結構
- ✅ 向後完全相容
- ✅ 無外部依賴
- ✅ 效能影響極小（< 5ms）

---

## 技術實施

### 1. 檔案修改清單

| 檔案 | 修改內容 | 狀態 |
|------|---------|------|
| `src/services/resume_tailoring_v31.py` | 新增 `safe_format()` 函數 | ✅ |
| `src/services/resume_tailoring_v31.py` | 更新 `_call_llm1()` 使用 safe_format | ✅ |
| `src/services/resume_tailoring_v31.py` | 更新 `_call_llm2()` 使用 safe_format | ✅ |
| `src/prompts/resume_tailoring/v1.1.0-resume-additional.yaml` | 修正所有 `\{` 為 `{{` | ✅ |
| `test/unit/test_safe_prompt_formatter.py` | 新增 19 個單元測試 | ✅ |
| `.github/workflows/ci-cd-main.yml` | 更新版本檢測邏輯 | ✅ |

### 2. Enhancement Fields 整合

#### 新增欄位結構

```json
{
  "resume_enhancement_project": {
    "proj001": {
      "name": "Project Name",
      "description": "Project description",
      "related_skill": "Skill Category"
    }
  },
  "resume_enhancement_certification": {
    "cert001": {
      "name": "Certification Name",
      "provider": "Provider Name",
      "related_skill": "Skill Category"
    }
  }
}
```

#### 預處理邏輯

```python
def _preprocess_enhancement_certifications(self, certifications) -> dict:
    """Group certifications by skill and format as HTML."""
    from collections import defaultdict
    from datetime import datetime
    
    if not certifications:
        return {}
    
    current_year = datetime.now().year
    skill_groups = defaultdict(list)
    
    # Handle both list and dict formats
    cert_list = []
    if isinstance(certifications, dict):
        for _cert_id, cert_data in certifications.items():
            if isinstance(cert_data, dict):
                cert_list.append(cert_data)
    elif isinstance(certifications, list):
        cert_list = certifications
        
    for cert in cert_list:
        if not isinstance(cert, dict):
            continue
        skill = cert.get('related_skill', '')
        if skill:
            name = cert.get('name', '')
            provider = cert.get('provider', '')
            if name and provider:
                html = f'<li class="opt-new"><strong>{name}</strong> - {provider} | {current_year}</li>'
                skill_groups[skill].append(html)
    
    return dict(skill_groups)
```

---

## Prompt 規範

### v1.1.0-resume-additional Prompt 結構

#### 元數據
```yaml
version: 1.1.0
metadata:
  author: "WenHao + Claude"
  created_at: "2025-08-27T00:00:00Z"
  updated_at: "2025-08-29T14:00:00Z"
  description: "Resume Additional Manager for education, projects, certifications"
  status: "active"
  task: "resume_tailoring"
  model_recommendation: "gpt-4.1"
```

#### LLM 配置
```yaml
llm_config:
  temperature: 0.2
  max_tokens: 5000
  top_p: 0.15
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

### 關鍵處理規則

#### 1. 專案區分規則

```
┌─────────────────────────────────────────────┐
│         PROJECT SECTION RULES                │
├─────────────────────────────────────────────┤
│ ✅ INCLUDE in Projects Section:              │
│ • Personal/side projects                     │
│ • Open source contributions                  │
│ • Hackathon projects                         │
│                                               │
│ ❌ NEVER INCLUDE in Projects:                │
│ • Work/professional projects → Experience    │
│ • Client projects → Experience               │
│ • Academic projects → Education (if enhanced)│
└─────────────────────────────────────────────┘
```

#### 2. 教育增強決策樹

```
IF years_of_experience < 2 OR is_current_student:
    → ENHANCE Education (add courses, GPA, projects)
    → Place BEFORE Experience section
ELSE:
    → STANDARD Education (degree only)
    → Place AFTER Experience section
```

#### 3. 認證處理流程（v1.1.0 簡化版）

1. **Python 預處理**（已完成）：
   - 按技能分組認證
   - 格式化為 HTML with CSS classes
   - 提供 `preprocessed_certifications_by_skill`

2. **LLM 選擇**（任務）：
   - 每個技能組選擇一個認證
   - 基於 JD 相關性選擇
   - 與現有認證合併

### CSS 類別參考

| Class | 用途 | 應用場景 |
|-------|------|---------|
| `opt-modified` | 修改的內容 | 增強的段落、改進的描述 |
| `opt-new` | 全新內容 | 新增的認證、專案 |
| `opt-placeholder` | 占位符 | [年份]、[公司]、百分比 |
| `opt-keyword-existing` | 現有關鍵字 | 已匹配的技能關鍵字 |
| `opt-keyword-missing` | 缺失關鍵字 | 新增的關鍵字 |

---

## 測試與驗證

### 測試結果統計

```
╔═════════════════════════════════════════════════════════════════════╗
║                          測試統計總覽                                   ║
╚═════════════════════════════════════════════════════════════════════╝

| 測試分類              | 通過 | 失敗 | 總計 | 耗時   | 狀態 |
|---------------------|------|------|------|--------|------|
| 🔍 Ruff 檢查         | ✅   | -    | -    | 0.0s   | ✅   |
| 🏗️ 服務模組測試      | 47   | 0    | 47   | 1.4s   | ✅   |
| 🛡️ Error Handler    | 30   | 0    | 30   | 1.7s   | ✅   |
| 🩺 Health & Keyword  | 16   | 0    | 16   | 1.2s   | ✅   |
| 🧮 Index Calculation | 20   | 0    | 20   | 2.8s   | ✅   |
| 📈 Gap Analysis      | 62   | 0    | 62   | 26.6s  | ✅   |
| 📚 Course Availability| 29   | 0    | 29   | 0.7s   | ✅   |
| 📊 Course Batch Query | 19   | 0    | 19   | 2.3s   | ✅   |
| 📝 Resume Tailoring   | 16   | 0    | 16   | 0.4s   | ✅   |
| 🎯 總計              | 240  | 0    | 240  | 37.5s  | ✅   |
```

### API 測試結果

```json
{
  "success": true,
  "optimized_resume": "[完整優化後的履歷 HTML]",
  "applied_improvements": [
    "[Structure: Summary] Modified: integrated 3 core strengths",
    "[Quick Win: Skills] Reorganized: 4 categories created",
    "[Presentation Gap: Experience] Enhanced: 7 improvements applied",
    "[Structure: Education] Standard: HIGHEST degree only",
    "[Skill Gap: Projects] Added: 3 enhancement projects",
    "[Skill Gap: Certifications] Added: 4 new certifications"
  ],
  "total_processing_time_ms": 7041,
  "llm1_processing_time_ms": 6891,
  "llm2_processing_time_ms": 4512
}
```

---

## 部署狀態

### 生產環境資訊

| 項目 | 值 |
|------|-----|
| **Container App** | airesumeadvisor-api-production |
| **Resource Group** | airesumeadvisorfastapi |
| **Region** | Japan East |
| **API Endpoint** | https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io |
| **Active Revision** | 20250829063534 |
| **Deployment Status** | ✅ Success |

### GitHub Actions CI/CD

```yaml
# 版本檢測邏輯
if [ -f "src/prompts/resume_tailoring/v1.0.0-resume-core.yaml" ] && \
   [ -f "src/prompts/resume_tailoring/v1.1.0-resume-additional.yaml" ]; then
  CORE_ACTIVE=$(grep -c 'status:.*active' "src/prompts/resume_tailoring/v1.0.0-resume-core.yaml")
  ADDITIONAL_V11_ACTIVE=$(grep -c 'status:.*active' "src/prompts/resume_tailoring/v1.1.0-resume-additional.yaml")
  if [ "$CORE_ACTIVE" -gt 0 ] && [ "$ADDITIONAL_V11_ACTIVE" -gt 0 ]; then
    TAILOR_VERSION="1.1.0-dual"
  fi
fi
```

---

## 未來建議

### 短期改進（1-2 週）

1. **監控增強**
   - 添加 SafePromptFormatter 效能指標
   - 追蹤 enhancement fields 使用率
   - 監控 LLM 回應品質

2. **文檔更新**
   - 建立 Prompt 編寫指南
   - 更新 API 文檔包含 enhancement fields
   - 創建整合範例

### 中期優化（1-3 個月）

1. **架構改進**
   - 評估遷移到 Jinja2 模板引擎
   - 實施 Prompt 版本管理系統
   - 優化並行處理邏輯

2. **功能擴展**
   - 支援更多 enhancement 類型
   - 實施 A/B 測試框架
   - 添加多語言支援

### 長期策略（3-6 個月）

1. **重構建議**
   - 將 JSON 範例從 YAML 分離
   - 建立獨立的 Prompt 管理服務
   - 實施微服務架構

2. **標準化**
   - 建立組織級 Prompt 標準
   - 創建可重用的 Prompt 組件庫
   - 制定版本遷移策略

---

## 結論

Resume Tailoring v1.1.0 成功解決了技術挑戰並實現了功能擴展。透過 SafePromptFormatter 解決方案，系統現在能穩定處理複雜的 prompt 模板，同時支援動態的履歷增強功能。所有測試通過，生產環境穩定運行，為未來的功能擴展奠定了堅實基礎。

### 關鍵學習

1. **模板系統設計**：在設計 prompt 系統時需考慮多層技術棧的相容性
2. **簡單解決方案**：Unicode 標記替換證明是簡單有效的解決方案
3. **測試覆蓋重要性**：完整的測試套件確保了解決方案的穩定性
4. **文檔的價值**：詳細的技術文檔加速了問題解決和知識傳承

---

**文檔維護**  
最後更新：2025-08-29  
下次審查：2025-09-30  
聯絡人：Technical Architecture Team

---

*本文檔整合了 8D Report、v1.1.0 Prompt Complete Documentation 和 SafePromptFormatter Solution 的所有內容*