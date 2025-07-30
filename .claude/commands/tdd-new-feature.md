# TDD 新功能開發指令

這個指令會啟動 test-writer-fixer agent，使用 Serena tools 智能地協助你進行 TDD 開發。

## 使用方式

在對話中輸入：
```
/tdd-new-feature
```

## 執行流程

### 階段 1：深入理解專案
test-writer-fixer agent 會使用 Serena tools：
1. 分析測試策略 (`TEST_STRATEGY.md`)
2. 檢查現有測試覆蓋 (`TEST_MATRIX.md`)
3. 理解 API 規格 (`API_REFERENCE.md`)
4. 掌握系統架構 (`ARCHITECTURE.md`)
5. 探索相關程式碼模組

### 階段 2：互動式需求收集
Agent 會詢問你：
- 要開發的功能名稱和端點
- 功能的業務需求
- 預期的輸入/輸出
- 效能需求
- 錯誤處理需求
- 安全性考量

### 階段 3：產生測試規格草稿
基於收集的資訊，agent 會：
1. 設計測試案例（單元/整合/效能/安全）
2. 分配測試編號
3. 評估優先級
4. 產生草稿檔案：
   - `test/docs/draft/TEST_SPEC_[功能名稱]_draft.md`
   - `test/docs/draft/TEST_MATRIX_[功能名稱]_draft.md`
   - `test/docs/draft/test_cases_[功能名稱]_summary.md`

### 階段 4：審查與確認
Agent 會：
1. 將草稿儲存到 `test/docs/draft/` 目錄
2. 展示草稿檔案路徑
3. 等待你 review 並提供反饋
4. 根據反饋修改草稿

### 階段 5：實作測試程式碼
確認後，agent 會：
1. 建立測試檔案結構
2. 撰寫單元測試
3. 撰寫整合測試
4. 撰寫效能測試
5. 設定測試資料和 fixtures

## Agent 指令

當 test-writer-fixer agent 啟動時，請告訴它：

```
請使用 Serena tools 協助我進行 TDD 開發：

1. 先深入理解專案：
   - 閱讀 test/TEST_STRATEGY.md 了解測試策略
   - 閱讀 test/TEST_MATRIX.md 了解現有覆蓋
   - 閱讀 docs/API_REFERENCE.md 了解 API 規格
   - 閱讀 docs/ARCHITECTURE.md 了解系統架構
   - 使用 Serena 的符號工具探索相關程式碼

2. 與我互動收集需求：
   - 詢問功能細節
   - 了解業務需求
   - 確認技術規格

3. 產生測試規格草稿：
   - 設計適當的測試案例
   - 產生 TEST_SPEC 更新草稿到 test/docs/draft/
   - 產生 TEST_MATRIX 更新草稿到 test/docs/draft/
   - 提供草稿檔案路徑讓我 review

4. 得到我的確認後：
   - 實作所有層級的測試程式碼
   - 使用 TDD 最佳實踐
   - 確保測試可執行且會失敗（紅燈）

請開始這個流程。
```

## 預期效果

- **智能理解**：Agent 會真正理解你的專案結構和需求
- **互動設計**：不是單向產生，而是雙向討論
- **品質保證**：基於專案標準產生高品質測試
- **完整覆蓋**：從規格到實作的完整 TDD 流程

## 範例對話

```
User: /tdd-new-feature

Agent: 我會使用 Serena tools 來協助你進行 TDD 開發。讓我先理解專案...

[Agent 讀取文檔和程式碼]

Agent: 我已經了解了專案結構。請告訴我你要開發什麼功能？

User: 我要開發履歷匹配指數計算功能

Agent: 了解。讓我問幾個問題來確保測試設計完整：
1. API 端點路徑是什麼？
2. 需要哪些輸入參數？
3. 預期的回應格式？
4. 有特殊的效能需求嗎？

[持續互動...]

Agent: 基於我們的討論，我設計了以下測試案例並產生了草稿：

📁 已產生的草稿檔案：
- test/docs/draft/TEST_SPEC_index_calculation_draft.md
- test/docs/draft/TEST_MATRIX_index_calculation_draft.md
- test/docs/draft/test_cases_index_calculation_summary.md

請 review 這些草稿檔案，有任何需要調整的地方請告訴我。

User: 看起來不錯，請開始實作

Agent: 好的，我現在開始撰寫測試程式碼...
```