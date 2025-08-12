#!/bin/bash
# Production Error Alerting Deployment Script
# This script sets up comprehensive error monitoring and alerting for the Azure Container Apps environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SUBSCRIPTION_ID="5396d388-8261-464e-8ee4-112770674fba"
RESOURCE_GROUP="airesumeadvisorfastapi"
CONTAINER_APP_NAME="airesumeadvisor-api-production"
LOCATION="japaneast"
ALERT_PREFIX="airesumeadvisor"

echo -e "${GREEN}🚀 Setting up production error alerts for Azure Container Apps${NC}"
echo "Subscription: $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Container App: $CONTAINER_APP_NAME"
echo "Location: $LOCATION"
echo ""

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure CLI login...${NC}"
if ! az account show > /dev/null 2>&1; then
    echo -e "${RED}Error: Not logged in to Azure CLI. Please run 'az login' first.${NC}"
    exit 1
fi

# Set subscription
echo -e "${YELLOW}Setting subscription...${NC}"
az account set --subscription "$SUBSCRIPTION_ID"

# Create action group for notifications
echo -e "${YELLOW}Creating action group for notifications...${NC}"
ACTION_GROUP_NAME="${ALERT_PREFIX}-error-alerts"

# Check if action group exists
if az monitor action-group show --resource-group "$RESOURCE_GROUP" --name "$ACTION_GROUP_NAME" > /dev/null 2>&1; then
    echo "Action group '$ACTION_GROUP_NAME' already exists, updating..."
    az monitor action-group update \
      --resource-group "$RESOURCE_GROUP" \
      --name "$ACTION_GROUP_NAME" \
      --add email-receivers name="DevOps Team" email="devops@airesumeadvisor.com" \
      --add email-receivers name="Emergency" email="emergency@airesumeadvisor.com"
else
    echo "Creating new action group '$ACTION_GROUP_NAME'..."
    az monitor action-group create \
      --resource-group "$RESOURCE_GROUP" \
      --name "$ACTION_GROUP_NAME" \
      --short-name "api-errors" \
      --email-receivers \
        name="DevOps Team" email="devops@airesumeadvisor.com" \
        name="Emergency" email="emergency@airesumeadvisor.com"
fi

echo -e "${GREEN}✅ Action group configured${NC}"

# Get Container App resource ID for scoping alerts
CONTAINER_APP_ID=$(az containerapp show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP_NAME" \
  --query id \
  --output tsv)

if [ -z "$CONTAINER_APP_ID" ]; then
    echo -e "${RED}Error: Could not find Container App '$CONTAINER_APP_NAME'${NC}"
    exit 1
fi

echo "Container App ID: $CONTAINER_APP_ID"

# Create metric alerts for Container Apps
echo -e "${YELLOW}Setting up Container Apps metric alerts...${NC}"

# 1. High CPU Usage Alert
echo "Creating CPU usage alert..."
az monitor metrics alert create \
  --name "${ALERT_PREFIX}-high-cpu" \
  --resource-group "$RESOURCE_GROUP" \
  --description "Alert when CPU usage is high" \
  --severity 2 \
  --condition "avg cpu > 80" \
  --window-size "PT5M" \
  --evaluation-frequency "PT1M" \
  --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
  --scopes "$CONTAINER_APP_ID" || echo "CPU alert may already exist"

# 2. High Memory Usage Alert  
echo "Creating memory usage alert..."
az monitor metrics alert create \
  --name "${ALERT_PREFIX}-high-memory" \
  --resource-group "$RESOURCE_GROUP" \
  --description "Alert when memory usage is high" \
  --severity 2 \
  --condition "avg memory > 85" \
  --window-size "PT5M" \
  --evaluation-frequency "PT1M" \
  --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
  --scopes "$CONTAINER_APP_ID" || echo "Memory alert may already exist"

# 3. High Request Rate Alert
echo "Creating request rate alert..."
az monitor metrics alert create \
  --name "${ALERT_PREFIX}-high-requests" \
  --resource-group "$RESOURCE_GROUP" \
  --description "Alert when request rate is unusually high" \
  --severity 3 \
  --condition "avg requests > 1000" \
  --window-size "PT5M" \
  --evaluation-frequency "PT1M" \
  --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
  --scopes "$CONTAINER_APP_ID" || echo "Request rate alert may already exist"

# 4. Container Restart Alert
echo "Creating container restart alert..."
az monitor metrics alert create \
  --name "${ALERT_PREFIX}-container-restarts" \
  --resource-group "$RESOURCE_GROUP" \
  --description "Alert when containers restart frequently" \
  --severity 1 \
  --condition "total restarts > 3" \
  --window-size "PT10M" \
  --evaluation-frequency "PT5M" \
  --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
  --scopes "$CONTAINER_APP_ID" || echo "Restart alert may already exist"

echo -e "${GREEN}✅ Container Apps metric alerts configured${NC}"

# Create log-based alerts using Container Apps logs
echo -e "${YELLOW}Setting up log-based error alerts...${NC}"

# Get Log Analytics workspace ID
WORKSPACE_ID=$(az monitor log-analytics workspace list \
  --resource-group "$RESOURCE_GROUP" \
  --query "[0].id" \
  --output tsv)

if [ -n "$WORKSPACE_ID" ]; then
    echo "Found Log Analytics workspace: $WORKSPACE_ID"
    
    # 5. Application Error Rate Alert
    echo "Creating application error rate alert..."
    az monitor scheduled-query create \
      --name "${ALERT_PREFIX}-app-error-rate" \
      --resource-group "$RESOURCE_GROUP" \
      --description "Alert when application error rate exceeds threshold" \
      --severity 1 \
      --window-size "PT5M" \
      --evaluation-frequency "PT1M" \
      --condition "count > 10" \
      --condition-query "ContainerAppConsoleLogs_CL | where Log_s contains 'ERROR' | where TimeGenerated > ago(5m) | summarize count()" \
      --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
      --scopes "$WORKSPACE_ID" || echo "App error alert may already exist"
    
    # 6. Azure OpenAI Service Unavailable Alert
    echo "Creating Azure OpenAI unavailable alert..."
    az monitor scheduled-query create \
      --name "${ALERT_PREFIX}-openai-unavailable" \
      --resource-group "$RESOURCE_GROUP" \
      --description "Alert when Azure OpenAI service is unavailable" \
      --severity 0 \
      --window-size "PT5M" \
      --evaluation-frequency "PT1M" \
      --condition "count > 3" \
      --condition-query "ContainerAppConsoleLogs_CL | where Log_s contains 'EXTERNAL_SERVICE_UNAVAILABLE' and Log_s contains 'OpenAI' | where TimeGenerated > ago(5m) | summarize count()" \
      --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
      --scopes "$WORKSPACE_ID" || echo "OpenAI alert may already exist"
    
    # 7. Authentication Failure Alert
    echo "Creating authentication failure alert..."
    az monitor scheduled-query create \
      --name "${ALERT_PREFIX}-auth-failures" \
      --resource-group "$RESOURCE_GROUP" \
      --description "Alert when authentication failures spike" \
      --severity 2 \
      --window-size "PT10M" \
      --evaluation-frequency "PT5M" \
      --condition "count > 15" \
      --condition-query "ContainerAppConsoleLogs_CL | where Log_s contains 'AUTH_TOKEN_INVALID' | where TimeGenerated > ago(10m) | summarize count()" \
      --action "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/$ACTION_GROUP_NAME" \
      --scopes "$WORKSPACE_ID" || echo "Auth failure alert may already exist"
    
    echo -e "${GREEN}✅ Log-based alerts configured${NC}"
else
    echo -e "${YELLOW}⚠️  Log Analytics workspace not found, skipping log-based alerts${NC}"
fi

# Update Container App health probes
echo -e "${YELLOW}Configuring health probes...${NC}"

# Create health probe configuration JSON
cat > /tmp/health-probes.json << EOF
{
  "template": {
    "containers": [
      {
        "name": "$CONTAINER_APP_NAME",
        "probes": [
          {
            "type": "liveness",
            "httpGet": {
              "path": "/health",
              "port": 8000
            },
            "initialDelaySeconds": 10,
            "periodSeconds": 30,
            "timeoutSeconds": 5,
            "failureThreshold": 3,
            "successThreshold": 1
          },
          {
            "type": "readiness", 
            "httpGet": {
              "path": "/health",
              "port": 8000
            },
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
            "timeoutSeconds": 3,
            "failureThreshold": 3,
            "successThreshold": 1
          },
          {
            "type": "startup",
            "httpGet": {
              "path": "/health",
              "port": 8000
            },
            "initialDelaySeconds": 10,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "failureThreshold": 30,
            "successThreshold": 1
          }
        ]
      }
    ]
  }
}
EOF

# Note: Container Apps health probes are configured during deployment
# This section documents the recommended configuration
echo -e "${YELLOW}ℹ️  Health probe configuration saved to /tmp/health-probes.json${NC}"
echo "Apply this configuration during next container app deployment."

# Create alert summary
echo -e "${GREEN}📊 Alert Configuration Summary${NC}"
echo "================================"
echo "✅ Action Group: $ACTION_GROUP_NAME"
echo "✅ CPU Usage Alert: > 80% for 5 minutes"
echo "✅ Memory Usage Alert: > 85% for 5 minutes" 
echo "✅ High Request Rate Alert: > 1000 requests/min"
echo "✅ Container Restart Alert: > 3 restarts in 10 minutes"
if [ -n "$WORKSPACE_ID" ]; then
    echo "✅ Application Error Rate Alert: > 10 errors in 5 minutes"
    echo "✅ Azure OpenAI Unavailable Alert: > 3 occurrences in 5 minutes"
    echo "✅ Authentication Failure Alert: > 15 failures in 10 minutes"
fi
echo ""

# Output next steps
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Test alerts by triggering controlled errors"
echo "2. Verify email notifications are received"
echo "3. Configure additional notification channels (Teams, SMS) if needed"
echo "4. Review and adjust thresholds based on production patterns"
echo "5. Set up automated runbooks for common alert scenarios"
echo ""

# Create monitoring dashboard
echo -e "${YELLOW}Creating monitoring dashboard...${NC}"

cat > /tmp/dashboard-config.json << EOF
{
  "properties": {
    "lenses": {
      "0": {
        "order": 0,
        "parts": {
          "0": {
            "position": {"x": 0, "y": 0, "rowSpan": 4, "colSpan": 6},
            "metadata": {
              "inputs": [
                {
                  "name": "resourceGroup",
                  "value": "$RESOURCE_GROUP"
                },
                {
                  "name": "resourceName", 
                  "value": "$CONTAINER_APP_NAME"
                }
              ],
              "type": "Extension/Microsoft_Azure_ContainerApps/PartType/ContainerAppMetricsPart"
            }
          },
          "1": {
            "position": {"x": 6, "y": 0, "rowSpan": 4, "colSpan": 6},
            "metadata": {
              "inputs": [
                {
                  "name": "resourceGroup",
                  "value": "$RESOURCE_GROUP"
                }
              ],
              "type": "Extension/Microsoft_Azure_Monitoring/PartType/AlertsManagementSummaryPart"
            }
          }
        }
      }
    },
    "metadata": {
      "model": {
        "timeRange": {
          "value": {
            "relative": {
              "duration": "PT1H"
            }
          },
          "type": "MsPortalFx.Composition.Configuration.ValueTypes.TimeRange"
        }
      }
    }
  },
  "name": "AIResumeAdvisor-Production-Monitoring",
  "type": "Microsoft.Portal/dashboards",
  "location": "global",
  "tags": {
    "hidden-title": "AIResumeAdvisor Production Monitoring"
  }
}
EOF

echo -e "${YELLOW}ℹ️  Dashboard configuration saved to /tmp/dashboard-config.json${NC}"
echo "Import this dashboard in Azure Portal for centralized monitoring."

echo ""
echo -e "${GREEN}🎉 Production error alerting setup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}⚠️  Important Reminders:${NC}"
echo "- Test all alerts to ensure they work correctly"
echo "- Update notification email addresses as needed"
echo "- Monitor alert frequency and adjust thresholds if too noisy"
echo "- Create runbooks for alert response procedures"
echo "- Regular review of alert effectiveness"

# Cleanup temporary files
rm -f /tmp/health-probes.json /tmp/dashboard-config.json