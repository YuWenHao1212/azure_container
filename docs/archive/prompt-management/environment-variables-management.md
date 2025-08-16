# 環境變數管理指南

> 最後更新：2025-08-16  
> 版本：1.0.0

## 📍 環境變數管理位置總覽

### 🎯 主要管理點（按優先級排序）

| 位置 | 檔案/指令 | 生效範圍 | 優先級 | 適用場景 |
|------|----------|---------|--------|----------|
| **1. CI/CD Pipeline** | `.github/workflows/ci-cd-main.yml` | 生產環境 | 最高（會覆蓋） | 每次部署時設定 |
| **2. Azure Portal** | Azure Container Apps 設定 | 生產環境 | 中（被CI/CD覆蓋） | 臨時調整 |
| **3. 本地 .env** | `.env` | 開發環境 | 本地最高 | 開發測試 |
| **4. Docker** | `Dockerfile` | 容器預設 | 最低 | 容器基礎設定 |
| **5. 程式碼預設** | `src/core/config.py` | 所有環境 | 最低 | 系統預設值 |

---

## 1️⃣ **CI/CD Pipeline（主要控制點）**

### 位置
`.github/workflows/ci-cd-main.yml` (第 341-370 行)

### 管理方式
```yaml
# 每次部署都會完全覆蓋 Azure 上的環境變數
az containerapp update \
  --set-env-vars \
    GAP_ANALYSIS_PROMPT_VERSION="${{ steps.prompt-versions.outputs.gap-analysis-version }}" \
    KEYWORD_EXTRACTION_PROMPT_VERSION="${{ steps.prompt-versions.outputs.keyword-extraction-version }}" \
    # ... 其他環境變數
```

### 如何修改
1. 編輯 `.github/workflows/ci-cd-main.yml`
2. 找到 `--set-env-vars` 區塊（約第 341 行）
3. 修改或新增環境變數
4. Git commit & push → 自動部署

### Prompt 版本控制邏輯
```bash
# CI/CD 自動偵測 active 版本（第 287-294 行）
GAP_VERSION=$(find_active_version "gap_analysis")
echo "gap-analysis-version=${GAP_VERSION:-2.1.8}" >> $GITHUB_OUTPUT
```

**重要**：CI/CD 每次部署都會覆蓋所有環境變數！

---

## 2️⃣ **Azure Portal（臨時調整）**

### 進入方式
1. [Azure Portal](https://portal.azure.com)
2. Container Apps → `airesumeadvisor-api-production`
3. Settings → Containers → Environment variables

### 使用 Azure CLI
```bash
# 查看當前環境變數
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env" \
  -o table

# 更新特定環境變數（會被下次 CI/CD 覆蓋）
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars GAP_ANALYSIS_PROMPT_VERSION=2.1.9
```

### 使用腳本
```bash
# 專門更新 Gap Analysis 版本
./scripts/update-gap-version-azure.sh 2.1.9

# 查看所有 prompt 版本
./scripts/check-prompt-versions-azure.sh
```

**注意**：這裡的修改會在下次 CI/CD 部署時被覆蓋！

---

## 3️⃣ **本地開發環境**

### 位置
`.env` (專案根目錄)

### 管理方式
```bash
# 複製範本
cp .env.example .env

# 編輯環境變數
vim .env
```

### 範例內容
```env
# Prompt 版本控制
GAP_ANALYSIS_PROMPT_VERSION=2.1.8
KEYWORD_EXTRACTION_PROMPT_VERSION=latest
INDEX_CALCULATION_PROMPT_VERSION=latest
RESUME_FORMAT_PROMPT_VERSION=latest
RESUME_TAILOR_PROMPT_VERSION=latest

# 其他設定
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 測試不同版本
```bash
# 臨時覆蓋
GAP_ANALYSIS_PROMPT_VERSION=2.1.7 python src/main.py

# 或修改 .env 後
source .env
python src/main.py
```

---

## 4️⃣ **Docker 容器**

### 位置
`Dockerfile`

### 管理方式
```dockerfile
# 設定預設值（優先級最低）
ENV GAP_ANALYSIS_PROMPT_VERSION=2.1.8
ENV KEYWORD_EXTRACTION_PROMPT_VERSION=latest
```

### 執行時覆蓋
```bash
# 建置時
docker build --build-arg GAP_ANALYSIS_PROMPT_VERSION=2.1.9 .

# 執行時
docker run -e GAP_ANALYSIS_PROMPT_VERSION=2.1.9 image-name
```

---

## 5️⃣ **程式碼預設值**

### 位置
- `src/core/config.py` - 系統設定
- `src/core/simple_prompt_manager.py` - Prompt 管理邏輯

### 優先級邏輯（SimplePromptManager）
```python
def get_resolved_version(self, task: str, requested_version: str = "latest") -> str:
    # 1. 環境變數最優先
    env_key = f"{task.upper().replace('-', '_')}_PROMPT_VERSION"
    env_version = os.getenv(env_key)
    if env_version:
        return env_version
    
    # 2. Active 版本次之
    active_version = self.get_active_version(task)
    if active_version:
        return active_version
    
    # 3. 最後使用 latest
    return self._get_latest_version(task)
```

---

## 📊 **環境變數完整列表**

### Prompt 版本控制
| 環境變數 | 預設值 | 說明 |
|---------|--------|------|
| `GAP_ANALYSIS_PROMPT_VERSION` | 2.1.8 | Gap Analysis prompt 版本 |
| `KEYWORD_EXTRACTION_PROMPT_VERSION` | latest | 關鍵字提取 prompt 版本 |
| `INDEX_CALCULATION_PROMPT_VERSION` | latest | 指數計算 prompt 版本 |
| `RESUME_FORMAT_PROMPT_VERSION` | latest | 履歷格式化 prompt 版本 |
| `RESUME_TAILOR_PROMPT_VERSION` | latest | 履歷客製化 prompt 版本 |

### 系統設定
| 環境變數 | 預設值 | 說明 |
|---------|--------|------|
| `ENVIRONMENT` | production | 執行環境 |
| `LOG_LEVEL` | INFO | 日誌級別 |
| `MONITORING_ENABLED` | false | 監控開關 |
| `LIGHTWEIGHT_MONITORING` | true | 輕量監控 |

### AI 模型設定
| 環境變數 | 預設值 | 說明 |
|---------|--------|------|
| `LLM_MODEL_KEYWORDS` | gpt-4.1-mini | 關鍵字提取模型 |
| `LLM_MODEL_GAP_ANALYSIS` | gpt-4.1 | Gap Analysis 模型 |
| `LLM_MODEL_RESUME_FORMAT` | gpt-4.1 | 履歷格式化模型 |
| `LLM_MODEL_RESUME_TAILOR` | gpt-4.1 | 履歷客製化模型 |

---

## 🔧 **實用操作指令**

### 查看當前版本
```bash
# Azure 生產環境
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?contains(name, 'PROMPT_VERSION')]" \
  -o table

# 本地環境
grep PROMPT_VERSION .env
```

### 快速切換版本
```bash
# 方法 1：修改 CI/CD 後 push（永久）
vim .github/workflows/ci-cd-main.yml
git add . && git commit -m "Update prompt versions"
git push

# 方法 2：Azure CLI（臨時，會被覆蓋）
./scripts/update-gap-version-azure.sh 2.1.9

# 方法 3：本地測試
export GAP_ANALYSIS_PROMPT_VERSION=2.1.9
python src/main.py
```

### 驗證版本生效
```python
# Python 腳本驗證
from src.core.simple_prompt_manager import prompt_manager

version = prompt_manager.get_resolved_version("gap_analysis", "latest")
print(f"Will use Gap Analysis version: {version}")
```

---

## ⚠️ **重要提醒**

1. **CI/CD 是最終控制點**
   - 每次 push 到 main 分支都會觸發部署
   - 部署時會完全覆蓋 Azure 上的環境變數
   - 要永久修改必須編輯 CI/CD 檔案

2. **Azure Portal/CLI 修改是臨時的**
   - 適合緊急調整和測試
   - 下次 CI/CD 部署會被覆蓋
   - 記得同步回 CI/CD 檔案

3. **版本優先級**
   ```
   環境變數 > Active 狀態 > Latest 版本
   ```

4. **建議工作流程**
   - 開發：修改 `.env` 本地測試
   - 測試：使用 Azure CLI 臨時調整
   - 生產：修改 CI/CD 檔案永久生效

---

## 📝 **快速參考卡**

```bash
# 最重要的檔案
.github/workflows/ci-cd-main.yml  # 第 341-370 行

# 查看設定
az containerapp show --name airesumeadvisor-api-production \
  --query "properties.template.containers[0].env" -o table

# 臨時修改
./scripts/update-gap-version-azure.sh 2.1.9

# 永久修改
編輯 .github/workflows/ci-cd-main.yml → git push
```

---

## 🔗 相關文檔

- [Prompt 版本管理規則](./prompt-version-rules.md)
- [CI/CD 配置說明](./github-actions-cicd.md)
- [Azure Container Apps 部署](./azure-deployment.md)