# Keyword Standardization Dictionary

此目錄包含關鍵字標準化系統使用的所有字典和規則。

## 📁 檔案結構

- **skills.yaml** - 技能相關映射（218 條目）
- **positions.yaml** - 職位相關映射（84 條目）
- **tools.yaml** - 工具和技術相關映射（154 條目）
- **patterns.yaml** - 模式匹配規則（60 條規則）

## 📊 統計摘要

| 類別 | 檔案 | 條目數 |
|------|------|--------|
| 技能 | skills.yaml | 218 |
| 職位 | positions.yaml | 84 |
| 工具 | tools.yaml | 154 |
| 模式 | patterns.yaml | 60 |
| **總計** | | **516** |

## 🔧 維護指南

### 新增映射

1. 確定要新增的映射屬於哪個類別
2. 在對應的 YAML 檔案中找到適當的分類
3. 遵循現有格式新增映射：
   ```yaml
   原始關鍵字: 標準化關鍵字
   ```

### 命名規範

- 所有鍵值（原始關鍵字）使用小寫
- 標準化值保持適當的大小寫（如 "Python", "AWS", "Machine Learning"）
- 縮寫詞保持大寫（如 "AI", "ML", "API"）

### 更新流程

1. **修改前**：備份現有檔案
2. **修改時**：
   - 更新對應的 YAML 檔案
   - 更新檔案頭部的 `Last Updated` 日期
   - 更新條目數統計
3. **修改後**：
   - 執行驗證腳本（如果有）
   - 測試修改是否正常運作
   - 提交變更並記錄在 CHANGE_LOG.md

### 注意事項

1. **避免衝突**：確保新增的映射不會與現有映射衝突
2. **保持一致性**：相似的詞彙應該映射到相同的標準形式
3. **考慮上下文**：某些詞彙可能在不同上下文有不同含義
4. **定期審查**：每季度審查一次，移除過時的映射

## 🔍 快速查找

### Skills (skills.yaml)
- Programming Languages: Python, Java, JavaScript, etc.
- AI/ML: Machine Learning, Deep Learning, NLP, etc.
- Data Science: Analytics, Statistics, Modeling, etc.
- Web Development: Frontend, Backend, Full Stack, etc.
- Databases: SQL, NoSQL, specific databases
- Cloud & DevOps: AWS, Azure, GCP, Docker, K8s, etc.

### Positions (positions.yaml)
- Data Roles: Analyst, Scientist, Engineer
- Software Engineering: Developer, Engineer, Architect
- Leadership: Tech Lead, Manager, Director
- Specialized: DevOps, Security, AI/ML Engineers

### Tools (tools.yaml)
- IDEs: VS Code, IntelliJ, PyCharm
- Frameworks: React, Angular, Django, Spring
- Databases: MySQL, PostgreSQL, MongoDB
- DevOps: Docker, Kubernetes, Jenkins, Terraform
- Cloud Services: EC2, S3, Lambda, Azure Services

### Patterns (patterns.yaml)
- Suffix Removal: Remove common suffixes like "programming", "skills"
- Abbreviation Expansion: Expand ML → machine learning
- Version Removal: Remove version numbers
- Special Characters: Normalize punctuation

## 📝 範例

### 新增技能映射
```yaml
# 在 skills.yaml 的適當分類下新增
rust programming: Rust
rust development: Rust
```

### 新增職位映射
```yaml
# 在 positions.yaml 的適當分類下新增
platform engineer: Platform Engineer
platform engineering: Platform Engineer
```

### 新增模式規則
```yaml
# 在 patterns.yaml 的適當分類下新增
- pattern: '\b(arch\.|architect)\s+'
  replacement: 'architect '
  type: normalization
  description: Normalize architect abbreviations
```

## 🛠️ 工具和腳本

（待開發）
- `validate_dictionaries.py` - 驗證字典完整性
- `export_to_csv.py` - 匯出為 CSV 格式
- `import_from_csv.py` - 從 CSV 匯入
- `find_duplicates.py` - 查找重複映射
- `test_standardization.py` - 測試標準化效果

## 📞 聯絡方式

如有問題或建議，請聯絡：
- 技術問題：開發團隊
- 內容更新：業務分析師
- 緊急修復：專案經理