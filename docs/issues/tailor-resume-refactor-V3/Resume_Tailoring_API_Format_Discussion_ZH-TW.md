# Resume Tailoring API 格式設計討論

## 📄 文件資訊
- **建立日期**: 2025-08-21 14:30 CST
- **目的**: 討論 `POST /api/v1/tailor-resume` 的最佳輸入格式設計
- **背景**: 配合 v3.0 重構，需要重新設計 API 格式以整合 Gap Analysis 結果

---

## 🎯 最終決定：簡化版完整傳遞格式 ⭐

根據討論結果，採用**簡化版方案 A**，移除不需要的資料，保留核心功能。

### 輸入格式 (最終版)

```json
{
  "original_resume": "string (200-50000 字元, HTML 格式)",
  "job_description": "string (200-10000 字元)",
  "original_index": {
    // 保留核心指標
    "similarity_percentage": 63,
    "keyword_coverage": {
      "coverage_percentage": 20,
      "covered_keywords": ["Python"],
      "missed_keywords": ["FastAPI", "REST API", "Cloud", "Docker"]
    },
    
    // 保留完整的分析內容 (HTML 格式)
    "gap_analysis": {
      "CoreStrengths": "<ol><li>🏆 Top Match: ...</li></ol>",
      "KeyGaps": "<ol><li>🔧 <b>FastAPI & REST API</b>...</li></ol>",
      "QuickImprovements": "<ol><li>🔧 <b>Highlight...</li></ol>",
      "OverallAssessment": "..."
      // ✅ 移除 SkillSearchQueries (Resume Tailoring 不需要)
    },
    
    // 保留結構分析
    "resume_structure": {
      "standard_sections": {
        "summary": "Personal Summary",  // 存在的標準章節及其實際名稱
        "skills": "Skill",
        "experience": "Work Experience",
        "education": "Education Background"
      },
      "custom_sections": ["Portfolio", "Awards"],  // 非標準章節名稱列表
      "education_enhancement_needed": true  // 在 resume_structure 內部
      // ✅ 移除詳細 metadata (Resume Tailoring 不需要)
    }
    // ✅ 移除最外層 metadata (Resume Tailoring 不需要)
  },
  
  "options": {
    "include_visual_markers": true,
    "language": "en",
    "format_version": "v3"
  }
}
```

### 回應格式 (最終版)

```json
{
  "success": true,
  "data": {
    "optimized_resume": "<完整 HTML，包含 CSS classes>",
    "applied_improvements": [
      "[Quick Win: Topic] Applied: specific change made",
      "[Presentation Gap: Skill] Surfaced from location",
      "[Skill Gap: Skill] Bridged via foundation",
      "[Structure: Section] Created/Modified for purpose"
    ],
    // 新增 timing tracking 功能
    "total_processing_time_ms": 2480,
    "stage_timings": {
      "pre_processing_ms": 280,
      "resume_writing_ms": 2100,
      "post_processing_ms": 100
    }
  },
  "warning": {
    "has_warning": false,
    "message": "",
    "details": []
  }
}
```

### 設計決策摘要

#### ✅ 採用的設計
- **簡化版方案 A**: 完整傳遞，移除不需要資料
- **字段重命名**: `gap_analysis_result` → `original_index` (更直觀)
- **直接升級**: 不支援舊格式，保留最新版本即可
- **簡化巢狀**: 儘量扁平化，符合 Bubble.io 限制
- **Timing 追蹤**: 保留效能監控功能

#### ❌ 移除的資料
- `SkillSearchQueries` (課程資訊 - Resume Tailoring 不需要)
- `metadata` (效能統計 - Resume Tailoring 不需要) 
- `resume_structure.metadata` (詳細統計 - Resume Tailoring 不需要)

#### 📋 重要確認事項
1. **`education_enhancement_needed`** 確認在 `resume_structure` 內部 ✅
2. **CSS 類別標記** 以句子為單位，不是章節為單位 ✅
3. **向後相容** 直接升級，不需要過渡期 ✅
4. **Request 大小** 10-50KB 可接受 ✅
5. **Timing 追蹤** 添加到回應中用於效能監控 ✅

### 實作優點

#### 🚀 前端簡化
```javascript
// Bubble.io 工作流程：
// 1. 調用 index-cal-and-gap-analysis，取得 response
// 2. 直接將 response.data 放入 original_index
// 3. 調用 tailor-resume
// 不需要任何資料轉換！
```

#### 🔧 後端簡化
```python
async def tailor_resume_v3(
    original_resume: str,
    job_description: str, 
    original_index: dict,
    options: dict = None
) -> dict:
    # 直接提取各種資料，不需要複雜轉換
    resume_structure = original_index.get("resume_structure", {})
    keyword_coverage = original_index.get("keyword_coverage", {})
    gap_analysis = original_index.get("gap_analysis", {})
    
    # 單一 LLM 調用替代兩階段架構
    return await self._execute_v3_optimization(context)
```

#### 📊 CSS 類別使用原則 (行為型分類策略)

基於 Gap Analysis 三大輸出的映射邏輯：

##### 🎯 標記邏輯
```
CoreStrengths + QuickImprovements → opt-modified
├─ CoreStrengths: 原履歷已有優勢，需要強化突出  
└─ QuickImprovements: 基於現有內容的改進建議

KeyGaps → opt-new
└─ KeyGaps: 原履歷缺少的技能/經驗，需要策略性新增

Quantification → opt-placeholder
└─ [X%], [TEAM SIZE], [Y years] 等量化佔位符
```

##### 🏷️ CSS 類別定義
- **`opt-modified`**: LLM 依據 **CoreStrengths** 和 **QuickImprovements** 優化現有履歷句子
- **`opt-new`**: LLM 依據 **KeyGaps** 新增句子（原履歷無明顯 evidence）
- **`opt-placeholder`**: 量化佔位符，需要用戶後續填入具體數值

##### 💡 標記範例
```html
<!-- 基於 CoreStrengths 強化現有優勢 -->
<span class="opt-modified">Enhanced Python development expertise with 5+ years experience</span>

<!-- 基於 QuickImprovements 優化現有內容 -->
<span class="opt-modified">Led cross-functional development team delivering scalable solutions</span>

<!-- 基於 KeyGaps 新增缺失技能 -->
<span class="opt-new">Exploring FastAPI framework for high-performance API development</span>

<!-- 量化佔位符 -->
Improved system performance by <span class="opt-placeholder">[X%]</span>
```

##### ⚠️ 重要原則
- **句子級別標記**: 以句子為單位，不是整個 section
- **語意清晰**: 前端可明確區分優化 vs 新增內容
- **Gap Analysis 映射**: 直接對應 Gap Analysis 的三大輸出類型

---

**文件版本**: v2.0  
**建立日期**: 2025-08-21 14:30 CST  
**最後更新**: 2025-08-21 15:23 CST  
**狀態**: ✅ 已確認 - 準備實作