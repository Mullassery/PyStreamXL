"""
Unified OpenTelemetry exporter for all Mullassery dashboards.
Supports: Prometheus, Datadog, Honeycomb, New Relic, Jaeger, etc.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DashboardMetrics:
    timestamp: str
    title: str
    metrics: Dict[str, Any]
    alerts: list
    recommendations: list


class OTELDashboardExporter:
    """
    Export dashboard metrics to OpenTelemetry-compatible backends.
    
    Supports:
      - Prometheus (via OTLP exporter)
      - Datadog (via Datadog exporter)
      - Honeycomb (via OTLP exporter)
      - New Relic (via OTLP exporter)
      - Jaeger (tracing)
      - AWS X-Ray (via AWS SDK)
    """
    
    def __init__(self, 
                 service_name: str,
                 backend: str = "prometheus",
                 endpoint: Optional[str] = None):
        """
        Initialize OTEL exporter.
        
        Args:
            service_name: Name of the service (e.g., "pystreamai")
            backend: Backend type (prometheus, datadog, honeycomb, newrelic, jaeger, xray)
            endpoint: Optional custom OTEL collector endpoint
        """
        self.service_name = service_name
        self.backend = backend or os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "prometheus")
        self.endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        
        self._init_backend()
    
    def _init_backend(self):
        """Initialize OpenTelemetry based on backend type."""
        try:
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.metrics import MeterProvider
            
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", "production"),
            })
            
            if self.backend == "prometheus":
                self._init_prometheus(resource)
            elif self.backend == "datadog":
                self._init_datadog(resource)
            elif self.backend in ["honeycomb", "newrelic", "jaeger"]:
                self._init_otlp(resource)
            else:
                self._init_otlp(resource)
                
        except ImportError:
            print("⚠️  OpenTelemetry not installed. Using JSON export fallback.")
            self.use_json_fallback = True
    
    def _init_prometheus(self, resource):
        """Initialize Prometheus exporter."""
        try:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader
            from opentelemetry.sdk.metrics import MeterProvider
            from prometheus_client import start_http_server
            
            reader = PrometheusMetricReader()
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            
            # Start Prometheus HTTP server on port 8000
            port = int(os.getenv("OTEL_METRICS_EXPORTER_PORT", 8000))
            start_http_server(port)
            print(f"✓ Prometheus exporter ready at http://localhost:{port}/metrics")
            
        except ImportError:
            print("Install: pip install opentelemetry-exporter-prometheus")
    
    def _init_datadog(self, resource):
        """Initialize Datadog exporter."""
        try:
            from opentelemetry.exporter.datadog.metric_exporter import DatadogMetricExporter
            from opentelemetry.sdk.metrics import MeterProvider
            
            exporter = DatadogMetricExporter(
                api_key=os.getenv("DD_API_KEY"),
                site=os.getenv("DD_SITE", "datadoghq.com"),
            )
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[exporter])
            print("✓ Datadog exporter ready")
            
        except ImportError:
            print("Install: pip install opentelemetry-exporter-datadog")
    
    def _init_otlp(self, resource):
        """Initialize OTLP exporter (for Honeycomb, New Relic, Jaeger, etc.)."""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.metrics import MeterProvider
            
            exporter = OTLPMetricExporter(endpoint=self.endpoint)
            self.meter_provider = MeterProvider(resource=resource, metric_readers=[exporter])
            print(f"✓ OTLP exporter ready at {self.endpoint}")
            
        except ImportError:
            print("Install: pip install opentelemetry-exporter-otlp")
    
    def export(self, metrics: DashboardMetrics) -> None:
        """Export dashboard metrics to OTEL backend."""
        if not hasattr(self, 'meter_provider'):
            self._export_json_fallback(metrics)
            return
        
        meter = self.meter_provider.get_meter(self.service_name)
        
        # Create metric instruments
        for key, value in metrics.metrics.items():
            if isinstance(value, (int, float)):
                # Gauge for numeric values
                gauge = meter.create_gauge(
                    name=f"{self.service_name}.{key.lower().replace(' ', '_')}",
                    description=key,
                )
                gauge.record(value)
            elif isinstance(value, dict):
                # Nested metrics
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        gauge = meter.create_gauge(
                            name=f"{self.service_name}.{key.lower().replace(' ', '_')}.{sub_key.lower().replace(' ', '_')}",
                            description=f"{key} → {sub_key}",
                        )
                        gauge.record(sub_value)
        
        # Track alerts and recommendations as metrics
        if metrics.alerts:
            alerts_gauge = meter.create_gauge(
                name=f"{self.service_name}.alerts_count",
                description="Number of active alerts",
            )
            alerts_gauge.record(len(metrics.alerts))
        
        if metrics.recommendations:
            recs_gauge = meter.create_gauge(
                name=f"{self.service_name}.recommendations_count",
                description="Number of recommendations",
            )
            recs_gauge.record(len(metrics.recommendations))
    
    def _export_json_fallback(self, metrics: DashboardMetrics) -> None:
        """Fallback: export to JSON if OTEL not available."""
        import json
        output_file = f"/tmp/{self.service_name}_metrics.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": metrics.timestamp,
                "title": metrics.title,
                "metrics": metrics.metrics,
                "alerts": metrics.alerts,
                "recommendations": metrics.recommendations,
            }, f, indent=2)
        print(f"✓ Metrics exported to {output_file}")


class OTELDashboardInstrumentor:
    """Instruments dashboard to automatically export metrics via OTEL."""
    
    def __init__(self, service_name: str, backend: str = "prometheus"):
        self.exporter = OTELDashboardExporter(service_name, backend)
    
    def record_metrics(self, metrics: DashboardMetrics) -> None:
        """Record metrics to OTEL backend."""
        self.exporter.export(metrics)
