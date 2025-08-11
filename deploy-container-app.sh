#!/bin/bash

# Azure Container Apps Deployment Script
# Based on existing production configuration
#
# Monitoring Log Configuration:
# - MONITORING_LOG_FILE is intentionally not set (empty) for Azure deployment
# - This enables automatic stdout collection by Azure Container Apps
# - All monitoring logs flow to Azure Log Analytics automatically
# - For local development, set MONITORING_LOG_FILE=logs/monitoring.log in .env

set -e

# Configuration
RESOURCE_GROUP="airesumeadvisorfastapi"
LOCATION="japaneast"
ENVIRONMENT_NAME="airesumeadvisor-env"
CONTAINER_APP_NAME="airesumeadvisor-api-new"
ACR_NAME="airesumeadvisorregistry"
IMAGE_NAME="airesumeadvisor-api"
IMAGE_TAG="latest"

echo "🚀 Deploying Azure Container App..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Container App: $CONTAINER_APP_NAME"

# Check if logged in to Azure
if ! az account show >/dev/null 2>&1; then
    echo "❌ Please login to Azure first: az login"
    exit 1
fi

# Set subscription
az account set --subscription "5396d388-8261-464e-8ee4-112770674fba"

# Login to ACR
echo "🔐 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

# Build and push image
echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME:$IMAGE_TAG .

echo "📤 Pushing image to ACR..."
docker tag $IMAGE_NAME:$IMAGE_TAG $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG
docker push $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG

# Create or update Container App
echo "🚀 Creating/updating Container App..."

# Check if Container App exists
if az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP >/dev/null 2>&1; then
    echo "📝 Updating existing Container App..."
    az containerapp update \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG \
        --cpu 1.0 \
        --memory 2Gi \
        --min-replicas 1 \
        --max-replicas 10 \
        --ingress external \
        --target-port 8000 \
        --transport http \
        --env-vars \
            ENVIRONMENT=production \
            LOG_LEVEL=INFO \
            MONITORING_ENABLED=false \
            LIGHTWEIGHT_MONITORING=true \
            AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com \
            AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan \
            AZURE_OPENAI_API_VERSION=2025-01-01-preview \
            LLM2_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com \
            GPT41_MINI_JAPANEAST_ENDPOINT=https://airesumeadvisor.openai.azure.com/ \
            EMBEDDING_ENDPOINT="https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15" \
            CORS_ORIGINS="https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com" \
            GPT41_MINI_JAPANEAST_DEPLOYMENT=gpt-4-1-mini-japaneast \
            GPT41_MINI_JAPANEAST_API_VERSION=2025-01-01-preview \
            LLM_MODEL_KEYWORDS=gpt-4.1-mini \
            LLM_MODEL_GAP_ANALYSIS=gpt-4.1 \
            LLM_MODEL_RESUME_FORMAT=gpt-4.1 \
            LLM_MODEL_RESUME_TAILOR=gpt-4.1 \
            AZURE_OPENAI_API_KEY=secretref:azure-openai-key \
            EMBEDDING_API_KEY=secretref:embedding-api-key \
            GPT41_MINI_JAPANEAST_API_KEY=secretref:gpt41-mini-key \
            JWT_SECRET_KEY=secretref:jwt-secret \
            CONTAINER_APP_API_KEY=secretref:container-app-api-key \
        --secrets \
            azure-openai-key=secretref:azure-openai-key \
            embedding-api-key=secretref:embedding-api-key \
            gpt41-mini-key=secretref:gpt41-mini-key \
            jwt-secret=secretref:jwt-secret \
            container-app-api-key=secretref:container-app-api-key
else
    echo "🆕 Creating new Container App..."
    az containerapp create \
        --name $CONTAINER_APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $ENVIRONMENT_NAME \
        --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG \
        --cpu 1.0 \
        --memory 2Gi \
        --min-replicas 1 \
        --max-replicas 10 \
        --ingress external \
        --target-port 8000 \
        --transport http \
        --registry-server $ACR_NAME.azurecr.io \
        --env-vars \
            ENVIRONMENT=production \
            LOG_LEVEL=INFO \
            MONITORING_ENABLED=false \
            LIGHTWEIGHT_MONITORING=true \
            AZURE_OPENAI_ENDPOINT=https://airesumeadvisor.openai.azure.com \
            AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4.1-japan \
            AZURE_OPENAI_API_VERSION=2025-01-01-preview \
            LLM2_ENDPOINT=https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com \
            GPT41_MINI_JAPANEAST_ENDPOINT=https://airesumeadvisor.openai.azure.com/ \
            EMBEDDING_ENDPOINT="https://wenha-m7qan2zj-swedencentral.cognitiveservices.azure.com/openai/deployments/text-embedding-3-large/embeddings?api-version=2023-05-15" \
            CORS_ORIGINS="https://airesumeadvisor.com,https://airesumeadvisor.bubbleapps.io,https://www.airesumeadvisor.com" \
            GPT41_MINI_JAPANEAST_DEPLOYMENT=gpt-4-1-mini-japaneast \
            GPT41_MINI_JAPANEAST_API_VERSION=2025-01-01-preview \
            LLM_MODEL_KEYWORDS=gpt-4.1-mini \
            LLM_MODEL_GAP_ANALYSIS=gpt-4.1 \
            LLM_MODEL_RESUME_FORMAT=gpt-4.1 \
            LLM_MODEL_RESUME_TAILOR=gpt-4.1 \
            AZURE_OPENAI_API_KEY=secretref:azure-openai-key \
            EMBEDDING_API_KEY=secretref:embedding-api-key \
            GPT41_MINI_JAPANEAST_API_KEY=secretref:gpt41-mini-key \
            JWT_SECRET_KEY=secretref:jwt-secret \
            CONTAINER_APP_API_KEY=secretref:container-app-api-key \
        --secrets \
            azure-openai-key=secretref:azure-openai-key \
            embedding-api-key=secretref:embedding-api-key \
            gpt41-mini-key=secretref:gpt41-mini-key \
            jwt-secret=secretref:jwt-secret \
            container-app-api-key=secretref:container-app-api-key
fi

# Get the app URL
APP_URL=$(az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" --output tsv)

echo "✅ Container App deployed successfully!"
echo "📍 URL: https://$APP_URL"
echo "🏥 Health check: https://$APP_URL/health"
echo "📚 API docs: https://$APP_URL/docs"

# Test health endpoint
echo "🩺 Testing health endpoint..."
if curl -f "https://$APP_URL/health" >/dev/null 2>&1; then
    echo "✅ Health check passed!"
else
    echo "⚠️  Health check failed - please check logs"
fi

echo "🎉 Deployment complete!"