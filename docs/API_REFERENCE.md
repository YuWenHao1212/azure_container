# API 參考文檔

## 基礎資訊

### Base URL

**生產環境 (Container Apps)** ✅ 正在開發重構中
```
https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
```
目前狀態：已完成 health 和 keyword extraction 端點

**開發環境 (Container Apps)** ⏸️ 未來規劃
```
https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
```
目前狀態：預留給未來使用，尚無活動

### 認證

Container Apps 支援兩種認證方式：

1. **Header 認證** (推薦)：
```
X-API-Key: [YOUR_API_KEY]
```

2. **Query Parameter 認證** (Function Apps 相容模式)：
```
?code=[YOUR_API_KEY]
```

> 💡 **最佳實踐**：建議使用 Header 認證方式，更安全且符合 RESTful 標準。Query Parameter 認證主要用於向後相容。

### API 版本
目前版本：v1

### 健康檢查端點
- `/health` - 系統整體健康狀態

**實際回應範例**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-08-02T01:24:59.031372"
  },
  "timestamp": "2025-08-02T01:24:59.031378"
}
```

### 請求格式
- Content-Type: `application/json`
- 字元編碼：UTF-8

### 回應格式
所有 API 回應遵循統一格式：

```json
{
  "success": true,
  "data": {
    // 端點特定資料
  },
  "error": {
    "code": "",
    "message": ""
  }
}
```

## API 端點

### 系統資訊端點

#### 根端點
`GET /` - 獲取 API 基本資訊

**回應範例**
```json
{
  "name": "AI Resume Advisor API",
  "version": "1.0.0",
  "environment": "production",
  "health_check": "/health",
  "documentation": "/docs",
  "api_version": "v1"
}
```

#### API 版本資訊
`GET /api/v1/` - 獲取 v1 API 資訊

**回應範例**
```json
{
  "version": "v1",
  "endpoints": {
    "keyword_extraction": "/api/v1/extract-jd-keywords",
    "index_calculation": "/api/v1/index-calculation",
    "gap_analysis": "/api/v1/index-cal-and-gap-analysis",
    "resume_format": "/api/v1/format-resume",
    "resume_tailoring": "/api/v1/tailor-resume",
    "course_search": "/api/v1/courses/search"
  }
}
```

#### 服務版本
`GET /api/v1/version` - 獲取服務版本和功能資訊

#### Prompt 版本
`GET /api/v1/prompt-version?language=en` - 獲取關鍵字提取的 prompt 版本
`GET /api/v1/prompts/version?task=keyword_extraction&language=en` - 獲取任意任務的 prompt 版本

#### 支援的語言
`GET /api/v1/tailor-resume/supported-languages` - 獲取履歷客製化支援的語言

### 監控與除錯端點 (僅限非生產環境)

#### 監控統計
`GET /api/v1/monitoring/stats` - 獲取 API 使用統計和效能指標

**回應範例**
```json
{
  "requests_total": 1520,
  "requests_by_endpoint": {
    "/api/v1/extract-jd-keywords": 850,
    "/api/v1/tailor-resume": 670
  },
  "average_response_time_ms": 2300,
  "error_rate": 0.02,
  "uptime_hours": 168
}
```

#### 錯誤儲存資訊
`GET /api/v1/debug/storage-info` - 獲取錯誤儲存配置資訊

#### 最近錯誤記錄
`GET /api/v1/debug/errors` - 獲取最近的錯誤記錄 (最多 50 筆)

#### 監控狀態除錯
`GET /debug/monitoring` - 獲取監控系統狀態

> ⚠️ **注意**：監控和除錯端點僅在開發環境中可用，生產環境會返回 404 錯誤。

### 核心功能端點

### 1. 提取職缺關鍵字
`POST /api/v1/extract-jd-keywords`

從職缺描述中提取關鍵技能和要求。

**支援語言**
- 英文 (en)
- 繁體中文 (zh-TW)
- 自動偵測 (auto) - 預設值

**請求參數**
```json
{
  "job_description": "string (最少 50 字元，最多 20000 字元)",
  "max_keywords": 16,  // 選填，預設 16，範圍 5-25
  "language": "auto",  // 選填，"auto"|“en"|“zh-TW"，預設 "auto"
  "prompt_version": "1.4.0",  // 選填，預設 "1.4.0"
  "include_standardization": true,  // 選填，預設 true
  "use_multi_round_validation": true  // 選填，預設 true
}
```

**回應範例**
```json
{
  "success": true,
  "data": {
    "keywords": ["Python", "FastAPI", "Azure", "Docker"],
    "keyword_count": 4,
    "confidence_score": 0.85,
    "extraction_method": "2_round_intersection",
    "processing_time_ms": 2500,
    "detected_language": "en",
    "prompt_version": "1.4.0",
    "intersection_stats": {
      "intersection_count": 15,
      "round1_count": 20,
      "round2_count": 18,
      "final_count": 15,
      "supplement_count": 0,
      "strategy_used": "pure_intersection"
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-07-26T10:30:00.000Z"
}
```

### 2. 計算匹配指數
`POST /api/v1/index-calculation`

計算履歷與職缺的匹配程度。

**請求參數**
```json
{
  "resume": "string (HTML 或純文字)",
  "job_description": "string (HTML 或純文字)",
  "keywords": ["string"] 或 "string"  // 關鍵字陣列或逗號分隔字串
}
```

**回應範例**
```json
{
  "success": true,
  "data": {
    "raw_similarity_percentage": 65,
    "similarity_percentage": 75,  // 轉換後的分數
    "keyword_coverage": {
      "total_keywords": 20,
      "covered_count": 15,
      "coverage_percentage": 75,
      "covered_keywords": ["Python", "API development", "Azure"],
      "missed_keywords": ["Docker", "Kubernetes", "GraphQL", "Redis", "MongoDB"]
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-07-26T10:30:00.000Z"
}
```

### 3. 指數計算與差距分析
`POST /api/v1/index-cal-and-gap-analysis`

同時計算匹配指數並分析履歷差距。

**版本更新 (v2.1.8)** ✨
- SkillSearchQueries 現在包含**課程可用性資訊**：`has_available_courses` 和 `course_count`
- KeyGaps 包含分類標記：`[Skill Gap]` 或 `[Presentation Gap]`
- [Skill Gap]: 候選人真正缺乏此技能，需要學習
- [Presentation Gap]: 候選人具備技能但履歷中未明確展示
- 技能分類更新：SKILL (1-3 月課程) vs FIELD (6+ 月專業認證)

**版本更新 (v4 - 2025-08-14)** 🚀
- 新增 `resume_structure` 欄位，提供履歷結構分析
- 使用 GPT-4.1 mini 快速識別履歷區塊結構
- 偵測標準區塊、自定義區塊及結構元數據
- 透過環境變數 `ENABLE_RESUME_STRUCTURE_ANALYSIS` 控制（預設啟用）

**版本更新 (2025-08-15)** 📊
- 新增 `metadata` 欄位，提供詳細效能計時分析
- 包含各階段執行時間：keyword_matching, embedding_generation, index_calculation, gap_analysis, course_availability, structure_analysis, pgvector_warmup
- 總執行時間和並行處理效率指標

**請求參數**
```json
{
  "resume": "string (HTML 或純文字)",
  "job_description": "string (HTML 或純文字)",
  "keywords": ["string"] 或 "string",  // 關鍵字陣列或逗號分隔字串
  "language": "en"  // 選填，"en"|“zh-TW"，預設 "en"
}
```

**回應範例**
```json
{
  "success": true,
  "data": {
    "raw_similarity_percentage": 65,
    "similarity_percentage": 75,
    "keyword_coverage": {
      "total_keywords": 20,
      "covered_count": 15,
      "coverage_percentage": 75,
      "covered_keywords": ["Python", "API development"],
      "missed_keywords": ["Docker", "Kubernetes"]
    },
    "gap_analysis": {
      "CoreStrengths": "<ul><li>Strong Python background</li><li>API development experience</li></ul>",
      "KeyGaps": "<ul><li>[Skill Gap] Container orchestration (Docker/Kubernetes) - No orchestration experience found</li><li>[Presentation Gap] Cloud deployment - Has AWS experience but not explicitly mentioned</li></ul>",
      "QuickImprovements": "<ul><li>Add 'AWS' explicitly to skills section</li><li>Complete Docker fundamentals course</li></ul>",
      "OverallAssessment": "<p>Good foundation with 75% match. Focus on DevOps skills to reach 90%+.</p>",
      // Skill categories explanation (v2.1.8+):
      // - SKILL: Quick-learn skills via single course (1-3 months)
      // - FIELD: Requires specialization/certification (6+ months)
      "SkillSearchQueries": [
        {
          "skill_name": "React",
          "skill_category": "SKILL",
          "description": "Frontend framework for building interactive user interfaces required for full-stack role",
          "has_available_courses": true,
          "course_count": 25,
          "available_course_ids": [
            "coursera_crse:v1-2598",
            "coursera_crse:v1-2599",
            "coursera_spzn:react-basics",
            "coursera_crse:v1-2601",
            "coursera_crse:v1-2602"
            // ... up to 25 course IDs
          ]
        },
        {
          "skill_name": "Kubernetes",
          "skill_category": "FIELD", 
          "description": "Container orchestration platform essential for modern DevOps practices",
          "has_available_courses": true,
          "course_count": 12,
          "available_course_ids": [
            "coursera_spzn:kubernetes-engine",
            "coursera_crse:v1-1234",
            "coursera_crse:v1-1235"
          ]
        },
        {
          "skill_name": "AWS",
          "skill_category": "FIELD",
          "description": "Cloud platform knowledge required for deploying and managing applications", 
          "has_available_courses": true,
          "course_count": 18,
          "available_course_ids": [
            "coursera_spzn:aws-fundamentals",
            "coursera_crse:v1-3001",
            "coursera_crse:v1-3002",
            "coursera_crse:v1-3003"
          ]
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
    "has_error": false,
    "code": "",
    "message": "",
    "details": ""
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "expected_minimum": 12,
    "actual_extracted": 0,
    "suggestion": ""
  },
  "timestamp": "2025-08-15T10:30:00.000Z",
  "metadata": {
    "phase_timings_ms": {
      "keyword_matching": 15,
      "embedding_generation": 450,
      "index_calculation": 320,
      "gap_analysis": 1800,
      "course_availability": 250,
      "structure_analysis": 180,
      "pgvector_warmup": 45
    },
    "total_time_ms": 3060,
    "parallel_efficiency": 85.2,
    "resource_pool_used": true
  }
}
```

### 4. 格式化履歷
`POST /api/v1/format-resume`

將 OCR 識別的文字轉換成結構化 HTML 履歷。

**請求參數**
```json
{
  "ocr_text": "string (最少 100 字元)",  // OCR 格式: 【Type】:Content
  "supplement_info": {  // 選填，補充資訊
    "name": "string",
    "email": "string",
    "linkedin": "string",
    "phone": "string",
    "location": "string"
  }
}
```

**回應範例**
```json
{
  "success": true,
  "data": {
    "formatted_resume": "<h2>John Smith</h2>\n<p>Email: john@example.com | Phone: +1-234-567-8900</p>\n<h3>Professional Summary</h3>\n<p>Experienced software engineer...</p>",
    "sections_detected": {
      "contact": true,
      "summary": true,
      "skills": true,
      "experience": true,
      "education": true,
      "projects": false,
      "certifications": false
    },
    "corrections_made": {
      "ocr_errors": 5,
      "date_standardization": 3,
      "email_fixes": 1,
      "phone_fixes": 1
    },
    "supplement_info_used": ["email", "phone"]
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  },
  "timestamp": "2025-07-26T10:30:00.000Z"
}
```

### 5. 客製化履歷 (v2.1.0-simplified)
`POST /api/v1/tailor-resume`

根據職缺要求和差距分析結果優化履歷，使用混合式 CSS 標記系統追蹤關鍵字變化。

**版本更新 (v2.1.0-simplified)** 🚀
- **混合式 CSS 標記**：LLM 語意標記 + Python 關鍵字後處理
- **關鍵字追蹤機制**：自動追蹤 still_covered、removed、newly_added、still_missing 四種狀態
- **防禦性變體匹配**：自動處理關鍵字變體（CI/CD ↔ CI-CD、Node.js ↔ NodeJS）
- **縮寫雙向對應**：智能識別縮寫（ML ↔ Machine Learning、NLP ↔ Natural Language Processing）
- **兩階段管線**：Instruction Compiler (GPT-4.1 mini) + Resume Writer (GPT-4.1)
- **效能優化**：P50 < 2.5秒 (比 v2.0.0 快 44%)，成本降低 200x
- **提示詞精簡**：從 10,534 字元降至 5,637 字元 (減少 47%)

**請求參數**
```json
{
  "job_description": "string (200-10000 字元)",  // 最少 200 字元
  "original_resume": "string (200-50000 字元, HTML 格式)",  // 最少 200 字元
  "gap_analysis": {  // 必填 - 來自 Gap Analysis API 的結果
    "core_strengths": ["string"],  // 3-5 項優勢
    "key_gaps": ["string"],  // 3-5 項差距（包含 [Skill Gap] 或 [Presentation Gap] 標記）
    "quick_improvements": ["string"],  // 3-5 項改進建議
    "covered_keywords": ["string"],  // 已涵蓋關鍵字（用於追蹤）
    "missing_keywords": ["string"],  // 缺少關鍵字（用於追蹤）
    "coverage_percentage": 75,  // 選填 - 關鍵字覆蓋率 (0-100)
    "similarity_percentage": 80  // 選填 - 履歷相似度分數 (0-100)
  },
  "options": {  // 選填
    "include_visual_markers": true,  // 預設 true - 啟用 CSS 類別標記
    "language": "en"  // "en"|"zh-TW"，預設 "en"
  }
}
```

**回應範例 (v2.1.0-simplified)**
```json
{
  "success": true,
  "data": {
    "optimized_resume": "<h2>John Smith</h2>
<p>Senior Software Engineer with expertise in <span class='skill-highlight'>Python</span> and cloud technologies...</p>
<ul>
  <li>Led <span class='keyword-added'>Docker</span> containerization reducing deployment time by 70%</li>
  <li>Implemented <span class='skill-highlight'>CI/CD pipelines</span> using Jenkins and GitLab</li>
  <li>Developed <span class='keyword-added'>machine learning</span> models for customer analytics</li>
</ul>",
    "applied_improvements": "<ul>
  <li>Added Docker containerization experience</li>
  <li>Highlighted CI/CD implementation</li>
  <li>Included machine learning projects</li>
  <li>Quantified achievements with metrics</li>
</ul>",
    "improvement_count": 4,
    "keyword_tracking": {
      "still_covered": ["Python", "JavaScript", "CI/CD"],  // 保持涵蓋
      "removed": ["PHP"],  // 被移除（觸發警告）
      "newly_added": ["Docker", "Kubernetes", "Machine Learning"],  // 新增
      "still_missing": ["GraphQL", "Rust"],  // 仍然缺少
      "warnings": ["Warning: 1 originally covered keywords were removed during optimization: PHP"]
    },
    "gap_analysis_insights": {
      "structure_found": {
        "sections": {
          "summary": "Professional Summary",
          "experience": "Work Experience", 
          "skills": "Technical Skills"
        },
        "metadata": {
          "total_sections": 3,
          "has_quantified_achievements": true
        }
      },
      "improvements_applied": 4
    },
    "coverage": {
      "before": {
        "percentage": 40,
        "covered": ["Python", "JavaScript", "CI/CD", "PHP"],
        "missed": ["Docker", "Kubernetes", "Machine Learning", "GraphQL", "Rust"]
      },
      "after": {
        "percentage": 70,  // 上限 100%
        "covered": ["Python", "JavaScript", "CI/CD", "Docker", "Kubernetes", "Machine Learning"],
        "missed": ["GraphQL", "Rust"]
      },
      "improvement": 30,
      "newly_added": ["Docker", "Kubernetes", "Machine Learning"],
      "removed": ["PHP"]  // 被移除的關鍵字（如果有的話）
    },
    "similarity": {
      "before": 60,  // 從 gap_analysis 輸入（不重複計算）
      "after": 85,   // 使用 IndexCalculationServiceV2 真實計算（embedding + cosine similarity + sigmoid）
      "improvement": 25  // 實際差值
    },
    "processing_time_ms": 2450,
    "stage_timings": {
      "instruction_compilation_ms": 280,  // Stage 1: GPT-4.1 mini
      "resume_writing_ms": 2100,  // Stage 2: GPT-4.1
      "keyword_detection_ms": 70  // 關鍵字檢測
    },
    "metadata": {
      "version": "v2.1.0-simplified",
      "pipeline": "two-stage-css-hybrid",
      "models": {
        "instruction_compiler": "gpt-4.1-mini",
        "resume_writer": "gpt-4.1"
      },
      "css_marking": "hybrid",  // hybrid = LLM + Python
      "keyword_variants_handled": true,
      "abbreviations_mapped": true
    }
  },
  "warning": {
    "has_warning": true,  // 當有關鍵字被移除時
    "message": "Optimization successful but 1 keywords removed",
    "code": "KEYWORDS_REMOVED",
    "details": ["PHP"]
  },
  "error": {
    "has_error": false,
    "code": "",
    "message": "",
    "details": ""
  }
}
```

**CSS 類別說明**
- `skill-highlight`: 原有且保持的關鍵字技能（藍色高亮）
- `keyword-added`: 新增的關鍵字技能（綠色高亮）
- `skill-gap`: 技能缺口相關內容（橘色提示）
- `improvement-metric`: 量化成就指標（粗體強調）

**關鍵字追蹤邏輯**
1. **still_covered**: 原本有、現在仍有的關鍵字
2. **removed**: 原本有、但被移除的關鍵字（觸發警告）
3. **newly_added**: 原本沒有、新增的關鍵字
4. **still_missing**: 原本沒有、現在仍沒有的關鍵字

**防禦性設計特性**
- 自動處理關鍵字變體：CI/CD = CI-CD、Node.js = NodeJS = Node
- 縮寫智能對應：ML = Machine Learning、AI = Artificial Intelligence
- 大小寫不敏感匹配：python = Python = PYTHON
- 部分匹配支援："JavaScript" 匹配 "JS"、"TypeScript" 匹配 "TS"
### 6. 搜尋相關課程
`POST /api/v1/courses/search`

使用向量相似度搜尋相關課程。

**請求參數**
```json
{
  "skill_name": "string (最多 100 字元)",
  "search_context": "string",  // 選填，搜尋上下文（最多 500 字元）
  "limit": 5,  // 選填，範圍 1-10，預設 5
  "similarity_threshold": 0.3  // 選填，範圍 0.1-1.0，預設 0.3
}
```

### 7. 搜尋類似課程
`POST /api/v1/courses/similar`

尋找與指定課程相似的其他課程。

**請求參數**
```json
{
  "course_id": "string",  // Coursera 課程 ID
  "limit": 5  // 選填，範圍 1-10，預設 5
}
```

**回應範例**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "python-data-science-ibm",
        "name": "Python for Data Science, AI & Development",
        "description": "Learn Python programming, data analysis with pandas, and build AI applications",
        "provider": "IBM",
        "provider_standardized": "IBM",
        "provider_logo_url": "https://d3njjcbhbojbot.cloudfront.net/api/utilities/v1/imageproxy/...",
        "price": 49.0,
        "currency": "USD",
        "image_url": "https://s3.amazonaws.com/coursera-course-photos/...",
        "affiliate_url": "https://www.coursera.org/learn/python-data-science?irclickid=...",
        "course_type": "course",
        "similarity_score": 92
      }
    ],
    "total_count": 25,
    "returned_count": 5,
    "query": "Python for data analysis and machine learning",
    "search_time_ms": 245,
    "filters_applied": {},
    "type_counts": {
      "course": 15,
      "certification": 5,
      "specialization": 3,
      "degree": 1,
      "project": 1
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  }
}
```

## 錯誤碼

### 標準錯誤格式
所有錯誤回應都遵循統一格式：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "人類可讀的錯誤訊息",
    "details": "額外的錯誤詳細資訊（如有）"
  },
  "timestamp": "2025-07-30T10:30:00.000Z"
}
```

### 錯誤碼清單

| 錯誤碼 | 說明 | HTTP 狀態碼 | 處理建議 |
|--------|------|-------------|----------|
| **客戶端錯誤 (4xx)** | | | |
| VALIDATION_ERROR | 輸入參數驗證失敗 | 400 | 檢查請求參數是否符合要求 |
| INVALID_REQUEST | 無效的請求格式或資料 | 400 | 確認請求格式正確 |
| UNSUPPORTED_LANGUAGE | 偵測到不支援的語言 | 400 | 使用英文或繁體中文內容 |
| UNAUTHORIZED | 缺少或無效的 API 金鑰 | 401 | 檢查 API Key 是否正確 |
| NOT_FOUND | 請求的資源不存在 | 404 | 確認端點 URL 正確 |
| PAYLOAD_TOO_LARGE | 請求內容超過大小限制 | 413 | 減少請求內容大小 |
| RATE_LIMIT_EXCEEDED | 超過 API 呼叫頻率限制 | 429 | 等待後重試或升級方案 |
| **伺服器錯誤 (5xx)** | | | |
| INTERNAL_SERVER_ERROR | 內部伺服器錯誤 | 500 | 稍後重試，如持續發生請聯絡支援 |
| LLM_SERVICE_ERROR | AI 服務處理錯誤 | 500 | 使用指數退避策略重試 |
| DATABASE_ERROR | 資料庫連線或查詢失敗 | 500 | 稍後重試 |
| TIMEOUT_ERROR | 請求處理超時 | 504 | 重試或減少請求複雜度 |
| SERVICE_UNAVAILABLE | 服務暫時無法使用 | 503 | 稍後重試 |
| **健康檢查錯誤** | | | |
| HEALTH_CHECK_FAILED | 健康檢查失敗 | 503 | 服務可能正在維護 |
| **監控相關錯誤** | | | |
| MONITORING_DISABLED | 監控功能在此環境已停用 | 404 | 僅在開發環境可用 |
| STORAGE_ERROR | 錯誤儲存失敗 | 500 | 內部問題，不影響主要功能 |

## Rate Limits

- 每分鐘：60 次請求
- 每小時：1000 次請求
- 並發請求：10

## 最佳實踐

### 1. 認證設定
```python
import requests

# 推薦：使用 Header 認證
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords",
    headers=headers,
    json={"job_description": "..."}
)

# 向後相容：Query Parameter 認證
response = requests.post(
    "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords?code=your-api-key",
    json={"job_description": "..."}
)
```

### 2. 錯誤處理與重試策略
```python
import requests
from time import sleep
import logging

logger = logging.getLogger(__name__)

def call_api_with_retry(url, data, api_key, max_retries=3):
    """
    智能重試機制，根據錯誤類型決定重試策略
    """
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url, 
                headers=headers,
                json=data,
                timeout=30  # 30 秒逾時
            )
            
            # 檢查 HTTP 狀態碼
            if response.status_code == 200:
                result = response.json()
                if result["success"]:
                    return result["data"]
                else:
                    error = result["error"]
                    logger.warning(f"API Error: {error['code']} - {error['message']}")
                    
                    # 根據錯誤碼決定是否重試
                    if error["code"] in ["SERVICE_UNAVAILABLE", "TIMEOUT_ERROR", "LLM_SERVICE_ERROR"]:
                        wait_time = 2 ** attempt  # 指數退避：2, 4, 8 秒
                        logger.info(f"Retrying in {wait_time} seconds...")
                        sleep(wait_time)
                        continue
                    elif error["code"] == "RATE_LIMIT_EXCEEDED":
                        logger.info("Rate limit exceeded, waiting 60 seconds...")
                        sleep(60)
                        continue
                    else:
                        # 不可重試的錯誤
                        raise Exception(f"{error['code']}: {error['message']}")
            else:
                # HTTP 錯誤
                if response.status_code >= 500:
                    # 伺服器錯誤，可重試
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s...")
                    sleep(wait_time)
                    continue
                else:
                    # 客戶端錯誤，不重試
                    response.raise_for_status()
                    
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                sleep(2 ** attempt)
                continue
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            if attempt < max_retries - 1:
                sleep(2 ** attempt)
                continue
            raise
    
    raise Exception(f"Failed after {max_retries} attempts")
```

### 3. 重試策略總結

| 錯誤類型 | 重試策略 | 等待時間 |
|---------|---------|---------|
| SERVICE_UNAVAILABLE (503) | 指數退避 | 2^n 秒 (2, 4, 8...) |
| TIMEOUT_ERROR (504) | 指數退避 | 2^n 秒 (2, 4, 8...) |
| LLM_SERVICE_ERROR (500) | 指數退避 | 2^n 秒 (2, 4, 8...) |
| RATE_LIMIT_EXCEEDED (429) | 固定等待 | 60 秒 |
| VALIDATION_ERROR (400) | 不重試 | - |
| UNAUTHORIZED (401) | 不重試 | - |
| 其他 4xx 錯誤 | 不重試 | - |

### 4. 效能優化技巧

#### 並發請求處理
```python
import asyncio
import aiohttp

async def async_api_call(session, url, data, api_key):
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    async with session.post(url, json=data, headers=headers) as response:
        return await response.json()

async def batch_process(job_descriptions, api_key):
    url = "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/api/v1/extract-jd-keywords"
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for jd in job_descriptions:
            task = async_api_call(session, url, {"job_description": jd}, api_key)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

# 使用範例
job_descriptions = ["JD1...", "JD2...", "JD3..."]
results = asyncio.run(batch_process(job_descriptions, "your-api-key"))
```

#### 連線重用
```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 建立持久連線
session = requests.Session()

# 設定重試策略
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# 使用 session 進行多次請求
response1 = session.post(url1, json=data1, headers=headers)
response2 = session.post(url2, json=data2, headers=headers)
```

### 5. 輸入資料準備

#### 文字清理範例
```python
import re
from bs4 import BeautifulSoup

def clean_text_input(text):
    """清理輸入文字"""
    # 移除 HTML 標籤
    if "<" in text and ">" in text:
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()
    
    # 移除多餘空白
    text = re.sub(r'\s+', ' ', text)
    
    # 移除控制字元
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    # 移除首尾空白
    text = text.strip()
    
    return text

def validate_input_length(text, min_length=50, max_length=20000):
    """驗證輸入長度"""
    if len(text) < min_length:
        raise ValueError(f"Text too short. Minimum {min_length} characters required.")
    if len(text) > max_length:
        raise ValueError(f"Text too long. Maximum {max_length} characters allowed.")
    return True
```

### 6. 完整使用範例

#### 關鍵字提取完整流程
```python
import requests
import logging
from typing import List, Dict

class AIResumeAdvisorClient:
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io"
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
    
    def extract_keywords(self, job_description: str, language: str = "auto") -> Dict:
        """提取職缺關鍵字"""
        url = f"{self.base_url}/api/v1/extract-jd-keywords"
        
        # 清理輸入
        job_description = clean_text_input(job_description)
        validate_input_length(job_description)
        
        # 發送請求
        response = self.session.post(url, json={
            "job_description": job_description,
            "language": language,
            "max_keywords": 20
        })
        
        # 處理回應
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                return result["data"]
            else:
                raise Exception(f"API Error: {result['error']['message']}")
        else:
            response.raise_for_status()
    
    def tailor_resume(self, job_description: str, resume: str, gap_analysis: Dict) -> Dict:
        """客製化履歷"""
        url = f"{self.base_url}/api/v1/tailor-resume"
        
        # 準備請求資料
        request_data = {
            "job_description": clean_text_input(job_description),
            "original_resume": resume,  # 保留 HTML 格式
            "gap_analysis": gap_analysis,
            "options": {
                "include_visual_markers": True,
                "language": "en"
            }
        }
        
        # 發送請求
        response = self.session.post(url, json=request_data, timeout=60)
        
        # 處理回應
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                return result["data"]
            else:
                raise Exception(f"API Error: {result['error']['message']}")
        else:
            response.raise_for_status()

# 使用範例
client = AIResumeAdvisorClient("your-api-key")

# 1. 提取關鍵字
keywords_data = client.extract_keywords(job_description)
print(f"提取到 {keywords_data['keyword_count']} 個關鍵字")
print(f"關鍵字: {', '.join(keywords_data['keywords'])}")

# 2. 客製化履歷
tailored_data = client.tailor_resume(
    job_description=job_description,
    resume=original_resume,
    gap_analysis={
        "core_strengths": ["Python expertise", "API development"],
        "key_gaps": [
            "[Skill Gap] Docker - No container experience",
            "[Presentation Gap] Kubernetes - Has orchestration skills but not mentioned"
        ],
        "quick_improvements": ["Complete Docker course", "Add K8s experience to resume"],
        "covered_keywords": keywords_data["keywords"][:10],
        "missing_keywords": keywords_data["keywords"][10:],
        "coverage_percentage": 75,  # 從 Index Calculation API 獲得
        "similarity_percentage": 80  # 從 Index Calculation API 獲得
    }
)
print(f"履歷優化後匹配度提升: {tailored_data['similarity']['improvement']}%")
```

### 7. 除錯技巧

#### 啟用詳細日誌
```python
import logging
import requests

# 設定日誌
logging.basicConfig(level=logging.DEBUG)

# 啟用 requests 的除錯日誌
import http.client
http.client.HTTPConnection.debuglevel = 1

# 現在所有 API 請求都會顯示詳細資訊
```

#### 測試端點連線
```python
def test_api_connection(base_url, api_key):
    """測試 API 連線"""
    try:
        # 測試健康檢查
        health_response = requests.get(f"{base_url}/health")
        print(f"Health check: {health_response.status_code}")
        
        # 測試認證
        auth_test = requests.get(
            f"{base_url}/api/v1/",
            headers={"X-API-Key": api_key}
        )
        print(f"Auth test: {auth_test.status_code}")
        
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False
```

## API 文檔與工具

### Swagger/OpenAPI 文檔
生產環境的互動式 API 文檔：
```
https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/docs
```

開發環境的互動式 API 文檔：
```
https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/docs
```

### Postman Collection
即將推出 Postman Collection，方便測試和整合。

### SDK
- Python SDK：開發中
- JavaScript/TypeScript SDK：規劃中
- Go SDK：規劃中

## 常見問題 (FAQ)

### Q: 如何獲取 API Key？
A: 請聯絡 AI Resume Advisor 團隊申請 API Key。企業客戶可申請專屬的高配額 Key。

### Q: API 有使用限制嗎？
A: 是的，預設限制為每分鐘 60 次請求。如需更高配額，請聯絡我們。

### Q: 支援哪些語言？
A: 目前支援英文 (en) 和繁體中文 (zh-TW)。語言偵測功能可自動識別輸入語言。

### Q: 如何處理大量請求？
A: 建議使用並發請求（參考效能優化章節）並實作適當的重試機制。我們的 API 支援高並發處理。

### Q: API 回應時間多長？
A: 
- 關鍵字提取：平均 2-3 秒
- 履歷客製化：平均 5-10 秒
- 其他端點：通常在 1 秒內

### Q: 如何確保資料安全？
A: 
- 所有通訊使用 HTTPS 加密
- API Key 應妥善保管，不要公開在程式碼中
- 敏感資料不會被儲存或記錄
- 符合 GDPR 和資料保護規範

## 變更日誌

### 2025-08-11
- Resume Tailoring v2.1.0-simplified：混合式 CSS 標記系統 + 關鍵字追蹤機制
  - 提示詞精簡 47% (10,534 → 5,637 字元)
  - 效能提升 44% (P50 < 2.5秒)
  - 防禦性關鍵字變體匹配
  - 縮寫雙向智能對應
- LLM Factory v2.0：統一 Embedding 服務管理
  - 整合 embedding-3-large 和 embedding-3-small
  - 自動處理部署映射

### 2025-08-10
- Gap Analysis v2.1.0：新增 [Skill Gap] 和 [Presentation Gap] 分類標記
- Resume Tailoring v2.0.0：實作兩階段架構 (Instruction Compiler + Resume Writer)
- 成本優化：使用 GPT-4.1 mini 降低成本 200x
- 效能提升：P50 < 4.5秒，比 v1.0 快 40%
- 改善差距分類精確度

### 2025-07-30
- 遷移至 Azure Container Apps 平台
- 新增監控和除錯端點
- 改善錯誤處理機制
- 支援 Header 認證方式

### 2025-07-26
- 發布 v1 API
- 支援六大核心功能
- 實作統一錯誤格式

## 測試與品質保證

### 測試覆蓋率
- **總測試案例**: 113 個
- **測試通過率**: 100% (113/113)
- **測試類型分布**:
  - 單元測試: 96 個
  - 整合測試: 16 個
  - 效能測試: 1 個

### API 端點測試覆蓋
| 端點 | 單元測試 | 整合測試 | 效能測試 |
|------|----------|----------|----------|
| `/health` | 9 | 1 | - |
| `/api/v1/extract-jd-keywords` | 88 | 15 | 1 |

### CI/CD 狀態
- **自動部署**: ✅ 已啟用
- **部署觸發**: 推送到 main 分支
- **測試閘門**: 所有測試必須通過
- **部署時間**: 約 5-7 分鐘

## 支援與聯絡

### 技術支援
- Email: support@airesumeadvisor.com
- 回應時間：工作日 24 小時內

### 問題回報
如發現 API 問題，請提供：
1. 請求的端點和參數
2. 錯誤訊息和錯誤碼
3. 請求時間 (timestamp)
4. 您的 API Key 前 8 碼（用於查詢）

### 功能建議
歡迎透過 email 提供功能建議和改進意見。

---

**文檔版本**: 2.2.0  
**最後更新**: 2025-08-10  
**維護團隊**: AI Resume Advisor Development Team