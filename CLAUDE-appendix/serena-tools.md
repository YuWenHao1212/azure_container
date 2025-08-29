# Serena MCP 工具完整參考

## Serena 工具詳細對照表

### 檔案操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 讀取檔案 | Read | `read_file` |
| 建立檔案 | Write | `create_text_file` |
| 列出目錄 | LS | `list_dir` |
| 找檔案 | Glob | `find_file` |

### 搜尋操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 搜尋內容 | Grep | `search_for_pattern` |
| 找函數/類別 | Grep + Read | `find_symbol` |
| 找引用 | 手動搜尋 | `find_referencing_symbols` |
| 程式碼概覽 | 多次 Read | `get_symbols_overview` |

### 編輯操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 編輯程式碼 | Edit/MultiEdit | `replace_symbol_body` |
| 插入程式碼 | Edit | `insert_before_symbol`/`insert_after_symbol` |
| 刪除程式碼 | Edit | `delete_lines` |
| 正則替換 | Edit | `replace_regex` |

## Serena 工具完整列表

### 📁 檔案操作
- `create_text_file` - 創建/覆寫檔案
- `read_file` - 讀取專案內的檔案
- `list_dir` - 列出目錄內容（支援遞迴）
- `find_file` - 在相對路徑中查找檔案

### 🔍 程式碼搜尋與分析
- `find_symbol` - 全域或局部搜尋符號（函數、類別等）
- `find_referencing_symbols` - 查找引用特定符號的位置
- `get_symbols_overview` - 獲取檔案或目錄的頂層符號概覽
- `search_for_pattern` - 在專案中搜尋模式

### ✏️ 程式碼編輯
- `insert_at_line` - 在特定行插入內容
- `insert_before_symbol` - 在符號定義前插入內容
- `insert_after_symbol` - 在符號定義後插入內容
- `replace_lines` - 替換行範圍內的內容
- `replace_symbol_body` - 替換符號的完整定義
- `replace_regex` - 使用正則表達式替換內容
- `delete_lines` - 刪除行範圍

### 🧠 記憶管理
- `write_memory` - 寫入命名記憶體（重要決策、設計理由）
- `read_memory` - 讀取記憶體
- `list_memories` - 列出所有記憶體
- `delete_memory` - 刪除記憶體

### 🛠️ 專案管理
- `onboarding` - 執行專案導入（識別結構、測試、建置）
- `initial_instructions` - 獲取專案初始指令
- `prepare_for_new_conversation` - 準備新對話的指令
- `summarize_changes` - 總結程式碼變更

### 🤔 思考工具
- `think_about_collected_information` - 思考收集資訊的完整性
- `think_about_task_adherence` - 思考是否偏離任務
- `think_about_whether_you_are_done` - 思考任務是否完成

### 🔧 其他工具
- `execute_shell_command` - 執行 shell 命令（當 Bash 不適用時）
- `restart_language_server` - 重啟語言伺服器
- `get_current_config` - 獲取當前配置