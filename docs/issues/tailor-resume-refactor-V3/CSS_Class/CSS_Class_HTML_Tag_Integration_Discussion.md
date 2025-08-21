# CSS Class 與 HTML 標籤整合討論

## 🤔 核心問題

如何同時使用：
1. CSS Class 標記（優化追蹤）
2. HTML 語義標籤（格式化）

特別是 `opt-keyword` / `opt-keyword-existing` 與 `<strong>` 的潛在衝突。

---

## 📊 使用場景分析

### 1. CSS Class 的用途（優化追蹤）
```html
<!-- 用於前端識別哪些內容被優化過 -->
<span class="opt-keyword">Python</span>         <!-- 新增的關鍵字 -->
<span class="opt-keyword-existing">Java</span>  <!-- 原有的關鍵字 -->
<span class="opt-modified">改寫的內容</span>      <!-- 修改過的內容 -->
<span class="opt-placeholder">[TEAM SIZE]</span> <!-- 需要填寫的佔位符 -->
```
**目的**：讓用戶在 UI 中看到哪些部分被優化了

### 2. HTML 語義標籤的用途（內容強調）
```html
<!-- 用於語義化和 ATS 解析 -->
<strong>Python</strong>     <!-- 重要技能/關鍵字 -->
<em>Google</em>             <!-- 公司名稱 -->
<em>Jan 2024 - Present</em> <!-- 日期 -->
```
**目的**：語義化標記，幫助 ATS 識別重要內容

---

## 💡 整合方案討論

### 方案 A：雙層標記（CSS Class + HTML Tag）
```html
<!-- 同時使用兩種標記 -->
<span class="opt-keyword"><strong>Python</strong></span>
<span class="opt-keyword-existing"><strong>Java</strong></span>

<!-- 優點：保留兩種功能 -->
<!-- 缺點：HTML 嵌套複雜 -->
```

### 方案 B：分離使用（根據上下文）
```html
<!-- 在技能列表中：只用 strong（因為都是關鍵字） -->
<p><strong>Programming:</strong> <strong>Python</strong> • <strong>Java</strong> • <strong>SQL</strong></p>

<!-- 在經驗描述中：用 CSS class 標記新增的關鍵字 -->
<li>Developed applications using <span class="opt-keyword">Python</span> and Django framework</li>
```

### 方案 C：優先級策略
```html
<!-- 規則：opt-keyword 類的 CSS class 優先，不再加 strong -->
<span class="opt-keyword">Python</span>  <!-- 不加 strong，因為 CSS 已經會顯示強調 -->

<!-- 但對於非關鍵字追蹤的重要內容，仍用 strong -->
<li>Led team of <strong>10 engineers</strong> to deliver project</li>
```

### 方案 D：語義分離（推薦）
```html
<!-- CSS Class = 優化追蹤（什麼被改了） -->
<!-- HTML Tag = 內容語義（什麼是重要的） -->

<!-- 範例1：新增的關鍵字（既是優化，也是重要內容） -->
<strong class="opt-keyword">Python</strong>

<!-- 範例2：原有的關鍵字（不是優化，但是重要內容） -->
<strong>Java</strong>  <!-- 如果原本就有，不需要 opt-keyword-existing -->

<!-- 範例3：修改的內容（可能包含重要和非重要） -->
<span class="opt-modified">Managed team of <strong>10 engineers</strong> using Agile</span>

<!-- 範例4：公司和日期（用 em，不用 strong） -->
<p><em>Google</em> • <em>Mountain View, CA</em> • <em>Jan 2024 - Present</em></p>
```

---

## 🎯 建議的整合原則

### 1. 目的分離
- **CSS Classes**：追蹤優化歷程（什麼被改變了）
- **HTML Tags**：標記內容重要性（什麼是關鍵的）

### 2. 使用規則

#### Strong 標籤使用場景
- ✅ JD 中的關鍵技能詞
- ✅ 重要數字/成就（如 "increased by **50%**"）
- ✅ 技能分類標題（如 "**Programming:**"）
- ❌ 公司名稱（用 `<em>`）
- ❌ 日期（用 `<em>`）

#### CSS Class 使用場景
- ✅ `opt-keyword`：新增的關鍵字
- ✅ `opt-keyword-existing`：要強調保留的原有關鍵字
- ✅ `opt-modified`：任何被改寫的內容
- ✅ `opt-new`：全新的 section 或段落
- ✅ `opt-placeholder`：需要用戶填寫的佔位符

### 3. 組合使用範例

```html
<!-- Core Competencies Section -->
<h2>Core Competencies</h2>
<p><strong>Programming:</strong> <strong class="opt-keyword">Python</strong> • <strong>Java</strong> • <strong class="opt-keyword">Go</strong></p>

<!-- Experience Section -->
<h3><strong>Senior Software Engineer</strong></h3>
<p><em>Google</em> • <em>Mountain View, CA</em> • <em>Jan 2024 - Present</em></p>
<ul>
<li>Led development team using <strong class="opt-keyword">Python</strong> and <strong>Django</strong></li>
<li class="opt-modified">Improved system performance by <strong>50%</strong> through optimization</li>
<li class="opt-new">Implemented <strong>CI/CD</strong> pipeline reducing deployment time by <strong>70%</strong></li>
</ul>
```

---

## 🤔 討論問題

### Q1: opt-keyword-existing 是否需要？
**場景**：原本履歷就有 "Java"，但想標記它很重要

**選項 A**：不需要 class，直接用 `<strong>Java</strong>`
**選項 B**：保留 class 用於追蹤 `<strong class="opt-keyword-existing">Java</strong>`

**建議**：選項 A，因為 "existing" 表示沒有優化動作，不需要追蹤

### Q2: 是否所有關鍵字都要 strong？
**問題**：如果整個 Skills section 都是關鍵字，全部 strong 會不會太多？

**建議**：
- Skills section：可以不用 strong（因為整個 section 都是技能）
- Experience bullets：選擇性使用 strong（只標記最相關的）
- Summary：選擇性使用 strong（2-3 個核心關鍵字）

### Q3: 嵌套標記的複雜度？
```html
<!-- 這樣會不會太複雜？ -->
<li class="opt-modified">
  Developed <strong class="opt-keyword">microservices</strong> using 
  <strong>Python</strong> and <strong class="opt-keyword">Kubernetes</strong>
</li>
```

**建議**：可接受，因為各有其功能：
- `opt-modified`：追蹤整個 bullet 被改寫
- `opt-keyword`：追蹤新增了哪些關鍵字
- `<strong>`：標記重要內容給 ATS

---

## 📋 最終建議

### 推薦：方案 D（語義分離）

1. **CSS Class** = 優化動作追蹤
2. **HTML Tag** = 內容重要性標記
3. **可以組合使用**：`<strong class="opt-keyword">Python</strong>`
4. **簡化原則**：
   - 如果原本就存在的關鍵字 → 只用 `<strong>`
   - 如果是新增的關鍵字 → `<strong class="opt-keyword">`
   - 如果是修改的內容 → `<span class="opt-modified">` 包住整個修改部分

這樣可以同時達到：
- ✅ 前端 UI 顯示優化標記
- ✅ ATS 友好的語義化 HTML
- ✅ 相對簡潔的標記結構