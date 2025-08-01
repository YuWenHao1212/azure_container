"""
Azure Application Insights integration for monitoring and telemetry.
"""
import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

from opencensus.ext.azure import metrics_exporter
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.stats import (
    aggregation as aggregation_module,
)
from opencensus.stats import (
    measure as measure_module,
)
from opencensus.stats import (
    stats as stats_module,
)
from opencensus.stats import (
    view as view_module,
)
from opencensus.tags import tag_key as tag_key_module
from opencensus.trace import tracer as tracer_module
from opencensus.trace.samplers import ProbabilitySampler

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for Application Insights monitoring and custom metrics."""

    def __init__(self):
        self.instrumentation_key = os.getenv(
            "APPINSIGHTS_INSTRUMENTATIONKEY",
            "e62aa619-199c-4f43-826e-bdec26344a26"  # Primary Application Insights
        )
        self.is_enabled = os.getenv("MONITORING_ENABLED", "true").lower() == "true"

        # Disable monitoring during tests
        if "pytest" in sys.modules:
            self.is_enabled = False
            logger.info("Monitoring disabled in test environment")

        if self.is_enabled:
            self._setup_monitoring()
        else:
            if "pytest" not in sys.modules:
                logger.info("Monitoring is disabled")

    def _setup_monitoring(self):
        """Initialize Application Insights components."""
        try:
            self._setup_telemetry_client()
            self._setup_logging()
            self._setup_tracing()
            self._setup_metrics()
            logger.info(f"Monitoring service initialized (Key: {self.instrumentation_key[:8]}...)")
        except Exception as e:
            logger.error(f"Failed to initialize monitoring: {e}")
            self.is_enabled = False

    def _setup_telemetry_client(self):
        """Setup Application Insights telemetry client for custom events."""
        from applicationinsights import TelemetryClient

        self.telemetry_client = TelemetryClient(self.instrumentation_key)
        # Enable telemetry with more aggressive sending
        self.telemetry_client.channel.sender.send_interval_in_milliseconds = 5000  # 5 seconds
        self.telemetry_client.channel.sender.max_telemetry_buffer_capacity = 500

        # Force immediate send for Azure Functions
        import atexit
        atexit.register(lambda: self.telemetry_client.flush())

    def track_request(self, endpoint: str, method: str, duration_ms: float,
                     success: bool, status_code: int, custom_properties: dict[str, Any] | None = None):
        """Track API request metrics."""
        if not self.is_enabled:
            return

        properties = {
            "endpoint": endpoint,
            "method": method,
            "duration_ms": duration_ms,
            "success": success,
            "status_code": status_code,
            "timestamp": datetime.now(UTC).isoformat()
        }

        if custom_properties:
            properties.update(custom_properties)

        # Send custom event to Application Insights
        if hasattr(self, 'logger'):
            self.logger.info(
                "RequestTracked",
                extra={
                    "custom_dimensions": properties
                }
            )

        # Also send as proper custom event
        if hasattr(self, 'telemetry_client'):
            self.telemetry_client.track_event("RequestTracked", properties)
            # Flush immediately for Azure Functions
            self.telemetry_client.flush()

    def track_keyword_extraction(self, language: str, prompt_version: str,
                               keyword_count: int, duration_ms: float,
                               success: bool, confidence_score: float):
        """Track keyword extraction business metrics."""
        if not self.is_enabled:
            return

        metrics = {
            "language": language,
            "prompt_version": prompt_version,
            "keyword_count": keyword_count,
            "duration_ms": duration_ms,
            "success": success,
            "confidence_score": confidence_score,
            "timestamp": datetime.now(UTC).isoformat()
        }

        # Send custom metrics
        if hasattr(self, 'metrics_recorder'):
            self._record_custom_metric(
                "keyword_extraction",
                metrics
            )

    def track_error(self, error_type: str, error_message: str,
                   endpoint: str | None = None, custom_properties: dict[str, Any] | None = None):
        """Track errors and exceptions."""
        if not self.is_enabled:
            return

        properties = {
            "error_type": error_type,
            "error_message": error_message,
            "endpoint": endpoint or "unknown",
            "timestamp": datetime.now(UTC).isoformat()
        }

        if custom_properties:
            properties.update(custom_properties)

        # Track as custom event for better querying
        self.track_event("ErrorTracked", properties)

        # Also send error to Application Insights logs
        if hasattr(self, 'logger'):
            self.logger.error(
                f"Error: {error_type}",
                extra={
                    "custom_dimensions": properties
                },
                exc_info=True
            )

    def track_dependency(self, dependency_type: str, dependency_name: str,
                        duration_ms: float, success: bool, data: str | None = None):
        """Track external dependency calls (e.g., OpenAI API)."""
        if not self.is_enabled:
            return

        # Track dependency
        if hasattr(self, 'tracer'):
            with self.tracer.span(name=f"{dependency_type}.{dependency_name}") as span:
                span.add_attribute("dependency.type", dependency_type)
                span.add_attribute("dependency.name", dependency_name)
                span.add_attribute("dependency.duration_ms", duration_ms)
                span.add_attribute("dependency.success", success)
                if data:
                    span.add_attribute("dependency.data", data)


    def _setup_logging(self):
        """Setup Azure logging handler."""
        handler = AzureLogHandler(
            connection_string=f"InstrumentationKey={self.instrumentation_key}"
        )
        handler.setLevel(logging.INFO)

        # Create a dedicated logger for Application Insights
        self.logger = logging.getLogger("azure.monitoring")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _setup_tracing(self):
        """Setup distributed tracing."""
        self.tracer = tracer_module.Tracer(
            exporter=AzureExporter(
                connection_string=f"InstrumentationKey={self.instrumentation_key}"
            ),
            sampler=ProbabilitySampler(1.0)
        )

    def _setup_metrics(self):
        """Setup custom metrics exporter."""
        self.stats = stats_module.stats
        self.view_manager = self.stats.view_manager
        self.stats_recorder = self.stats.stats_recorder

        # Register the exporter
        exporter = metrics_exporter.new_metrics_exporter(
            connection_string=f"InstrumentationKey={self.instrumentation_key}"
        )
        self.view_manager.register_exporter(exporter)

        # Define measures
        self.request_duration_measure = measure_module.MeasureFloat(
            "request_duration",
            "The duration of requests in milliseconds",
            "ms"
        )

        self.keyword_count_measure = measure_module.MeasureInt(
            "keyword_count",
            "Number of keywords extracted",
            "keywords"
        )

        # Define tags
        self.endpoint_key = tag_key_module.TagKey("endpoint")
        self.method_key = tag_key_module.TagKey("method")
        self.status_key = tag_key_module.TagKey("status")
        self.language_key = tag_key_module.TagKey("language")

        # Create views
        self._create_views()

    def _create_views(self):
        """Create and register metric views."""
        # Request duration view
        duration_view = view_module.View(
            "request_duration_distribution",
            "Distribution of request durations",
            [self.endpoint_key, self.method_key, self.status_key],
            self.request_duration_measure,
            aggregation_module.DistributionAggregation(
                [50, 100, 200, 500, 1000, 2000, 5000, 10000]
            )
        )

        # Keyword count view
        keyword_view = view_module.View(
            "keyword_count_distribution",
            "Distribution of keyword counts",
            [self.language_key],
            self.keyword_count_measure,
            aggregation_module.DistributionAggregation(
                [5, 10, 12, 15, 20, 25, 30]
            )
        )

        # Register views
        self.view_manager.register_view(duration_view)
        self.view_manager.register_view(keyword_view)

    def _record_custom_metric(self, metric_name: str, properties: dict[str, Any]):
        """Record custom metrics to Application Insights."""
        if hasattr(self, 'logger'):
            self.logger.info(
                f"CustomMetric.{metric_name}",
                extra={
                    "custom_dimensions": properties
                }
            )

    def track_metric(self, name: str, value: float, properties: dict[str, Any] | None = None):
        """Track a custom metric."""
        if not self.is_enabled:
            return

        metric_properties = {
            "metric_name": name,
            "metric_value": value,
            "timestamp": datetime.now(UTC).isoformat()
        }

        if properties:
            metric_properties.update(properties)

        self._record_custom_metric(name, metric_properties)

    def track_event(self, name: str, properties: dict[str, Any] | None = None):
        """Track a custom event."""
        if not self.is_enabled:
            return

        event_properties = {
            "event_name": name,
            "timestamp": datetime.now(UTC).isoformat()
        }

        if properties:
            event_properties.update(properties)

        # Log to traces for debugging
        if hasattr(self, 'logger'):
            self.logger.info(
                f"CustomEvent.{name}",
                extra={
                    "custom_dimensions": event_properties
                }
            )

        # Send as proper custom event using telemetry client
        if hasattr(self, 'telemetry_client'):
            self.telemetry_client.track_event(name, event_properties)
            # Flush immediately for Azure Functions
            self.telemetry_client.flush()


# Global monitoring instance
monitoring_service = MonitoringService()
