#!/bin/bash
# Script to update Gap Analysis prompt version on Azure Container Apps

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="airesumeadvisorfastapi"
CONTAINER_APP="airesumeadvisor-api-production"
VERSION="${1:-2.1.1}"  # Default to 2.1.1 if not specified

echo -e "${YELLOW}🔄 Updating Gap Analysis Prompt Version to ${VERSION}${NC}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Container App: ${CONTAINER_APP}"
echo ""

# Check if logged in to Azure
if ! az account show &>/dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Please run: az login${NC}"
    exit 1
fi

# Update environment variable
echo -e "${YELLOW}📝 Updating GAP_ANALYSIS_PROMPT_VERSION...${NC}"
if az containerapp update \
    --name "${CONTAINER_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --set-env-vars GAP_ANALYSIS_PROMPT_VERSION="${VERSION}" \
    --output none; then
    echo -e "${GREEN}✅ Environment variable updated successfully${NC}"
else
    echo -e "${RED}❌ Failed to update environment variable${NC}"
    exit 1
fi

# Verify the update
echo -e "${YELLOW}🔍 Verifying configuration...${NC}"
CURRENT_VERSION=$(az containerapp show \
    --name "${CONTAINER_APP}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query "properties.template.containers[0].env[?name=='GAP_ANALYSIS_PROMPT_VERSION'].value | [0]" \
    -o tsv)

if [ "${CURRENT_VERSION}" == "${VERSION}" ]; then
    echo -e "${GREEN}✅ Version confirmed: ${CURRENT_VERSION}${NC}"
else
    echo -e "${RED}❌ Version mismatch! Expected: ${VERSION}, Got: ${CURRENT_VERSION}${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Gap Analysis prompt version successfully updated to ${VERSION}!${NC}"
echo -e "${YELLOW}Note: The container will automatically restart with the new configuration.${NC}"