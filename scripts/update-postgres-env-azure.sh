#!/bin/bash

# Update PostgreSQL environment variables in Azure Container Apps
# This script adds the PostgreSQL connection details as environment variables

echo "🔧 Updating PostgreSQL environment variables in Azure Container Apps..."

# Set the environment variables
az containerapp update \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --set-env-vars \
    POSTGRES_HOST="airesumeadvisor-courses-db-eastasia.postgres.database.azure.com" \
    POSTGRES_DATABASE="coursesdb" \
    POSTGRES_USER="coursesadmin" \
    POSTGRES_PASSWORD="CourseDB@2025#Secure"

echo "✅ PostgreSQL environment variables updated successfully!"
echo ""
echo "📊 Verifying configuration..."
az containerapp show \
  --name airesumeadvisor-api-production \
  --resource-group airesumeadvisorfastapi \
  --query "properties.template.containers[0].env[?name=='POSTGRES_HOST' || name=='POSTGRES_DATABASE' || name=='POSTGRES_USER'].{name:name, value:value}" \
  -o table

echo ""
echo "🔄 Container will restart automatically to apply changes"