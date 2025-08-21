# Resume Tailoring V3 重構專案

**版本**: 1.0.0  
**建立日期**: 2025-01-20  
**專案狀態**: 🔵 規劃階段  
**維護者**: AI Resume Advisor Team

## 📋 專案概述

本專案旨在重構 `/api/v1/tailor-resume` API，從 V2.1.0 升級到 V3.0.0，主要改進包括：

1. **架構簡化**: 移除冗餘的 Instruction Compiler
2. **標記系統重構**: 實作五種精確的 HTML 標記
3. **Gap 類型感知**: 充分利用 Gap Analysis 的智慧分類

## 🎯 核心改進

### 移除 Instruction Compiler
- 節省 ~300ms 延遲
- 減少 GPT-4.1 mini API 成本
- 簡化架構複雜度

### 新 HTML 標記系統（5種）
| 標記 | CSS Class | 用途 |
|------|-----------|------|
| Gap 優化 | `opt-gap` | 基於 Key Gap 的改進 |
| 改進優化 | `opt-improvement` | Quick Improvement 實施 |
| 既有關鍵字 | `opt-keyword-existing` | 標記原有關鍵字 |
| 新增關鍵字 | `opt-keyword-new` | 標記新加入關鍵字 |
| 佔位符 | `opt-placeholder` | 需用戶填寫的數值 |

### Gap 類型處理
- 🔧 **SKILL Gaps**: 技術技能（1-3個月）
- 📚 **FIELD Gaps**: 領域知識（3-6個月）
- 💼 **SOFT Skills**: 軟技能

## 📂 文檔結構

```
tailor-resume-refactor-v3/
├── README.md                           # 本文件
├── MASTER_PLAN.md                      # 完整重構規劃
├── phase1/                             # Phase 1：架構簡化
│   ├── ARCHITECTURE_SIMPLIFICATION.md  # 架構簡化詳解
│   ├── HTML_MARKING_SYSTEM.md         # 標記系統規格
│   ├── GAP_TYPE_HANDLING.md           # Gap 類型策略
│   └── IMPLEMENTATION_CHECKLIST.md    # 實作檢查清單
└── phase2/                             # Phase 2：並行優化
    └── PARALLEL_PROCESSING_DRAFT.md   # 並行處理草案
```

## 🚀 實施階段

### Phase 1: 架構簡化與標記重構（本週）
- **目標**: 簡化架構，實作新標記系統
- **預計時程**: 4-5 天
- **優先級**: 高
- **狀態**: 規劃中

### Phase 2: 並行處理優化（待評估）
- **目標**: 提升效能（如需要）
- **預計時程**: 3-5 天
- **優先級**: 中
- **狀態**: 草案

## 📊 預期成效

| 指標 | 現況 (V2.1.0) | 目標 (V3.0.0) | 改善 |
|------|---------------|---------------|------|
| 回應時間 | ~4.5秒 | <3.5秒 | -22% |
| LLM 調用 | 2次 | 1次 | -50% |
| API 成本 | $0.15 | $0.12 | -20% |
| 標記精確度 | 中 | 高 | +40% |

## 🔗 相關資源

### 現有文檔
- [V2.1.0 實作分析](../tailor-resume-refactor/API_ANALYSIS_20250811.md)
- [Gap Analysis V2.1.8](../index-cal-gap-analysis-evolution/features/GAP_ANALYSIS_V218.md)
- [當前 Prompt](../../../src/prompts/resume_tailoring/v2.1.0-simplified.yaml)

### 程式碼位置
- **服務實作**: `src/services/resume_tailoring.py`
- **API 端點**: `src/api/v1/resume_tailoring.py`
- **測試檔案**: `test/integration/test_resume_tailoring_api.py`

## 📝 快速導航

1. **了解全貌**: 閱讀 [MASTER_PLAN.md](./MASTER_PLAN.md)
2. **Phase 1 細節**: 查看 [phase1/](./phase1/) 目錄
3. **實作步驟**: 參考 [IMPLEMENTATION_CHECKLIST.md](./phase1/IMPLEMENTATION_CHECKLIST.md)
4. **標記規格**: 詳見 [HTML_MARKING_SYSTEM.md](./phase1/HTML_MARKING_SYSTEM.md)

## 🚨 重要提醒

1. **LLM Factory 使用**: 所有 LLM 調用必須通過 `get_llm_client()`
2. **測試資料長度**: Resume 和 JD 必須 ≥ 200 字元
3. **Ruff 檢查**: 所有程式碼必須通過 `ruff check --line-length=120`

## 📞 聯絡資訊

- **專案負責人**: WenHao
- **技術支援**: Claude Code
- **問題回報**: GitHub Issues

---

**最後更新**: 2025-01-20  
**下次評審**: 2025-01-24（Phase 1 完成後）