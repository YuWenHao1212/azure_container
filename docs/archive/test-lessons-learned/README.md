# 測試經驗教訓歸檔

**歸檔日期**: 2025-08-19  
**歸檔原因**: 已整合至綜合測試設計指南

## 📁 歸檔內容

本資料夾包含原始的測試相關經驗教訓文檔，這些內容已被整合到新的統一測試設計指南中。

### 歸檔文檔清單

1. **lessons_learned_ci_test_failures.md**
   - CI/CD 測試失敗除錯案例
   - Course Batch Query 單元測試問題
   - 環境隔離和條件初始化經驗

2. **precommit-test-lesson-learned.md**
   - Pre-commit 測試隔離 DO's 和 DON'T's
   - AsyncMock 最佳實踐
   - Import 系統污染問題

3. **test-implementation-lessons-learned.md**
   - Index Cal and Gap Analysis V2 測試實作經驗
   - LLM Factory 違規問題
   - JSON 解析和效能測試診斷

4. **test-implementation-summary.md**
   - Resume Tailoring 測試實作總結
   - Test ID 標記完善
   - 防禦性設計實作

## 📚 新文檔位置

這些經驗教訓已整合至：

- **[綜合測試設計指南](../../development/COMPREHENSIVE_TEST_DESIGN_GUIDE.md)**
  - 完整的測試設計原則和最佳實踐
  - 整合所有歷史經驗教訓

- **[測試快速參考卡](../../development/TEST_QUICK_REFERENCE.md)**
  - DO's 和 DON'T's 快速查詢
  - 常用命令和診斷工具

- **[測試疑難排解指南](../../development/TEST_TROUBLESHOOTING_GUIDE.md)**
  - 按症狀分類的問題解決方案
  - 包含所有歷史案例分析

## ⚠️ 注意事項

- 這些文檔保留作為歷史參考
- **請使用新的綜合指南**進行日常開發
- 如需查詢特定歷史案例，可參考原始文檔

## 🔗 相關資源

- [Mock 策略指南](../../issues/service-module-refactor/MOCK_STRATEGY_GUIDE.md)
- [測試資料要求](../../issues/service-module-refactor/TEST_DATA_REQUIREMENTS.md)
- [CLAUDE.md 測試規則章節](../../../../CLAUDE.md#🧪-測試設計核心規則)

---

**維護說明**: 這些文檔已歸檔，不再更新。請更新綜合測試設計指南。