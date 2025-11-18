# RFC-0005: Performance Monitoring Infrastructure

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 3-5 days
**Priority:** P1 (Quick Win)

## Summary

Add comprehensive performance monitoring to track operation times, identify bottlenecks, and enable data-driven optimization decisions.

## Motivation

Currently lacking:
1. **No timing metrics**: Can't measure operation performance
2. **No bottleneck identification**: Guessing at slow spots
3. **No regression detection**: Performance issues go unnoticed
4. **No capacity planning data**: Can't predict scaling needs

## Detailed Design

### Metrics Collection

```python
# common/metrics.py
import time
from functools import wraps
from contextlib import contextmanager

class Metrics:
    """Simple metrics collection"""

    _instance = None
    _metrics = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(self, name, value, tags=None):
        """Record a metric value"""
        key = self._make_key(name, tags)
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append({
            'value': value,
            'timestamp': time.time()
        })

    def timer(self, name, tags=None):
        """Context manager for timing"""
        return TimerContext(self, name, tags)

    @staticmethod
    def timed(name, tags=None):
        """Decorator for timing functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    Metrics.get_instance().record(
                        f"{name}.duration_seconds",
                        duration,
                        tags
                    )
            return wrapper
        return decorator


class TimerContext:
    def __init__(self, metrics, name, tags):
        self.metrics = metrics
        self.name = name
        self.tags = tags

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start
        self.metrics.record(
            f"{self.name}.duration_seconds",
            duration,
            self.tags
        )
```

### Integration Points

```python
# PDF Parsing
@Metrics.timed("pdf.parse", tags={"parser": "deepdoc"})
def parse_pdf(binary):
    # ... existing code

# Search
with Metrics.get_instance().timer("search.query"):
    results = es_conn.search(query)

# LLM Calls
@Metrics.timed("llm.chat")
def chat(self, messages, gen_conf):
    # ... existing code
```

### Prometheus Endpoint

```python
# api/apps/metrics_app.py
from flask import Blueprint
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

metrics_app = Blueprint('metrics', __name__)

@metrics_app.route('/metrics')
def prometheus_metrics():
    """Expose metrics for Prometheus scraping"""
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pdf_parse_duration_seconds` | Histogram | PDF parsing time |
| `embedding_duration_seconds` | Histogram | Embedding generation time |
| `search_duration_seconds` | Histogram | Search query time |
| `llm_duration_seconds` | Histogram | LLM inference time |
| `api_request_duration_seconds` | Histogram | API endpoint time |
| `document_queue_size` | Gauge | Pending documents |
| `active_connections` | Gauge | Database connections |

## Implementation Plan

### Day 1-2: Foundation
1. Create metrics collection module
2. Add timing decorator and context manager
3. Set up Prometheus endpoint

### Day 3-4: Integration
1. Add metrics to PDF parser
2. Add metrics to embedding pipeline
3. Add metrics to search
4. Add metrics to LLM calls
5. Add API middleware for request timing

### Day 5: Dashboard
1. Create Grafana dashboard template
2. Configure alerts for key thresholds
3. Documentation

## Success Criteria

- [ ] All key operations have timing metrics
- [ ] Prometheus endpoint exposing metrics
- [ ] Grafana dashboard showing performance
- [ ] Alerts for performance regressions
- [ ] Documentation for adding new metrics

## Stakeholder Approvals

- [ ] Ops/SRE Lead
- [ ] Backend Lead
