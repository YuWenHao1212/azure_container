# Azure Container API - Claude Code 協作指南

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
- **AI 模型**: GPT-4.1 mini + GPT-4o-2
- **資料庫**: PostgreSQL + pgvector (課程搜尋)

## 已部署環境

### 生產環境
- **URL**: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:20250730-100726-3530cfd`
- **資源**: 1 CPU, 2GB RAM, 4GB 暫存空間

### 開發環境  
- **URL**: https://airesumeadvisor-api-dev.calmisland-ea7fe91e.japaneast.azurecontainerapps.io
- **鏡像**: `airesumeadvisorregistry.azurecr.io/airesumeadvisor-api:dev-secure`

## 環境配置

### 生產環境變數
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
MONITORING_ENABLED=false
LIGHTWEIGHT_MONITORING=true

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# GPT-4.1 Mini Japan East (高效能)
GPT41_MINI_JAPANEAST_ENDPOINT=https://airesumeadvisor.openai.azure.com/
GPT41_MINI_JAPANEAST_DEPLOYMENT=gpt-4-1-mini-japaneast
GPT41_MINI_JAPANEAST_API_VERSION=2025-01-01-preview

# Embedding Service
LLM2_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com
EMBEDDING_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15

# Model Selection
LLM_MODEL_KEYWORDS=gpt41-mini  # 高效能關鍵字提取

# Security (stored as secrets)
AZURE_OPENAI_API_KEY=<secret>
EMBEDDING_API_KEY=<secret>
GPT41_MINI_JAPANEAST_API_KEY=<secret>
JWT_SECRET_KEY=<secret>
CONTAINER_APP_API_KEY=<secret>

# CORS
CORS_ORIGINS=https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com
```

## Serena MCP 整合

### 🚀 Serena MCP 啟動指南

#### 常見啟動錯誤
```
ERROR - Error activating project '.serena/project.yml' at startup: 
Project '.serena/project.yml' not found: Not a valid project name or directory.
```
**原因**：Serena 嘗試將配置檔案路徑當作專案名稱

#### ✅ 正確啟動步驟

**每次新對話或 compact 操作後，請依序執行：**

1. **啟動專案**（最關鍵步驟）
   ```python
   # 使用專案名稱（推薦）
   mcp__serena__activate_project("azure_container")
   # 或使用當前目錄
   mcp__serena__activate_project(".")
   ```

2. **載入初始指令**
   ```python
   mcp__serena__initial_instructions()
   ```

3. **檢查 Onboarding 狀態**（選擇性）
   ```python
   mcp__serena__check_onboarding_performed()
   # 如果顯示 "Onboarding not performed yet"，執行：
   mcp__serena__onboarding()
   ```

#### ⚠️ 重要提醒
- **永遠先啟動專案**：其他所有 Serena 工具都需要先有活躍的專案
- **使用專案名稱**：不要使用 `.serena/project.yml` 路徑
- **每次新對話都要重新啟動**：Serena 狀態不會跨對話保存

### Serena 配置狀態
- ✅ MCP 伺服器已添加並連接
- ✅ 上下文模式：`ide-assistant`
- ✅ 專案路徑：`/Users/yuwenhao/Documents/GitHub/azure_container`
- ✅ 工具：語義檢索、符號編輯、智能程式碼分析

### Serena 核心功能
- 🔍 **智能程式碼閱讀**：避免讀取不必要的檔案，使用符號工具精確定位
- ⚡ **高效編輯**：符號編輯 + 正則表達式編輯雙重模式
- 🧠 **語義理解**：理解程式碼符號間的關係和引用
- 📝 **記憶管理**：整合專案記憶和開發決策記錄

### Serena 工具優先原則
**🚨 重要：優先使用 Serena MCP 工具，而非 Claude 內建工具**

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