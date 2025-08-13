# GitHub Secrets 設定指南

## ⚠️ 重要提醒

GitHub Actions workflows 需要以下 Secrets 才能正常運作。請在 GitHub repository 設定這些 Secrets。

## 📋 必要的 Secrets

### 1. Azure 認證 Secrets

需要建立 Service Principal 並設定以下 Secrets：

| Secret 名稱 | 說明 | 如何取得 |
|------------|------|----------|
| `AZURE_CLIENT_ID` | Service Principal Client ID | 執行下方的 az 指令 |
| `AZURE_CLIENT_SECRET` | Service Principal Secret | 執行下方的 az 指令 |
| `AZURE_SUBSCRIPTION_ID` | Azure 訂閱 ID | `5396d388-8261-464e-8ee4-112770674fba` |
| `AZURE_TENANT_ID` | Azure Tenant ID | 執行下方的 az 指令 |

#### 建立 Service Principal：

```bash
az ad sp create-for-rbac \
  --name "github-actions-sp" \
  --role contributor \
  --scopes /subscriptions/5396d388-8261-464e-8ee4-112770674fba/resourceGroups/airesumeadvisorfastapi \
  --sdk-auth
```

這會輸出 JSON，從中提取對應的值。

### 2. Container Registry Secrets

| Secret 名稱 | 說明 | 如何取得 |
|------------|------|----------|
| `ACR_USERNAME` | Container Registry 使用者名稱 | `airesumeadvisorregistry` |
| `ACR_PASSWORD` | Container Registry 密碼 | Azure Portal → Container Registry → Access keys |

### 3. Azure OpenAI Secrets

| Secret 名稱 | 說明 | 範例值 |
|------------|------|--------|
| `AZURE_OPENAI_ENDPOINT` | OpenAI 端點 | `https://airesumeadvisor.openai.azure.com` |
| `AZURE_OPENAI_API_KEY` | OpenAI API 金鑰 | 從 Azure Portal 取得 |
| `EMBEDDING_ENDPOINT` | Embedding 端點 | 從 Azure Portal 取得 |
| `COURSE_EMBEDDING_ENDPOINT` | Course Embedding 端點 | 從 Azure Portal 取得 |

### 4. 應用程式 Secrets

| Secret 名稱 | 說明 | 建議 |
|------------|------|-------|
| `JWT_SECRET_KEY` | JWT 簽名金鑰 | 使用強隨機字串 |
| `CONTAINER_APP_API_KEY` | Container App API 金鑰 | 使用強隨機字串 |

## 🔧 設定步驟

### 步驟 1：前往 GitHub Repository Settings

1. 開啟你的 GitHub repository
2. 點擊 **Settings** 標籤
3. 在左側選單找到 **Secrets and variables** → **Actions**

### 步驟 2：新增 Secrets

對每個 Secret：
1. 點擊 **New repository secret**
2. 輸入 **Name**（必須完全符合上表的名稱）
3. 輸入 **Secret** 值
4. 點擊 **Add secret**

### 步驟 3：驗證設定

設定完成後，你應該在 Secrets 頁面看到類似：

```
ACR_PASSWORD             Updated 1 minute ago
ACR_USERNAME             Updated 1 minute ago
AZURE_CLIENT_ID          Updated 1 minute ago
AZURE_CLIENT_SECRET      Updated 1 minute ago
AZURE_OPENAI_API_KEY     Updated 1 minute ago
AZURE_OPENAI_ENDPOINT    Updated 1 minute ago
AZURE_SUBSCRIPTION_ID    Updated 1 minute ago
AZURE_TENANT_ID          Updated 1 minute ago
CONTAINER_APP_API_KEY    Updated 1 minute ago
COURSE_EMBEDDING_ENDPOINT Updated 1 minute ago
EMBEDDING_ENDPOINT       Updated 1 minute ago
JWT_SECRET_KEY          Updated 1 minute ago
```

## 🔍 疑難排解

### Workflow 失敗：Error: Input required and not supplied

這表示某個 Secret 未設定。檢查錯誤訊息中提到的 Secret 名稱。

### Workflow 失敗：Authentication failed

檢查 Azure Service Principal 是否：
- 有正確的權限
- Client Secret 未過期
- Subscription ID 正確

### 測試 Secrets

可以建立簡單的測試 workflow：

```yaml
name: Test Secrets
on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Check secrets
        run: |
          echo "Checking if secrets are set..."
          if [ -z "${{ secrets.AZURE_CLIENT_ID }}" ]; then
            echo "❌ AZURE_CLIENT_ID not set"
          else
            echo "✅ AZURE_CLIENT_ID is set"
          fi
          # 重複檢查其他 secrets
```

## 📝 注意事項

1. **永遠不要** 在程式碼中直接寫入 Secrets
2. **定期輪換** Secrets，特別是 API keys
3. **限制權限** - Service Principal 只給必要的權限
4. **使用環境** - 可以為不同環境（dev/staging/prod）設定不同的 Secrets

## 🔐 安全最佳實踐

- 使用強密碼產生器產生 API keys
- Service Principal 設定過期時間
- 定期審查 Secrets 使用情況
- 啟用 GitHub 的 Secret scanning

---

**最後更新**: 2025-08-13
**重要**: 完成設定後，請重新執行失敗的 workflow 以驗證設定正確。