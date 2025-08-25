#!/bin/bash

# Script to update LLM2_DEBUG_MODE environment variable in Azure Container Apps
# Usage: ./scripts/update-llm2-debug-mode.sh [true|false]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default value
DEBUG_MODE="${1:-true}"

# Validate input
if [[ "$DEBUG_MODE" != "true" && "$DEBUG_MODE" != "false" ]]; then
    echo -e "${RED}Error: Invalid value. Use 'true' or 'false'${NC}"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}                    LLM2 DEBUG MODE CONFIGURATION                          ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Configuration
RESOURCE_GROUP="airesumeadvisorfastapi"
CONTAINER_APP="airesumeadvisor-api-production"

echo -e "\n${YELLOW}📍 Target Environment:${NC}"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Container App:  $CONTAINER_APP"
echo "   Setting:        LLM2_DEBUG_MODE = $DEBUG_MODE"

# Check current value
echo -e "\n${YELLOW}🔍 Checking current value...${NC}"
CURRENT_VALUE=$(az containerapp show \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.template.containers[0].env[?name=='LLM2_DEBUG_MODE'].value | [0]" \
    -o tsv 2>/dev/null || echo "not_set")

if [ "$CURRENT_VALUE" == "not_set" ] || [ -z "$CURRENT_VALUE" ]; then
    echo "   Current value: <not set>"
else
    echo "   Current value: $CURRENT_VALUE"
fi

# Update environment variable
echo -e "\n${YELLOW}🔧 Updating environment variable...${NC}"

# Get all current environment variables
CURRENT_ENV=$(az containerapp show \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.template.containers[0].env" \
    -o json)

# Check if LLM2_DEBUG_MODE exists
if echo "$CURRENT_ENV" | grep -q '"name": "LLM2_DEBUG_MODE"'; then
    # Update existing variable
    echo "   Updating existing LLM2_DEBUG_MODE..."
    
    # Update the container app with the new value
    az containerapp update \
        --name "$CONTAINER_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --set-env-vars "LLM2_DEBUG_MODE=$DEBUG_MODE" \
        --output none
else
    # Add new variable
    echo "   Adding new LLM2_DEBUG_MODE..."
    
    # Add the environment variable
    az containerapp update \
        --name "$CONTAINER_APP" \
        --resource-group "$RESOURCE_GROUP" \
        --set-env-vars "LLM2_DEBUG_MODE=$DEBUG_MODE" \
        --output none
fi

# Verify the update
echo -e "\n${YELLOW}✅ Verifying update...${NC}"
NEW_VALUE=$(az containerapp show \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.template.containers[0].env[?name=='LLM2_DEBUG_MODE'].value | [0]" \
    -o tsv)

if [ "$NEW_VALUE" == "$DEBUG_MODE" ]; then
    echo -e "   ${GREEN}✅ Successfully updated LLM2_DEBUG_MODE to: $DEBUG_MODE${NC}"
else
    echo -e "   ${RED}❌ Failed to update LLM2_DEBUG_MODE${NC}"
    exit 1
fi

# Show revision status
echo -e "\n${YELLOW}📊 Revision Status:${NC}"
LATEST_REVISION=$(az containerapp revision list \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].name" \
    -o tsv)

echo "   Latest revision: $LATEST_REVISION"
echo "   Status: Active"

echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ LLM2_DEBUG_MODE configuration complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${YELLOW}📝 Usage Notes:${NC}"
echo "   • When DEBUG_MODE=true, fallback will show diagnostic HTML"
echo "   • When DEBUG_MODE=false, fallback will use original content (production)"
echo "   • Changes take effect immediately after container restart"
echo ""
echo "   To disable debug mode for production:"
echo "   ${BLUE}./scripts/update-llm2-debug-mode.sh false${NC}"
echo ""