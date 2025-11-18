# Performance Analysis and Scaling RAGFlow

**Reading time:** 8 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- Performance characteristics of key operations
- Bottlenecks and optimization opportunities
- Concurrent processing model
- Scaling strategies for production

---

## Introduction

Understanding performance characteristics is crucial for production deployments. This post analyzes RAGFlow's performance profile, identifies bottlenecks, and explores scaling strategies.

---

## Performance Profile

### Operation Timing

| Operation | Typical Time | Bottleneck |
|-----------|--------------|------------|
| PDF upload (10 pages) | 1-2s | Network I/O |
| PDF parsing (10 pages) | 5-15s | CPU (layout recognition) |
| PDF parsing (50 pages) | 30-60s | CPU + memory |
| Scanned PDF OCR | 2-5 min/100 pages | GPU/CPU |
| Embedding (100 chunks) | 2-10s | API latency |
| Hybrid search | 100-500ms | Elasticsearch |
| LLM inference | 2-30s | Model/API |

### Memory Footprint

| Component | Memory Usage |
|-----------|--------------|
| Flask server | 500MB-1GB |
| PDF parser (per doc) | 200-500MB |
| OCR models (loaded) | 500MB-1GB |
| Embedding batch | 100-300MB |

---

## Bottleneck Analysis

### 1. PDF Parsing (CPU-bound)

The PDF parser is the primary bottleneck for document-heavy workflows:

```python
# Performance-critical path
def parse_pdf(binary):
    # 1. Extract with pdfplumber (~20% of time)
    pdf = pdfplumber.open(BytesIO(binary))

    # 2. Layout recognition (~40% of time)
    for page in pdf.pages:
        image = page.to_image()
        layout = layout_recognizer(image)  # ONNX inference

    # 3. OCR if needed (~30% of time for scanned docs)
    if needs_ocr:
        ocr_results = ocr_engine(images)

    # 4. Text concatenation (~10% of time)
    merged = concat_with_xgboost(sections)
```

**Optimization opportunities:**

1. **Parallel page processing**: Pages can be processed independently
2. **GPU acceleration**: ONNX Runtime with CUDA
3. **Selective OCR**: Skip OCR for text-heavy PDFs
4. **Model quantization**: INT8 models for faster inference

### 2. Embedding Generation (API-bound)

```python
# Current implementation
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    embeddings = api_call(batch)  # Network latency
```

**Optimization opportunities:**

1. **Increase batch size**: 32-64 for local models
2. **Async requests**: Parallel API calls
3. **Local models**: Eliminate API latency
4. **Caching**: Cache embeddings for unchanged content

### 3. Search Latency (I/O-bound)

```python
# Hybrid search timing breakdown
# - Full-text query: ~20ms
# - Vector query: ~50-100ms
# - Fusion: ~10ms
# - Reranking: ~100-500ms (optional)
```

**Optimization opportunities:**

1. **Elasticsearch tuning**: Replica shards, query caching
2. **Index optimization**: Proper field types, refresh interval
3. **Skip reranking**: For time-sensitive queries
4. **Infinity DB**: Alternative with better vector performance

---

## Concurrent Processing Model

### Flask Server

```python
# api/ragflow_server.py
run_simple(
    hostname=settings.HOST_IP,
    port=settings.HOST_PORT,
    application=app,
    threaded=True,  # Thread per request
)
```

**Characteristics:**
- Thread-per-request model
- Suitable for I/O-bound operations
- Not ideal for CPU-bound (GIL limitation)

### Document Processing

```python
# Background task processing
# Uses distributed locking for singleton operations

lock = RedisDistributedLock("task_runner")
if lock.acquire():
    process_pending_documents()
    lock.release()
```

### Agent Workflow Execution

```python
# Concurrent component execution
executor = ThreadPoolExecutor(max_workers=5)

for component_id in execution_order:
    future = executor.submit(component.run)
```

**Limitation:** Only 5 concurrent components per workflow execution.

### Async Operations with Trio

```python
# Embedding pipeline uses Trio for async
import trio

async def embed_chunks(chunks):
    async with trio.open_nursery() as nursery:
        for batch in batches:
            nursery.start_soon(embed_batch, batch)
```

---

## Scaling Strategies

### Horizontal Scaling

```
                    Load Balancer
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
   │ RAGFlow │     │ RAGFlow │     │ RAGFlow │
   │   #1    │     │   #2    │     │   #3    │
   └────┬────┘     └────┬────┘     └────┬────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────┴────┐ ┌───┴────┐ ┌───┴───┐
         │  MySQL  │ │  ES    │ │ Redis │
         │(primary)│ │(cluster)│ │(cluster)│
         └─────────┘ └────────┘ └───────┘
```

**Requirements:**
- Shared MySQL (or replicas)
- Elasticsearch cluster
- Redis for distributed locking
- Shared MinIO for file storage

### Kubernetes Deployment

```yaml
# helm/values.yaml
replicaCount: 3

resources:
  requests:
    memory: "2Gi"
    cpu: "2"
  limits:
    memory: "4Gi"
    cpu: "4"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Database Scaling

**Elasticsearch:**
- Increase shards for large indices
- Add replica shards for read throughput
- Use SSD storage for better I/O

```json
{
  "settings": {
    "number_of_shards": 5,
    "number_of_replicas": 2,
    "refresh_interval": "5s"
  }
}
```

**MySQL:**
- Read replicas for query scaling
- Connection pooling
- Query optimization

---

## Resource Recommendations

### Development

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 16GB | 32GB |
| Disk | 50GB SSD | 100GB SSD |
| GPU | Optional | GTX 1080+ |

### Production (per instance)

| Resource | Small | Medium | Large |
|----------|-------|--------|-------|
| CPU | 4 cores | 8 cores | 16 cores |
| RAM | 8GB | 16GB | 32GB |
| Disk | 100GB | 500GB | 1TB |

### Production (total cluster)

| Workload | Instances | ES Nodes | MySQL |
|----------|-----------|----------|-------|
| 100 users | 2 | 3 | 1 |
| 1000 users | 5 | 5 | 2 (primary + replica) |
| 10000 users | 10+ | 7+ | 3+ (cluster) |

---

## Optimization Checklist

### Quick Wins (< 1 week)

- [ ] Enable GPU for OCR/layout recognition
- [ ] Increase Elasticsearch query cache size
- [ ] Set appropriate chunk token sizes (512-1024)
- [ ] Skip reranking for latency-sensitive queries
- [ ] Use local embedding models for high volume

### Medium Term (2-4 weeks)

- [ ] Implement embedding caching
- [ ] Add async document processing queue
- [ ] Optimize PDF parser with parallel pages
- [ ] Configure Elasticsearch index settings
- [ ] Set up monitoring and alerting

### Long Term (> 1 month)

- [ ] Migrate to Infinity for better vector performance
- [ ] Implement model quantization (INT8)
- [ ] Add GPU cluster for heavy workloads
- [ ] Custom chunking for domain-specific documents
- [ ] Implement tiered storage (hot/warm/cold)

---

## Monitoring Recommendations

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| API response time | > 5s p95 |
| Document processing time | > 2min per doc |
| Search latency | > 1s p95 |
| Error rate | > 1% |
| Queue depth | > 100 pending |

### Logging

```python
# Current logging configuration
LOG_FORMAT = "%(asctime)-15s %(levelname)-8s %(process)d %(message)s"

# Recommended additions:
# - Request tracing IDs
# - Operation timing
# - Resource utilization
```

### Suggested Stack

- **Metrics**: Prometheus + Grafana
- **Logs**: ELK Stack or Loki
- **Tracing**: Jaeger or Zipkin
- **Alerts**: AlertManager or PagerDuty

---

## Benchmarking

### Document Processing Benchmark

```python
import time
from rag.app.naive import chunk

def benchmark_parsing(file_path, iterations=10):
    with open(file_path, 'rb') as f:
        binary = f.read()

    times = []
    for _ in range(iterations):
        start = time.time()
        chunks = chunk("test.pdf", binary)
        times.append(time.time() - start)

    return {
        "mean": sum(times) / len(times),
        "min": min(times),
        "max": max(times),
        "p95": sorted(times)[int(0.95 * len(times))]
    }
```

### Search Benchmark

```python
def benchmark_search(kb_id, queries, iterations=100):
    times = []
    for query in queries:
        for _ in range(iterations // len(queries)):
            start = time.time()
            results = search(kb_id, query)
            times.append(time.time() - start)

    return {
        "mean_ms": 1000 * sum(times) / len(times),
        "p95_ms": 1000 * sorted(times)[int(0.95 * len(times))]
    }
```

---

## Key Takeaways

1. **PDF parsing is the main bottleneck**—CPU-bound with layout recognition taking ~40% of time.

2. **Embedding generation is API-bound**—batch optimization and local models help.

3. **Horizontal scaling works well** with proper shared state (Redis locks, shared storage).

4. **GPU acceleration is important** for OCR-heavy workloads.

5. **Monitor operation timing** to identify regressions and optimization opportunities.

6. **Kubernetes HPA** works well for handling variable loads.

---

## Conclusion

RAGFlow's performance is primarily bounded by document parsing for ingestion and LLM latency for queries. The architecture supports horizontal scaling, but careful attention to resource allocation and configuration is needed for production deployments.

For most use cases, start with the recommended development configuration, monitor actual performance, and scale based on observed bottlenecks rather than anticipated load.

---

## Further Reading

- [RFC-0002: PDF Parser Modularization](../rfcs/RFC-0002-pdf-parser-modularization.md)
- [RFC-0005: Performance Monitoring](../rfcs/RFC-0005-performance-monitoring.md)
- [Metrics Summary](../initial-analysis/metrics-summary.md)
