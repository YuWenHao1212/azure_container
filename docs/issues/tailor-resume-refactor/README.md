# Resume Tailoring v2.0.0 重構專案

## 📋 專案概述

本專案透過**三階段架構**重構 Resume Tailoring API，將原本單一複雜的 LLM 任務拆分為三個專注的組件，大幅提升品質與效能。

## 🏗️ 核心架構改變

### 現有架構（v1.1.0）問題
- 單一 589 行的巨大 prompt，LLM 需同時處理分析、決策和寫作
- 認知負荷過重，導致輸出不穩定
- Token 使用量大（~8000），回應緩慢
- 難以維護和調試

### 新架構（v2.0.0）：三階段管線
```
Gap Analysis → Instruction Compiler → Resume Writer
    (分析)          (指令生成)           (內容寫作)
```

1. **Gap Analysis（增強版）**：深度分析並標記 gap 類型
2. **Instruction Compiler（新增）**：GPT-4.1 mini 將分析轉換為精確指令
3. **Resume Writer（簡化版）**：專注高品質內容生成

## 📊 效能目標與預期成效

| 指標 | v1.1.0 (現況) | v2.0.0 (目標) | 改善幅度 |
|------|--------------|---------------|----------|
| 架構複雜度 | 單一複雜 LLM | 三階段分工 | 職責分離 |
| Prompt 大小 | 589 行 | 150-200 行 | -70% |
| Token 使用 | ~8000 | ~3000 | -62% |
| P50 回應時間 | 5-6s | < 4s | -33% |
| P95 回應時間 | 8-10s | < 6s | -40% |
| 維護難度 | 高 | 低 | ⬇️⬇️ |

## 🚀 實作階段

### 階段 1：增強 Gap Analysis 輸出（第 1 天）
- 在 KeyGaps 中加入 `[Skill Gap]` 或 `[Presentation Gap]` 標記
- 最小變更，保持向後相容
- 必須通過完整測試

### 階段 2：建立 Instruction Compiler（第 2-3 天）
- 新增 GPT-4.1 mini 服務
- 解析 gap 分類，生成結構化指令
- 成本極低（~$0.0008），延遲短（~300ms）

### 階段 3：簡化主 Prompt（第 4 天）
- 從 589 行簡化至 150-200 行
- 保留 Chain of Thought 和 Few-shot examples
- 專注執行品質

### 階段 4：整合測試（第 5-6 天）
- 端到端測試
- 效能驗證
- 品質評估

## 📁 專案結構

### 文檔
- [實作計畫](./implementation-plan.md) - 詳細技術方案
- [測試與部署](./testing-and-deployment.md) - 測試策略與部署流程

### 核心檔案
```
src/
├── services/
│   ├── resume_tailoring.py      # 主服務（改造）
│   ├── instruction_compiler.py  # 新增：GPT-4.1 mini 編譯器
│   └── gap_analysis_v2.py       # Gap Analysis（調整輸出）
├── prompts/
│   ├── gap_analysis/
│   │   └── v2.1.0.yaml          # 增強版（加入分類標記）
│   └── resume_tailoring/
│       ├── v1.1.0.yaml          # 現有版本
│       └── v2.0.0-en.yaml       # 新版本（簡化）
└── models/
    └── api/
        └── resume_tailoring.py  # API 模型（新增欄位）
```

## 🔄 API 變更

### Gap Analysis API 增強
```html
<!-- 新的 KeyGaps 格式（加入分類標記） -->
<ul>
  <li><strong>[Skill Gap]</strong> Kubernetes orchestration - No experience, need 4-6 weeks learning</li>
  <li><strong>[Presentation Gap]</strong> Machine Learning - Has experience but not mentioned explicitly</li>
</ul>
```

### Resume Tailoring API 變更
```json
// 新增必填欄位（請求）
{
  "original_similarity": 75,          // 從 Gap Analysis 取得
  "original_coverage_percentage": 60, // 從 Gap Analysis 取得
  "gap_analysis": { ... }             // 現有欄位
}
```

## 📈 成功標準

### 必須達成
- ✅ 每階段通過 `python test/scripts/pre_commit_check_advanced.py`（137 個測試）
- ✅ P50 < 4s, P95 < 6s
- ✅ Token 使用減少 50% 以上
- ✅ Ruff 檢查無錯誤

### 加分項目
- 品質分數提升 10% 以上
- P50 < 3.5s
- 使用者滿意度提升

## 🚦 部署策略

- **無需向後相容**（沒有 live users）
- 直接替換 v1.1.0
- 簡化部署流程，無需 fallback 機制

## 📝 注意事項

### 技術決策
1. 使用 GPT-4.1 mini 做預處理（快速、便宜、準確）
2. 保留 prompt engineering 最佳實踐（COT、few-shot）
3. 職責分離：分析、指令、寫作各司其職

### 風險管理
- 每階段都有完整測試覆蓋
- 逐步實作，降低整合風險
- 保留詳細日誌以便調試

## 👥 團隊與時程

- **負責人**: Claude Code + WenHao
- **開始日期**: 2025-01-16
- **預計完成**: 2025-01-22（6 個工作天）
- **版本**: v2.0.0

---

**最後更新**: 2025-01-16  
**狀態**: 🚧 開發中