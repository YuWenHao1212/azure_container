# Azure Container API - Claude Code 協作指南

## 🚨 對話啟動必做事項

**每次新對話或 compact 後，立即執行：**
1. 初始化 Serena：使用 `mcp__serena__activate_project("azure_container")`
2. 如果初始化失敗，改用 `mcp__serena__activate_project(".")`

**Serena 工具速查**：
- 檔案：`read_file` > Read、`create_text_file` > Write、`list_dir` > LS、`find_file` > Glob
- 搜尋：`find_symbol` > Grep、`search_for_pattern` > 搜尋內容、`find_referencing_symbols` > 找引用
- 編輯：`replace_symbol_body` > Edit、`insert_before/after_symbol` > 插入、`replace_regex` > 正則替換
- 記得：優先用 Serena MCP 工具，除非任務明確需要 Claude 內建工具

---

> 基於原有 azure_fastapi 專案，從容器中還原並針對 Container Apps 最佳化

## 專案概述

本專案是從已部署的生產容器 `airesumeadvisor-api-production` (鏡像：`20250730-100726-3530cfd`) 中還原的完整 AI 履歷優化平台。

### 核心功能
- 🔍 **關鍵字提取** - 從職缺描述提取技能關鍵字
- 📊 **匹配指數計算** - 評估履歷與職缺的匹配度  
- 📈 **差距分析** - 找出技能缺口並提供改進建議
- 📄 **履歷格式化** - OCR 文字轉結構化 HTML
- ✍️ **履歷客製化** - AI 智能改寫履歷內容
- 🎓 **課程推薦** - 向量搜尋相關學習資源

### 技術架構
- **框架**: FastAPI (原生運行，無 ASGI 適配層)
- **架構模式**: FHS (Functional Hierarchy Structure)
- **部署平台**: Azure Container Apps (Japan East)
- **AI 模型**: GPT-4.1 (主要) + GPT-4.1 mini (關鍵字提取)
- **資料庫**: PostgreSQL + pgvector (課程搜尋)

## 已部署環境

### 生產環境 (目前開發中使用)
- **URL**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:20250730-100726-3530cfd`
- **資源**: 1 CPU, 2GB RAM, 4GB 暫存空間
- **狀態**: ✅ 活躍使用中 - 所有開發測試都在此環境進行

### 開發環境 (未來規劃)
- **URL**: https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:dev-secure`
- **狀態**: ⏸️ 暫未使用 - 預留給未來測試需求

## 環境配置

### 生產環境變數
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
MONITORING_ENABLED=false
LIGHTWEIGHT_MONITORING=true

# Azure OpenAI - Japan East Region (統一配置)
# 所有模型都部署在 Japan East，使用共同的 API Key
AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com
AZURE_OPENAI_API_KEY=<secret>  # 共用的 API Key
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Model Deployments (都在 Japan East)
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan              # 主要 GPT-4.1 模型
GPT41_MINI_JAPANEAST_DEPLOYMENT=gpt-4-1-mini-japaneast  # 高效能 GPT-4.1 Mini

# GPT-4.1 Mini 配置 (使用相同的 endpoint 和 key)
GPT41_MINI_JAPANEAST_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
GPT41_MINI_JAPANEAST_API_KEY=${AZURE_OPENAI_API_KEY}
GPT41_MINI_JAPANEAST_API_VERSION=${AZURE_OPENAI_API_VERSION}

# Embedding Services (都在 Japan East，共用 API Key)
EMBEDDING_ENDPOINT=https://airesumeadvisor.openai.azure.com/openai/deployments/embedding-3-large-japan/embeddings?api-version=2023-05-15
EMBEDDING_API_KEY=${AZURE_OPENAI_API_KEY}

# Course Embedding (課程搜尋專用)
COURSE_EMBEDDING_ENDPOINT=https://airesumeadvisor.openai.azure.com/openai/deployments/embedding-3-small-japan/embeddings?api-version=2023-05-15
COURSE_EMBEDDING_API_KEY=${AZURE_OPENAI_API_KEY}

# Model Selection
LLM_MODEL_KEYWORDS=gpt41-mini     # 快速關鍵字提取
LLM_MODEL_GAP_ANALYSIS=gpt4o-2    # 詳細分析
LLM_MODEL_RESUME_FORMAT=gpt4o-2   # 高品質格式化
LLM_MODEL_RESUME_TAILOR=gpt4o-2   # 履歷客製化

# Security
JWT_SECRET_KEY=<secret>
CONTAINER_APP_API_KEY=<secret>

# CORS
CORS_ORIGINS=https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com
```

## 快速開始

### 本地開發
```bash
# 1. 複製環境變數
cp .env.example .env
# 編輯 .env 填入實際的 API keys

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 啟動應用程式
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 部署
```bash
# 1. 建立鏡像
docker build -t azure-container-api .

# 2. 運行容器
docker run -p 8000:8000 --env-file .env azure-container-api
```

### Azure Container Registry
```bash
# 1. 登入 ACR
az acr login --name airesumeadvisorregistry

# 2. 標記並推送
docker tag azure-container-api airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest
docker push airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:latest
```

## API 端點

### 健康檢查
- `GET /health` - 健康狀態
- `GET /` - API 資訊
- `GET /docs` - Swagger 文檔

### 核心功能
- `POST /api/v1/extract-jd-keywords` - 關鍵字提取
- `POST /api/v1/index-calculation` - 匹配指數計算
- `POST /api/v1/index-cal-and-gap-analysis` - 指數計算與差距分析
- `POST /api/v1/format-resume` - 履歷格式化
- `POST /api/v1/tailor-resume` - 履歷客製化
- `POST /api/v1/courses/search` - 課程搜尋

### 認證
Container Apps 支援兩種認證方式：
- **Header**: `X-API-Key: your-api-key` (推薦)
- **Query Parameter**: `?code=your-api-key` (Function Apps 相容)

## 效能優化

### Container Apps vs Functions 比較
| 指標 | Functions | Container Apps | 改善 |
|------|-----------|----------------|------|
| 總回應時間 | 6.0s | 2.8s | -53% |
| 架構開銷 | 3.2s | 0s | -100% |
| 冷啟動時間 | 2-3s | 0.1-0.5s | -80% |
| 並發能力 | < 0.5 QPS | 20-50 QPS | 40-100x |

### 優化策略
- **模型選擇**: 關鍵字提取使用 GPT-4.1 mini (更快)
- **輕量監控**: 預設啟用輕量級監控，生產關閉重度監控
- **資源配置**: 1 CPU + 2GB RAM，自動擴展 2-10 實例

## 開發指南

### 程式碼品質要求 (Ruff)

**重要：撰寫程式碼時必須遵循 Ruff 規範，避免在 commit 時出現錯誤**

#### 主要規則：
1. **行長度限制**: 120 字元 (設定在 pyproject.toml)
2. **Import 排序**: 使用 isort 規則，自動分組和排序
3. **命名規範**: 遵循 PEP8 (類別用 PascalCase，函數用 snake_case)
4. **型別標註**: 使用 Python 3.11+ 語法
5. **例外處理**: 使用 `raise ... from e` 進行異常鏈接

#### 常見錯誤預防：
- **F401**: 不要 import 未使用的模組
- **E501**: 行長度不要超過 120 字元
- **B904**: 重新拋出異常時使用 `from e`
- **RUF012**: 類別的可變屬性使用 `ClassVar` 標註
- **SIM102**: 合併巢狀的 if 條件使用 `and`
- **SIM108**: 使用三元運算符取代簡單的 if-else
- **S110**: try-except-pass 要加上日誌記錄

#### 特殊處理：
- **S311**: `random.random()` 用於非安全性用途時加上 `# noqa: S311`
- **S324**: 使用 MD5 做快取時加上 `# noqa: S324`

#### 執行檢查：
```bash
# 檢查程式碼
ruff check src/ --line-length=120

# 自動修復可修復的問題
ruff check src/ --fix

# 檢查並修復 (包含較不安全的修復)
ruff check src/ --fix --unsafe-fixes
```

### 測試執行
```bash
# 程式碼風格檢查
ruff check src/ --fix

# 單元測試
pytest tests/unit/ -v

# 整合測試  
pytest tests/integration/ -v
```

### 程式碼修改分級測試
- **Level 0**: Prompt 修改 - YAML 格式驗證
- **Level 1**: 程式碼風格 - Ruff 檢查
- **Level 2**: 功能修改 - 單元測試
- **Level 3**: API 修改 - 整合測試

### Git 工作流程
```bash
# 1. 建立功能分支
git checkout -b feature/new-feature

# 2. 開發並測試
# ...執行對應層級測試

# 3. 提交
git commit -m "feat: add new feature"

# 4. 推送
git push origin feature/new-feature
```

## 監控與除錯

### 生產監控
- **Application Insights**: 整合完整遙測
- **健康檢查**: `/health` 端點自動監控
- **錯誤追蹤**: 統一錯誤格式與分類

### 開發除錯端點 (非生產環境)
- `GET /api/v1/monitoring/stats` - 監控統計
- `GET /api/v1/debug/storage-info` - 錯誤儲存資訊  
- `GET /api/v1/debug/errors` - 最近錯誤記錄
- `GET /debug/monitoring` - 監控狀態除錯

## 部署說明

### Azure Resources
- **Subscription**: 5396d388-8261-464e-8ee4-112770674fba
- **Resource Group**: airesumeadvisorfastapi  
- **Container Registry**: airesumeadvisorregistry
- **Container Environment**: Japan East

### 部署流程
1. 建立並測試 Docker 鏡像
2. 推送到 Azure Container Registry
3. 更新 Container Apps 配置
4. 驗證部署與健康檢查
5. 監控效能指標

## 安全最佳實踐

- ✅ 非 root 用戶運行容器
- ✅ 敏感資料使用 Azure 秘密管理
- ✅ CORS 設定限制來源網域
- ✅ API Key 認證保護端點
- ✅ 輸入驗證與清理
- ✅ 錯誤日誌不包含敏感資訊

## 參考資料

- **原始專案**: `/Users/yuwenhao/Documents/GitHub/azure_fastapi/`
- **Container Registry**: https://portal.azure.com/#@wenhaoairesumeadvisor.onmicrosoft.com/resource/subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi/providers/Microsoft.ContainerRegistry/registries/airesumeadvisorregistry
- **Container Apps**: https://portal.azure.com/#@wenhaoairesumeadvisor.onmicrosoft.com/resource/subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi/providers/Microsoft.App/containerApps/

---

**文檔版本**: 1.0.0  
**建立日期**: 2025-07-30  
**基於**: 生產容器 `20250730-100726-3530cfd`  
**維護者**: Claude Code + WenHao

---

## 附錄：Serena MCP 工具完整參考

### Serena 工具詳細對照表

#### 檔案操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 讀取檔案 | Read | `read_file` |
| 建立檔案 | Write | `create_text_file` |
| 列出目錄 | LS | `list_dir` |
| 找檔案 | Glob | `find_file` |

#### 搜尋操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 搜尋內容 | Grep | `search_for_pattern` |
| 找函數/類別 | Grep + Read | `find_symbol` |
| 找引用 | 手動搜尋 | `find_referencing_symbols` |
| 程式碼概覽 | 多次 Read | `get_symbols_overview` |

#### 編輯操作（用 Serena 取代 Claude）
| 任務 | ❌ 不要用 | ✅ 請用 Serena |
|------|-----------|----------------|
| 編輯程式碼 | Edit/MultiEdit | `replace_symbol_body` |
| 插入程式碼 | Edit | `insert_before_symbol`/`insert_after_symbol` |
| 刪除程式碼 | Edit | `delete_lines` |
| 正則替換 | Edit | `replace_regex` |

### Serena 工具完整列表

#### 📁 檔案操作
- `create_text_file` - 創建/覆寫檔案
- `read_file` - 讀取專案內的檔案
- `list_dir` - 列出目錄內容（支援遞迴）
- `find_file` - 在相對路徑中查找檔案

#### 🔍 程式碼搜尋與分析
- `find_symbol` - 全域或局部搜尋符號（函數、類別等）
- `find_referencing_symbols` - 查找引用特定符號的位置
- `get_symbols_overview` - 獲取檔案或目錄的頂層符號概覽
- `search_for_pattern` - 在專案中搜尋模式

#### ✏️ 程式碼編輯
- `insert_at_line` - 在特定行插入內容
- `insert_before_symbol` - 在符號定義前插入內容
- `insert_after_symbol` - 在符號定義後插入內容
- `replace_lines` - 替換行範圍內的內容
- `replace_symbol_body` - 替換符號的完整定義
- `replace_regex` - 使用正則表達式替換內容
- `delete_lines` - 刪除行範圍

#### 🧠 記憶管理
- `write_memory` - 寫入命名記憶體（重要決策、設計理由）
- `read_memory` - 讀取記憶體
- `list_memories` - 列出所有記憶體
- `delete_memory` - 刪除記憶體

#### 🛠️ 專案管理
- `onboarding` - 執行專案導入（識別結構、測試、建置）
- `initial_instructions` - 獲取專案初始指令
- `prepare_for_new_conversation` - 準備新對話的指令
- `summarize_changes` - 總結程式碼變更

#### 🤔 思考工具
- `think_about_collected_information` - 思考收集資訊的完整性
- `think_about_task_adherence` - 思考是否偏離任務
- `think_about_whether_you_are_done` - 思考任務是否完成

#### 🔧 其他工具
- `execute_shell_command` - 執行 shell 命令（當 Bash 不適用時）
- `restart_language_server` - 重啟語言伺服器
- `get_current_config` - 獲取當前配置

### Serena 啟動故障排除

#### 常見錯誤與解決方案

1. **錯誤**: `Project '.serena/project.yml' not found`
   - **原因**: 嘗試使用配置檔案路徑而非專案名稱
   - **解決**: 使用 `mcp__serena__activate_project("azure_container")`

2. **錯誤**: 工具無法使用
   - **原因**: 未先啟動專案
   - **解決**: 確保先執行專案啟動步驟

3. **錯誤**: 狀態遺失
   - **原因**: 新對話或 compact 後狀態重置
   - **解決**: 重新執行啟動步驟