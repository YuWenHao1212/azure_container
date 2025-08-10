# Resume Tailoring v2.0.0 測試規格修正總結

## 修正日期
2025-08-10

## 主要修正項目

### 1. 架構誤解修正（最重要）
**問題**: 原文檔描述為三階段架構
**修正**: 
- Resume Tailoring 只有**兩階段**：
  1. Stage 1: Instruction Compiler (GPT-4.1 mini)
  2. Stage 2: Resume Writer (GPT-4)
- Gap Analysis 是**獨立的 API 端點**，其結果作為 API 參數傳入，不是內部調用

### 2. 錯誤碼規範
**問題**: 使用 400 錯誤碼處理驗證錯誤
**修正**: 根據 `FASTAPI_ERROR_CODES_STANDARD.md`：
- 驗證錯誤使用 **422** (Unprocessable Entity)
- 外部服務錯誤使用 **502** (Bad Gateway)
- 使用標準錯誤碼如 `VALIDATION_TOO_SHORT`、`EXTERNAL_SERVICE_ERROR`

### 3. InstructionCompiler 格式說明
**新增內容**：完整的 JSON 輸出格式，包含：
- summary: 摘要優化策略
- skills: 技能添加和重組
- experience: 經驗優化指令
- education: 教育背景調整
- optimization_strategy: 整體優化策略

### 4. Fallback 機制詳述
**新增說明**：
- 當 GPT-4.1 mini 返回無效 JSON 時的處理
- 程式化生成基本指令的邏輯
- 關鍵字優先級處理（使用前 5-10 個 missing_keywords）

### 5. 效能測試優化
**修正**：
- 合併 P50 和 P95 測試為單一測試（20 個請求）
- 移除不必要的 Token 優化測試（物理現象）
- 移除架構效益測試（無實際測試價值）
- 測試數量從 21 個減至 18 個

### 6. API 請求格式修正
**重要變更**：
```yaml
# 正確格式
request:
  original_resume: "HTML content..."
  job_description: "JD content..."
  gap_analysis:  # 必須包含，從 Gap Analysis API 獲得
    core_strengths: [...]
    key_gaps: [...]
    quick_improvements: [...]
    covered_keywords: [...]
    missing_keywords: [...]
  options:
    language: "en"
```

## 關鍵理解點

1. **Gap Analysis 不是 Resume Tailoring 的一部分**
   - 是獨立的 API 端點 `/api/v1/index-cal-and-gap-analysis`
   - 結果必須由客戶端傳入 Resume Tailoring API

2. **時間追蹤只記錄兩個階段**
   - instruction_compilation_ms
   - resume_writing_ms
   - 不記錄 gap_analysis_ms（因為不是內部調用）

3. **必要欄位完整性**
   - 所有指令欄位都有明確定義
   - _validate_instructions 方法確保欄位完整

## 後續建議

1. **更新實作程式碼**：移除 ResumeTailoringService 中的 Gap Analysis 內部調用
2. **更新 API 文檔**：確保 API_REFERENCE.md 清楚說明參數結構
3. **實作測試案例**：根據修正後的規格實作所有 18 個測試

## 文檔版本歷史
- v1.0.0: 初始版本（有架構誤解）
- v1.0.1: 修正版本（正確的兩階段架構）