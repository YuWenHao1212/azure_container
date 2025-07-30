---
description: 快速記錄當前對話重點到 Obsidian
allowed-tools: Read, Write, Bash
---

# /take-note 指令

## 概述
`/take-note` 指令能自動擷取並儲存 Claude Code 對話中的重要內容到你的 Obsidian 知識庫。

## 語法
```
/take-note
```

## 功能說明
執行此指令時，系統會：

1. **取得台灣時區時間**
   - 使用工具獲取 Asia/Taipei 時區的當前時間
   - 時間格式精確到分鐘（YYYY-MM-DD HH:mm）

2. **擷取當前對話內容**
   - 討論的核心概念
   - 解決方案和程式碼片段
   - 關鍵決策和理由
   - 學到的新知識

3. **生成結構化筆記**
   ```markdown
   # [主題] - YYYY-MM-DD HH:mm
   
   ## 📍 Context
   - Project: [當前專案名稱]
   - Topic: [討論主題]
   
   ## 🎯 Key Points
   [重點整理]
   
   ## 💡 Solutions/Code
   [解決方案或程式碼]
   
   ## 📚 Learnings
   [學到的知識]
   
   ## 🔗 References
   [相關連結或檔案]
   ```

4. **儲存至 Obsidian**
   - **位置**：`/Users/yuwenhao/Library/Mobile Documents/iCloud~md~obsidian/Documents/Root/WenHao/Inbox/Qiuck Note/`
   - **檔名**：`YYYY-MM-DD-HH-mm-[主題簡述].md`
   - **格式**：Markdown 並支援 Obsidian 的 [[wikilinks]]

## 使用範例

### 範例 1：解決 bug 後
```
User: /take-note
Assistant: 我已擷取我們的除錯過程並儲存為 "2024-01-15-14-30-fix-async-error-handling.md"
```

### 範例 2：學習新概念
```
User: /take-note
Assistant: 我已將關於 React hooks 優化的討論儲存為 "2024-01-15-15-45-react-hooks-performance.md"
```

## 實作細節

### 時間處理
```bash
# 取得台灣時區時間（Asia/Taipei）
TW_TIME=$(TZ='Asia/Taipei' date +"%Y-%m-%d-%H-%M")
# 格式：YYYY-MM-DD-HH-mm（精確到分鐘）
```

### 檔案路徑建構
```bash
OBSIDIAN_PATH="/Users/yuwenhao/Library/Mobile Documents/iCloud~md~obsidian/Documents/Root/WenHao"
QUICK_NOTE_PATH="$OBSIDIAN_PATH/Inbox/Qiuck Note"
TIMESTAMP=$TW_TIME  # 使用台灣時間
FILENAME="$TIMESTAMP-$TOPIC_SUMMARY.md"
```

### 內容擷取邏輯
1. 使用工具取得台灣時區的當前時間
2. 分析對話中最近的 10-20 則訊息
3. 識別主要主題和子主題
4. 擷取程式碼區塊和重要指令
5. 總結關鍵決策和學習內容
6. 使用預定義模板格式化並加入台灣時間戳記

## 設定配置

### 必要設定
- Obsidian vault 必須位於指定路徑
- "Qiuck Note" 資料夾必須存在（注意拼寫）
- Claude Code 需要寫入權限

### 選用自訂
- 在 CLAUDE.local.md 中修改模板結構
- 添加自訂標籤或 metadata
- 更改檔案命名規則

## 錯誤處理

### 常見問題
1. **找不到路徑**：確認 Obsidian vault 存在於指定位置
2. **權限被拒**：檢查 Quick Note 資料夾的寫入權限
3. **iCloud 同步問題**：等待同步完成後再存取筆記

### 失敗時的備援行為
如果指令執行失敗：
1. 在對話中顯示格式化的筆記內容
2. 提供手動儲存的說明
3. 記錄錯誤詳情供疑難排解

## 與每日筆記整合

此指令與自動化每日筆記系統完美配合：
- 使用 `/take note` 建立的快速筆記會在晚上 8:00 自動處理
- 原始筆記整合後會移至 `legacy/YYYY/MM/` 歸檔
- 內容會永久保存在每日筆記中

## 最佳實踐

1. **使用描述性主題**：主題會成為檔名的一部分
2. **立即擷取**：趁記憶猶新時執行指令
3. **檢視每日筆記**：查看你的快速筆記如何被整合
4. **適當使用標籤**：使用 Obsidian 標籤以便更好地組織
5. **時區一致性**：所有筆記都使用台灣時間（UTC+8）確保時間記錄的一致性

## 相關指令
- `/organize-notes`：手動觸發每日筆記整理
- `分析本週筆記`：生成週總結
- `提取關鍵概念`：從筆記中提取概念