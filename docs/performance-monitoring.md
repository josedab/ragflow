# Performance Monitoring

RAGFlow includes a comprehensive performance monitoring infrastructure that tracks operation times, identifies bottlenecks, and enables data-driven optimization decisions.

## Overview

The monitoring system provides:
- **Timing metrics** for all key operations
- **Prometheus-compatible** metrics export
- **Grafana dashboard** for visualization
- **Simple API** for adding new metrics

## Quick Start

### Accessing Metrics

Once RAGFlow is running, you can access metrics at:

- **Prometheus endpoint**: `GET /v1/metrics/prometheus`
- **JSON endpoint**: `GET /v1/metrics/json`
- **Health check**: `GET /v1/metrics/health`

### Example: Fetching Metrics

```bash
# Get Prometheus-formatted metrics
curl http://localhost:9380/v1/metrics/prometheus

# Get JSON-formatted metrics
curl http://localhost:9380/v1/metrics/json

# Check health
curl http://localhost:9380/v1/metrics/health
```

## Available Metrics

### API Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `api_request_duration_seconds` | Histogram | HTTP request duration by endpoint |
| `api_requests_total` | Counter | Total HTTP requests by endpoint and status |

### Document Processing Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pdf_parse_duration_seconds` | Histogram | PDF parsing duration |
| `embedding_duration_seconds` | Histogram | Embedding generation duration |

### Search & LLM Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `search_duration_seconds` | Histogram | Search query duration |
| `llm_duration_seconds` | Histogram | LLM inference duration |

## Adding Custom Metrics

### Using Decorators

```python
from common.metrics import Metrics

# Time a function
@Metrics.timed("my_operation", tags={"version": "1.0"})
def my_function():
    # ... your code
    pass

# Count function calls
@Metrics.counted("my_counter")
def my_counted_function():
    # ... your code
    pass
```

### Using Context Managers

```python
from common.metrics import Metrics, measure_time

# Using the Metrics class directly
metrics = Metrics.get_instance()
with metrics.timer("my_operation"):
    # ... your code
    pass

# Using the convenience function
with measure_time("my_operation", {"label": "value"}):
    # ... your code
    pass
```

### Direct Recording

```python
from common.metrics import (
    get_metrics,
    record_duration,
    increment_counter,
    set_gauge
)

# Record duration
record_duration("custom_operation", duration_seconds, {"tag": "value"})

# Increment counter
increment_counter("events", 1, {"type": "error"})

# Set gauge
set_gauge("queue_size", current_size, {"queue": "main"})

# Using the Metrics instance directly
metrics = get_metrics()
metrics.histogram("my_histogram", value, labels={"label": "value"})
metrics.counter("my_counter", 1, labels={"label": "value"})
metrics.gauge("my_gauge", value, labels={"label": "value"})
```

## Prometheus Integration

### Scrape Configuration

Add RAGFlow to your Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'ragflow'
    static_configs:
      - targets: ['ragflow-server:9380']
    metrics_path: '/v1/metrics/prometheus'
    scrape_interval: 15s
```

### Alert Rules

Example alert rules for common issues:

```yaml
groups:
  - name: ragflow
    rules:
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, sum(rate(api_request_duration_seconds_bucket[5m])) by (le)) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          description: "95th percentile API latency is above 5 seconds"

      - alert: HighErrorRate
        expr: sum(rate(api_requests_total{status=~"5.."}[5m])) / sum(rate(api_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5%"

      - alert: SlowPDFParsing
        expr: histogram_quantile(0.95, sum(rate(pdf_parse_duration_seconds_bucket[5m])) by (le)) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow PDF parsing detected"
          description: "95th percentile PDF parsing time is above 60 seconds"
```

## Grafana Dashboard

A pre-built Grafana dashboard is available at `docker/monitoring/grafana-dashboard.json`.

### Importing the Dashboard

1. Open Grafana
2. Go to Dashboards > Import
3. Upload the JSON file or paste its contents
4. Select your Prometheus data source
5. Click Import

### Dashboard Panels

The dashboard includes:
- **API Performance**: Request duration and rate by endpoint
- **Document Processing**: PDF parsing and embedding generation times
- **Search & LLM**: Search query and LLM inference durations
- **Error Rates**: API error rates by endpoint

## Dependencies

For full Prometheus support, install the `prometheus_client` package:

```bash
pip install prometheus_client
```

Without this package, the system falls back to simple in-memory metrics that are still accessible via the JSON endpoint.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  Application    │────▶│  Metrics Module  │────▶│  Prometheus   │
│  (PDF, LLM,     │     │  (common/metrics │     │  /v1/metrics/ │
│   Search, API)  │     │   .py)           │     │  prometheus   │
└─────────────────┘     └──────────────────┘     └───────────────┘
                                │
                                ▼
                        ┌───────────────┐
                        │  JSON API     │
                        │  /v1/metrics/ │
                        │  json         │
                        └───────────────┘
```

## Best Practices

1. **Use meaningful metric names**: Follow the pattern `<subsystem>_<operation>_<unit>`
2. **Add appropriate labels**: Use labels for dimensions like `model`, `endpoint`, `status`
3. **Don't over-label**: Too many label combinations can cause cardinality issues
4. **Use histograms for durations**: Histograms allow calculating percentiles
5. **Use counters for events**: Counters only go up, perfect for request counts
6. **Use gauges for current values**: Gauges can go up or down, perfect for queue sizes

## Troubleshooting

### Metrics Not Appearing

1. Check if the application started successfully
2. Verify the metrics endpoint is accessible: `curl http://localhost:9380/v1/metrics/health`
3. Check application logs for errors

### High Cardinality

If Prometheus is slow or using too much memory:
1. Review label usage in custom metrics
2. Reduce the number of unique label combinations
3. Consider aggregating metrics before export

### Missing Prometheus Metrics

If only JSON metrics are available:
1. Install `prometheus_client`: `pip install prometheus_client`
2. Restart the application

## Performance Impact

The metrics collection is designed to be lightweight:
- Timer overhead: ~1-5 microseconds per operation
- Memory usage: Limited to 1000 entries per metric (simple metrics)
- Thread-safe: Safe for concurrent use

For extremely high-throughput scenarios, consider sampling or batching metrics.
