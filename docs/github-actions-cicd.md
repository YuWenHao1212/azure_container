# GitHub Actions CI/CD 策略

## 🎯 整體架構

採用**補充性 workflow** 策略，專門的 workflow 處理特定任務，與主 CI/CD pipeline 協同工作。

## 📦 Workflow 檔案說明

### 1. 主要 CI/CD Pipeline (`ci-cd-main.yml`)

**用途**: 完整的建置、測試與部署流程
**觸發**: Push 到 main 分支或手動觸發

**核心功能**：
- 執行完整測試套件（174+ 測試）
- 建置並推送 Docker 映像到 Azure Container Registry
- **自動偵測 active prompt 版本**（掃描 YAML 檔案中的 `status: active`）
- 部署到 Azure Container Apps 並設定環境變數
- 執行健康檢查與煙霧測試

**增強功能（新增）**：
- 自動掃描 `src/prompts/*/v*.yaml` 檔案
- 部署時自動設定 prompt 版本環境變數
- 保持向後相容性

### 2. Prompt 版本更新 (`prompt-version-update.yml`)

**用途**: 快速切換 prompt 版本，無需完整部署
**觸發**: 手動 workflow dispatch

**主要功能**：
- 驗證 prompt 檔案存在
- 執行目標測試驗證新版本
- 直接更新 Container Apps 環境變數
- 無需 Docker 重建
- 支援 production 與 development 環境

**使用場景**：
- A/B 測試版本切換
- 快速回滾到先前版本
- 在 production 前先在 development 測試

### 3. Prompt A/B 測試 (`prompt-ab-testing.yml`)

**用途**: 比較兩個 prompt 版本的效能
**觸發**: 手動 workflow dispatch

**主要功能**：
- 平行執行不同版本測試
- 測量回應時間與品質指標
- 產生比較報告
- 協助資料驅動決策

**使用場景**：
- 比較 Gap Analysis v2.1.0 vs v2.1.1
- 測試 prompt 變更的效能影響
- 驗證品質改進

### 4. 回滾部署 (`rollback.yml`)

**用途**: 快速回滾到先前的容器版本
**觸發**: 手動 workflow dispatch

**功能**：
- 列出版本歷史
- 切換流量到先前版本
- 停用有問題的版本
- 健康檢查驗證

## 🔧 環境變數策略

### Prompt 版本控制變數

每個 API 任務支援環境變數覆寫：

- `GAP_ANALYSIS_PROMPT_VERSION`
- `KEYWORD_EXTRACTION_PROMPT_VERSION`
- `INDEX_CALCULATION_PROMPT_VERSION`
- `RESUME_FORMAT_PROMPT_VERSION`
- `RESUME_TAILOR_PROMPT_VERSION`

### 優先順序

1. **環境變數**（如果設定）
2. **Active 版本**（從 YAML metadata）
3. **Latest 版本**（預設）

## 📋 部署場景

### 場景 1：程式碼更新 + Prompt 變更

1. Push 程式碼到 main 分支
2. `ci-cd-main.yml` 自動觸發
3. 執行所有 prompt 版本測試
4. 偵測 active prompt 版本
5. 更新 Container Apps（新映像 + 版本）

### 場景 2：僅更新 Prompt 版本

1. 執行 `prompt-version-update.yml` workflow
2. 選擇任務與版本
3. 測試驗證新版本
4. 更新 Container Apps 環境變數
5. 無需 Docker 重建

### 場景 3：A/B 測試新 Prompt

1. 建立新 prompt 版本（如 v2.1.1）
2. 執行 `prompt-ab-testing.yml` workflow
3. 與當前版本比較（如 v2.1.0）
4. 檢視效能指標
5. 如果較佳，使用 `prompt-version-update.yml` 更新

### 場景 4：緊急回滾

1. 部署後發現問題
2. 執行 `rollback.yml` workflow
3. 流量切換到先前版本
4. 可在無停機時間下進行調查

## 🛠️ 初始設定

### 1. GitHub Secrets 配置

在 GitHub repository → Settings → Secrets 新增：

#### Azure 認證
```json
{
  "clientId": "YOUR_CLIENT_ID",
  "clientSecret": "YOUR_CLIENT_SECRET",
  "subscriptionId": "5396d388-8261-464e-8ee4-112770674fba",
  "tenantId": "YOUR_TENANT_ID"
}
```

#### Container Registry
- `ACR_USERNAME`: airesumeadvisorregistry
- `ACR_PASSWORD`: 從 Azure Portal 取得

#### API Keys
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `CONTAINER_APP_API_KEY`
- `JWT_SECRET_KEY`

### 2. 建立 Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "github-actions-sp" \
  --role contributor \
  --scopes /subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi \
  --sdk-auth
```

## 💻 使用指令

### GitHub CLI 指令

```bash
# 觸發 prompt 版本更新
gh workflow run prompt-version-update.yml \
  -f task=gap_analysis \
  -f version=2.1.1 \
  -f environment=production

# 執行 A/B 測試
gh workflow run prompt-ab-testing.yml \
  -f task=gap_analysis \
  -f version_a=2.1.0 \
  -f version_b=2.1.1 \
  -f test_samples=20

# 緊急回滾
gh workflow run rollback.yml \
  -f reason="偵測到高錯誤率"
```

### 本地腳本

```bash
# 快速更新版本
./scripts/update-gap-version-azure.sh 2.1.1

# 查詢當前版本
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
  -o tsv
```

## 📊 監控與警報

### 關鍵指標

- 每個 prompt 版本的 API 回應時間
- 端點錯誤率
- 模型 token 使用量
- Gap Analysis 品質分數

### 警報觸發條件

- 回應時間 > SLA 閾值
- 錯誤率 > 1%
- 健康檢查失敗
- Prompt 載入失敗

## 🔒 安全考量

### Secrets 管理
- 所有敏感資料存在 GitHub Secrets
- Azure 認證使用 Service Principal
- API keys 定期輪換

### 存取控制
- Workflow dispatch 需要 repository write 權限
- Azure 權限使用最小權限原則
- Container Apps 使用 API key 認證

## 🐛 疑難排解

### 常見問題

**1. Prompt 檔案找不到**
- 確認檔案存在：`src/prompts/{task}/v{version}.yaml`
- 檢查版本號拼寫

**2. 新 prompt 測試失敗**
- 檢視 prompt 變更的相容性
- 檢查 token 限制與回應格式
- 驗證測試資料

**3. 部署失敗**
- 驗證 Azure 認證有效性
- 檢查 container registry 存取
- 確認資源群組權限

**4. 版本未更新**
- 確認環境變數名稱
- 檢查 Container Apps 配置
- 驗證版本是否 active

## ✨ 最佳實踐

### Prompt 版本管理
- 標記 active 版本（metadata 中設定 `status: active`）
- 使用語義化版本（如 2.1.0, 2.1.1）
- 在 prompt YAML 中記錄變更
- 標記為 active 前先測試新版本

### 測試策略
- 使用真實資料測試 prompt 變更
- 重大變更使用 A/B 測試
- 監控回應時間與品質指標
- 保留可用的回滾版本

### 部署安全
- 分階段部署（dev → production）
- 部署後監控指標
- 準備好回滾程序
- 記錄版本變更

## 🚀 未來增強計畫

### 規劃功能

1. **自動化 Prompt 優化**
   - 基於 ML 的 prompt 調整
   - 自動 A/B 測試排程
   - 基於效能的版本選擇

2. **多環境支援**
   - Staging 環境 workflows
   - 藍綠部署策略
   - 金絲雀發布

3. **增強監控**
   - Prompt 專屬儀表板
   - 版本比較分析
   - 使用者回饋整合

## 📚 相關文檔

- [Prompt 版本管理](./prompt-version-management.md)
- [CLAUDE.md](../CLAUDE.md) - 專案說明
- [API 文檔](./API.md)

## 📝 版本歷史

- v1.0.0 - 初始 GitHub Actions 設定
- v1.1.0 - 新增 prompt 版本偵測
- v1.2.0 - 實作 A/B 測試 workflow
- v1.3.0 - 增強自動版本偵測

---

**最後更新**: 2025-08-13
**維護團隊**: DevOps Team