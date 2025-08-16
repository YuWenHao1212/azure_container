# Azure Container Apps CI/CD 部署指南

## 📋 概述

本專案使用 GitHub Actions 自動化 CI/CD 流程，將應用程式部署到 Azure Container Apps。

### 工作流程
1. 推送程式碼到 `main` 分支
2. 自動執行測試套件
   - Level 0: Prompt 驗證
   - Level 1: 程式碼風格 (Ruff)
   - Level 2: 單元測試 (96 個)
   - Level 3: 整合測試 (16 個)
   - Level 4: 效能測試 (1 個)
3. 建置 Docker 映像並推送到 Azure Container Registry
4. 部署到 Azure Container Apps
5. 執行健康檢查和煙霧測試

## 🔧 設定步驟

### 1. 建立 Azure Service Principal

執行以下命令建立 Service Principal：

```bash
# 建立 Service Principal 並授予資源群組的 Contributor 權限
az ad sp create-for-rbac \
  --name "github-actions-azure-container" \
  --role Contributor \
  --scopes /subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi \
  --sdk-auth
```

輸出範例：
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "subscriptionId": "5396d388-8261-464e-8ee4-112770674fba",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### 2. 授予 Container Registry 權限

```bash
# 取得 ACR 資源 ID
ACR_ID=$(az acr show --name airesumeadvisorregistry --query id -o tsv)

# 授予 AcrPush 權限
az role assignment create \
  --assignee <clientId-from-above> \
  --role AcrPush \
  --scope $ACR_ID
```

### 3. 設定 GitHub Secrets

在 GitHub Repository 中設定以下 Secrets：
1. 前往 Settings > Secrets and variables > Actions
2. 點擊 "New repository secret"
3. 新增以下 Secrets：

#### Azure 認證
- `AZURE_CLIENT_ID`: Service Principal 的 clientId
- `AZURE_CLIENT_SECRET`: Service Principal 的 clientSecret
- `AZURE_TENANT_ID`: Service Principal 的 tenantId
- `AZURE_SUBSCRIPTION_ID`: `5396d388-8261-464e-8ee4-112770674fba`

#### Container Registry
```bash
# 取得 ACR 認證
az acr credential show --name airesumeadvisorregistry
```
- `ACR_USERNAME`: 上述命令輸出的 username
- `ACR_PASSWORD`: 上述命令輸出的 passwords[0].value

#### Azure OpenAI
從您的 `.env` 檔案複製以下值：
- `AZURE_OPENAI_ENDPOINT`: `https://airesumeadvisor.openai.azure.com`
- `AZURE_OPENAI_API_KEY`: 您的 Azure OpenAI API Key
- `EMBEDDING_ENDPOINT`: Embedding 服務端點
- `COURSE_EMBEDDING_ENDPOINT`: 課程 Embedding 服務端點

#### 應用程式密鑰
- `JWT_SECRET_KEY`: JWT 密鑰（從 .env 複製）
- `CONTAINER_APP_API_KEY`: API 存取密鑰（從 .env 複製）

## 📦 工作流程說明

### CI/CD 主流程 (`ci-cd-main.yml`)
- **觸發**: 推送到 `main` 分支
- **步驟**:
  1. 執行測試套件
  2. 建置 Docker 映像
  3. 推送到 Azure Container Registry
  4. 部署到 Container Apps
  5. 健康檢查驗證

### 回滾流程 (`rollback.yml`)
- **觸發**: 手動
- **功能**: 回滾到指定版本或前一個版本
- **使用方式**:
  1. Actions > Rollback Deployment > Run workflow
  2. 輸入要回滾的版本（選填）和原因
  3. 執行回滾

### 清理流程 (`cleanup.yml`)
- **觸發**: 每週日凌晨 2 點（UTC）或手動
- **功能**: 清理超過 30 天的舊映像和非活動修訂版本
- **保留策略**:
  - 保留最近 30 天的映像
  - 保留最近 10 個修訂版本

## 🚀 使用方式

### 部署新版本
```bash
# 1. 提交程式碼
git add .
git commit -m "feat: 新功能"

# 2. 推送到 main 分支（自動觸發部署）
git push origin main

# 3. 在 GitHub Actions 頁面監控部署進度
```

### 手動回滾
1. 前往 Actions 頁面
2. 選擇 "Rollback Deployment"
3. 點擊 "Run workflow"
4. 填寫回滾原因
5. 執行回滾

### 查看部署狀態
- GitHub Actions: https://github.com/YuWenHao1212/azure_container/actions
- 生產環境: https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health

## 🔍 故障排除

### 常見問題

1. **認證錯誤**
   - 確認 Service Principal 有正確的權限
   - 檢查 GitHub Secrets 是否正確設定

2. **映像推送失敗**
   - 確認 ACR 認證正確
   - 檢查 Service Principal 有 AcrPush 權限

3. **部署失敗**
   - 查看 Container App 日誌
   - 確認環境變數設定正確
   - 檢查健康檢查端點是否正常

### 查看日誌
```bash
# 查看 Container App 日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --follow

# 查看特定修訂版本的日誌
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --revision <revision-name>
```

## 🧪 測試與品質保證

### 測試統計
- **總測試案例**: 113 個
- **測試通過率**: 100%
- **測試層級**:
  - 單元測試: 96 個
  - 整合測試: 16 個
  - 效能測試: 1 個

### 測試報告
- 位置: `/test/logs/`
- 格式: JSON 和文字報告
- 保留策略: 最新 6 份

## 📊 監控

### Application Insights
- 已整合完整遙測
- 監控 API 效能和錯誤率
- 自定義指標追蹤

### 健康檢查
- 端點: `/health`
- 自動監控服務健康狀態
- 部署後自動驗證

## 🔒 安全注意事項

1. **密鑰管理**
   - 所有敏感資料透過 GitHub Secrets 管理
   - 不要在程式碼中硬編碼任何密鑰
   - 定期輪換密鑰

2. **最小權限原則**
   - Service Principal 只有必要的權限
   - 限定在特定資源群組範圍

3. **映像安全**
   - 使用多階段建置減少映像大小
   - 定期更新基礎映像
   - 掃描安全漏洞

## 📅 維護計劃

### 每週
- 自動清理舊映像（週日凌晨）
- 檢查部署日誌和錯誤率

### 每月
- 檢視 CI/CD 效能
- 更新依賴套件
- 審查安全設定

### 每季
- 輪換密鑰
- 優化部署流程
- 更新文檔

---

**最後更新**: 2025-08-02  
**維護者**: DevOps Team