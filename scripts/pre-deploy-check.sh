#!/bin/bash
# Pre-deployment environment variables check script
# Usage: ./scripts/pre-deploy-check.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}         CI/CD 部署前環境變數確認表${NC}"
echo -e "${CYAN}================================================${NC}"
echo ""

# Function to find active version
find_active_version() {
  local task=$1
  local dir="src/prompts/$task"
  
  if [ ! -d "$dir" ]; then
    echo ""
    return
  fi
  
  for file in $dir/v*.yaml; do
    if [ -f "$file" ]; then
      if grep -qE 'status:\s*["'\'']?active["'\'']?' "$file" 2>/dev/null; then
        basename "$file" .yaml | sed 's/^v//'
        return
      fi
    fi
  done
  
  echo ""
}

# 1. Prompt Versions
echo -e "${YELLOW}📝 Prompt 版本設定：${NC}"
echo "┌─────────────────────────────────────┬──────────────┬────────────┐"
echo "│ 環境變數                            │ 預期值       │ 狀態       │"
echo "├─────────────────────────────────────┼──────────────┼────────────┤"

# Check each prompt task
tasks=("gap_analysis" "keyword_extraction" "index_calculation" "resume_format" "resume_tailor")
defaults=("2.1.8" "latest" "latest" "latest" "latest")

for i in "${!tasks[@]}"; do
  task="${tasks[$i]}"
  default="${defaults[$i]}"
  active_version=$(find_active_version "$task")
  
  # Convert task name to env var format
  env_name=$(echo "$task" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
  env_name="${env_name}_PROMPT_VERSION"
  
  if [ -n "$active_version" ]; then
    printf "│ %-35s │ ${GREEN}%-12s${NC} │ ${GREEN}active${NC}      │\n" "$env_name" "$active_version"
  else
    printf "│ %-35s │ ${YELLOW}%-12s${NC} │ ${YELLOW}預設${NC}        │\n" "$env_name" "$default"
  fi
done

echo "└─────────────────────────────────────┴──────────────┴────────────┘"
echo ""

# 2. LLM Models
echo -e "${YELLOW}🤖 LLM 模型設定（硬編碼）：${NC}"
echo "┌─────────────────────────────────────┬──────────────────────┐"
echo "│ 環境變數                            │ 設定值               │"
echo "├─────────────────────────────────────┼──────────────────────┤"
echo "│ LLM_MODEL_KEYWORDS                  │ gpt-4.1-mini         │"
echo "│ LLM_MODEL_GAP_ANALYSIS              │ gpt-4.1              │"
echo "│ LLM_MODEL_RESUME_FORMAT             │ gpt-4.1              │"
echo "│ LLM_MODEL_RESUME_TAILOR             │ gpt-4.1              │"
echo "└─────────────────────────────────────┴──────────────────────┘"
echo ""

# 3. System Settings
echo -e "${YELLOW}⚙️  系統設定（硬編碼）：${NC}"
echo "┌─────────────────────────────────────┬──────────────────────┐"
echo "│ 環境變數                            │ 設定值               │"
echo "├─────────────────────────────────────┼──────────────────────┤"
echo "│ ENVIRONMENT                         │ production           │"
echo "│ LOG_LEVEL                           │ INFO                 │"
echo "│ MONITORING_ENABLED                  │ false                │"
echo "│ LIGHTWEIGHT_MONITORING              │ true                 │"
echo "│ USE_RULE_BASED_DETECTOR             │ true                 │"
echo "└─────────────────────────────────────┴──────────────────────┘"
echo ""

# 4. Azure Settings
echo -e "${YELLOW}☁️  Azure OpenAI 設定：${NC}"
echo "┌─────────────────────────────────────┬──────────────────────────────┐"
echo "│ 環境變數                            │ 來源/值                      │"
echo "├─────────────────────────────────────┼──────────────────────────────┤"
echo "│ AZURE_OPENAI_ENDPOINT               │ \${{ secrets.* }}            │"
echo "│ AZURE_OPENAI_API_KEY                │ \${{ secrets.* }} [隱藏]     │"
echo "│ AZURE_OPENAI_API_VERSION            │ 2025-01-01-preview           │"
echo "│ AZURE_OPENAI_GPT4_DEPLOYMENT        │ gpt-4.1-japan                │"
echo "│ GPT41_MINI_JAPANEAST_DEPLOYMENT     │ gpt-4-1-mini-japaneast       │"
echo "└─────────────────────────────────────┴──────────────────────────────┘"
echo ""

# 5. Check GitHub Secrets (if gh CLI is available)
echo -e "${YELLOW}🔐 GitHub Secrets 檢查：${NC}"
if command -v gh &> /dev/null; then
  echo "檢查 GitHub Secrets 是否存在..."
  secrets=("AZURE_OPENAI_ENDPOINT" "AZURE_OPENAI_API_KEY" "EMBEDDING_ENDPOINT" 
           "COURSE_EMBEDDING_ENDPOINT" "JWT_SECRET_KEY" "CONTAINER_APP_API_KEY")
  
  for secret in "${secrets[@]}"; do
    if gh secret list 2>/dev/null | grep -q "^$secret"; then
      echo -e "  ${secret}: ${GREEN}✓ 已設定${NC}"
    else
      echo -e "  ${secret}: ${RED}✗ 未設定${NC}"
    fi
  done
else
  echo "  GitHub CLI 未安裝，無法檢查 Secrets"
  echo "  請手動確認 GitHub Settings → Secrets 中已設定所有必要的 secrets"
fi
echo ""

# 6. Summary
echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}                    摘要${NC}"
echo -e "${CYAN}================================================${NC}"

# Count active versions
active_count=0
for task in "${tasks[@]}"; do
  if [ -n "$(find_active_version "$task")" ]; then
    ((active_count++))
  fi
done

echo -e "✅ 找到 ${GREEN}${active_count}${NC} 個 active prompt 版本"
echo -e "📍 CI/CD 配置檔案：${BLUE}.github/workflows/ci-cd-main.yml${NC}"
echo -e "📍 環境變數設定行：第 ${BLUE}341-370${NC} 行"
echo -e "📍 版本偵測邏輯行：第 ${BLUE}287-298${NC} 行"
echo ""

# Warning about override
echo -e "${YELLOW}⚠️  重要提醒：${NC}"
echo "1. CI/CD 部署會完全覆蓋 Azure Container Apps 上的所有環境變數"
echo "2. 若要永久修改，必須編輯 .github/workflows/ci-cd-main.yml"
echo "3. Azure Portal 或 CLI 的修改只是臨時的"
echo ""

# Final confirmation
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  請確認以上設定正確後再執行 git push 部署！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Optional: Show diff preview
read -p "是否要查看與當前 Azure 設定的差異？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo -e "${BLUE}正在獲取當前 Azure 設定...${NC}"
  
  # Get current Azure settings
  current_gap=$(az containerapp show \
    --name airesumeadvisor-api-production \
    --resource-group airesumeadvisorfastapi \
    --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
    -o tsv 2>/dev/null)
  
  if [ -n "$current_gap" ]; then
    expected_gap=$(find_active_version "gap_analysis")
    [ -z "$expected_gap" ] && expected_gap="2.1.8"
    
    echo "GAP_ANALYSIS_PROMPT_VERSION:"
    echo "  當前 Azure: $current_gap"
    echo "  下次部署: $expected_gap"
    
    if [ "$current_gap" != "$expected_gap" ]; then
      echo -e "  ${YELLOW}⚠️ 版本將會變更${NC}"
    else
      echo -e "  ${GREEN}✓ 版本不變${NC}"
    fi
  else
    echo "無法連接到 Azure（可能需要先執行 az login）"
  fi
fi

echo ""