#!/bin/bash

# Enable Deficit Filling in Azure Container Apps
# Stage 3 of Course Availability Restoration

set -e

echo "================================================"
echo "Stage 3: Enable Deficit Filling Mechanism"
echo "================================================"
echo ""

# Check if user is logged in to Azure
echo "Checking Azure login status..."
if ! az account show &>/dev/null; then
    echo "❌ Not logged in to Azure. Please run: az login"
    exit 1
fi

echo "✅ Azure login confirmed"
echo ""

# Configuration
RESOURCE_GROUP="airesumeadvisorfastapi"
CONTAINER_APP="airesumeadvisor-api-production"

# Show current configuration
echo "📊 Current Environment Variables:"
echo "--------------------------------"
az containerapp show \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --query "properties.template.containers[0].env[?name=='ENABLE_DEFICIT_FILLING' || name=='COURSE_THRESHOLD_SKILL' || name=='COURSE_THRESHOLD_FIELD' || name=='COURSE_THRESHOLD_DEFAULT' || name=='COURSE_MIN_THRESHOLD'].{name:name, value:value}" \
    -o table

echo ""
echo "🔧 Stage 3: Enabling Deficit Filling..."
echo "This will set ENABLE_DEFICIT_FILLING=true"
echo ""

# Prompt for confirmation
read -p "Do you want to proceed? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Operation cancelled"
    exit 1
fi

# Update environment variable
echo "Updating container app configuration..."
az containerapp update \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --set-env-vars \
        ENABLE_DEFICIT_FILLING=true \
    --output none

echo "✅ Deficit filling enabled successfully!"
echo ""

# Show new configuration
echo "📊 New Environment Variables:"
echo "-----------------------------"
az containerapp show \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --query "properties.template.containers[0].env[?name=='ENABLE_DEFICIT_FILLING' || name=='COURSE_THRESHOLD_SKILL' || name=='COURSE_THRESHOLD_FIELD'].{name:name, value:value}" \
    -o table

echo ""
echo "🚀 Deployment Status:"
echo "--------------------"
# Get the latest revision
LATEST_REVISION=$(az containerapp revision list \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --query "[0].name" -o tsv)

echo "Latest revision: $LATEST_REVISION"
echo ""

echo "⏳ Waiting for deployment to stabilize (30 seconds)..."
sleep 30

# Check revision status
REVISION_STATUS=$(az containerapp revision show \
    --name $CONTAINER_APP \
    --resource-group $RESOURCE_GROUP \
    --revision $LATEST_REVISION \
    --query "properties.runningState" -o tsv)

if [ "$REVISION_STATUS" == "Running" ]; then
    echo "✅ Deployment successful! Revision is running."
else
    echo "⚠️  Revision status: $REVISION_STATUS"
fi

echo ""
echo "================================================"
echo "Stage 3 Complete!"
echo "================================================"
echo ""
echo "Next Steps:"
echo "1. Test the API to verify deficit filling is working"
echo "2. Monitor logs for 'Applying deficit filling' messages"
echo "3. Verify course type diversity in responses"
echo "4. If successful, proceed to Stage 4 (adjust thresholds)"
echo ""
echo "To test:"
echo "  python test/scripts/test_production_deficit_filling.py"
echo ""
echo "To rollback:"
echo "  az containerapp update --name $CONTAINER_APP --resource-group $RESOURCE_GROUP --set-env-vars ENABLE_DEFICIT_FILLING=false"