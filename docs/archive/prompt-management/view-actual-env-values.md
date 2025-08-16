# 查看環境變數實際值指南

> 建立日期：2025-08-16  
> 用途：查看 CI/CD 變數和生產環境的實際值

## 🔍 查看實際值的方法

---

## 1️⃣ **查看 Azure Container Apps 當前實際值**

### 方法 A：Azure CLI（推薦）
```bash
# 查看所有環境變數的實際值
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env" \
  -o table

# 只看 Prompt 版本
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?contains(name, 'PROMPT_VERSION')]" \
  -o table

# 看特定變數（例如 GAP_ANALYSIS_PROMPT_VERSION）
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
  -o tsv
```

### 方法 B：Azure Portal
1. 登入 [Azure Portal](https://portal.azure.com)
2. 搜尋 "Container Apps"
3. 選擇 `airesumeadvisor-api-production`
4. 左側選單：Settings → Containers
5. 點擊 "Edit and deploy"
6. 切換到 "Environment variables" 標籤
7. 這裡可以看到所有變數的實際值

---

## 2️⃣ **查看 CI/CD 變數的實際值**

### A. GitHub Secrets（敏感資料）
```bash
# 這些無法直接查看（安全考量）
${{ secrets.AZURE_OPENAI_API_KEY }}  # ❌ 無法查看
${{ secrets.JWT_SECRET_KEY }}         # ❌ 無法查看

# 但可以在 GitHub 設定中確認是否存在
# GitHub → Settings → Secrets and variables → Actions
```

### B. Steps 輸出值（可查看）
```bash
# CI/CD 執行時的動態值
${{ steps.prompt-versions.outputs.gap-analysis-version }}

# 查看方法：
# 1. 去 GitHub Actions 頁面
# 2. 點擊最近的 workflow run
# 3. 展開 "Detect prompt versions" 步驟
# 4. 會看到類似：
#    Detected prompt versions:
#    - Gap Analysis: 2.1.8
#    - Keyword Extraction: latest
```

### C. 在 CI/CD 中加入除錯輸出
```yaml
# 可以暫時修改 CI/CD 來顯示實際值
- name: Debug - Show actual values
  run: |
    echo "=== Actual Values Being Set ==="
    echo "GAP_ANALYSIS_PROMPT_VERSION: ${{ steps.prompt-versions.outputs.gap-analysis-version }}"
    echo "KEYWORD_EXTRACTION_PROMPT_VERSION: ${{ steps.prompt-versions.outputs.keyword-extraction-version }}"
    echo "Container App: ${{ env.CONTAINER_APP_NAME }}"
    echo "Resource Group: ${{ env.RESOURCE_GROUP }}"
```

---

## 3️⃣ **從運行中的容器查看**

### 方法 A：透過 API Health 端點
```bash
# 如果 health 端點有顯示版本資訊
curl https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health

# 回應可能包含：
{
  "status": "healthy",
  "version": "1.0.0",
  "prompt_versions": {
    "gap_analysis": "2.1.8",  # 實際使用的版本
    "keyword_extraction": "latest"
  }
}
```

### 方法 B：Container Logs
```bash
# 查看容器日誌（會顯示載入的版本）
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --type console \
  --follow

# 可能看到：
# INFO: Loading Gap Analysis prompt version: 2.1.8
# INFO: Using environment variable: GAP_ANALYSIS_PROMPT_VERSION=2.1.8
```

---

## 4️⃣ **建立查看腳本**

### 創建 `scripts/check-actual-env-values.sh`
```bash
#!/bin/bash

echo "=== 查看生產環境實際值 ==="
echo ""

# 1. Prompt 版本
echo "📝 Prompt 版本："
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?contains(name, 'PROMPT_VERSION')].{Name:name, Value:value}" \
  -o table

echo ""

# 2. LLM 模型設定
echo "🤖 LLM 模型："
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?contains(name, 'LLM_MODEL')].{Name:name, Value:value}" \
  -o table

echo ""

# 3. 系統設定
echo "⚙️ 系統設定："
for var in ENVIRONMENT LOG_LEVEL MONITORING_ENABLED LIGHTWEIGHT_MONITORING; do
  VALUE=$(az containerapp show \
    --name airesumeadvisor-api-production \
    --resource-group airesumeadvisorfastapi \
    --query "properties.template.containers[0].env[?name=='$var'].value | [0]" \
    -o tsv)
  echo "$var: $VALUE"
done

echo ""

# 4. 當前 Revision
echo "📦 當前 Revision："
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "[?properties.trafficWeight==\`100\`].{Name:name, Created:properties.createdTime, Active:properties.active}" \
  -o table
```

---

## 5️⃣ **CI/CD 變數來源對照表**

| CI/CD 變數 | 來源 | 如何查看實際值 |
|------------|------|----------------|
| `${{ secrets.XXX }}` | GitHub Secrets | 無法查看（安全） |
| `${{ env.XXX }}` | workflow env 區塊 | 看 CI/CD 檔案第 8-12 行 |
| `${{ steps.XXX.outputs.YYY }}` | 前面步驟的輸出 | GitHub Actions 執行日誌 |
| `${GAP_VERSION:-2.1.8}` | Shell 變數+預設值 | 執行時決定 |

### CI/CD env 區塊的實際值
```yaml
env:
  REGISTRY: airesumeadvisorregistry.azurecr.io
  IMAGE_NAME: airesumeadvisor-api
  CONTAINER_APP_NAME: airesumeadvisor-api-production
  RESOURCE_GROUP: airesumeadvisorfastapi
```

### Steps 輸出的實際值（第 287-302 行的邏輯）
```bash
# CI/CD 會自動偵測並輸出：
gap-analysis-version: 2.1.8        # 如果找到 active
keyword-extraction-version: latest  # 如果沒有 active
index-calculation-version: latest   
resume-format-version: latest      
resume-tailor-version: latest      
```

---

## 6️⃣ **完整查看指令集**

```bash
# 1. 查看所有環境變數
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env" \
  -o json | jq '.'

# 2. 匯出到檔案
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env" \
  -o json > current-env-vars.json

# 3. 比較版本
echo "設定的版本："
grep "PROMPT_VERSION" current-env-vars.json | grep -o '"value": "[^"]*"'

# 4. 查看最近部署
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "[-5:].{Revision:name, Created:properties.createdTime, Traffic:properties.trafficWeight}" \
  -o table
```

---

## 7️⃣ **實際值範例**

根據目前設定，實際值應該是：

| 變數名稱 | CI/CD 設定 | 實際值（預期） |
|---------|-----------|---------------|
| `GAP_ANALYSIS_PROMPT_VERSION` | `${{ steps.prompt-versions.outputs.gap-analysis-version }}` | `2.1.8` |
| `KEYWORD_EXTRACTION_PROMPT_VERSION` | `${{ steps.prompt-versions.outputs.keyword-extraction-version }}` | `latest` |
| `LLM_MODEL_GAP_ANALYSIS` | `gpt-4.1` | `gpt-4.1` |
| `LLM_MODEL_KEYWORDS` | `gpt-4.1-mini` | `gpt-4.1-mini` |
| `ENVIRONMENT` | `production` | `production` |
| `LOG_LEVEL` | `INFO` | `INFO` |

---

## 🔧 **快速診斷指令**

```bash
# 一鍵查看關鍵設定
echo "=== Gap Analysis 版本 ==="
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
  -o tsv

echo "=== 最近部署時間 ==="
az containerapp revision list \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "[?properties.active==\`true\`] | [0].properties.createdTime" \
  -o tsv
```

---

## 📝 總結

1. **GitHub Secrets**：無法查看實際值（安全考量）
2. **Steps 輸出**：看 GitHub Actions 執行日誌
3. **最終結果**：用 Azure CLI 查看 Container Apps
4. **建議**：使用提供的腳本定期檢查實際值