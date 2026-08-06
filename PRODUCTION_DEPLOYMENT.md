# 🚀 Production Deployment Guide

Complete guide for deploying Mullassery dashboards in production environments.

## Pre-Production Checklist

- [ ] All 9 Tier 1+2 repos installed via pip
- [ ] Keyboard shortcuts configured: `bash scripts/setup_shortcuts.sh`
- [ ] OTEL exporter installed: `pip install opentelemetry-exporter-otlp`
- [ ] Monitoring backend selected (Prometheus/Datadog/Honeycomb/New Relic)
- [ ] Environment variables configured
- [ ] Dashboard tested locally: `dash-[package]-live`
- [ ] JSON export verified: `dash-[package]-export`

## Production Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Production Deployment                      │
└─────────────────────────────────────────────────────────────┘

Tier 1: Application Level
  ├─ PyStreamAI (Deployment metrics)
  ├─ PyStreamMCP (Tool orchestration)
  ├─ PyStreamPDF (Document processing)
  ├─ PyStreamXL (Formula extraction)
  ├─ StatGuardian (Data quality)
  └─ PyReverseETL (Activation pipelines)

Tier 2: Infrastructure Level
  ├─ PyTerrainMap (Spatial analysis)
  ├─ PyRoboReplay (Multi-modal fusion)
  └─ PyRoboSimulator (World engine)

Tier 3: Dashboards (All packages above)
  ├─ Persistent daemon mode (auto-start)
  ├─ Keyboard shortcuts (dash-[pkg], dash-[pkg]-live, dash-[pkg]-export)
  └─ OTEL exporters (Prometheus/Datadog/Honeycomb/New Relic)

Tier 4: Monitoring Backend
  ├─ Prometheus + Grafana (OSS, on-prem)
  ├─ Datadog (Managed, enterprise)
  ├─ Honeycomb (Cloud-native, tracing)
  ├─ New Relic (Full observability)
  └─ Jaeger (Distributed tracing)
```

## Kubernetes Deployment

### 1. Install Mullassery Package

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mullassery-config
  namespace: default
data:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector.observability:4317"
  OTEL_DEPLOYMENT_ENVIRONMENT: "production"
  OTEL_SERVICE_NAME: "pystreamai"

---
apiVersion: v1
kind: Secret
metadata:
  name: monitoring-credentials
  namespace: default
type: Opaque
stringData:
  DD_API_KEY: "your-datadog-api-key"
  HONEYCOMB_API_KEY: "your-honeycomb-api-key"

---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mullassery-metrics-exporter
  namespace: default
spec:
  schedule: "*/1 * * * *"  # Every minute
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: mullassery-exporter
          containers:
          - name: exporter
            image: python:3.11-slim
            imagePullPolicy: IfNotPresent
            envFrom:
            - configMapRef:
                name: mullassery-config
            - secretRef:
                name: monitoring-credentials
            command:
            - sh
            - -c
            - |
              set -e
              echo "Installing dependencies..."
              pip install -q opentelemetry-exporter-otlp pystreamai
              echo "Exporting metrics..."
              dash-pystreamai-export
              echo "✓ Metrics exported"
            resources:
              requests:
                memory: "256Mi"
                cpu: "100m"
              limits:
                memory: "512Mi"
                cpu: "500m"
          restartPolicy: OnFailure
          backoffLimit: 3
```

### 2. OTEL Collector (OpenTelemetry)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    
    processors:
      batch:
        send_batch_size: 1000
        timeout: 10s
      
      memory_limiter:
        check_interval: 1s
        limit_mib: 512
    
    exporters:
      datadog:
        api:
          key: ${DD_API_KEY}
          site: datadoghq.com
      
      prometheus:
        endpoint: "0.0.0.0:8888"
      
      otlp:
        endpoint: honeycomb-collector.observability:4317
        headers:
          x-honeycomb-team: ${HONEYCOMB_API_KEY}
    
    service:
      pipelines:
        metrics:
          receivers: [otlp]
          processors: [batch, memory_limiter]
          exporters: [datadog, prometheus]
        
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [otlp]

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 2
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-k8s:latest
        ports:
        - containerPort: 4317  # OTLP gRPC
        - containerPort: 4318  # OTLP HTTP
        - containerPort: 8888  # Prometheus
        env:
        - name: DD_API_KEY
          valueFrom:
            secretKeyRef:
              name: monitoring-credentials
              key: DD_API_KEY
        - name: HONEYCOMB_API_KEY
          valueFrom:
            secretKeyRef:
              name: monitoring-credentials
              key: HONEYCOMB_API_KEY
        volumeMounts:
        - name: config
          mountPath: /etc/otel
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1"
      volumes:
      - name: config
        configMap:
          name: otel-collector-config

---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
spec:
  type: ClusterIP
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: 4317
  - name: otlp-http
    port: 4318
    targetPort: 4318
  - name: prometheus
    port: 8888
    targetPort: 8888
  selector:
    app: otel-collector
```

### 3. Prometheus Scrape Config

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
    - job_name: 'mullassery'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - default
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: otel-collector
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        action: keep
        regex: "8888"
```

## Docker Deployment

### Single Service

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install all Mullassery packages
RUN pip install --no-cache-dir \
  opentelemetry-exporter-otlp \
  pystreamai \
  pystreammcp \
  pystreampdf \
  pystreamxl \
  statguardian \
  pyreverseetl

# Setup dashboard shortcuts
COPY scripts/setup_shortcuts.sh /app/
RUN bash /app/setup_shortcuts.sh

# Export metrics every minute
CMD ["bash", "-c", "\
  export OTEL_EXPORTER_OTLP_ENDPOINT='${OTEL_ENDPOINT:-http://otel-collector:4317}'; \
  while true; do \
    echo '[Dashboard Export] Starting...'; \
    dash-pystreamai-export && \
    dash-pystreammcp-export && \
    dash-pystreampdf-export; \
    echo '[Dashboard Export] Complete. Sleeping 60s...'; \
    sleep 60; \
  done"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  mullassery-exporter:
    build: .
    container_name: mullassery-dashboards
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_DEPLOYMENT_ENVIRONMENT: production
      DD_API_KEY: ${DD_API_KEY}
    depends_on:
      - otel-collector
    networks:
      - monitoring

  otel-collector:
    image: otel/opentelemetry-collector-k8s:latest
    container_name: otel-collector
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml
    command: ["--config=/etc/otel/config.yaml"]
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    depends_on:
      - prometheus
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

## Monitoring Dashboards

### Prometheus Queries

```promql
# PyStreamAI deployment health
pystreamai_status

# Inference latency (p99)
histogram_quantile(0.99, pystreamai_latency_metrics_p99)

# Error rate
rate(pystreamai_error_handling_total_errors[5m])

# Cost over 24h
pystreamai_cost_metrics_24h_total

# PyStreamMCP selective intelligence reduction
pystreammcp_selective_intelligence_stats_filtered

# StatGuardian data quality
statguardian_data_quality_by_table

# All packages uptime
sum(rate(pystreamai_uptime[5m]))
```

### Grafana Dashboard JSON

Import from: https://grafana.com/grafana/dashboards (search: "Mullassery")

Or create manually:
1. Data Source: Prometheus (http://localhost:9090)
2. Panel 1: All Services Status (gauge)
3. Panel 2: Metrics by Package (table)
4. Panel 3: Error Rate Trend (graph)
5. Panel 4: Cost Analysis (stat)

## Health Checks

### Liveness Check

```bash
#!/bin/bash
# health_check.sh
pystreamai dashboard --static > /dev/null 2>&1
[ $? -eq 0 ] && echo "healthy" || echo "unhealthy"
```

### Metrics Export Health

```bash
#!/bin/bash
# metrics_health.sh
curl -s http://localhost:8000/metrics | grep -q pystreamai_status
[ $? -eq 0 ] && echo "metrics OK" || echo "metrics FAIL"
```

## Logging & Debugging

### Enable Debug Logging

```bash
export OTEL_LOG_LEVEL=DEBUG
export OTEL_EXPORTER_OTLP_HEADERS="authorization=Bearer your_token"
dash-pystreamai-live 2>&1 | tee /var/log/mullassery.log
```

### Monitor Export Success

```bash
tail -f /var/log/mullassery.log | grep -i "export\|error"
```

### Validate Metrics Format

```bash
cat /tmp/pystreamai_metrics.json | jq '.metrics'
```

## Performance Tuning

### CPU/Memory Optimization

```bash
# Reduce export frequency in Kubernetes
schedule: "*/5 * * * *"  # Every 5 minutes instead of 1

# Batch multiple dashboards in single export
for pkg in pystreamai pystreammcp pysteampdf; do
  dash-$pkg-export
done

# Limit metric cardinality
export OTEL_SAMPLING_RATE=0.1  # 10% sampling
```

### Network Optimization

```bash
# Use gRPC batching
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Increase batch size
export OTEL_METRICS_EXPORTER_BATCH_SIZE=1000

# Connection pooling (automatic in gRPC)
```

## Backup & Recovery

### Export Metrics for Backup

```bash
#!/bin/bash
BACKUP_DIR="/backups/mullassery-metrics"
mkdir -p $BACKUP_DIR

for pkg in pystreamai pystreammcp pystreampdf pystreamxl statguardian pyreverseetl pyterrainmap pyroboreplay pyrobosimulator; do
  dash-$pkg-export > "$BACKUP_DIR/${pkg}_$(date +%Y%m%d_%H%M%S).json"
done

# Compress and upload
tar -czf mullassery_metrics_backup.tar.gz $BACKUP_DIR
aws s3 cp mullassery_metrics_backup.tar.gz s3://backup-bucket/mullassery/
```

## Compliance & Security

- [ ] All API keys in environment variables (not in code)
- [ ] OTEL endpoint uses mTLS (in production)
- [ ] Metrics do not contain PII
- [ ] Export logs retained for 90 days
- [ ] Regular security audits of OTEL pipeline
- [ ] Access control on Grafana/Datadog dashboards

---

**Need help?** Check OTEL_SETUP_GUIDE.md for backend-specific setup.
