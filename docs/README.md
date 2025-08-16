# 📚 文檔中心

## 核心文檔

### 🎯 環境變數與部署管理（整合文檔）
**[ENVIRONMENT-AND-PROMPT-MANAGEMENT.md](./ENVIRONMENT-AND-PROMPT-MANAGEMENT.md)**

這份整合文檔包含了以下內容：
- ✅ 環境變數配置與管理
- ✅ Prompt 版本管理系統
- ✅ CI/CD 工作流程詳解
- ✅ Azure 部署指南
- ✅ 故障排除與監控
- ✅ 最佳實踐與維護指南

> 💡 這是唯一需要查看的操作手冊，整合了原本 7 份文檔的精華內容

---

## 其他重要文檔

### 專案文檔
- [API 文檔](./api-documentation.md) - API 端點詳細說明
- [架構設計](./architecture.md) - 系統架構與設計決策
- [資料庫設計](./database-design.md) - PostgreSQL 與 pgvector 設計

### 功能文檔
- [Index Calculation](./index-calculation/) - 匹配指數計算
- [Gap Analysis](./issues/index-cal-and-gap-analysis-v4-refactor/) - 差距分析實作
- [Resume Tailoring](./resume-tailoring/) - 履歷客製化

### 問題追蹤
- [Issues](./issues/) - 已解決問題與實作歷程
- [Performance](./performance/) - 效能優化記錄

---

## 📁 已歸檔文檔

以下文檔已整合到主文檔中，保留在 archive 供參考：

### `/docs/archive/`
- `DEPLOYMENT.md` - 原始部署文檔

### `/docs/archive/prompt-management/`
- `env-vars-config-table.md` - 環境變數配置表
- `environment-variables-management.md` - 環境變數管理
- `prompt-version-rules.md` - Prompt 版本規則
- `view-actual-env-values.md` - 查看實際值指南
- `prompt-version-management.md` - Prompt 版本管理
- `github-actions-cicd.md` - CI/CD 策略

---

## 🔄 文檔整合歷程

### 2025-08-16 整合專案
**原始文檔數量**: 7 份分散文檔 + DEPLOYMENT.md  
**整合後**: 1 份完整操作手冊

**整合原則**：
1. 移除重複資訊
2. 保留實用操作指令
3. 組織邏輯流暢
4. 便於快速查找

**主要改進**：
- 統一查詢入口
- 清晰的層級結構
- 實用的快速參考
- 完整的故障排除

---

## 📝 維護指南

### 新增內容時
1. 優先更新 `ENVIRONMENT-AND-PROMPT-MANAGEMENT.md`
2. 避免創建分散的小文檔
3. 保持文檔結構清晰

### 定期檢查
- 每月：檢查環境變數是否有更新
- 每季：審查文檔準確性
- 每次重大變更：更新相關章節

---

最後更新：2025-08-16