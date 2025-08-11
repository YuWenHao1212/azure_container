# Resume Tailoring API v2.1.0-simplified 重構專案

## 📋 專案概述

本專案重構 `/api/v1/tailor-resume` API，實作混合 CSS 標記系統與完整的關鍵字追蹤功能。

## 🏗️ 架構改進

### 兩階段管線架構
1. **Stage 1: Instruction Compiler** (GPT-4.1 mini) - 結構分析
2. **Stage 2: Resume Writer** (GPT-4.1) - 內容優化

### 混合 CSS 標記系統
- **LLM 生成**：語意標記（opt-modified, opt-new, opt-placeholder）
- **Python 後處理**：關鍵字標記（opt-keyword, opt-keyword-existing）

## 📊 關鍵改進

| 功能 | 說明 |
|------|------|
| **關鍵字追蹤** | 四種狀態：still_covered, removed, newly_added, still_missing |
| **警告機制** | 關鍵字被移除時觸發警告（HTTP 200 + warning） |
| **錯誤處理** | 標準化錯誤碼（VALIDATION_*, EXTERNAL_*, SYSTEM_*） |
| **效能目標** | P50 < 4.5s, P95 < 7.5s |

## 📁 專案文檔

| 文檔 | 說明 | 狀態 |
|------|------|------|
| [API_ANALYSIS_20250811.md](./API_ANALYSIS_20250811.md) | 完整技術分析與設計方案 | ✅ 最終版本 |
| [IMPLEMENTATION_TESTING.md](./IMPLEMENTATION_TESTING.md) | 實作步驟與測試計畫 | 📝 待實作 |

## 🚀 實作狀態

### ✅ 已完成
- 混合 CSS 標記方案設計
- 關鍵字追蹤邏輯設計
- 錯誤處理策略確定
- API 回應格式定義

### 📝 待實作
- 關鍵字檢測方法實作
- 後處理邏輯整合
- API 路由更新
- 測試案例撰寫

## 🔄 版本歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| v2.1.0-simplified | 2025-08-11 | 混合 CSS 標記系統設計完成 |
| v2.0.0 | 2025-01-16 | 兩階段架構實作 |
| v1.1.0 | - | 原始單一 LLM 架構 |

---

**維護者**: Claude Code + WenHao  
**最後更新**: 2025-08-11  
**狀態**: 🚧 設計完成，待實作