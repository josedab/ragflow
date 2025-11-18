# RAGFlow Quick Start Guide

**Analysis Date:** November 18, 2025
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`
**Version:** 0.22.0

## Executive Summary

RAGFlow is a production-grade, open-source RAG (Retrieval-Augmented Generation) engine built on deep document understanding. It's a full-stack application combining:

- **Python Backend**: Flask-based API server with Peewee ORM
- **React Frontend**: UmiJS 4 framework with TypeScript
- **Microservices**: Docker-based deployment with 9+ services
- **AI Integration**: 50+ LLM providers, 30+ embedding models

## Key Metrics at a Glance

| Metric | Value |
|--------|-------|
| Total Lines of Code | 260,575 |
| Python Files | 523 |
| TypeScript/TSX Files | 1,140 |
| Test Files | 103 |
| Documentation Files | 48 |
| Python LOC | 116,698 |
| Frontend LOC | 143,877 |
| Dependencies (Python) | 140+ |
| Dependencies (Frontend) | 120+ |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    RAGFlow Architecture                  │
├─────────────────────────────────────────────────────────┤
│  Frontend (React + UmiJS + TypeScript)                  │
│  - Ant Design + shadcn/ui components                    │
│  - Zustand + React Query state management               │
│  - XYFlow for workflow canvas                           │
├─────────────────────────────────────────────────────────┤
│  API Layer (Flask + Blueprints)                         │
│  - RESTful endpoints with Swagger/OpenAPI               │
│  - Session + Token + OAuth authentication               │
│  - 180+ API endpoints across 9 modules                  │
├─────────────────────────────────────────────────────────┤
│  Service Layer (Peewee ORM + MySQL)                     │
│  - 28 database models                                   │
│  - 20+ service classes                                  │
│  - Distributed locking with Redis                       │
├─────────────────────────────────────────────────────────┤
│  RAG Core (Document Processing + LLM)                   │
│  - 14+ document parsers (PDF, DOCX, Excel, etc.)        │
│  - OCR + Layout recognition + Table detection           │
│  - 50+ LLM providers with unified interface             │
├─────────────────────────────────────────────────────────┤
│  Agent System (Workflow Engine)                         │
│  - 17 agent components                                  │
│  - 22 external tool integrations                        │
│  - GraphRAG with knowledge graphs                       │
├─────────────────────────────────────────────────────────┤
│  Data Layer                                             │
│  - Elasticsearch/OpenSearch/Infinity (vector search)    │
│  - MySQL (relational data)                              │
│  - Redis (caching, distributed locks)                   │
│  - MinIO (object storage)                               │
└─────────────────────────────────────────────────────────┘
```

## Top 5 Findings

### 1. Deep Document Understanding
RAGFlow's PDF parser (1,400+ lines) implements sophisticated document understanding with:
- Layout recognition (11 element types)
- OCR with multi-language support
- Table structure detection
- XGBoost-based text concatenation decisions

### 2. Flexible LLM Abstraction
Factory pattern with dynamic registration supports 50+ LLM providers through a unified interface with:
- Automatic retry with exponential backoff
- Error classification and handling
- Streaming support for all providers

### 3. Hybrid Search Implementation
Combines full-text (BM25) and semantic (vector) search with configurable weights:
- Default: 5% full-text, 95% semantic
- Automatic fallback on no results
- Optional reranking step

### 4. Agent Workflow System
Visual workflow editor with:
- DAG-based execution model
- Variable late-binding via regex patterns
- ThreadPoolExecutor (5 workers max)
- Real-time streaming events

### 5. Enterprise-Ready Features
- Multi-tenant support with team sharing
- OAuth integration (GitHub, Google, etc.)
- Kubernetes deployment via Helm
- MCP (Model Context Protocol) server

## Quick Navigation

- **[Repository Structure](./repository-structure.md)** - Directory layout and key files
- **[Dependency Graph](./dependency-graph.md)** - Technology stack visualization
- **[Metrics Summary](./metrics-summary.md)** - Detailed code metrics
- **[Terminology Glossary](./terminology-glossary.md)** - Project-specific terms

## Getting Started for Contributors

### Prerequisites
- Python 3.10-3.12
- Node.js >= 18.20.4
- Docker & Docker Compose
- 16GB+ RAM, 50GB+ disk

### Quick Development Setup

```bash
# Backend
uv sync --python 3.10 --all-extras
uv run download_deps.py
pre-commit install

# Start services
docker compose -f docker/docker-compose-base.yml up -d

# Run backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh

# Frontend (in separate terminal)
cd web
npm install
npm run dev
```

## Key Design Decisions

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Architecture | Modular monolith with microservices data layer | Simplicity over pure microservices complexity |
| ORM | Peewee (lightweight) | Simplicity over SQLAlchemy's features |
| Frontend State | Zustand + React Query | Separation of client/server state |
| Document Engine | Elasticsearch/Infinity switchable | Flexibility over single-vendor lock-in |
| LLM Integration | Factory pattern with 50+ providers | Maintenance burden for broad compatibility |

## Recommended Reading Order

1. **This document** - High-level overview
2. **[Blog 1: Architecture Overview](../blog-series/01-architecture-overview.md)** - Detailed architecture
3. **[Repository Structure](./repository-structure.md)** - Navigate the codebase
4. **[Blog 2: Deep Dive into Document Processing](../blog-series/02-deep-dive-document-processing.md)** - Core RAG functionality
5. **[RFCs](../rfcs/)** - Improvement proposals

## Contact & Resources

- **GitHub**: https://github.com/infiniflow/ragflow
- **Documentation**: https://ragflow.io/docs
- **Issues**: https://github.com/infiniflow/ragflow/issues

---

*This analysis is based on commit `341e5904c847948d13e339f7df6aacd67ab8b652` and reflects the state of RAGFlow v0.22.0 as of November 2025.*
