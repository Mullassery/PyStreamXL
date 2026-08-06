# 🔭 OpenTelemetry Setup Guide for Mullassery Dashboards

All Mullassery dashboards support OpenTelemetry (OTEL) for seamless integration with monitoring backends.

## Supported Backends

| Backend | Protocol | Setup Time | Cost | Use Case |
|---------|----------|-----------|------|----------|
| **Prometheus** | OTLP | 5 min | Free/OSS | On-prem monitoring |
| **Datadog** | Native | 2 min | Paid | Enterprise APM |
| **Honeycomb** | OTLP | 3 min | Paid | Distributed tracing |
| **New Relic** | OTLP | 3 min | Paid | Full observability |
| **Jaeger** | OTLP | 5 min | Free/OSS | Distributed tracing |
| **AWS X-Ray** | AWS SDK | 2 min | Paid | AWS-native tracing |

## Quick Start

### 1. Prometheus (Local/OSS)

```bash
# Install dependencies
pip install opentelemetry-exporter-prometheus prometheus-client

# Set environment
export OTEL_EXPORTER_OTLP_PROTOCOL=prometheus
export OTEL_METRICS_EXPORTER_PORT=8000

# Start dashboard
$ dash-pystreamai-live

# View metrics
$ curl http://localhost:8000/metrics
```

**Prometheus scrape config:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mullassery'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

### 2. Datadog

```bash
# Install dependency
pip install opentelemetry-exporter-datadog

# Set environment
export DD_API_KEY="your_api_key_here"
export DD_SITE="datadoghq.com"  # or datadoghq.eu
export OTEL_EXPORTER_OTLP_PROTOCOL=datadog

# Start dashboard
$ dash-pystreamai-live

# View in Datadog
# Metrics appear in Datadog under service: "pystreamai"
```

**Agent config (optional - for traces):**
```yaml
# datadog.yaml
apm_config:
  enabled: true
  bind_host: localhost
  bind_port: 8126
```

### 3. Honeycomb (Cloud/OTEL)

```bash
# Install dependency
pip install opentelemetry-exporter-otlp

# Set environment
export OTEL_EXPORTER_OTLP_ENDPOINT="https://api.honeycomb.io"
export OTEL_EXPORTER_OTLP_HEADERS="x-honeycomb-team=$(cat ~/.honeycomb_key)"
export OTEL_SERVICE_NAME="mullassery"

# Start dashboard
$ dash-pystreamai-live

# View in Honeycomb
# Dataset: mullassery, Service: pystreamai
```

### 4. New Relic (OTLP)

```bash
# Install dependency
pip install opentelemetry-exporter-otlp

# Set environment
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.nr-data.net:4317"
export OTEL_EXPORTER_OTLP_HEADERS="api-key=$(cat ~/.newrelic_key)"
export OTEL_DEPLOYMENT_ENVIRONMENT="production"

# Start dashboard
$ dash-pystreamai-live

# View in New Relic
# APM → Services → pystreamai
```

### 5. Jaeger (Distributed Tracing)

```bash
# Install Jaeger locally
docker run -d \
  --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Install dependency
pip install opentelemetry-exporter-otlp

# Set environment
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"

# Start dashboard
$ dash-pystreamai-live

# View traces
# http://localhost:16686
```

## Environment Variables Reference

```bash
# OTEL Configuration
OTEL_EXPORTER_OTLP_PROTOCOL        # prometheus, datadog, grpc (default: prometheus)
OTEL_EXPORTER_OTLP_ENDPOINT        # Collector endpoint (default: http://localhost:4317)
OTEL_EXPORTER_OTLP_HEADERS         # Custom headers (e.g., API keys)
OTEL_METRICS_EXPORTER_PORT         # Prometheus port (default: 8000)
OTEL_DEPLOYMENT_ENVIRONMENT        # dev/staging/production (default: production)
OTEL_SERVICE_NAME                  # Service name (override)

# Backend-Specific
DD_API_KEY                          # Datadog API key
DD_SITE                             # Datadog site (datadoghq.com or datadoghq.eu)
HONEYCOMB_API_KEY                   # Honeycomb API key
NEW_RELIC_API_KEY                   # New Relic API key
AWS_REGION                          # For X-Ray
```

## Usage Examples

### Export to Multiple Backends

```bash
# Terminal 1: Prometheus exporter
export OTEL_EXPORTER_OTLP_PROTOCOL=prometheus
dash-pystreamai-live

# Terminal 2: JSON export for custom processing
while true; do
  dash-pystreamai-export
  sleep 60
done

# Terminal 3: Parse metrics
jq '.metrics' /tmp/pystreamai_metrics.json
```

### CI/CD Integration

```bash
# GitHub Actions / GitLab CI
- name: Export Metrics
  env:
    OTEL_EXPORTER_OTLP_PROTOCOL: prometheus
  run: dash-pystreamai-export > metrics.json

- name: Upload to Datadog
  run: |
    curl -X POST https://api.datadoghq.com/api/v1/series \
      -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \
      -d @metrics.json
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

# Install packages
RUN pip install opentelemetry-exporter-otlp pystreamai

# Set environment
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
ENV OTEL_DEPLOYMENT_ENVIRONMENT=production

# Start dashboard exporter
CMD ["bash", "-c", "while true; do dash-pystreamai-export; sleep 60; done"]
```

### Kubernetes Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-config
data:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  OTEL_DEPLOYMENT_ENVIRONMENT: "production"

---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mullassery-metrics
spec:
  schedule: "*/1 * * * *"  # Every minute
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: exporter
            image: python:3.11
            envFrom:
            - configMapRef:
                name: otel-config
            command:
            - sh
            - -c
            - |
              pip install opentelemetry-exporter-otlp pystreamai && \
              dash-pystreamai-export
          restartPolicy: OnFailure
```

## Troubleshooting

**Metrics not appearing?**
```bash
# Check OTEL configuration
echo $OTEL_EXPORTER_OTLP_ENDPOINT
echo $OTEL_EXPORTER_OTLP_PROTOCOL

# Test connectivity
curl -v http://localhost:4317

# View local JSON export
cat /tmp/pystreamai_metrics.json | jq
```

**Permission denied on port 8000?**
```bash
# Use custom port
export OTEL_METRICS_EXPORTER_PORT=9090
dash-pystreamai-live
```

**Module not found?**
```bash
# Install missing exporter
pip install opentelemetry-exporter-prometheus
pip install opentelemetry-exporter-otlp
pip install opentelemetry-exporter-datadog
```

## Best Practices

1. **Always use environment variables** for sensitive data (API keys)
2. **Set OTEL_DEPLOYMENT_ENVIRONMENT** to track production vs staging
3. **Use OTLP for cloud backends** (Honeycomb, New Relic) — automatic retry & batching
4. **Enable sampling** in production to reduce costs
5. **Monitor the exporter itself** — check export success rates
6. **Use JSON fallback** for offline/disconnected scenarios

## Advanced: Custom Instrumentation

```python
from otel_exporter import OTELDashboardExporter, DashboardMetrics

# Initialize exporter
exporter = OTELDashboardExporter(
    service_name="pystreamai",
    backend="prometheus",  # or "datadog", "honeycomb", etc.
)

# Create metrics
metrics = DashboardMetrics(
    timestamp="2026-07-30T...",
    title="PyStreamAI Dashboard",
    metrics={"status": "healthy", "uptime": 3600},
    alerts=[],
    recommendations=[]
)

# Export to backend
exporter.export(metrics)
```

## Support Matrix

| Package | Prometheus | Datadog | Honeycomb | New Relic | Jaeger |
|---------|-----------|---------|-----------|-----------|--------|
| pystreamai | ✅ | ✅ | ✅ | ✅ | ✅ |
| pystreammcp | ✅ | ✅ | ✅ | ✅ | ✅ |
| pystreampdf | ✅ | ✅ | ✅ | ✅ | ✅ |
| pystreamxl | ✅ | ✅ | ✅ | ✅ | ✅ |
| statguardian | ✅ | ✅ | ✅ | ✅ | ✅ |
| pyreverseetl | ✅ | ✅ | ✅ | ✅ | ✅ |
| pyterrainmap | ✅ | ✅ | ✅ | ✅ | ✅ |
| pyroboreplay | ✅ | ✅ | ✅ | ✅ | ✅ |
| pyrobosimulator | ✅ | ✅ | ✅ | ✅ | ✅ |

---

Need help? See `DASHBOARD_SHORTCUTS.md` or check individual package documentation.
