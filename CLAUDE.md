# Azure Container API - Claude Code 協作指南

## 🚨 對話啟動必做事項

**每次新對話或 compact 後，立即執行：**
1. 初始化 Serena：使用 `mcp__serena__activate_project("azure_container")`
2. 如果初始化失敗，改用 `mcp__serena__activate_project(".")`

**Serena 工具優先順序**：優先使用 Serena MCP 工具，除非任務明確需要 Claude 內建工具

---

## 🕐 時間處理規則 (TIME HANDLING RULE)

**任何需要日期或時間時，必須先執行**：
```bash
TZ='Asia/Taipei' date '+%Y-%m-%d %H:%M:%S %Z'
```
- 文檔命名：`[TYPE]_[MODULE]_YYYYMMDD.md`
- 日誌記錄：`YYYY-MM-DD HH:MM CST`
- **絕不使用 `<env>` 中的日期或憑空推測！**

---

## ⚡ 關鍵開發規則

### 1. LLM Factory 規則 ⚠️ **最重要**
**必須**使用 LLM Factory (`get_llm_client`)，**禁止**直接使用 OpenAI SDK 或 `get_azure_openai_client`
違規會導致 500 錯誤 "deployment does not exist"

### 2. Ruff 檢查規則
```bash
# 🚨 所有功能實作完成前必須執行並通過
ruff check src/ test/ --line-length=120
```

### 3. Git Push 確認
推送到 main branch 需要確認：
- 手動確認：`git push origin main` (輸入 'yes')
- 自動確認：`AUTO_CONFIRM_PUSH=yes git push origin main`

### 4. 測試資料長度
所有測試 JD 和 Resume **必須 ≥ 200 字元**

---

## 📚 文檔快速導航

| 主題 | 位置 | 說明 |
|-----|------|------|
| **測試規則詳解** | `CLAUDE-appendix/test-rules.md` | 五大黃金測試規則、Mock 策略 |
| **課程快取系統** | `CLAUDE-appendix/course-cache.md` | 動態快取設計與監控 |
| **部署環境** | `CLAUDE-appendix/environments.md` | 生產/開發環境配置 |
| **Ruff 完整指南** | `CLAUDE-appendix/ruff-guide.md` | 程式碼品質規則與錯誤解決 |
| **Git 工作流程** | `CLAUDE-appendix/git-workflow.md` | 分支策略與 commit 規範 |
| **Serena 工具參考** | `CLAUDE-appendix/serena-tools.md` | 完整工具對照表 |
| **環境變數** | `.env.example` | 完整環境變數配置與註解 |
| **API 文檔** | `docs/API_REFERENCE.md` | API 端點說明 |
| **測試文檔** | `docs/development/TEST_QUICK_REFERENCE.md` | 測試快速參考 |
| **部署管理** | `docs/ENVIRONMENT-AND-PROMPT-MANAGEMENT.md` | 環境與 Prompt 管理 |
| **監控端點** | `docs/api/monitoring.md` | 監控與除錯 API |
| **安全實踐** | `docs/security.md` | 安全檢查清單 |

---

## 🔧 快速參考

### 專案概述
AI 履歷優化平台，從生產容器還原，針對 Container Apps 最佳化。

### 核心功能
- 關鍵字提取、匹配指數計算、差距分析
- 履歷格式化、履歷客製化、課程推薦

### 技術架構
- FastAPI + Azure Container Apps (Japan East)
- GPT-4.1 + GPT-4.1 mini
- PostgreSQL + pgvector

### API 端點
- `POST /api/v1/extract-jd-keywords` - 關鍵字提取
- `POST /api/v1/index-calculation` - 匹配指數
- `POST /api/v1/index-cal-and-gap-analysis` - 組合分析
- `POST /api/v1/format-resume` - 履歷格式化
- `POST /api/v1/tailor-resume` - 履歷客製化

### Azure Portal 連結
- [Container Registry](https://portal.azure.com/#@wenhaoairesumeadvisor.onmicrosoft.com/resource/subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi/providers/Microsoft.ContainerRegistry/registries/airesumeadvisorregistry)
- [Container Apps](https://portal.azure.com/#@wenhaoairesumeadvisor.onmicrosoft.com/resource/subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi/providers/Microsoft.App/containerApps/)

---

## 🛠️ Serena 啟動故障排除

### 常見錯誤與解決

1. **錯誤**: `Project '.serena/project.yml' not found`
   - **解決**: 使用 `mcp__serena__activate_project("azure_container")`

2. **錯誤**: 工具無法使用
   - **解決**: 確保先執行專案啟動步驟

3. **錯誤**: 狀態遺失
   - **解決**: 新對話或 compact 後重新執行啟動步驟

---

**文檔版本**: 2.0.0 (精簡版)  
**更新日期**: 2025-08-29  
**維護者**: Claude Code + WenHao