# 指數計算與差距分析（Index Calculation and Gap Analysis）

## 功能概述

結合履歷匹配指數計算與深度差距分析，提供求職者全面的職位適配度評估和改進建議。這是一個組合型 API，同時執行兩項核心分析。

## API 端點

`POST /api/v1/index-cal-and-gap-analysis`

## 核心功能

### 1. 履歷匹配指數計算
- **相似度評分**：使用 Azure OpenAI Embeddings 計算履歷與職缺的語義相似度
- **關鍵字覆蓋分析**：評估履歷中職缺關鍵字的覆蓋程度
- **雙重評分機制**：
  - 原始相似度（Raw Similarity）：直接的餘弦相似度
  - 轉換相似度（Transformed Similarity）：經 Sigmoid 函數優化的分數

### 2. 差距分析（Gap Analysis）
- **核心優勢識別**：找出候選人與職位要求高度匹配的 3-5 項優勢
- **關鍵差距分析**：識別影響候選資格的 3-5 項關鍵缺失
- **快速改進建議**：提供 3-5 項立即可執行的履歷優化建議
- **整體評估報告**：150-250 字的綜合評估，包含適配度和成功機率
- **技能發展優先級**：基於差距分析推薦 3-6 項需要學習的技能

### 3. 多語言支援
- 英文（en）- 預設
- 繁體中文（zh-TW）
- 自動保持輸出語言與請求一致

## 技術實作

### 處理流程
```
請求接收
    │
    ├─> 指數計算（並行處理）
    │   ├─> 履歷 Embedding 生成
    │   ├─> 職缺 Embedding 生成
    │   └─> 關鍵字覆蓋分析
    │       ├─> matched_keywords (匹配的關鍵字)
    │       └─> missing_keywords (缺失的關鍵字)
    │
    └─> 差距分析（依賴指數計算結果）
        ├─> 接收 matched_keywords 和 missing_keywords
        ├─> LLM 分析（GPT-4）- 使用關鍵字匹配資訊
        ├─> 結構化解析
        └─> HTML 格式化
    │
    └─> 結果整合與返回
```

### 關鍵技術組件
1. **IndexCalculationService**
   - Embedding 生成：text-embedding-3-large
   - 相似度計算：Cosine Similarity
   - Sigmoid 轉換：x0=0.373, k=15.0

2. **GapAnalysisService**
   - LLM 模型：gpt-4.1-japan (部署在 Japan East)
   - 重試機制：最多 3 次，指數退避
   - 空欄位檢測與自動重試
   - 依賴 IndexCalculationService 的關鍵字匹配結果

### 效能特性
- **並行處理**：Embedding 生成採用並行處理
- **錯誤重試**：Gap Analysis 具備智能重試機制
- **監控追蹤**：詳細的時間分解和指標收集

## 使用範例

### 請求範例

```python
import requests

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/index-cal-and-gap-analysis",
    headers={"X-API-Key": "YOUR_API_KEY"},
    json={
        # resume 可以是 HTML 或純文字格式，系統會自動處理 HTML 標籤
        "resume": """
        Senior Software Engineer with 8+ years of experience in Python and cloud technologies.
        Expertise in FastAPI, Django, and microservices architecture.
        Led development teams and delivered scalable solutions for enterprise clients.
        """,
        "job_description": """
        Seeking a Python Full Stack Developer with 5+ years of experience.
        Required: Python, FastAPI, React, Docker, Kubernetes, AWS.
        Experience with CI/CD pipelines and DevOps practices is essential.
        """,
        "keywords": ["Python", "FastAPI", "React", "Docker", "Kubernetes", "AWS", "CI/CD", "DevOps"],
        "language": "en"  # 或 "zh-TW"
    }
)
```

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
          "skill_category": "SKILL",
          "description": "Frontend framework for building interactive user interfaces required for full-stack role",
          "has_available_courses": true,
          "course_count": 25
        },
        {
          "skill_name": "Kubernetes", 
          "skill_category": "FIELD",
          "description": "Container orchestration platform essential for modern DevOps practices",
          "has_available_courses": true,
          "course_count": 12
        },
        {
          "skill_name": "AWS",
          "skill_category": "FIELD",
          "description": "Cloud platform knowledge required for deploying and managing applications",
          "has_available_courses": true,
          "course_count": 18
        }
      ]
    },
    "resume_structure": {
      "standard_sections": {
        "summary": "Professional Summary",
        "skills": "Technical Skills",
        "experience": "Work Experience",
        "education": "Education",
        "certifications": null,
        "projects": null
      },
      "custom_sections": ["Languages", "Publications"],
      "metadata": {
        "total_experience_entries": 3,
        "total_education_entries": 1,
        "has_quantified_achievements": true,
        "estimated_length": "2 pages"
      }
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

## 差距分析詳解

### 1. 核心優勢（Core Strengths）
識別候選人相對於職位要求的優勢：
- 直接匹配的技術技能
- 超越要求的經驗年資
- 相關的成就和專案經驗
- 可轉移的技能和知識

### 2. 關鍵差距（Key Gaps）
分析影響候選資格的缺失：
- 技術技能差距（工具、軟體、方法論）
- 經驗差距（產業、職級、特定職能）
- 知識差距（領域專業、認證、方法論）
- 按重要性排序的差距

### 3. 快速改進（Quick Improvements）
提供立即可執行的履歷優化建議：
- 調整措辭以更好匹配職缺語言
- 添加細節以突出相關經驗
- 重組建議以提升影響力
- 量化現有成就的機會
- 關鍵字整合建議

### 4. 整體評估（Overall Assessment）
平衡的綜合評估包含：
- 目前的適配度和競爭力
- 最關鍵的改進領域
- 縮小差距的實際時間表
- 定位策略建議
- 信心水平和成功機率

### 5. 技能發展優先級（SkillSearchQueries）
基於差距分析的學習建議：
- 可通過課程/培訓發展的具體技能
- 按對工作成功的影響和學習可行性排序
- 技術和非技術技能的混合
- 足夠具體以便課程匹配
- 考慮候選人當前水平和學習路徑

**技能分類說明 (v2.1.8+)**：
- **SKILL**: 透過單一課程快速學習的技能 (1-3 個月)
  - 例如：React、Docker、Python框架
  - 特徵：具體工具、語言框架、短期可掌握
- **FIELD**: 需要專業認證或深度學習的領域 (6+ 個月)
  - 例如：Kubernetes、AWS、Machine Learning
  - 特徵：複雜系統、需要實務經驗、長期投資

**課程可用性資訊**：
- `has_available_courses`: 是否有相關課程可供學習
- `course_count`: 可用課程數量，由 Course Availability 服務提供

### 6. 履歷結構分析（Resume Structure）- V4 新增功能
使用 GPT-4.1 mini 快速分析履歷結構，識別區塊組織和內容特徵：

**standard_sections（標準區塊映射）**：
- 偵測六個標準履歷區塊的標題
- 每個欄位的值為實際區塊標題（如 "Professional Summary"）或 null（表示不存在）
- 包含：summary、skills、experience、education、certifications、projects

**custom_sections（自定義區塊）**：
- 識別非標準但常見的履歷區塊
- 例如：Languages（語言能力）、Publications（出版物）、Awards（獎項）

**metadata（結構元數據）**：
- `total_experience_entries`：工作經歷項目數量
- `total_education_entries`：教育背景項目數量
- `has_quantified_achievements`：是否包含量化成就（數字、百分比、指標）
- `estimated_length`：預估頁數（"1 page"、"2 pages" 等）

## 效能指標

### 回應時間
- **平均總時間**：3-5 秒（目標：< 4 秒）
- **指數計算**：1-2 秒
- **差距分析**：2-3 秒
- **並行處理優化**：節省約 30% 時間

### 準確度與品質
- **相似度計算一致性**：> 95%
- **差距分析完整性**：90%（具有重試機制）
- **多語言支援品質**：英文和中文同等品質

## 最佳實踐

### 輸入準備
1. **履歷內容**
   - 提供完整、結構化的履歷
   - 包含技能、經驗、成就等關鍵資訊
   - HTML 或純文字格式均可（系統會使用 `clean_html_text` 自動處理 HTML 標籤）

2. **職缺描述**
   - 完整的職位要求和責任描述
   - 明確列出必要和優先的技能
   - 保持原始格式

3. **關鍵字列表**
   - 從職缺中提取的關鍵技能和要求
   - 可使用關鍵字提取 API 預處理
   - 支援陣列或逗號分隔字串

### 結果解讀
1. **匹配指數**
   - 75% 以上：高度匹配
   - 60-74%：中等匹配，需要一些改進
   - 45-59%：部分匹配，需要顯著提升
   - 45% 以下：匹配度低，需要大幅改進

2. **差距分析應用**
   - 優先處理快速改進建議
   - 根據技能發展優先級制定學習計劃
   - 使用整體評估調整求職策略

## 限制與注意事項

### 技術限制
- 最大文本長度：履歷 30KB，職缺 30KB（純文本約 2000 字）
- 關鍵字數量：建議 5-25 個
- 語言限制：僅支援英文和繁體中文

### 分析限制
1. 無法評估軟性因素（如文化契合度）
2. 不考慮地理位置或薪資要求
3. 技能評估基於文本匹配，可能遺漏隱含能力

### API 限制
- 請求頻率限制：遵循整體 API 配額
- 回應時間：高峰期可能稍有延長
- 並發請求：建議控制在合理範圍

## 錯誤處理

### 常見錯誤
| 錯誤碼 | 說明 | 解決方案 |
|--------|------|----------|
| VALIDATION_ERROR | 輸入驗證失敗 | 檢查必填欄位和格式 |
| TEXT_TOO_SHORT | 文本長度不足 | 確保履歷/職缺有足夠內容 |
| SERVICE_ERROR | 服務暫時不可用 | 稍後重試 |
| LANGUAGE_NOT_SUPPORTED | 不支援的語言 | 使用 en 或 zh-TW |

### 重試策略
- Gap Analysis 具有內建重試機制（最多 3 次）
- 客戶端建議實施指數退避重試
- 監控空欄位警告並適當處理

## 未來改進方向

### 短期優化
- **快取機制**：為相同輸入實施結果快取
- **批次處理**：支援多個履歷同時分析
- **更精確的技能匹配**：整合技能標準化服務

### 中期增強
- **產業特定分析**：根據不同產業調整評估標準
- **視覺化報告**：生成圖表和視覺化分析結果
- **歷史追蹤**：追蹤候選人改進進度

### 長期願景
- **AI 驅動的改進建議**：更智能的個人化建議
- **即時互動分析**：支援即時調整和重新分析
- **整合學習平台**：直接連結到推薦的學習資源

## V2 版本說明

### 升級中的 V2 API

正在開發中的 V2 版本 (`/api/v1/index-cal-and-gap-analysis-v2`) 將提供：

1. **效能優化**
   - 利用 IndexCalculationServiceV2 的快取機制
   - 預期 P50 < 2秒，P95 < 4秒
   - 減少重複 embedding 計算

2. **完全向後相容**
   - 保持相同的回應格式
   - 新增可選的效能指標欄位
   - 支援漸進式升級

3. **增強功能**
   - 部分結果支援（如 gap analysis 失敗時仍返回 index 結果）
   - 更詳細的服務時間分解
   - 智能重試機制

V2 版本目前處於規劃階段，將在完成測試後逐步部署。

## 相關功能

- [關鍵字提取](keyword_extraction.md) - 預處理職缺關鍵字
- [履歷客製化](resume_tailoring.md) - 基於差距分析優化履歷
- [課程搜尋](course_search.md) - 尋找技能發展資源