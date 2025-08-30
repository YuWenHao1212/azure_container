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

**版本更新 (2025-08-21 - Education Enhancement)** 🎓
- **Education Enhancement 智慧決策**：新增履歷結構分析中的教育背景強化邏輯
- **四大判斷條件**：工作經驗 < 2年、目前學生、畢業未滿12個月、僅有實習經驗
- **metadata 欄位擴充**：
  - `years_of_experience`: 全職工作年數（排除實習）
  - `is_current_student`: 是否為在學學生
  - `months_since_graduation`: 畢業月數（可為 null）
  - `has_only_internships`: 是否只有實習經驗
- **education_enhancement_needed**: 最終 Education Enhancement 決策結果
- **Prompt v1.0.2 啟用**：整合 Education Enhancement 指標計算邏輯
- **V3 True Parallel 架構**：真正並行處理，structure_analysis 與其他任務同步執行

**版本更新 (2025-08-26 - Course Details Optimization)** 🚀
- **API 回應最佳化**：新增 `course_details` 欄位環境變數控制
- **環境變數**：`INCLUDE_COURSE_DETAILS` (預設: `"false"` 用於生產環境最佳化)
- **資料傳輸減少**：70-80% 回應大小減少（移除每個技能的 25 個課程詳細資訊）
- **內部功能保留**：Resume enhancement 功能完全不受影響
- **動態控制**：開發環境可設定 `INCLUDE_COURSE_DETAILS=true` 包含完整課程詳細資訊
- **向後相容**：API 介面保持一致，僅動態排除 `course_details` 欄位

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
    "raw_similarity_percentage": 41,
    "similarity_percentage": 63,
    "keyword_coverage": {
      "total_keywords": 5,
      "covered_count": 1,
      "coverage_percentage": 20,
      "covered_keywords": ["Python"],
      "missed_keywords": ["FastAPI", "REST API", "Cloud", "Docker"]
    },
    "gap_analysis": {
      "CoreStrengths": "<ol><li>🏆 Top Match: Demonstrated expertise in data processing, visualization, and interpretation, supporting executive decision-making and business growth through advanced analytics and KPI dashboards.</li><li>⭐ Key Strength: Strong SQL and MySQL proficiency, evidenced by hands-on experience in data management projects and the design of P&L databases and dashboards for large-scale product lines.</li><li>⭐ Key Strength: Deep experience in project management and cross-functional collaboration, including leading teams, coordinating with IT, and managing complex product development initiatives in automotive and consumer sectors.</li></ol>",
      "KeyGaps": "<ol><li>🔧 <b>FastAPI & REST API</b>: Not evident in resume. If experienced, add immediately. Otherwise, budget 2-3 months to learn modern API frameworks and integration.</li><li>🔧 <b>Cloud Platforms</b>: No trace found. Either a resume gap to fix, or requires 3-4 months training in AWS, Azure, or GCP for data management and deployment.</li><li>🔧 <b>Docker & Containerization</b>: Absent from current resume. Possibly overlooked? Add it, or plan 2-3 months to develop containerization and orchestration skills.</li></ol>",
      "QuickImprovements": "<ol><li>🔧 <b>Highlight \"REST API\" Experience</b>: If you have worked with APIs during data integration or dashboard development, add \"REST API integration for data pipelines and reporting\" to your Skills section and reference in relevant project bullet points.</li><li>🔧 <b>Surface \"Cloud\" Experience</b>: If you have used cloud-based tools (e.g., Tableau Online, cloud-hosted databases), specify \"Cloud data analytics platforms (e.g., Tableau Online, MySQL Cloud)\" in your Skills section and mention cloud deployment in project descriptions.</li><li>🔧 <b>Add \"Docker\" to Skills Section</b>: If you have automated deployment or managed environments, include \"Docker: Container deployment and orchestration\" in Skills and reference any related automation in project management bullets.</li></ol>",
      "OverallAssessment": "[V2.1.8-100W] You have good alignment for the Data Analyst role, with strong data analysis, SQL, and project management experience. However, gaps in modern API frameworks (FastAPI, REST API), cloud platforms, and containerization (Docker) must be addressed for full readiness. First, optimize your resume to surface any hidden experience with APIs, cloud, or containerization. Then, invest 3-6 months in targeted upskilling through hands-on projects and online courses. With focused effort, you can strengthen your technical profile and become a competitive candidate for data-driven roles in SaaS and life sciences.",
      // Skill categories explanation (v2.1.8+):
      // - SKILL: Quick-learn skills via single course (1-3 months)
      // - FIELD: Requires specialization/certification (6+ months)
      //
      // Course details field (v2025-08-26+):
      // - course_details: 詳細課程資訊陣列（預設被排除以優化傳輸）
      // - 環境變數控制：INCLUDE_COURSE_DETAILS="true" 時會包含此欄位
      // - 內含完整課程資訊：name, type, provider, description, similarity 等
      // - 生產環境預設排除，開發環境可啟用完整資訊
      "SkillSearchQueries": [
        {
          "skill_name": "FastAPI & REST API Frameworks",
          "skill_category": "SKILL",
          "description": "Learn to design, build, and integrate modern APIs for scalable data pipelines and analytics applications.",
          "has_available_courses": true,
          "course_count": 25,
          "available_course_ids": [
            "coursera_crse:dQxbeqjfEeywagovoAKHOQ",
            "coursera_crse:BEUHr70KEe-LvhIuPUA7nw",
            "coursera_crse:JCbeFVUAEeulPAroU7-MFQ",
            "coursera_crse:Eg_J1V1hEe-vHBLsSjPJnw",
            "coursera_crse:veV0Fh6fEfC5wQ7Ux-t3bw"
            // ... up to 25 course IDs
          ]
        },
        {
          "skill_name": "Cloud Platforms (AWS, Azure, GCP)",
          "skill_category": "SKILL",
          "description": "Gain proficiency in deploying, managing, and analyzing data using leading cloud services for enterprise solutions.",
          "has_available_courses": true,
          "course_count": 25,
          "available_course_ids": [
            "coursera_crse:oI7VwBJ6Ee-r_Ar_6dbL9Q",
            "coursera_spzn:QroLL3-XEeu17gr5PLNEuQ",
            "coursera_crse:ALMS0NyJEe6J_wr_0biVVQ",
            "coursera_crse:PrflEV_QEe-vHBLsSjPJnw",
            "coursera_crse:9txV54HFEe-uPQ6cY8b-gw"
            // ... up to 25 course IDs
          ]
        },
        {
          "skill_name": "Docker & Containerization",
          "skill_category": "SKILL",
          "description": "Master container creation, orchestration, and deployment workflows for efficient data operations and reproducible environments.",
          "has_available_courses": true,
          "course_count": 25,
          "available_course_ids": [
            "coursera_crse:bkM_lRGtEe-zqA6_zzhdJQ",
            "coursera_crse:IftJTkUoEfClyxI_Dgx85Q",
            "coursera_crse:bjkOnvoIEe-glg6vww23RQ",
            "coursera_crse:FVsG5P-dEe-m2BKpUCEabw",
            "coursera_crse:UQ1bm74iEe-LvhIuPUA7nw"
            // ... up to 25 course IDs
          ]
        }
      ]
    },
    "resume_structure": {
      "standard_sections": {
        "summary": "Personal Summary",
        "skills": "Skill", 
        "experience": "Work Experience",
        "education": "Education Background",
        "certifications": "Certification",
        "projects": "Personal Project"
      },
      "custom_sections": [],
      "metadata": {
        "total_experience_entries": 5,
        "total_education_entries": 3,
        "has_quantified_achievements": true,
        "estimated_length": "long",
        "years_of_experience": 19,
        "is_current_student": true,
        "months_since_graduation": null,
        "has_only_internships": false
      },
      "education_enhancement_needed": true
    },
    "resume_enhancement_project": [
      {
        "id": "coursera_prjt:BEUHr70KEe-LvhIuPUA7nw",
        "name": "Build REST API with FastAPI",
        "provider": "Google",
        "description": "Hands-on project to build and deploy production-ready REST APIs using FastAPI framework, including authentication, database integration, and deployment",
        "related_skill": "FastAPI & REST API Frameworks"
      },
      {
        "id": "coursera_prjt:IftJTkUoEfClyxI_Dgx85Q",
        "name": "Docker Containerization Fundamentals",
        "provider": "IBM",
        "description": "Learn to containerize applications, manage Docker images and containers, and implement multi-container applications with Docker Compose",
        "related_skill": "Docker & Containerization"
      }
    ],
    "resume_enhancement_certification": [
      {
        "id": "coursera_spzn:QroLL3-XEeu17gr5PLNEuQ",
        "name": "Google Cloud Professional Cloud Architect",
        "provider": "Google",
        "description": "Comprehensive certification path covering GCP services, architecture patterns, security, and best practices for designing scalable cloud solutions",
        "related_skill": "Cloud Platforms (AWS, Azure, GCP)"
      },
      {
        "id": "coursera_cert:ALMS0NyJEe6J_wr_0biVVQ",
        "name": "AWS Solutions Architect Associate",
        "provider": "Amazon",
        "description": "Learn to design distributed systems on AWS, implement secure and scalable architectures, and optimize cloud infrastructure for performance and cost",
        "related_skill": "Cloud Platforms (AWS, Azure, GCP)"
      },
      {
        "id": "coursera_spzn:bjkOnvoIEe-glg6vww23RQ",
        "name": "Docker and Kubernetes Specialization",
        "provider": "Google",
        "description": "Master container orchestration with Kubernetes, including deployment strategies, service mesh, monitoring, and production-ready configurations",
        "related_skill": "Docker & Containerization"
      }
    ],
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
  "timestamp": "2025-08-21T05:29:56.574338",
  "metadata": {
    "version": "3.0",
    "language_detected": "en",
    "processing_approach": "v3_true_parallel",
    "optimization": "Plan B - Gap starts after keywords only",
    "phase_timings_ms": {
      "embedding_generation": 154.5,
      "index_calculation": 152.86,
      "gap_analysis": 7969.78
    },
    "detailed_timings_ms": {
      "total_time": 8277.15,
      "keyword_matching_time": 15.97,
      "embedding_time": 154.5,
      "index_calculation_time": 152.86,
      "gap_analysis_time": 7969.78,
      "course_availability_time": 1493.54,
      "structure_analysis_time": 1767.76,
      "structure_wait_time": 8003.01,
      "pgvector_warmup_time": 1229.05
    },
    "execution_timeline": {
      "parallel_tasks": {
        "keywords": {"start": 0, "end": 15.97},
        "embeddings": {"start": 0, "end": 154.5},
        "structure_analysis": {
          "start": 0,
          "end": 1767.76,
          "wait_time": 8003.01,
          "actual_completed": true
        },
        "pgvector_warmup": {"start": 0, "end": 1229.05}
      },
      "sequential_tasks": {
        "index_calculation": {"start": 154.5, "end": 307.36},
        "gap_analysis": {"start": 307.36, "end": 8277.14},
        "course_availability": {"start": 8277.14, "end": 8277.15}
      }
    },
    "parallel_efficiency": 0,
    "resource_pool_used": true,
    "structure_analysis_enabled": true
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

### 5. 客製化履歷 (v3.1.0)
`POST /api/v1/tailor-resume`

根據職缺要求和差距分析結果優化履歷，使用雙 LLM 架構實現更精準的履歷優化。

**版本更新 (v3.1.0)** 🚀
- **雙 LLM 架構**：Core LLM 處理結構優化，Additional LLM 處理 enhancement fields
- **直接使用 original_index**：接收完整的 Gap Analysis API 回應，無需轉換
- **Enhancement Fields 支援**：自動整合建議的專案和認證
- **簡化輸入格式**：移除不使用的欄位（OverallAssessment、SkillSearchQueries）

**請求參數**
```json
{
  "job_description": "string (最少 50 字元，最多 10000 字元)",
  "original_resume": "string (HTML 格式，最少 100 字元，最多 50000 字元)",
  "original_index": {
    // 直接使用 /api/v1/index-cal-and-gap-analysis 的回應
    // 必要欄位
    "similarity_percentage": 82,
    "keyword_coverage": {
      "covered_keywords": ["Python", "AWS"],
      "missed_keywords": ["Kubernetes"],
      "coverage_percentage": 75
    },
    "gap_analysis": {
      "CoreStrengths": "<ul><li>Strong Python expertise</li></ul>",
      "KeyGaps": "<ul><li>Missing cloud certification</li></ul>",
      "QuickImprovements": "<ul><li>Add Kubernetes experience</li></ul>"
      // OverallAssessment 和 SkillSearchQueries 不需要
    },
    // 選用欄位
    "resume_structure": {
      "standard_sections": {
        "summary": "Personal Summary",
        "skills": "Technical Skills",
        "experience": "Work Experience"
      },
      "custom_sections": [],
      "education_enhancement_needed": false
    },
    "resume_enhancement_project": [
      // 陣列格式，從 Gap Analysis API 直接傳入
      {
        "id": "coursera_prjt:BEUHr70KEe-LvhIuPUA7nw",
        "name": "Build Cloud Native Apps",
        "description": "Hands-on project to build cloud applications",
        "provider": "Google",
        "related_skill": "Cloud Computing"
      }
    ],
    "resume_enhancement_certification": [
      // 陣列格式，從 Gap Analysis API 直接傳入
      {
        "id": "coursera_cert:ALMS0NyJEe6J_wr_0biVVQ",
        "name": "AWS Solutions Architect",
        "provider": "Amazon Web Services",
        "description": "Learn to design distributed systems on AWS",
        "related_skill": "AWS Cloud"
      }
    ]
  },
  "options": {
    "include_visual_markers": true,  // 預設 true
    "language": "zh-TW",             // "en" 或 "zh-TW"，預設 "en"
    "format_version": "v3"           // 預設 "v3"
  }
}

```

**回應範例 (v3.1.0)**
```json
{
  "success": true,
  "data": {
    "optimized_resume": "<h2>John Smith</h2>
<p>Senior Software Engineer with expertise in <span class='opt-strength'>Python</span> and cloud technologies...</p>
<ul>
  <li><span class='opt-keyword'>Led Docker containerization</span> reducing deployment time by 70%</li>
  <li>Implemented <span class='opt-strength'>CI/CD pipelines</span> using Jenkins and GitLab</li>
  <li>Developed <span class='opt-improvement'>machine learning models</span> for customer analytics</li>
</ul>",
    "applied_improvements": [
      "[Section: Summary] Created new professional summary highlighting cloud architecture expertise",
      "[Section: Skills] Reorganized skills into job-relevant categories, added Kubernetes and Terraform",
      "[Section: Experience - Tech Corp] Converted 5 bullets to STAR format, added quantification",
      "[Section: Projects] Enhanced ML project description with technologies and impact metrics"
    ],
    "Keywords": {
      "kcr_improvement": 50,
      "kcr_before": 40,
      "kcr_after": 90,
      "kw_before_covered": ["Python", "JavaScript", "CI/CD"],
      "kw_before_missed": ["Docker", "Kubernetes", "Machine Learning", "GraphQL", "Rust"],
      "kw_after_covered": ["Python", "JavaScript", "CI/CD", "Docker", "Kubernetes", "Machine Learning"],
      "kw_after_missed": ["GraphQL", "Rust"],
      "newly_added": ["Docker", "Kubernetes", "Machine Learning"],
      "kw_removed": []
    },
    "similarity": {
      "SS_improvement": 25,
      "SS_before": 60,
      "SS_after": 85
    },
    "total_processing_time_ms": 8880,
    "pre_processing_ms": 280,
    "llm1_processing_time_ms": 6080,
    "llm2_processing_time_ms": 4080,
    "post_processing_ms": 2600,
    "stage_timings": {
      "llm1_start_time_ms": 280,
      "llm1_finish_time_ms": 6360,
      "llm2_start_time_ms": 280,
      "llm2_finish_time_ms": 4360
    }
  },
  "metadata": {
    "llm1_prompt_version": "v1.0.0-resume-core",
    "llm2_prompt_version": "v1.0.0-resume-additional",
    "llm1_model": "gpt-4.1",
    "llm2_model": "gpt-4.1"
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "details": []
  },
  "error": {
    "has_error": false,
    "code": "",
    "message": "",
    "details": ""
  }
}
```

**CSS 類別說明 (v3.1.0)**
- `opt-strength`: 強調的核心優勢內容
- `opt-keyword`: 新增的關鍵字
- `opt-improvement`: 應用的改進建議
- `opt-placeholder`: 需要用戶填入的量化指標占位符
- `opt-new`: 新增的內容區塊
- `opt-modified`: 修改過的內容

**API 調用流程**
1. 調用 `/api/v1/index-cal-and-gap-analysis` 獲取完整分析結果
2. 將整個回應的 `data` 欄位作為 `original_index` 傳入
3. 調用 `/api/v1/tailor-resume` 進行履歷優化
4. 不需要任何資料轉換或重新格式化

**向後相容性**
服務層同時支援新舊格式：
- 新格式：包含 `keyword_coverage` 的巢狀結構
- 舊格式：頂層直接包含 `covered_keywords`、`missing_keywords` 等欄位
- 自動偵測並適配不同格式
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

### 8. 批次查詢課程詳情
`POST /api/v1/courses/get-by-ids`

根據課程 ID 列表批次查詢課程詳細資訊，支援 Bubble.io 前端展示。

**請求參數**
```json
{
  "course_ids": ["string"],          // 必填，課程 ID 列表（1-100 個）
  "max_courses": 20,                 // 選填，最多查詢幾個（1-100）
  "full_description": true,          // 選填，是否返回完整描述，預設 true
  "description_max_length": 500,     // 選填，描述截斷長度（字元），預設 500
  "enable_time_tracking": true,      // 選填，啟用時間追蹤，預設 true
  "format_description_html": true    // 選填，將描述格式化為 HTML，預設 true
}
```

**HTML 格式化功能**
- **預設啟用**：`format_description_html` 預設為 `true`
- **欄位名稱固定**：始終使用 `description` 欄位，不會改變名稱
- 當 `format_description_html=true`（預設）：`description` 欄位包含 HTML 格式化內容
- 當 `format_description_html=false`：`description` 欄位包含原始純文字
- 支援：HTML 轉義、換行處理、Markdown 轉換、URL 自動連結、Bullet Points
- 適合直接在 Bubble.io HTML 元件中顯示，無需額外處理

**回應範例（簡化結構）**
```json
{
  "success": true,
  "courses": [
    {
      "id": "coursera_crse:v1-2598",
      "name": "React - The Complete Guide",
      "description": "Learn React.js from the ground up...",  // 當 format_description_html=false 時為純文字
      // 或
      "description": "<p>Learn React.js from the ground up...</p>",  // 當 format_description_html=true 時為 HTML
      "provider": "Academind",
      "provider_standardized": "Academind",
      "provider_logo_url": "https://example.com/logo.png",
      "price": 49.99,
      "currency": "USD",
      "image_url": "https://example.com/course.jpg",
      "affiliate_url": "https://www.coursera.org/learn/react",
      "course_type": "course",
      "duration": "40 hours",
      "difficulty": "Intermediate",
      "rating": 4.7,
      "enrollment_count": 150000
    }
  ],
  "total_found": 1,
  "requested_count": 1,
  "processed_count": 1,
  "skipped_count": 0,
  "not_found_ids": [],
  "cache_hit_rate": 0.0,
  "from_cache_count": 0,
  "all_not_found": false,
  "fallback_url": null,
  "time_tracking": {
    "enabled": true,
    "total_ms": 125,
    "timeline": [
      {"task": "preparation", "duration_ms": 3, "description": "Input validation"},
      {"task": "cache_operations", "duration_ms": 15, "description": "Cache lookup"},
      {"task": "db_operations", "duration_ms": 85, "description": "Database query"},
      {"task": "processing", "duration_ms": 22, "description": "Response formatting"}
    ],
    "summary": {
      "preparation_pct": 2.4,
      "cache_operations_pct": 12.0,
      "db_operations_pct": 68.0,
      "processing_pct": 17.6
    }
  },
  "error": {
    "code": "",
    "message": "",
    "details": ""
  }
}
```

**特殊情況處理**
- **空列表請求**: 返回成功但空結果，提供 fallback_url
- **部分失敗**: 返回找到的課程，not_found_ids 列出未找到的 ID
- **超過限制**: 使用 max_courses 限制查詢數量，剩餘 ID 計入 skipped_count

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