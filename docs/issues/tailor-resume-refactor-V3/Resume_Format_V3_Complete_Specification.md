# Resume Format V3 完整規格書

## 📋 版本資訊
- **版本**: 3.0.0 Final
- **日期**: 2025-08-21
- **狀態**: Production Ready
- **適用**: OCR Format 和 Resume Tailoring 共用格式

---

## 🎯 核心設計原則

### 1. 統一輸出格式
- OCR 和 Resume Tailoring 使用相同的輸出格式
- HTML 格式輸出，相容 TinyMCE 編輯器
- 標準化 section 順序和格式

### 2. 五層證據架構
```
1. Core Competencies - 技能關鍵字層
2. Professional Summary - 整體價值層  
3. Professional Experience - 具體成就層
4. Projects - 額外能力層
5. Certifications - 資格認證層
```

### 3. 統一專案放置原則
```
工作專案 → Professional Experience
學術專案 → Education (Academic Projects)
個人專案 → Projects Section
```

每個專案只出現在一個位置，不重複。

---

## 📐 標準履歷結構

### 🔄 Section 順序（動態調整）

#### 標準順序 (Education Enhancement OFF)
1. **Contact Information** (固定模板)
2. **Professional Summary**
3. **Core Competencies**
4. **Professional Experience**
5. **Education**
6. **Projects** (個人/Side Projects)
7. **Certifications & Achievements**

#### 應屆生順序 (Education Enhancement ON)
1. **Contact Information** (固定模板)
2. **Professional Summary**
3. **Core Competencies**
4. **Education** (Enhanced) ⬆️
5. **Professional Experience**
6. **Projects** (個人/Side Projects)
7. **Certifications & Achievements**

### 📝 各 Section 格式規範

#### 1. Contact Information
```html
<h3>John Doe</h3>
<p>Email: john.doe@email.com | Phone: +1-234-567-8900 | LinkedIn: linkedin.com/in/johndoe | Location: San Francisco, CA</p>
```

#### 2. Professional Summary
```html
<h2>Professional Summary</h2>
<p>Technical Leader with 10+ years driving end-to-end product development using <strong>Python</strong> and <strong>data analytics</strong>. Successfully launched products exceeding 35M units ($500M+ revenue) while managing cross-functional teams across 4 countries. Currently leading AI-powered SaaS platform development.</p>
```

#### 3. Core Competencies
```html
<h2>Core Competencies</h2>
<p><strong>Data Engineering & Analytics:</strong> Python • SQL • Apache Spark • Tableau • Power BI • Pandas • NumPy</p>
<p><strong>Project Management:</strong> Agile/Scrum • Risk Management • PMP Certified • Product Lifecycle</p>
<p><strong>Cloud & Infrastructure:</strong> AWS (EC2, S3, Lambda) • Azure • Docker • Kubernetes • CI/CD</p>
<p><strong>Leadership:</strong> Cross-functional Team Leadership • Vendor Management • Process Optimization</p>
```

#### 4. Professional Experience
```html
<h2>Professional Experience</h2>

<h3><strong>Technical Product Lead</strong></h3>
<p><em>AIResumeAdvisor</em> • <em>Remote</em> • <em>Jan 2024 - Present</em></p>
<ul>
<li>Architected AI-powered platform using <strong>Python</strong> and <strong>GPT-4 API</strong>, serving 1,000+ users with 99.9% uptime</li>
<li>Reduced development costs by 40% through strategic vendor management and <strong>Agile</strong> sprint optimization</li>
<li>Implemented <strong>CI/CD pipeline</strong> with Docker and automated testing, achieving 2-week release cycles</li>
<li>Built machine learning models for resume analysis, improving matching accuracy by 35%</li>
</ul>
```

#### 5. Projects
```html
<h2>Projects</h2>

<h3><strong>AI Resume Optimizer</strong></h3>
<p><em>Personal Project</em> • <em>Jan 2024 - Present</em></p>
<p>Open-source tool for automated resume enhancement using NLP</p>
<ul>
<li>Technologies: Python, TensorFlow, FastAPI, React, PostgreSQL</li>
<li>Impact: 500+ GitHub stars, used by 1,000+ job seekers monthly</li>
<li>Link: github.com/wenhaoyu/resume-optimizer</li>
</ul>
```

#### 6. Education

##### Standard Format (預設)
```html
<h2>Education</h2>

<h3>Master of Science - Decision Making and Applied Analytics</h3>
<p><em>Minerva University</em> • <em>San Francisco (Remote)</em> • <em>Sep 2023 - May 2025 (Expected)</em></p>
<ul>
<li>Relevant Coursework: Machine Learning, Statistical Analysis, Data Visualization</li>
<li>Thesis: Development and Implementation of AI-Powered Resume Optimization Platform</li>
</ul>
```

##### Enhanced Format (條件觸發)
```html
<h2>Education</h2>

<h3>Master of Science - Decision Making and Applied Analytics</h3>
<p><em>Minerva University</em> • <em>San Francisco (Remote)</em> • <em>Sep 2023 - May 2025 (Expected)</em></p>
<p><strong>GPA:</strong> 3.85/4.0</p>

<p><strong>Relevant Coursework:</strong></p>
<ul>
<li>Advanced Machine Learning • Statistical Modeling • Big Data Analytics</li>
<li>Cloud Computing Architecture • Data Visualization • Optimization Methods</li>
</ul>

<p><strong>Academic Projects:</strong></p>
<ul>
<li><strong>AI Resume Optimizer</strong> - Thesis project using NLP achieving 92% accuracy</li>
<li><strong>Real-time Stock Predictor</strong> - LSTM model with 78% prediction accuracy</li>
<li><strong>Customer Churn Analysis</strong> - Random Forest reducing churn by 25%</li>
</ul>

<p><strong>Leadership & Activities:</strong></p>
<ul>
<li>Teaching Assistant - Data Science (2 semesters, 150+ students)</li>
<li>President - Data Science Association (200+ members)</li>
<li>1st Place - Google Cloud ML Hackathon 2024</li>
</ul>
```

#### 7. Certifications & Achievements
```html
<h2>Certifications & Achievements</h2>

<h3>Certifications</h3>
<ul>
<li><strong>Project Management Professional (PMP)</strong> - Project Management Institute | 2018</li>
<li><strong>AWS Certified Solutions Architect</strong> - Amazon Web Services | 2023</li>
<li><strong>Google Data Analytics Certificate</strong> - Google | 2022</li>
</ul>

<h3>Achievements</h3>
<ul>
<li><strong>Product Excellence Award</strong> - AUO Optics | 2020</li>
<li><strong>Best Paper Award</strong> - DataCon Taiwan | 2023</li>
</ul>
```

---

## 🎓 Education Enhancement 決策邏輯

### 觸發條件
```python
def should_enhance_education(profile):
    """決定是否要強化 Education section"""
    return any([
        profile.years_of_experience < 2,
        profile.is_current_student,
        profile.months_since_graduation < 12,
        profile.has_only_internships
    ])
```

### Enhancement 內容
1. **GPA** - 只顯示 ≥ 3.0
2. **Relevant Coursework** - 6-8門相關課程
3. **Academic Projects** - 最多3個（保留在 Education）
4. **Leadership & Activities** - 選擇性顯示

### 重要規則
- **只強化最高學歷**
- **不包含難以標準化的榮譽**（Dean's List等）
- **Academic Projects 不移到 Projects section**

---

## 💡 核心指導原則

### 1. 關鍵字策略 (Role-Aligned Skills)
```python
skills_categorization = {
    "Technical Skills": ["直接技術能力"],
    "Tools & Technologies": ["工具和平台"],
    "Domain Knowledge": ["領域專業知識"],
    "Soft Skills": ["領導、溝通等"]
}
```

### 2. 證據分層展示
- **每層都要有關鍵字**但避免重複堆疊
- **量化成就**：使用數字、百分比、金額
- **行動動詞**：Led, Built, Implemented, Achieved
- **結果導向**：展示 impact 而非責任

### 3. ATS 優化
- 使用標準 HTML 標籤
- 關鍵字自然分布
- 避免圖片、表格、特殊字符
- 保持格式簡潔易解析

---

## 💻 LLM Prompt 實作指引

### 基本 Prompt 結構
```python
prompt = f"""
Generate an HTML-formatted resume following these strict rules:

1. SECTION ORDER (CRITICAL):
   If Education Enhancement is ON (recent grad/student):
     - Professional Summary
     - Core Competencies  
     - Education (Enhanced)
     - Professional Experience
     - Projects
     - Certifications & Achievements
   
   If Education Enhancement is OFF (experienced professional):
     - Professional Summary
     - Core Competencies
     - Professional Experience
     - Education (Standard)
     - Projects
     - Certifications & Achievements

2. HTML STRUCTURE:
   - Use <h2> for section titles
   - Use <h3> for job titles/degree names with <strong> tags
   - Use <p> for meta info with <em> for company/location/date
   - Use <ul><li> for bullet points
   - Use <strong> to emphasize keywords from JD

3. PROJECT PLACEMENT RULES:
   - Work projects → Stay in Professional Experience bullets
   - Academic projects → Stay in Education section (if enhanced)
   - Personal/side projects → Go to Projects section
   - NEVER duplicate projects across sections

4. EDUCATION ENHANCEMENT LOGIC:
   If user has < 2 years experience OR is current student:
     - Add GPA if >= 3.0
     - Add 6-8 relevant courses
     - Add max 3 academic projects (one line each)
     - Add leadership/activities if applicable
   
   Otherwise keep standard format with just degree info.

5. CORE COMPETENCIES FORMAT:
   - Single line per category with bullet separator
   - Format: <strong>Category:</strong> Skill1 • Skill2 • Skill3
   - Categories based on JD analysis

Input Resume: {resume_text}
Target Job Description: {job_description}
Years of Experience: {years_of_experience}
Currently Student: {is_student}
"""
```

### Few-shot Example 提示
提供2-3個完整範例，包含：
1. **Senior Professional** (10+ years, Enhancement OFF)
2. **Recent Graduate** (0-1 year, Enhancement ON)  
3. **Career Changer** (3-5 years, 視情況)

---

## 📊 完整範例

### Example 1: 應屆生 (Enhancement ON)

```markdown
## PROFESSIONAL SUMMARY

Recent CS graduate with strong foundation in **machine learning** and **data engineering**. Developed 3 production-ready applications during internships, including an AI-powered recommendation system serving 10K+ users. Seeking to leverage **Python** expertise and **cloud computing** skills in a data engineering role.

## CORE COMPETENCIES

**Programming Languages:** Python • Java • SQL • JavaScript • C++
**Data & ML Tools:** TensorFlow • PyTorch • Pandas • NumPy • Scikit-learn
**Cloud & DevOps:** AWS • Docker • Kubernetes • Git • CI/CD
**Databases:** PostgreSQL • MongoDB • Redis • Elasticsearch

## EDUCATION

### Master of Science - Computer Science
*Stanford University* • *Stanford, CA* • *Sep 2023 - Jun 2025 (Expected)*
**GPA:** 3.92/4.0

**Relevant Coursework:**
• Machine Learning • Deep Learning • Distributed Systems
• Cloud Computing • Database Systems • Algorithm Design

**Academic Projects:**
• **Distributed ML Framework** - Built scalable training system achieving 3x speedup
• **NLP Sentiment Analyzer** - BERT-based model with 94% accuracy on Twitter data
• **Real-time Data Pipeline** - Kafka + Spark processing 1M events/sec

**Leadership & Activities:**
• Teaching Assistant - CS231n Deep Learning (2 quarters, 200+ students)
• VP Engineering - Stanford AI Club (50+ members)
• 1st Place - Google Cloud Hackathon 2024

## PROFESSIONAL EXPERIENCE

### **Machine Learning Intern**
*Google* • *Mountain View, CA* • *Jun 2024 - Sep 2024*

• Developed recommendation algorithm improving CTR by 15% using **TensorFlow**
• Built data pipeline processing 100GB+ daily using **Apache Beam**
• Implemented A/B testing framework serving 1M+ users

### **Software Engineering Intern**
*Meta* • *Menlo Park, CA* • *Jun 2023 - Sep 2023*

• Created React dashboard reducing report generation time by 60%
• Optimized PostgreSQL queries improving response time by 40%

## PROJECTS

### **Open Source ML Library**
*Personal Project* • *Jan 2024 - Present*

Contributing to scikit-learn with focus on ensemble methods
• Technologies: Python, NumPy, Cython
• Impact: 5 merged PRs, 100+ GitHub stars on fork

## CERTIFICATIONS & ACHIEVEMENTS

### Certifications
• **AWS Certified Solutions Architect** - Amazon | 2024
• **TensorFlow Developer Certificate** - Google | 2023

### Achievements
• **Dean's Award for Academic Excellence** - Stanford | 2024
• **Best Paper Award** - "Efficient Distributed Training" - NeurIPS Workshop | 2024
```

### Example 2: 資深專業人士 (Enhancement OFF)

```markdown
## PROFESSIONAL SUMMARY

Technical Leader with 10+ years driving end-to-end product development using **Python** and **data analytics**. Successfully launched products exceeding 35M units ($500M+ revenue) while managing cross-functional teams across 4 countries. Currently leading AI-powered SaaS platform development with expertise in machine learning and cloud architecture.

## CORE COMPETENCIES

**Data Engineering & Analytics:** Python • SQL • Apache Spark • Tableau • Power BI • Pandas
**Project Management:** Agile/Scrum • Risk Management • PMP Certified • Product Lifecycle
**Cloud & Infrastructure:** AWS • Azure • Docker • Kubernetes • CI/CD • Terraform
**Leadership:** Team Building • Vendor Management • Strategic Planning • P&L Management

## PROFESSIONAL EXPERIENCE

### **Technical Product Lead**
*AIResumeAdvisor* • *Remote* • *Jan 2024 - Present*

• Architected AI platform using **Python** and **GPT-4**, serving 10K+ users
• Reduced infrastructure costs by 40% through AWS optimization
• Led team of 8 engineers delivering features in 2-week sprints
• Implemented MLOps pipeline reducing model deployment time by 70%

### **Senior Engineering Manager**
*Microsoft* • *Seattle, WA* • *Jul 2018 - Dec 2023*

• Managed 25-person team building Azure ML services
• Launched 3 products generating $50M+ annual revenue
• Improved system reliability from 99.5% to 99.99% uptime
• Established engineering best practices adopted company-wide

### **Principal Data Engineer**
*Amazon* • *Seattle, WA* • *Jan 2015 - Jun 2018*

• Built recommendation engine processing 1B+ daily events
• Designed data warehouse handling 100TB+ with <100ms queries
• Led migration to microservices reducing costs by 35%

## EDUCATION

### Master of Science - Computer Science
*University of Washington* • *Seattle, WA* • *Sep 2013 - Jun 2015*
• Specialization: Distributed Systems and Machine Learning

### Bachelor of Science - Computer Engineering
*UC Berkeley* • *Berkeley, CA* • *Sep 2009 - May 2013*

## PROJECTS

### **Cloud Cost Optimizer**
*Open Source Project* • *2023 - Present*

Automated tool for AWS/Azure cost optimization
• Technologies: Python, Terraform, CloudFormation
• Impact: 500+ stars, saves users average $10K/month

## CERTIFICATIONS & ACHIEVEMENTS

### Certifications
• **Project Management Professional (PMP)** - PMI | 2019
• **AWS Solutions Architect Professional** - Amazon | 2020
• **Certified Kubernetes Administrator** - CNCF | 2021

### Achievements
• **Engineering Excellence Award** - Microsoft | 2022
• **Patent Holder** - "Distributed ML Training System" | 2021
```

---

## 🔍 驗證檢查清單

### 格式驗證
- [ ] Section 順序符合 Enhancement 狀態
- [ ] HTML 標籤使用正確
- [ ] 日期格式一致（MMM YYYY）
- [ ] 公司名和日期用 bullet 分隔

### 內容驗證
- [ ] 關鍵字適當標記 `<strong>`
- [ ] 成就包含量化指標
- [ ] 專案放置符合統一原則
- [ ] Education Enhancement 只應用於最高學歷

### ATS 優化驗證
- [ ] 無特殊字符或圖片
- [ ] 關鍵字自然分布
- [ ] 格式簡潔易解析

---

## 8. CSS Class 與 HTML Tag 整合系統

### 8.1 設計原則：語義分離

採用 **語義分離** (Semantic Separation) 方案：
- **HTML Tags** (`<strong>`, `<em>`)：表達內容的語義重要性
- **CSS Classes** (`opt-*`)：標記優化狀態和追蹤來源

### 8.2 CSS Class 命名規範

| CSS Class | 用途 | 顏色 | 應用場景 |
|-----------|------|------|----------|
| `opt-keyword-add` | 新增的關鍵字 | 紫色邊框 | 從 JD 新增到履歷的關鍵字 |
| `opt-keyword-existing` | 既有的關鍵字 | 藍色背景 | 履歷中已存在且匹配 JD 的關鍵字 |
| `opt-modified` | 修改的內容 | 淺黃背景 | 經過優化調整的句子或段落 |
| `opt-new` | 新增的段落 | 綠色左邊框 | 完全新增的項目或段落 |
| `opt-placeholder` | 佔位符 | 淺紅背景 | 需要使用者填寫的內容 |

### 8.3 HTML 實作範例

```html
<!-- 新增的關鍵字 -->
<strong class="opt-keyword-add">Machine Learning</strong>

<!-- 既有的關鍵字 -->
<strong class="opt-keyword-existing">Python</strong>

<!-- 修改的內容 -->
<span class="opt-modified">Led cross-functional team of 8 engineers</span>

<!-- 新增的段落 -->
<li class="opt-new">
  Implemented <strong class="opt-keyword-add">MLOps pipeline</strong> reducing deployment time by 70%
</li>

<!-- 佔位符 -->
<span class="opt-placeholder">[具體成果數據]</span>
```

### 8.4 CSS 樣式定義

```css
/* 新增關鍵字 - 紫色邊框 */
strong.opt-keyword-add {
    color: #6366F1 !important;
    border: 1px solid #C7D2FE !important;
    font-weight: 600;
    padding: 0 2px;
}

/* 既有關鍵字 - 藍色背景 */
strong.opt-keyword-existing {
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 600;
    padding: 0 4px;
    border-radius: 2px;
}

/* 修改內容 - 淺黃背景 */
.opt-modified {
    background-color: #FFF3CD !important;
    padding: 0 2px;
}

/* 新增段落 - 綠色左邊框 */
.opt-new {
    border-left: 4px solid #10B981 !important;
    padding-left: 8px !important;
    margin-left: -12px !important;
}

/* 佔位符 - 淺紅背景虛線框 */
.opt-placeholder {
    background-color: #FEE2E2 !important;
    border: 1px dashed #F87171 !important;
    padding: 2px 4px;
    cursor: pointer;
}

/* Hover 效果 */
.opt-keyword-add:hover,
.opt-keyword-existing:hover {
    opacity: 0.8;
    transition: opacity 0.2s;
}

/* Dark mode 支援 */
@media (prefers-color-scheme: dark) {
    strong.opt-keyword-add {
        color: #A5B4FC !important;
        border-color: #6366F1 !important;
    }
    
    strong.opt-keyword-existing {
        background-color: #3B82F6 !important;
    }
}
```

### 8.5 Python 後處理實作指引

```python
def apply_optimization_markup(text: str, keyword_tracking: dict) -> str:
    """
    應用 CSS class 和 HTML tag 標記
    
    Args:
        text: 原始文本
        keyword_tracking: {
            'newly_added': [...],      # 新增的關鍵字
            'still_covered': [...],    # 既有的關鍵字
            'modified_sections': [...] # 修改的段落
        }
    """
    
    # 處理新增關鍵字
    for keyword in keyword_tracking['newly_added']:
        pattern = rf'{re.escape(keyword)}'
        replacement = f'<strong class="opt-keyword-add">{keyword}</strong>'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # 處理既有關鍵字
    for keyword in keyword_tracking['still_covered']:
        pattern = rf'{re.escape(keyword)}'
        replacement = f'<strong class="opt-keyword-existing">{keyword}</strong>'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text
```

### 8.6 優勢與考量

**優勢：**
- ✅ **ATS 友好**：`<strong>` 標籤被 ATS 系統正確識別為重要內容
- ✅ **語義清晰**：HTML 表達重要性，CSS 表達優化狀態
- ✅ **視覺區分**：不同顏色清楚標識內容來源和狀態
- ✅ **編輯器相容**：TinyMCE 可正確處理和保留標記
- ✅ **可擴展性**：易於添加新的優化狀態類別

**注意事項：**
- 避免過度標記造成視覺混亂
- 確保顏色對比度符合 WCAG 2.1 AA 標準
- 提供使用者選項隱藏/顯示優化標記
- 匯出 PDF 時可選擇保留或移除標記

---

## 🚀 實作注意事項

### API 整合
1. OCR Format API 和 Resume Tailoring API 共用此格式
2. 前端 TinyMCE 編輯器相容性已驗證
3. 輸出 HTML 需進行 XSS 防護

### 版本管理
- 格式版本號記錄在輸出 metadata
- 向後相容舊版本（v2.x）
- 重大變更需要遷移計畫

### 監控指標
- 格式正確率 > 99%
- Education Enhancement 準確率 > 95%
- 專案分類準確率 > 90%

---

## 📝 更新日誌

### v3.0.0 (2025-08-21)
- ✅ 統一 OCR 和 Tailoring 輸出格式
- ✅ 實作統一專案放置原則
- ✅ 標準化 Education Enhancement
- ✅ 移除難以標準化的元素
- ✅ Core Competencies 改為單行格式
- ✅ 新增動態 Section 順序（Enhancement ON 時 Education 在前）
- ✅ 整合 CSS Class 與 HTML Tag 標記系統
- ✅ 改名 opt-keyword → opt-keyword-add
- ✅ 支援 opt-keyword-existing 與 <strong> 標籤結合

---

**維護者**: AIResumeAdvisor Team  
**最後更新**: 2025-08-21  
**狀態**: Production Ready