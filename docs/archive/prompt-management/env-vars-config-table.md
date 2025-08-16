# 環境變數配置表 (Environment Variables Configuration Table)

> 最後更新：2025-08-16  
> 用途：CI/CD 部署前確認環境變數設定值

## 📋 環境變數設定總表

### 🎯 Prompt 版本設定
| 環境變數 | CI/CD 邏輯 | 預期值 | 說明 |
|---------|-----------|--------|------|
| `GAP_ANALYSIS_PROMPT_VERSION` | 偵測 active 或預設 `2.1.8` | **2.1.8** | src/prompts/gap_analysis/v2.1.8.yaml (active) |
| `KEYWORD_EXTRACTION_PROMPT_VERSION` | 偵測 active 或預設 `latest` | **latest** | 使用最新版本 |
| `INDEX_CALCULATION_PROMPT_VERSION` | 偵測 active 或預設 `latest` | **latest** | 使用最新版本 |
| `RESUME_FORMAT_PROMPT_VERSION` | 偵測 active 或預設 `latest` | **latest** | 使用最新版本 |
| `RESUME_TAILOR_PROMPT_VERSION` | 偵測 active 或預設 `latest` | **latest** | 使用最新版本 |

### 🤖 LLM 模型設定（硬編碼）
| 環境變數 | 設定值 | 說明 |
|---------|--------|------|
| `LLM_MODEL_KEYWORDS` | **gpt-4.1-mini** | 關鍵字提取使用小模型 |
| `LLM_MODEL_GAP_ANALYSIS` | **gpt-4.1** | Gap Analysis 使用大模型 |
| `LLM_MODEL_RESUME_FORMAT` | **gpt-4.1** | 履歷格式化使用大模型 |
| `LLM_MODEL_RESUME_TAILOR` | **gpt-4.1** | 履歷客製化使用大模型 |

### ⚙️ 系統設定（硬編碼）
| 環境變數 | 設定值 | 說明 |
|---------|--------|------|
| `ENVIRONMENT` | **production** | 生產環境 |
| `LOG_LEVEL` | **INFO** | 日誌級別 |
| `MONITORING_ENABLED` | **false** | 重度監控關閉 |
| `LIGHTWEIGHT_MONITORING` | **true** | 輕量監控開啟 |
| `USE_RULE_BASED_DETECTOR` | **true** | 使用規則語言檢測 |

### 🔐 Azure OpenAI 設定（來自 GitHub Secrets）
| 環境變數 | 來源 | 實際值 |
|---------|------|--------|
| `AZURE_OPENAI_ENDPOINT` | `${{ secrets.AZURE_OPENAI_ENDPOINT }}` | https://airesumeadvisor.openai.azure.com |
| `AZURE_OPENAI_API_KEY` | `${{ secrets.AZURE_OPENAI_API_KEY }}` | [隱藏] |
| `AZURE_OPENAI_API_VERSION` | 硬編碼 | **2025-01-01-preview** |
| `AZURE_OPENAI_GPT4_DEPLOYMENT` | 硬編碼 | **gpt-4.1-japan** |
| `GPT41_MINI_JAPANEAST_DEPLOYMENT` | 硬編碼 | **gpt-4-1-mini-japaneast** |

### 🔌 Embedding 服務（混合設定）
| 環境變數 | 來源 | 說明 |
|---------|------|------|
| `EMBEDDING_ENDPOINT` | `${{ secrets.EMBEDDING_ENDPOINT }}` | embedding-3-large 端點 |
| `EMBEDDING_API_KEY` | `${{ secrets.AZURE_OPENAI_API_KEY }}` | 共用 API Key |
| `COURSE_EMBEDDING_ENDPOINT` | `${{ secrets.COURSE_EMBEDDING_ENDPOINT }}` | embedding-3-small 端點 |
| `COURSE_EMBEDDING_API_KEY` | `${{ secrets.AZURE_OPENAI_API_KEY }}` | 共用 API Key |

### 🔒 安全設定（來自 GitHub Secrets）
| 環境變數 | 來源 | 說明 |
|---------|------|------|
| `JWT_SECRET_KEY` | `${{ secrets.JWT_SECRET_KEY }}` | JWT 簽名金鑰 |
| `CONTAINER_APP_API_KEY` | `${{ secrets.CONTAINER_APP_API_KEY }}` | API 認證金鑰 |

### 🌐 CORS 設定（硬編碼）
| 環境變數 | 設定值 |
|---------|--------|
| `CORS_ORIGINS` | **https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com** |

---

## 🔍 CI/CD 部署前檢查清單

### 1. Prompt 版本確認
```bash
# 執行這個腳本來預覽將會使用的版本
bash -c '
find_active_version() {
  local task=$1
  local dir="src/prompts/$task"
  
  for file in $dir/v*.yaml 2>/dev/null; do
    if [ -f "$file" ]; then
      if grep -qE "status:\s*[\"'\'']?active[\"'\'']?" "$file"; then
        basename "$file" .yaml | sed "s/^v//"
        return
      fi
    fi
  done
  echo ""
}

echo "=== Prompt 版本預覽 ==="
echo "Gap Analysis: $(find_active_version gap_analysis || echo "2.1.8 (預設)")"
echo "Keyword Extraction: $(find_active_version keyword_extraction || echo "latest (預設)")"
echo "Index Calculation: $(find_active_version index_calculation || echo "latest (預設)")"
echo "Resume Format: $(find_active_version resume_format || echo "latest (預設)")"
echo "Resume Tailor: $(find_active_version resume_tailor || echo "latest (預設)")"
'
```

### 2. GitHub Secrets 確認
前往 GitHub → Settings → Secrets and variables → Actions，確認以下 secrets 存在：
- [ ] AZURE_OPENAI_ENDPOINT
- [ ] AZURE_OPENAI_API_KEY
- [ ] EMBEDDING_ENDPOINT
- [ ] COURSE_EMBEDDING_ENDPOINT
- [ ] JWT_SECRET_KEY
- [ ] CONTAINER_APP_API_KEY
- [ ] AZURE_CLIENT_ID
- [ ] AZURE_CLIENT_SECRET
- [ ] AZURE_TENANT_ID
- [ ] AZURE_SUBSCRIPTION_ID

### 3. CI/CD 檔案位置確認
```bash
# 關鍵設定位置
檔案：.github/workflows/ci-cd-main.yml

第 8-12 行：基本設定
第 287-298 行：Prompt 版本偵測邏輯
第 341-370 行：環境變數設定
```

---

## 📝 快速修改指南

### 修改 Prompt 版本
```yaml
# .github/workflows/ci-cd-main.yml 第 294-298 行
echo "gap-analysis-version=${GAP_VERSION:-2.1.8}" >> $GITHUB_OUTPUT  # 改這裡的預設值
```

### 修改 LLM 模型
```yaml
# .github/workflows/ci-cd-main.yml 第 358-361 行
LLM_MODEL_KEYWORDS=gpt-4.1-mini \      # 改成其他模型
LLM_MODEL_GAP_ANALYSIS=gpt-4.1 \       # 改成其他模型
```

### 修改系統設定
```yaml
# .github/workflows/ci-cd-main.yml 第 342-345 行
ENVIRONMENT=production \                # 可改為 development, staging
LOG_LEVEL=INFO \                        # 可改為 DEBUG, WARNING, ERROR
```

---

## 🚀 部署前最終確認腳本

創建 `scripts/pre-deploy-check.sh`：
```bash
#!/bin/bash

echo "================================================"
echo "         CI/CD 部署前環境變數確認"
echo "================================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 檢查 prompt 版本
echo -e "${YELLOW}📝 Prompt 版本設定：${NC}"
for task in gap_analysis keyword_extraction index_calculation resume_format resume_tailor; do
  dir="src/prompts/$task"
  active_version=""
  
  if [ -d "$dir" ]; then
    for file in $dir/v*.yaml; do
      if [ -f "$file" ] && grep -qE 'status:\s*["'\'']?active["'\'']?' "$file" 2>/dev/null; then
        active_version=$(basename "$file" .yaml | sed 's/^v//')
        break
      fi
    done
  fi
  
  task_upper=$(echo $task | tr '[:lower:]' '[:upper:]' | tr '-' '_')
  if [ -n "$active_version" ]; then
    echo -e "  ${task_upper}_PROMPT_VERSION: ${GREEN}${active_version}${NC} (active)"
  else
    default="latest"
    [ "$task" = "gap_analysis" ] && default="2.1.8"
    echo -e "  ${task_upper}_PROMPT_VERSION: ${YELLOW}${default}${NC} (預設)"
  fi
done

echo ""
echo -e "${YELLOW}🤖 LLM 模型設定：${NC}"
echo "  LLM_MODEL_KEYWORDS: gpt-4.1-mini"
echo "  LLM_MODEL_GAP_ANALYSIS: gpt-4.1"
echo "  LLM_MODEL_RESUME_FORMAT: gpt-4.1"
echo "  LLM_MODEL_RESUME_TAILOR: gpt-4.1"

echo ""
echo -e "${YELLOW}⚙️ 系統設定：${NC}"
echo "  ENVIRONMENT: production"
echo "  LOG_LEVEL: INFO"
echo "  MONITORING_ENABLED: false"
echo "  LIGHTWEIGHT_MONITORING: true"

echo ""
echo -e "${YELLOW}🔐 Secrets 檢查：${NC}"
# 這裡只能檢查 .env 檔案是否有設定（本地）
if [ -f .env ]; then
  for secret in AZURE_OPENAI_API_KEY JWT_SECRET_KEY CONTAINER_APP_API_KEY; do
    if grep -q "^${secret}=" .env; then
      echo -e "  ${secret}: ${GREEN}✓ 本地已設定${NC}"
    else
      echo -e "  ${secret}: ${YELLOW}⚠ 本地未設定${NC}"
    fi
  done
else
  echo "  .env 檔案不存在（CI/CD 會使用 GitHub Secrets）"
fi

echo ""
echo "================================================"
echo -e "${GREEN}請確認以上設定正確後再執行部署！${NC}"
echo "================================================"
```

---

## 📊 版本變更追蹤表

| 日期 | 變更項目 | 舊值 | 新值 | 負責人 |
|------|---------|------|------|--------|
| 2025-08-16 | GAP_ANALYSIS_PROMPT_VERSION 預設值 | 2.1.1 | 2.1.8 | Claude |
| 2025-08-16 | 修正 active 版本偵測邏輯 | 不支援引號 | 支援引號 | Claude |
| | | | | |

---

## 🔗 相關資源

- [環境變數管理指南](./environment-variables-management.md)
- [Prompt 版本管理規則](./prompt-version-rules.md)
- [查看實際值指南](./view-actual-env-values.md)
- [CI/CD 配置](.github/workflows/ci-cd-main.yml)