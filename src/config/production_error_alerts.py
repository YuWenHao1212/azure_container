"""
Production environment error alerting configuration.

This module defines error thresholds, alerting rules, and monitoring
configurations for the production environment to ensure rapid response
to critical issues.
"""

import logging
from dataclasses import dataclass

from src.core.monitoring_logger import get_business_logger

logger = logging.getLogger(__name__)


@dataclass
class ErrorThreshold:
    """Error threshold configuration for alerting."""
    error_code: str
    threshold_count: int  # Number of errors in time window
    time_window_minutes: int  # Time window for counting errors
    severity: str  # 'critical', 'high', 'medium', 'low'
    alert_channels: list[str]  # Where to send alerts
    description: str


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    condition: str  # Error condition description
    threshold: ErrorThreshold
    enabled: bool = True
    cooldown_minutes: int = 30  # Minimum time between alerts


class ProductionErrorAlerts:
    """
    Production environment error alerting system.

    Integrates with lightweight monitoring to track error patterns
    and trigger alerts when thresholds are exceeded.
    """

    def __init__(self):
        """Initialize production error alerting."""
        self.business_logger = get_business_logger()
        self.alert_rules = self._initialize_alert_rules()
        self._last_alert_times: dict[str, float] = {}

    def _initialize_alert_rules(self) -> list[AlertRule]:
        """Initialize production alert rules."""
        return [
            # Critical System Errors
            AlertRule(
                name="high_internal_error_rate",
                condition="SYSTEM_INTERNAL_ERROR rate > 5 per 5 minutes",
                threshold=ErrorThreshold(
                    error_code="SYSTEM_INTERNAL_ERROR",
                    threshold_count=5,
                    time_window_minutes=5,
                    severity="critical",
                    alert_channels=["teams", "email", "sms"],
                    description="High rate of internal server errors"
                )
            ),

            # Authentication Issues
            AlertRule(
                name="auth_token_failures",
                condition="AUTH_TOKEN_INVALID rate > 10 per 10 minutes",
                threshold=ErrorThreshold(
                    error_code="AUTH_TOKEN_INVALID",
                    threshold_count=10,
                    time_window_minutes=10,
                    severity="high",
                    alert_channels=["teams", "email"],
                    description="Multiple authentication failures"
                )
            ),

            # External Service Issues
            AlertRule(
                name="azure_openai_unavailable",
                condition="EXTERNAL_SERVICE_UNAVAILABLE rate > 3 per 5 minutes",
                threshold=ErrorThreshold(
                    error_code="EXTERNAL_SERVICE_UNAVAILABLE",
                    threshold_count=3,
                    time_window_minutes=5,
                    severity="critical",
                    alert_channels=["teams", "email", "sms"],
                    description="Azure OpenAI service unavailable"
                )
            ),

            # Rate Limiting Issues
            AlertRule(
                name="rate_limit_exceeded",
                condition="EXTERNAL_RATE_LIMIT_EXCEEDED rate > 20 per 15 minutes",
                threshold=ErrorThreshold(
                    error_code="EXTERNAL_RATE_LIMIT_EXCEEDED",
                    threshold_count=20,
                    time_window_minutes=15,
                    severity="high",
                    alert_channels=["teams", "email"],
                    description="High rate of external API rate limiting"
                )
            ),

            # Timeout Issues
            AlertRule(
                name="service_timeouts",
                condition="EXTERNAL_SERVICE_TIMEOUT rate > 10 per 10 minutes",
                threshold=ErrorThreshold(
                    error_code="EXTERNAL_SERVICE_TIMEOUT",
                    threshold_count=10,
                    time_window_minutes=10,
                    severity="high",
                    alert_channels=["teams", "email"],
                    description="High rate of service timeouts"
                )
            ),

            # Validation Issues (indicating data quality problems)
            AlertRule(
                name="high_validation_errors",
                condition="VALIDATION_ERROR rate > 50 per 30 minutes",
                threshold=ErrorThreshold(
                    error_code="VALIDATION_ERROR",
                    threshold_count=50,
                    time_window_minutes=30,
                    severity="medium",
                    alert_channels=["teams"],
                    description="High rate of validation errors"
                )
            ),

            # Processing Errors
            AlertRule(
                name="processing_failures",
                condition="PROCESSING_ERROR rate > 15 per 15 minutes",
                threshold=ErrorThreshold(
                    error_code="PROCESSING_ERROR",
                    threshold_count=15,
                    time_window_minutes=15,
                    severity="high",
                    alert_channels=["teams", "email"],
                    description="High rate of processing failures"
                )
            )
        ]

    def get_alert_configuration(self) -> dict:
        """
        Get complete alert configuration for production deployment.

        Returns:
            Dictionary containing alert rules and thresholds
        """
        return {
            "alert_rules": [
                {
                    "name": rule.name,
                    "condition": rule.condition,
                    "enabled": rule.enabled,
                    "cooldown_minutes": rule.cooldown_minutes,
                    "threshold": {
                        "error_code": rule.threshold.error_code,
                        "count": rule.threshold.threshold_count,
                        "time_window_minutes": rule.threshold.time_window_minutes,
                        "severity": rule.threshold.severity,
                        "alert_channels": rule.threshold.alert_channels,
                        "description": rule.threshold.description
                    }
                }
                for rule in self.alert_rules
            ],
            "notification_settings": {
                "teams_webhook": "${TEAMS_WEBHOOK_URL}",
                "email_smtp": {
                    "server": "${SMTP_SERVER}",
                    "port": 587,
                    "username": "${SMTP_USERNAME}",
                    "password": "${SMTP_PASSWORD}",
                    "from_email": "alerts@airesumeadvisor.com",
                    "to_emails": ["devops@airesumeadvisor.com"]
                },
                "sms": {
                    "service": "twilio",
                    "account_sid": "${TWILIO_ACCOUNT_SID}",
                    "auth_token": "${TWILIO_AUTH_TOKEN}",
                    "from_number": "${TWILIO_FROM_NUMBER}",
                    "to_numbers": ["${EMERGENCY_CONTACT_PHONE}"]
                }
            },
            "global_settings": {
                "default_cooldown_minutes": 30,
                "max_alerts_per_hour": 10,
                "business_hours_only": False,  # Critical alerts 24/7
                "timezone": "Asia/Taipei"
            }
        }

    def get_azure_monitor_kusto_queries(self) -> dict[str, str]:
        """
        Get Kusto queries for Azure Monitor alerting.

        These queries can be used in Azure Monitor to set up automated alerts
        based on Application Insights logs.

        Returns:
            Dictionary of alert name to Kusto query mapping
        """
        return {
            "high_internal_error_rate": """
traces
| where timestamp > ago(5m)
| where customDimensions.error_code == "SYSTEM_INTERNAL_ERROR"
| summarize count() by bin(timestamp, 1m)
| where count_ > 1
            """,

            "azure_openai_unavailable": """
traces
| where timestamp > ago(5m)
| where customDimensions.error_code == "EXTERNAL_SERVICE_UNAVAILABLE"
| where message contains "Azure OpenAI"
| summarize count()
| where count_ >= 3
            """,

            "rate_limit_exceeded": """
traces
| where timestamp > ago(15m)
| where customDimensions.error_code == "EXTERNAL_RATE_LIMIT_EXCEEDED"
| summarize count() by bin(timestamp, 1m)
| where count_ > 1
            """,

            "auth_failures_spike": """
traces
| where timestamp > ago(10m)
| where customDimensions.error_code == "AUTH_TOKEN_INVALID"
| summarize count()
| where count_ >= 10
            """,

            "service_timeouts": """
traces
| where timestamp > ago(10m)
| where customDimensions.error_code == "EXTERNAL_SERVICE_TIMEOUT"
| summarize count()
| where count_ >= 10
            """
        }

    def get_container_apps_health_probes(self) -> dict:
        """
        Get health probe configuration for Container Apps.

        Returns:
            Health probe configuration for early error detection
        """
        return {
            "liveness_probe": {
                "path": "/health",
                "port": 8000,
                "initial_delay_seconds": 10,
                "period_seconds": 30,
                "timeout_seconds": 5,
                "failure_threshold": 3,
                "success_threshold": 1
            },
            "readiness_probe": {
                "path": "/health/ready",
                "port": 8000,
                "initial_delay_seconds": 5,
                "period_seconds": 10,
                "timeout_seconds": 3,
                "failure_threshold": 3,
                "success_threshold": 1
            },
            "startup_probe": {
                "path": "/health",
                "port": 8000,
                "initial_delay_seconds": 10,
                "period_seconds": 10,
                "timeout_seconds": 5,
                "failure_threshold": 30,
                "success_threshold": 1
            }
        }

    def generate_deployment_script(self) -> str:
        """
        Generate Azure CLI deployment script for setting up alerts.

        Returns:
            Shell script for deploying alert rules to Azure
        """
        return '''#!/bin/bash
# Production Error Alerting Setup Script
# Deploy this script to configure error alerts in Azure Monitor

set -e

SUBSCRIPTION_ID="5396d388-8261-464e-8ee4-112770674fba"
RESOURCE_GROUP="airesumeadvisorfastapi"
APP_INSIGHTS_NAME="airesumeadvisor-insights"
CONTAINER_APP_NAME="airesumeadvisor-api-production"

echo "Setting up production error alerts..."

# Create action group for notifications
az monitor action-group create \\
  --resource-group $RESOURCE_GROUP \\
  --name "airesumeadvisor-error-alerts" \\
  --short-name "api-errors" \\
  --email-receivers name="DevOps Team" email="devops@airesumeadvisor.com"

# High internal error rate alert
az monitor scheduled-query create \\
  --resource-group $RESOURCE_GROUP \\
  --name "high-internal-error-rate" \\
  --description "Alert when internal error rate exceeds threshold" \\
  --severity 0 \\
  --window-size "PT5M" \\
  --evaluation-frequency "PT1M" \\
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/components/$APP_INSIGHTS_NAME" \\
  --condition "count 'Heartbeat' > 5" \\
  --action-groups "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/airesumeadvisor-error-alerts"

# Azure OpenAI service unavailable alert
az monitor scheduled-query create \\
  --resource-group $RESOURCE_GROUP \\
  --name "azure-openai-unavailable" \\
  --description "Alert when Azure OpenAI service is unavailable" \\
  --severity 0 \\
  --window-size "PT5M" \\
  --evaluation-frequency "PT1M" \\
  --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Insights/components/$APP_INSIGHTS_NAME" \\
  --condition "count 'Heartbeat' > 3" \\
  --action-groups "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/actionGroups/airesumeadvisor-error-alerts"

echo "Error alerts configured successfully!"
        '''


# Singleton instance
_production_alerts = None


def get_production_error_alerts() -> ProductionErrorAlerts:
    """Get production error alerts singleton."""
    global _production_alerts
    if _production_alerts is None:
        _production_alerts = ProductionErrorAlerts()
    return _production_alerts
