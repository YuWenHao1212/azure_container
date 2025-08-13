#!/bin/bash
# Script to update Gap Analysis prompt version on Azure Container Apps
# Usage: ./scripts/update-gap-version-azure.sh [version]
# Example: ./scripts/update-gap-version-azure.sh 2.1.0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="airesumeadvisorfastapi"
CONTAINER_APP="airesumeadvisor-api-production"
VERSION="${1:-2.1.1}"  # Default to 2.1.1 if not specified

# Function to print with timestamp
print_with_time() {
    echo -e "${1}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $2"
}

# Function to check version with retry
check_version_with_retry() {
    local expected_version=$1
    local max_attempts=10
    local wait_time=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_with_time "$BLUE" "Attempt $attempt/$max_attempts: Checking version..."
        
        # Get current version from Azure
        CURRENT_VERSION=$(az containerapp show \
            --name "${CONTAINER_APP}" \
            --resource-group "${RESOURCE_GROUP}" \
            --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
            -o tsv 2>/dev/null)
        
        if [ "${CURRENT_VERSION}" == "${expected_version}" ]; then
            print_with_time "$GREEN" "✅ Version confirmed: ${CURRENT_VERSION}"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                print_with_time "$RED" "❌ Version verification failed after $max_attempts attempts"
                print_with_time "$RED" "   Expected: ${expected_version}, Got: ${CURRENT_VERSION}"
                return 1
            else
                print_with_time "$YELLOW" "   Current version: ${CURRENT_VERSION:-'not set'}, waiting ${wait_time}s..."
                sleep $wait_time
                ((attempt++))
            fi
        fi
    done
}

# Main script starts here
echo ""
print_with_time "$YELLOW" "🔄 Gap Analysis Prompt Version Update Script"
echo -e "${YELLOW}================================================${NC}"
echo "Target Version: ${VERSION}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Container App: ${CONTAINER_APP}"
echo -e "${YELLOW}================================================${NC}"
echo ""

# Step 1: Check if logged in to Azure
print_with_time "$BLUE" "📌 Step 1: Checking Azure login status..."
if ! az account show &>/dev/null; then
    print_with_time "$RED" "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi
ACCOUNT_NAME=$(az account show --query "user.name" -o tsv)
print_with_time "$GREEN" "✅ Logged in as: ${ACCOUNT_NAME}"
echo ""

# Step 2: Check current version before update
print_with_time "$BLUE" "📌 Step 2: Checking current version..."
BEFORE_VERSION=$(az containerapp show \
    --name "${CONTAINER_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
    -o tsv 2>/dev/null)

if [ -z "${BEFORE_VERSION}" ]; then
    print_with_time "$YELLOW" "⚠️  No version currently set (will use default from YAML)"
else
    print_with_time "$BLUE" "📍 Current version: ${BEFORE_VERSION}"
fi
echo ""

# Step 3: Check if the target version YAML file exists locally
print_with_time "$BLUE" "📌 Step 3: Verifying prompt file exists..."
PROMPT_FILE="src/prompts/gap_analysis/v${VERSION}.yaml"
if [ -f "${PROMPT_FILE}" ]; then
    print_with_time "$GREEN" "✅ Found prompt file: ${PROMPT_FILE}"
else
    print_with_time "$YELLOW" "⚠️  Warning: Local file ${PROMPT_FILE} not found"
    print_with_time "$YELLOW" "   Make sure the version exists in the deployed container"
fi
echo ""

# Step 4: Update environment variable
print_with_time "$BLUE" "📌 Step 4: Updating GAP_ANALYSIS_PROMPT_VERSION to ${VERSION}..."
if az containerapp update \
    --name "${CONTAINER_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --set-env-vars GAP_ANALYSIS_PROMPT_VERSION="${VERSION}" \
    --output none; then
    print_with_time "$GREEN" "✅ Environment variable update command executed successfully"
else
    print_with_time "$RED" "❌ Failed to update environment variable"
    exit 1
fi
echo ""

# Step 5: Wait for container to restart
print_with_time "$BLUE" "📌 Step 5: Waiting for container to restart..."
print_with_time "$YELLOW" "⏳ Container typically takes 30-60 seconds to restart with new configuration"
echo ""

# Step 6: Verify the update with retry
print_with_time "$BLUE" "📌 Step 6: Verifying version update..."
if check_version_with_retry "${VERSION}"; then
    echo ""
    print_with_time "$GREEN" "🎉 SUCCESS! Gap Analysis prompt version updated:"
    echo -e "${GREEN}   ${BEFORE_VERSION:-'(default)'} → ${VERSION}${NC}"
    echo ""
    
    # Step 7: Test the endpoint (optional)
    print_with_time "$BLUE" "📌 Step 7: Testing health endpoint..."
    HEALTH_URL="https://airesumeadvisor-api-production.calmisland-ea7fe91e.japaneast.azurecontainerapps.io/health"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null)
    
    if [ "${HTTP_CODE}" == "200" ]; then
        print_with_time "$GREEN" "✅ Health check passed (HTTP ${HTTP_CODE})"
    else
        print_with_time "$YELLOW" "⚠️  Health check returned HTTP ${HTTP_CODE}"
    fi
    
    echo ""
    print_with_time "$BLUE" "📝 Summary:"
    echo "   • Version updated to: ${VERSION}"
    echo "   • Container has restarted"
    echo "   • API is ready to use with new prompt version"
    echo ""
    print_with_time "$GREEN" "✅ Update completed successfully!"
else
    echo ""
    print_with_time "$RED" "❌ Update verification failed!"
    print_with_time "$YELLOW" "💡 Troubleshooting tips:"
    echo "   1. Check if the container is still restarting:"
    echo "      az containerapp replica list --name ${CONTAINER_APP} --resource-group ${RESOURCE_GROUP}"
    echo "   2. Check container logs:"
    echo "      az containerapp logs show --name ${CONTAINER_APP} --resource-group ${RESOURCE_GROUP}"
    echo "   3. Manually verify the environment variable:"
    echo "      az containerapp show --name ${CONTAINER_APP} --resource-group ${RESOURCE_GROUP} --query \"properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION']\" -o table"
    exit 1
fi