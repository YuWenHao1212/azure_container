#!/bin/bash
# Pre-push environment configuration check
# This script shows what environment variables will be overwritten in GitHub Actions
# and asks for user confirmation before pushing to main

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Only run this check when pushing to main
if [ "$CURRENT_BRANCH" != "main" ]; then
    exit 0
fi

echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}                    PRE-PUSH CONFIGURATION CHECK                         ${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  You are pushing to main branch. GitHub Actions will deploy with these settings:${NC}"
echo ""

# Function to find active versions (can be multiple for different languages)
find_active_versions() {
  local task=$1
  local dir="src/prompts/$task"
  local versions=""
  
  if [ ! -d "$dir" ]; then
    echo "NOT_FOUND"
    return
  fi
  
  # Find all active versions (including language variants)
  for file in $dir/v*.yaml; do
    if [ -f "$file" ]; then
      if grep -qE 'status:\s*["'\'']?active["'\'']?' "$file" 2>/dev/null; then
        # Extract version from filename
        local version=$(basename "$file" .yaml | sed 's/^v//')
        if [ -n "$versions" ]; then
          versions="$versions, $version"
        else
          versions="$version"
        fi
      fi
    fi
  done
  
  if [ -z "$versions" ]; then
    echo "latest"
  else
    echo "$versions"
  fi
}

# Detect prompt versions (may include multiple language variants)
GAP_VERSIONS=$(find_active_versions "gap_analysis")
KEYWORD_VERSIONS=$(find_active_versions "keyword_extraction")
INDEX_VERSIONS=$(find_active_versions "index_calculation")
FORMAT_VERSIONS=$(find_active_versions "resume_format")
TAILOR_VERSIONS=$(find_active_versions "resume_tailor")

# Set defaults if not found
GAP_VERSIONS=${GAP_VERSIONS:-"2.1.8"}
KEYWORD_VERSIONS=${KEYWORD_VERSIONS:-"latest"}
INDEX_VERSIONS=${INDEX_VERSIONS:-"latest"}
FORMAT_VERSIONS=${FORMAT_VERSIONS:-"latest"}
TAILOR_VERSIONS=${TAILOR_VERSIONS:-"latest"}

# Display configuration that will be deployed
echo -e "${BLUE}${BOLD}📝 Active Prompt Versions (from YAML files):${NC}"
echo "┌─────────────────────────────────────┬────────────────────────────────────┐"
echo "│ Task                                │ Active Versions                    │"
echo "├─────────────────────────────────────┼────────────────────────────────────┤"
printf "│ %-35s │ ${GREEN}%-34s${NC} │\n" "Gap Analysis" "$GAP_VERSIONS"
printf "│ %-35s │ ${GREEN}%-34s${NC} │\n" "Keyword Extraction" "$KEYWORD_VERSIONS"
printf "│ %-35s │ ${GREEN}%-34s${NC} │\n" "Index Calculation" "$INDEX_VERSIONS"
printf "│ %-35s │ ${GREEN}%-34s${NC} │\n" "Resume Format" "$FORMAT_VERSIONS"
printf "│ %-35s │ ${GREEN}%-34s${NC} │\n" "Resume Tailor" "$TAILOR_VERSIONS"
echo "└─────────────────────────────────────┴────────────────────────────────────┘"
echo ""
echo -e "${CYAN}ℹ️  Note: System supports multiple active versions for different languages${NC}"
echo -e "${CYAN}   The prompt manager will select the appropriate version based on request language${NC}"
echo ""

echo -e "${BLUE}${BOLD}🤖 LLM Model Configuration (hardcoded in CI/CD):${NC}"
echo "┌─────────────────────────────────────┬──────────────┐"
echo "│ Model Setting                       │ Value        │"
echo "├─────────────────────────────────────┼──────────────┤"
printf "│ %-35s │ ${CYAN}%-12s${NC} │\n" "LLM_MODEL_KEYWORDS" "gpt-4.1-mini"
printf "│ %-35s │ ${CYAN}%-12s${NC} │\n" "LLM_MODEL_GAP_ANALYSIS" "gpt-4.1"
printf "│ %-35s │ ${CYAN}%-12s${NC} │\n" "LLM_MODEL_RESUME_FORMAT" "gpt-4.1"
printf "│ %-35s │ ${CYAN}%-12s${NC} │\n" "LLM_MODEL_RESUME_TAILOR" "gpt-4.1"
echo "└─────────────────────────────────────┴──────────────┘"
echo ""

echo -e "${BLUE}${BOLD}🔑 GitHub Secrets Status (will be injected):${NC}"
echo "┌─────────────────────────────────────┬──────────────┐"
echo "│ Secret Name                         │ Status       │"
echo "├─────────────────────────────────────┼──────────────┤"

# Check if we can access GitHub CLI
if command -v gh &> /dev/null; then
    # Try to check secret existence (requires gh auth)
    SECRETS_LIST=$(gh secret list 2>/dev/null || echo "")
    
    if [ -n "$SECRETS_LIST" ]; then
        # Check each required secret
        REQUIRED_SECRETS=(
            "AZURE_OPENAI_API_KEY"
            "AZURE_OPENAI_ENDPOINT"
            "JWT_SECRET_KEY"
            "CONTAINER_APP_API_KEY"
            "AZURE_CLIENT_ID"
            "AZURE_CLIENT_SECRET"
            "AZURE_TENANT_ID"
            "AZURE_SUBSCRIPTION_ID"
        )
        
        for secret in "${REQUIRED_SECRETS[@]}"; do
            if echo "$SECRETS_LIST" | grep -q "$secret"; then
                printf "│ %-35s │ ${GREEN}✅ Set${NC}       │\n" "$secret"
            else
                printf "│ %-35s │ ${RED}❌ Missing${NC}   │\n" "$secret"
            fi
        done
    else
        echo "│ ${YELLOW}GitHub CLI available but not authenticated${NC}    │"
        echo "│ Run 'gh auth login' to check secrets status   │"
    fi
else
    echo "│ ${YELLOW}Install GitHub CLI (gh) to check secrets${NC}      │"
    echo "│ Secrets will be injected by GitHub Actions    │"
fi
echo "└─────────────────────────────────────┴──────────────┘"
echo ""

echo -e "${BLUE}${BOLD}🚀 Deployment Target:${NC}"
echo "┌─────────────────────────────────────┬──────────────────────────────────────┐"
printf "│ %-35s │ %-36s │\n" "Environment" "Production"
printf "│ %-35s │ %-36s │\n" "Container App" "airesumeadvisor-api-production"
printf "│ %-35s │ %-36s │\n" "Resource Group" "airesumeadvisorfastapi"
printf "│ %-35s │ %-36s │\n" "Region" "Japan East"
echo "└─────────────────────────────────────┴──────────────────────────────────────┘"
echo ""

# Check for potential issues
WARNINGS=()

# Check if any prompt version is "NOT_FOUND"
if [[ "$GAP_VERSIONS" == "NOT_FOUND" ]] || [[ "$KEYWORD_VERSIONS" == "NOT_FOUND" ]] || 
   [[ "$INDEX_VERSIONS" == "NOT_FOUND" ]] || [[ "$FORMAT_VERSIONS" == "NOT_FOUND" ]] || 
   [[ "$TAILOR_VERSIONS" == "NOT_FOUND" ]]; then
    WARNINGS+=("Some prompt directories not found - will use defaults")
fi

# Check for no active versions (all should have at least one)
for task in gap_analysis keyword_extraction resume_format; do
    dir="src/prompts/$task"
    if [ -d "$dir" ]; then
        active_count=$(grep -l 'status:.*active' $dir/*.yaml 2>/dev/null | wc -l)
        if [ "$active_count" -eq 0 ]; then
            WARNINGS+=("No active versions found in $task - will use latest")
        fi
    fi
done

# Display warnings if any
if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}⚠️  Warnings:${NC}"
    for warning in "${WARNINGS[@]}"; do
        echo -e "  ${YELLOW}• $warning${NC}"
    done
    echo ""
fi

# Show commit info
echo -e "${BLUE}${BOLD}📦 Commit Information:${NC}"
LATEST_COMMIT=$(git log -1 --oneline)
echo "  Latest commit: $LATEST_COMMIT"
CHANGED_FILES=$(git diff --name-only HEAD~ 2>/dev/null | wc -l)
echo "  Changed files: $CHANGED_FILES"
echo ""

# Ask for confirmation
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${MAGENTA}${BOLD}Do you want to proceed with push to main? This will trigger deployment.${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -n "Type 'yes' to continue or 'no' to cancel: "
read -r response

if [[ "$response" != "yes" ]]; then
    echo ""
    echo -e "${RED}❌ Push cancelled by user${NC}"
    echo "You can make changes and try again later."
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Configuration confirmed. Proceeding with push...${NC}"
echo ""

# Continue with the push
exit 0