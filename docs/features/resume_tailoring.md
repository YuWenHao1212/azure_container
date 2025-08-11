# 履歷客製化功能 (v2.1.0-simplified)

## 功能概述

運用 AI 技術根據特定職缺要求客製化履歷內容，使用混合式 CSS 標記系統追蹤關鍵字變化，在保持真實性的前提下優化表達方式以提高匹配度。

**v2.1.0-simplified 核心創新** 🚀
- **混合式 CSS 標記**：LLM 語意標記 + Python 關鍵字後處理
- **關鍵字追蹤機制**：自動追蹤 still_covered、removed、newly_added、still_missing 四種狀態
- **防禦性變體匹配**：自動處理關鍵字變體（CI/CD ↔ CI-CD、Node.js ↔ NodeJS）
- **縮寫雙向對應**：智能識別縮寫（ML ↔ Machine Learning）
- **提示詞精簡**：從 10,534 字元降至 5,637 字元（減少 47%）
- **效能優化**：P50 < 2.5秒（比 v2.0.0 快 44%）

## API 端點

`POST /api/v1/tailor-resume`

## 核心功能

### 1. 混合式 CSS 標記系統
- **LLM 語意標記**：由 GPT-4.1 智能判斷並添加 CSS 類別
- **Python 後處理**：精確驗證和補充關鍵字標記
- **四種 CSS 類別**：
  - `skill-highlight`: 原有且保持的技能（藍色）
  - `keyword-added`: 新增的關鍵字（綠色）
  - `skill-gap`: 技能缺口內容（橘色）
  - `improvement-metric`: 量化成就（粗體）

### 2. 關鍵字追蹤機制
- **still_covered**: 原本有、現在仍有的關鍵字
- **removed**: 原本有、但被移除的關鍵字（觸發警告）
- **newly_added**: 原本沒有、新增的關鍵字
- **still_missing**: 原本沒有、現在仍沒有的關鍵字

### 3. 防禦性設計
- **變體匹配**：
  - CI/CD = CI-CD = CI CD
  - Node.js = NodeJS = Node
  - React.js = ReactJS = React
- **縮寫對應**（雙向）：
  - ML ↔ Machine Learning
  - AI ↔ Artificial Intelligence
  - NLP ↔ Natural Language Processing
  - API ↔ Application Programming Interface
  - CI/CD ↔ Continuous Integration/Continuous Deployment
- **大小寫不敏感**：python = Python = PYTHON
- **部分匹配**："JavaScript" 可匹配 "JS"

### 4. 智能改寫策略
- **關鍵字融入**：自然嵌入職缺關鍵字
- **經驗強調**：突顯相關工作經歷
- **成就量化**：加入具體數據支撐
- **Gap 處理**：
  - [Skill Gap]：策略性定位可轉移技能
  - [Presentation Gap]：明確展示已有技能

## 技術實作

### v2.1.0-simplified 兩階段架構

#### Stage 1: Instruction Compiler (GPT-4.1 mini)
- **目的**：分析履歷結構並編譯優化指令
- **模型**：GPT-4.1 mini（成本降低 200x）
- **處理時間**：~280ms
- **輸出**：結構化分析結果

#### Stage 2: Resume Writer (GPT-4.1)
- **目的**：執行履歷優化並添加 CSS 標記
- **模型**：GPT-4.1 (Japan East deployment)
- **處理時間**：~2100ms
- **輸出**：優化後的 HTML 履歷（含 CSS 標記）

### 處理流程
```python
1. 接收請求並驗證（最少 200 字元）
2. Stage 1: Instruction Compiler
   - 分析履歷結構（sections、metadata）
   - 識別改進機會
   - 編譯優化指令
3. Stage 2: Resume Writer
   - 執行優化指令
   - 添加 CSS 標記（LLM 語意判斷）
   - 整合缺失關鍵字
4. Python 後處理
   - 檢測關鍵字存在（_detect_keywords_presence）
   - 分類關鍵字狀態（_categorize_keywords）
   - 驗證和補充 CSS 標記
5. IndexCalculationServiceV2 計算準確指標
   - 使用 Azure OpenAI embeddings 計算相似度
   - 如果服務失敗，拋出 ServiceError（不使用估算值）
6. 返回結果（含警告訊息）或錯誤響應
```

### 關鍵方法實作

#### 關鍵字檢測
```python
def _detect_keywords_presence(html_content: str, keywords: List[str]) -> Set[str]:
    """
    防禦性關鍵字檢測，處理變體和縮寫
    - 移除 HTML 標籤
    - 正規化文字（小寫、移除特殊字元）
    - 建立關鍵字模式（含變體）
    - 匹配並返回找到的關鍵字
    """
```

#### 關鍵字分類
```python
def _categorize_keywords(
    originally_covered: Set[str],
    currently_covered: Set[str],
    covered_keywords: List[str],
    missing_keywords: List[str]
) -> Dict:
    """
    分類關鍵字為四種狀態
    - still_covered: 原有且保持
    - removed: 原有但被移除（警告）
    - newly_added: 新增的關鍵字
    - still_missing: 仍然缺少
    """
```

## 使用範例

### 請求範例 (v2.1.0-simplified)
```python
import requests

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/tailor-resume",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        "job_description": "Senior Backend Engineer with Python, Docker, Kubernetes...",  # 最少 200 字元
        "original_resume": "<html><body><h2>John Smith</h2><p>Python developer...</p></body></html>",
        "gap_analysis": {
            "core_strengths": ["Python expertise", "API development", "Team leadership"],
            "key_gaps": [
                "[Skill Gap] Kubernetes orchestration",
                "[Presentation Gap] Docker containerization"
            ],
            "quick_improvements": ["Add Docker projects", "Get Kubernetes certification"],
            "covered_keywords": ["Python", "API", "SQL"],
            "missing_keywords": ["Kubernetes", "Docker", "GraphQL"],
            "coverage_percentage": 60,
            "similarity_percentage": 70
        },
        "options": {
            "language": "en",
            "include_visual_markers": True  # 啟用 CSS 標記
        }
    }
)

result = response.json()
```

### 成功回應範例
```json
{
  "success": true,
  "data": {
    "optimized_resume": "<h2>John Smith</h2>
<p>Senior Backend Engineer with <span class='skill-highlight'>Python</span> expertise...</p>
<ul>
  <li>Implemented <span class='keyword-added'>Docker</span> containerization reducing deployment time by 70%</li>
  <li>Built scalable <span class='skill-highlight'>APIs</span> serving 1M+ requests/day</li>
  <li>Preparing for <span class='skill-gap'>Kubernetes</span> certification</li>
</ul>",
    "applied_improvements": "<ul>
  <li>Highlighted Docker containerization experience</li>
  <li>Quantified API performance metrics</li>
  <li>Added Kubernetes learning initiative</li>
</ul>",
    "improvement_count": 3,
    "keyword_tracking": {
      "still_covered": ["Python", "API", "SQL"],
      "removed": [],
      "newly_added": ["Docker"],
      "still_missing": ["Kubernetes", "GraphQL"],
      "warnings": []
    },
    "coverage": {
      "before": {
        "percentage": 60,
        "covered": ["Python", "API", "SQL"],
        "missed": ["Kubernetes", "Docker", "GraphQL"]
      },
      "after": {
        "percentage": 73,
        "covered": ["Python", "API", "SQL", "Docker"],
        "missed": ["Kubernetes", "GraphQL"]
      },
      "improvement": 13,
      "newly_added": ["Docker"]
    },
    "processing_time_ms": 2380,
    "stage_timings": {
      "instruction_compilation_ms": 280,
      "resume_writing_ms": 2100
    }
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "details": []
  }
}
```

### 服務失敗錯誤回應範例
當 IndexCalculationServiceV2 無法計算準確指標時：
```json
{
  "success": false,
  "data": null,
  "error": {
    "has_error": true,
    "code": "SERVICE_CALCULATION_ERROR",
    "message": "Failed to calculate similarity metrics",
    "details": "Please try again later",
    "field_errors": {}
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "details": []
  }
}
```

**重要說明**：為確保資料準確性，當 IndexCalculationServiceV2 失敗時系統會返回錯誤而非使用不準確的估算值。這確保了所有回應的指標都是基於實際計算結果。

## 效能指標

### v2.1.0-simplified 效能提升
| 指標 | v1.0 | v2.0.0 | v2.1.0-simplified | 改善 |
|------|------|--------|-------------------|------|
| P50 回應時間 | 7.2s | 4.5s | 2.5s | -44% |
| P95 回應時間 | 11.5s | 7.8s | 4.2s | -46% |
| Token 使用量 | 15K | 12K | 8.5K | -29% |
| Prompt 長度 | 15K字 | 10.5K字 | 5.6K字 | -47% |
| API 成本 | $0.15 | $0.08 | $0.045 | -44% |

### 關鍵字追蹤效能
- 關鍵字檢測：P50 < 50ms, P95 < 100ms
- 關鍵字分類：P50 < 10ms, P95 < 20ms
- 變體匹配開銷：< 5ms
- 縮寫對應開銷：< 3ms

## 品質保證

### 測試覆蓋
- **單元測試**：關鍵字檢測、分類、變體匹配
- **整合測試**：API 端點、錯誤處理、警告機制
- **效能測試**：回應時間、關鍵字處理效能
- **Test ID 標準**：所有測試都有 API-TAILOR-XXX-YY 標記

### 防禦性設計驗證
- 處理 LLM 輸出變異性
- 關鍵字大小寫不敏感
- 特殊字元正規化（- _ . /）
- 縮寫雙向查找
- HTML 標籤過濾
- 空值和邊界條件處理

## 注意事項

1. **最少字元要求**：JD 和履歷都需要至少 200 字元
2. **關鍵字移除警告**：當原有關鍵字被移除時會觸發警告
3. **覆蓋率上限**：覆蓋率最高 100%，不會超過
4. **LLM Factory 使用**：所有 LLM 調用必須通過 LLM Factory
5. **CSS 標記相容性**：確保前端正確渲染 CSS 類別
6. **服務依賴**：IndexCalculationServiceV2 失敗時將返回 SERVICE_CALCULATION_ERROR，不使用估算值

## 錯誤處理

### SERVICE_CALCULATION_ERROR
當 IndexCalculationServiceV2 無法計算準確的相似度指標時：
- **觸發條件**：Azure OpenAI 服務不可用、網路問題、API 超時等
- **回應行為**：返回錯誤而非不準確的估算值
- **錯誤格式**：
```json
{
  "success": false,
  "error": {
    "code": "SERVICE_CALCULATION_ERROR",
    "message": "Failed to calculate similarity metrics",
    "details": "Please try again later"
  }
}
```

### 其他錯誤類型
- **VALIDATION_TOO_SHORT**：輸入內容少於 200 字元
- **EXTERNAL_RATE_LIMIT_EXCEEDED**：AI 服務請求頻率限制
- **EXTERNAL_SERVICE_TIMEOUT**：AI 服務處理超時
- **SYSTEM_INTERNAL_ERROR**：系統內部錯誤

## 相關功能

- [差距分析](gap_analysis.md) - 提供 gap_analysis 輸入
- [匹配指數計算](index_calculation.md) - 提供覆蓋率和相似度
- [關鍵字提取](keyword_extraction.md) - 職缺關鍵字識別

## 版本歷史

- **v2.1.0-simplified** (2025-08-11)：混合式 CSS 標記 + 關鍵字追蹤 + 移除 fallback 機制
  - 混合式 CSS 標記系統（LLM 語意標記 + Python 後處理）
  - 關鍵字追蹤機制（still_covered, removed, newly_added, still_missing）
  - **重要變更**：移除 IndexCalculationServiceV2 失敗時的 fallback 估算值
  - 新增 SERVICE_CALCULATION_ERROR 錯誤處理
  - 提升資料準確性，確保所有指標都是實際計算結果
- **v2.0.0** (2025-08-10)：兩階段架構實作
- **v1.0.0** (2025-07-20)：初始版本發布

---

**文檔版本**: 2.1.0  
**最後更新**: 2025-08-11  
**維護團隊**: AI Resume Advisor Development Team