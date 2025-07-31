# TDD 測試開發指令

這個指令會啟動 test-writer-fixer agent，使用 Serena tools 智能地協助你進行 TDD 開發。
支援**新功能開發**和**現有功能補充測試**兩種場景。

## 使用方式

在對話中輸入：
```
/tdd-new-feature
```

## 執行流程

### 階段 1：需求收集與分析
Agent 會先了解你的測試需求：
- 是新功能開發還是現有功能補充測試？
- 功能/端點名稱是什麼？
- 測試的目的（新功能驗證？補充覆蓋？bug 修復？效能測試？）
- 業務需求和預期行為
- 特殊的測試考量（效能、安全、邊界情況）

### 階段 2：針對性研究
基於你的需求，agent 會進行分層研究：

#### 必看文檔（所有情況都要看）
- `test/TEST_STRATEGY.md` - 理解測試策略和優先級
- `test/TEST_MATRIX.md` - 掌握現有測試覆蓋狀況
- `docs/API_REFERENCE.md` - 了解 API 規格和標準
- `docs/ARCHITECTURE.md` - 理解系統架構設計
- `docs/DEPLOYMENT.md` - 掌握部署和環境配置

#### 針對性研究
- **功能文檔**：查看 `docs/features/` 下相關功能的詳細文檔
  - 如：測試關鍵字提取就看 `keyword_extraction.md`
- **現有程式碼**：使用 Serena 工具精確定位相關模組
  - 如果是現有功能：分析現有實作和測試
  - 如果是新功能：研究類似功能的實作模式
- **測試範例**：參考現有測試的寫法和模式
  - 單元測試：`test/unit/`
  - 整合測試：`test/integration/`

### 階段 3：確認理解
Agent 會向你報告：
- 對需求的理解總結
- 建議的測試範圍和類型
- 測試優先級評估
- 預計的工作內容
**等待你確認後才繼續**

### 階段 4：產生測試規格草稿
確認後，agent 會：
1. 設計測試案例（單元/整合/效能/安全）
2. 分配測試編號（遵循專案規範）
3. 評估優先級（P0/P1/P2）
4. 產生草稿檔案：
   - `test/docs/draft/TEST_SPEC_[功能名稱]_draft.md`
   - `test/docs/draft/TEST_MATRIX_[功能名稱]_draft.md`
   - `test/docs/draft/test_cases_[功能名稱]_summary.md`

### 階段 5：審查與修改
Agent 會：
1. 展示草稿檔案路徑
2. 等待你 review 並提供反饋
3. 根據反饋修改草稿
4. 確認最終版本

### 階段 6：實作測試程式碼
最終確認後，agent 會：
1. 建立或更新測試檔案
2. 撰寫相應層級的測試
3. 設定測試資料和 fixtures
4. 確保測試遵循 TDD 原則（紅燈優先）

## Agent 指令

當 test-writer-fixer agent 啟動時，請告訴它：

```
請使用 Serena MCP tools（而非 Claude 內建工具）協助我進行 TDD 測試開發：

重要：優先使用 Serena 工具，而非 Claude 內建工具：
- 讀取檔案：使用 Serena 的 read_file（不要用 Read）
- 搜尋內容：使用 Serena 的 search_for_pattern（不要用 Grep）
- 找檔案：使用 Serena 的 find_file（不要用 Glob）
- 編輯程式碼：使用 Serena 的符號編輯工具（不要用 Edit/MultiEdit）

1. 先收集我的測試需求：
   - 詢問是新功能還是現有功能補充測試
   - 了解要測試的功能/端點名稱
   - 確認測試目的和重點
   - 了解特殊需求（效能、安全、邊界情況等）

2. 基於需求進行針對性研究：
   - 必看文檔：
     • test/TEST_STRATEGY.md - 測試策略
     • test/TEST_MATRIX.md - 測試覆蓋
     • docs/API_REFERENCE.md - API 規格
     • docs/ARCHITECTURE.md - 系統架構
     • docs/DEPLOYMENT.md - 部署配置
   - 針對性研究：
     • 使用 read_file 讀取 docs/features/ 下的相關功能文檔
     • 使用 find_symbol 和 get_symbols_overview 精確定位相關程式碼
     • 使用 search_for_pattern 搜尋測試範例
     • 使用 find_referencing_symbols 了解程式碼關聯

3. 向我確認理解：
   - 總結你對需求的理解
   - 說明建議的測試方案
   - 列出預計的工作項目
   - 等待我的確認再繼續

4. 產生測試規格草稿：
   - 設計適當的測試案例
   - 產生 TEST_SPEC 更新草稿到 test/docs/draft/
   - 產生 TEST_MATRIX 更新草稿到 test/docs/draft/
   - 提供草稿檔案路徑讓我 review

5. 根據我的反饋修改後：
   - 實作測試程式碼
   - 確保遵循 TDD 原則（紅燈優先）
   - 使用專案的測試最佳實踐

請開始收集需求。
```

## 預期效果

- **效率優先**：只研究相關部分，不浪費時間
- **雙向確認**：確保理解正確後才執行
- **靈活支援**：支援新功能和現有功能測試
- **品質保證**：基於專案標準產生高品質測試

## 範例對話

### 範例 1：現有功能補充測試
```
User: /tdd-new-feature

Agent: 我會使用 Serena tools 協助你進行 TDD 測試開發。
請問你是要為新功能開發測試，還是為現有功能補充測試？

User: 現有的 keyword extraction 功能，我想補充一些邊界測試

Agent: 了解，你想為 keyword extraction 補充邊界測試。讓我問幾個問題：
1. 目前你發現哪些邊界情況需要測試？
2. 是否有特定的 bug 或問題促使這次補充？
3. 需要測試哪些極端情況？（如超長輸入、特殊字符等）

User: 主要是想測試多語言混合的情況，還有輸入超過 10000 字的情況

Agent: 我現在會針對性地研究 keyword extraction 相關的程式碼和現有測試...

[Agent 使用 Serena tools 精確研究]

Agent: 我已經分析完成，這是我的理解：
- 現有測試涵蓋了基本功能和中英文單語言情況
- 缺少多語言混合（如中英日混合）的測試
- 目前最長測試案例只有 6000 字符
- 建議新增 4 個測試案例，優先級 P1

要繼續產生測試規格草稿嗎？

User: 好的，請繼續
```

### 範例 2：新功能開發
```
User: /tdd-new-feature

Agent: 我會使用 Serena tools 協助你進行 TDD 測試開發。
請問你是要為新功能開發測試，還是為現有功能補充測試？

User: 新功能，要開發履歷技能差距分析的 API

Agent: 了解，這是一個新功能開發。請告訴我：
1. API 端點路徑規劃是什麼？
2. 主要的輸入會是什麼？（履歷資料？職缺需求？）
3. 預期輸出什麼樣的分析結果？
4. 有特殊的效能要求嗎？（如回應時間限制）

[收集需求後...]

Agent: 基於你的需求，我會研究相關的現有模組...
[針對性研究]

Agent: 這是我對需求的理解總結：
- 端點：POST /api/v1/skill-gap-analysis
- 輸入：履歷技能列表 + 職缺需求技能
- 輸出：技能差距報告，包含缺失技能和建議
- 效能：< 3 秒回應時間
- 建議測試類型：單元測試(8個)、整合測試(3個)、效能測試(1個)

確認無誤嗎？
```