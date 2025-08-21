# Resume Tailoring HTML 輸出分析：當前 vs V3 規格

## 📊 當前實作分析

### 當前 HTML 標籤使用
根據程式碼分析，當前 `/api/v1/tailor-resume` 使用的 HTML 標籤：

1. **基本結構標籤**
   - `<h2>` - Section 標題（但沒看到明確定義）
   - `<p>` - 段落
   - `<ul>`, `<li>` - 列表項目
   - `<span>` - 內聯標記

2. **CSS Classes（優化標記）**
   ```
   opt-modified     - 修改過的內容
   opt-new          - 新增的內容/section
   opt-placeholder  - 佔位符（如 [TEAM SIZE]）
   opt-keyword      - 新增的關鍵字
   opt-keyword-existing - 原有的關鍵字
   ```

3. **當前輸出格式特點**
   - 沒有明確的 HTML 結構規範
   - 主要依賴 LLM 自行決定 HTML 格式
   - 重點在 CSS class 標記優化內容
   - 沒有固定的 section 順序

---

## 🆚 V3 規格對比

### V3 HTML 標籤規範

```html
<!-- Contact Information -->
<h3>John Doe</h3>
<p>Email: john.doe@email.com | Phone: +1-234-567-8900 | LinkedIn: linkedin.com/in/johndoe | Location: San Francisco, CA</p>

<!-- Section 標題 -->
<h2>Professional Summary</h2>
<h2>Core Competencies</h2>
<h2>Professional Experience</h2>
<h2>Projects</h2>
<h2>Education</h2>
<h2>Certifications & Achievements</h2>

<!-- 職位/學位 -->
<h3><strong>Job Title</strong></h3>
<p><em>Company Name</em> • <em>Location</em> • <em>Date Range</em></p>

<!-- 內容 -->
<ul>
<li>Achievement with <strong>keyword</strong> emphasis</li>
</ul>

<!-- Core Competencies 特殊格式 -->
<p><strong>Category:</strong> Skill1 • Skill2 • Skill3</p>
```

---

## 📋 主要差異

| 項目 | 當前實作 | V3 規格 |
|------|---------|---------|
| **Contact** | 未定義 | `<h3>` + `<p>` 固定格式 |
| **Section 標題** | 可能用 `<h2>` | 明確 `<h2>` |
| **職位/學位** | 未定義 | `<h3><strong>Title</strong></h3>` |
| **公司/學校資訊** | 未定義 | `<p><em>Company</em> • <em>Location</em> • <em>Date</em></p>` |
| **技能展示** | 未定義 | 單行 `<p><strong>Category:</strong> Skills</p>` |
| **關鍵字強調** | CSS class 標記 | `<strong>` 標籤 |
| **Section 順序** | 無固定順序 | 動態順序（根據 Enhancement） |

---

## 🔧 需要的調整

### 1. HTML 結構標準化
**當前問題**：
- LLM 自由決定 HTML 格式
- 沒有一致的標籤使用規則

**V3 解決方案**：
```python
# 明確的 HTML 模板
SECTION_TEMPLATES = {
    "contact": "<h3>{name}</h3>\n<p>{contact_info}</p>",
    "section_title": "<h2>{title}</h2>",
    "job_title": "<h3><strong>{title}</strong></h3>\n<p><em>{company}</em> • <em>{location}</em> • <em>{dates}</em></p>",
    "bullet_point": "<li>{content}</li>",
    "skill_category": "<p><strong>{category}:</strong> {skills}</p>"
}
```

### 2. Section 順序控制
**當前問題**：
- 沒有 section 順序邏輯

**V3 解決方案**：
```python
def get_section_order(education_enhancement_on: bool):
    if education_enhancement_on:
        return ["Summary", "Core Competencies", "Education", "Experience", "Projects", "Certifications"]
    else:
        return ["Summary", "Core Competencies", "Experience", "Education", "Projects", "Certifications"]
```

### 3. CSS Class 整合
**保留當前的優化標記**：
- `opt-modified` - 繼續使用
- `opt-new` - 繼續使用
- `opt-placeholder` - 繼續使用
- `opt-keyword` / `opt-keyword-existing` - 繼續使用

**新增 V3 結構標記**：
- 使用 `<strong>` 標記 JD 關鍵字（除了 CSS class）
- 使用 `<em>` 標記公司/日期等 metadata

### 4. Core Competencies 格式
**當前**：可能是列表格式
**V3**：單行格式
```html
<h2>Core Competencies</h2>
<p><strong>Programming:</strong> Python • Java • SQL</p>
<p><strong>Cloud:</strong> AWS • Azure • GCP</p>
```

### 5. Education Enhancement
**新增邏輯**：
```python
if years_of_experience < 2 or is_student:
    # Enhanced format with GPA, Coursework, Academic Projects
    use_enhanced_education_format = True
    # Education section 移到 Experience 前面
    move_education_before_experience = True
```

---

## 💡 實作建議

### Phase 1: Prompt 更新
更新 `v2.1.0-simplified.yaml` 加入：
1. 明確的 HTML 標籤規則
2. Section 順序邏輯
3. Core Competencies 單行格式
4. Education Enhancement 判斷

### Phase 2: Post-Processing
在 `_process_optimization_result_v2` 加入：
1. HTML 結構驗證
2. Section 順序調整
3. 格式標準化

### Phase 3: 測試驗證
1. 確認 HTML 輸出符合 V3 規格
2. 驗證 TinyMCE 相容性
3. 測試 ATS 解析效果

---

## 📝 結論

當前實作重點在**內容優化標記**（CSS classes），但缺乏**結構化 HTML 規範**。

V3 規格提供了：
1. ✅ 標準化的 HTML 結構
2. ✅ 動態 Section 順序
3. ✅ Education Enhancement 邏輯
4. ✅ 統一的專案放置原則

建議保留當前的 CSS class 優化標記系統，同時加入 V3 的結構化規範，達到最佳效果。