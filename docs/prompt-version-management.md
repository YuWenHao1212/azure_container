# Prompt 版本管理系統

## 📋 系統概述

本專案使用統一的 SimplePromptManager 管理所有 API 的 prompt 版本，支援靈活的版本切換與 A/B 測試。

## 🎯 核心特性

### 版本選擇優先級

所有 API 遵循相同的版本選擇邏輯：

```
1. 環境變數 (TASK_PROMPT_VERSION) - 最高優先級
2. Active 版本 (metadata.status = "active") 
3. Latest 版本 (最新版本) - 預設選項
```

### 環境變數命名規則

統一使用 `TASK_PROMPT_VERSION` 格式：

```bash
# Gap Analysis
GAP_ANALYSIS_PROMPT_VERSION=2.1.1

# Keyword Extraction  
KEYWORD_EXTRACTION_PROMPT_VERSION=1.4.0

# Index Calculation
INDEX_CALCULATION_PROMPT_VERSION=2.0.0

# Resume Format
RESUME_FORMAT_PROMPT_VERSION=1.0.0

# Resume Tailoring
RESUME_TAILOR_PROMPT_VERSION=2.1.0
```

## 📊 版本狀態追蹤

### Gap Analysis Prompt 版本歷程

| 版本 | 狀態 | 部署日期 | 主要改進 |
|------|------|----------|----------|
| v2.1.0 | Stable | 2025-01-16 | 新增 [Skill Gap] 和 [Presentation Gap] 標記 |
| v2.1.1 | Active | 2025-08-13 | - 限制 150 字內<br>- 移除數字預測<br>- 優先處理 Presentation Gaps<br>- 採用綜合分析方式 |

### 其他 API Prompt 版本

| API | 當前版本 | 狀態 | 說明 |
|-----|---------|------|------|
| Keyword Extraction | v1.4.0 | Active | 支援多語言提取 |
| Index Calculation | v2.0.0 | Active | 增強匹配演算法 |
| Resume Format | v1.0.0 | Active | 基礎格式化功能 |
| Resume Tailoring | v2.1.0 | Active | 改進客製化品質 |

## 🔧 使用指南

### 本地開發測試

```bash
# 設定特定版本
export GAP_ANALYSIS_PROMPT_VERSION=2.1.0

# 執行測試
pytest test/integration/test_gap_analysis_v2_integration_complete.py -v

# 清除環境變數（使用預設）
unset GAP_ANALYSIS_PROMPT_VERSION
```

### Docker 容器配置

```dockerfile
# Dockerfile
ENV GAP_ANALYSIS_PROMPT_VERSION=2.1.1
ENV KEYWORD_EXTRACTION_PROMPT_VERSION=1.4.0
```

### Azure Container Apps 部署

#### 快速切換版本（無需重新部署）

```bash
# 使用提供的腳本
./scripts/update-gap-version-azure.sh 2.1.1

# 或使用 Azure CLI
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars GAP_ANALYSIS_PROMPT_VERSION=2.1.1
```

#### 查詢當前版本

```bash
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
  -o tsv
```

## 🧪 測試策略

### 單元測試驗證

```python
import os
from src.core.simple_prompt_manager import prompt_manager

def test_env_var_override():
    """測試環境變數覆蓋功能"""
    os.environ["GAP_ANALYSIS_PROMPT_VERSION"] = "2.1.0"
    
    version = prompt_manager.get_resolved_version("gap_analysis")
    assert version == "2.1.0"
```

### A/B 測試比較

```bash
# 比較兩個版本效能
GAP_ANALYSIS_PROMPT_VERSION=2.1.0 python test_performance.py
GAP_ANALYSIS_PROMPT_VERSION=2.1.1 python test_performance.py
```

## 📈 程式碼整合

### 統一使用 SimplePromptManager

所有服務都使用相同模式：

```python
from src.core.simple_prompt_manager import prompt_manager

# 載入 prompt（自動處理版本選擇）
prompt_config = prompt_manager.load_prompt_config("gap_analysis", version="latest")

# 系統會自動：
# 1. 檢查 GAP_ANALYSIS_PROMPT_VERSION 環境變數
# 2. 若無，尋找 status: active 的版本
# 3. 若無，使用最新版本
```

### 移除的重複程式碼

已移除各 API 中的特定版本管理邏輯：

**之前（重複）**：
```python
# 每個 API 都有自己的版本管理
version = self.settings.gap_analysis_prompt_version
```

**現在（統一）**：
```python
# 所有 API 使用相同介面
prompt_config = prompt_manager.load_prompt_config(task, "latest")
```

## 🔄 版本回滾程序

### 快速回滾（秒級）

```bash
# 立即切換到穩定版本
./scripts/update-gap-version-azure.sh 2.1.0

# 無需重新部署，容器自動重啟使用新版本
```

### 驗證回滾

```bash
# 確認版本已更新
curl https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health

# 查看日誌確認載入版本
az containerapp logs show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --type console
```

## 📝 版本命名規範

### 檔案命名格式

```
v{主版本}.{次版本}.{修訂版本}[-語言代碼].yaml

範例：
- v2.1.1.yaml        # 預設英文版
- v2.1.1-zh-TW.yaml  # 繁體中文版
```

### 版本號規則

- **主版本**：重大改變，可能不相容
- **次版本**：新功能或改進
- **修訂版**：錯誤修復或小調整

## 🚀 部署檢查清單

新版本部署前確認：

- [ ] 建立新的 YAML 檔案在正確路徑
- [ ] 設定 metadata.status（active/inactive/testing）
- [ ] 本地測試通過
- [ ] 更新版本文檔
- [ ] 設定環境變數（如需要）
- [ ] 部署到 Container Apps
- [ ] 驗證正確版本被載入
- [ ] 監控效能指標

## 🔍 除錯指南

### 日誌訊息解讀

```log
INFO: Using version from environment: GAP_ANALYSIS_PROMPT_VERSION=2.1.1
INFO: Using active version: 2.1.0
INFO: Using latest version: 2.1.1
INFO: Loaded prompt config: task=gap_analysis, version=2.1.1
```

### 常見問題

**Q: 環境變數設定了但沒生效？**
- 檢查變數名稱格式（大寫、底線分隔）
- 確認容器已重啟
- 查看日誌確認載入順序

**Q: 如何確認使用哪個版本？**
```python
from src.core.simple_prompt_manager import prompt_manager
version = prompt_manager.get_resolved_version("gap_analysis")
print(f"Current version: {version}")
```

**Q: 版本檔案找不到？**
- 確認檔案路徑：`src/prompts/{task}/v{version}.yaml`
- 檢查版本號格式是否正確
- 確認檔案已部署到容器

## 🏗️ 系統架構優勢

### 減少重複程式碼
- 統一版本管理邏輯
- 單一維護點
- 新 API 自動繼承功能

### 提高靈活性
- 所有 API 支援版本切換
- 支援 A/B 測試
- 無需重新部署即可調整

### 簡化維護
- 集中式配置管理
- 標準化錯誤處理
- 一致的日誌格式

## 📚 相關資源

- [GitHub Actions CI/CD 策略](./github-actions-cicd.md)
- [API 文檔](./API.md)
- [CLAUDE.md](../CLAUDE.md) - 專案說明

---

**最後更新**: 2025-08-13
**維護團隊**: AI Resume Advisor DevOps