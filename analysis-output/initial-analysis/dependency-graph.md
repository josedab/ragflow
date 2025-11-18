# RAGFlow Dependency Graph

**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## Technology Stack Visualization

```mermaid
graph TB
    subgraph Frontend["Frontend (React)"]
        UMI[UmiJS 4]
        REACT[React 18]
        TS[TypeScript 5]
        ZUSTAND[Zustand]
        RQ[React Query]
        ANTD[Ant Design 5]
        RADIX[Radix UI/shadcn]
        TAILWIND[Tailwind CSS]
        XYFLOW[XYFlow]
    end

    subgraph Backend["Backend (Python)"]
        FLASK[Flask 3]
        PEEWEE[Peewee ORM]
        WERKZEUG[Werkzeug]
        FLASGGER[Flasgger/Swagger]
    end

    subgraph AI["AI/ML Layer"]
        OPENAI[OpenAI SDK]
        ANTHROPIC[Anthropic SDK]
        LITELLM[LiteLLM]
        ONNX[ONNX Runtime]
        XGBOOST[XGBoost]
        SKLEARN[scikit-learn]
    end

    subgraph DocProc["Document Processing"]
        PDFPLUMBER[pdfplumber]
        PYPDF[PyPDF]
        DOCX[python-docx]
        OPENCV[OpenCV]
        NLTK[NLTK]
        TIKTOKEN[tiktoken]
    end

    subgraph DataLayer["Data Layer"]
        ES[Elasticsearch 8]
        INFINITY[Infinity]
        MYSQL[MySQL]
        REDIS[Redis/Valkey]
        MINIO[MinIO]
    end

    subgraph Infra["Infrastructure"]
        DOCKER[Docker]
        K8S[Kubernetes]
        NGINX[Nginx]
        HELM[Helm]
    end

    REACT --> ZUSTAND
    REACT --> RQ
    REACT --> ANTD
    REACT --> RADIX
    UMI --> REACT
    TS --> UMI

    FLASK --> PEEWEE
    FLASK --> WERKZEUG
    FLASK --> FLASGGER

    AI --> Backend
    DocProc --> Backend
    Backend --> DataLayer
    Frontend --> Backend
    Infra --> DataLayer
    Infra --> Backend
```

## Core Dependencies by Category

### Python Backend Framework

```mermaid
graph LR
    A[Flask 3.0.3] --> B[Werkzeug 3.0.6]
    A --> C[Blinker 1.7.0]
    A --> D[Flask-CORS 5.0.0]
    A --> E[Flask-Login 0.6.3]
    A --> F[Flask-Session 0.8.0]
    A --> G[Flask-Mail 0.10.0]
    A --> H[Flasgger 0.9.7.1]
    I[Peewee 3.17.1] --> J[PyMySQL 1.1.1]
```

### LLM Provider Dependencies

| Provider | Package | Version | Purpose |
|----------|---------|---------|---------|
| OpenAI | openai | >= 1.45.0 | GPT models, embeddings |
| Anthropic | anthropic | 0.34.1 | Claude models |
| LiteLLM | litellm | >= 1.74.15 | Universal LLM proxy (26 providers) |
| Google | google-genai | >= 1.41.0 | Gemini models |
| Google | vertexai | 1.70.0 | Vertex AI models |
| Azure | azure-identity | 1.17.1 | Azure authentication |
| Zhipu | zhipuai | 2.0.1 | Zhipu AI (GLM) |
| Baidu | qianfan | 0.4.6 | Baidu Qianfan |
| ByteDance | volcengine | 1.0.194 | Volcano Engine |
| Alibaba | dashscope | 1.20.11 | Tongyi Qianwen |
| Cohere | cohere | 5.6.2 | Cohere embeddings/rerank |
| Mistral | mistralai | 0.4.2 | Mistral models |
| Groq | groq | 0.9.0 | Groq inference |
| Replicate | replicate | 0.31.0 | Replicate models |
| Voyage | voyageai | 0.2.3 | Voyage embeddings |
| Ollama | ollama | >= 0.5.0 | Local models |

### Document Processing Dependencies

```mermaid
graph TD
    subgraph PDF
        A[pdfplumber 0.10.4]
        B[pypdf 6.0.0]
        C[pypdf2 3.0.1]
    end

    subgraph Office
        D[python-docx 1.1.2]
        E[python-pptx 1.0.2]
        F[openpyxl 3.1.0]
    end

    subgraph Vision
        G[opencv-python 4.10.0.84]
        H[pillow 10.4.0]
        I[onnxruntime 1.19.2]
    end

    subgraph NLP
        J[nltk 3.9.1]
        K[tiktoken 0.7.0]
        L[datrie 0.8.3]
    end
```

### Frontend Component Dependencies

```mermaid
graph TD
    subgraph Core
        A[React 18.2.0]
        B[UmiJS 4.0.90]
        C[TypeScript 5.0.3]
    end

    subgraph State
        D[Zustand 4.5.2]
        E[React Query 5.40.0]
        F[Immer 10.1.1]
    end

    subgraph UI
        G[Ant Design 5.12.7]
        H[Radix UI 27 packages]
        I[Tailwind CSS 3]
        J[Lucide React 0.546.0]
    end

    subgraph Visualization
        K[XYFlow 12.3.6]
        L[Recharts 2.12.4]
        M[AntV G6 5.0.10]
    end

    A --> D
    A --> E
    A --> G
    A --> H
    B --> A
    C --> B
```

## Data Storage Dependencies

### Primary Data Stores

| Service | Package | Version | Purpose |
|---------|---------|---------|---------|
| Elasticsearch | elasticsearch | 8.12.1 | Vector search, full-text |
| Elasticsearch DSL | elasticsearch-dsl | 8.12.0 | Query building |
| OpenSearch | opensearch-py | 2.7.1 | AWS alternative |
| Infinity | infinity-sdk | 0.6.5 | High-performance alternative |
| Redis | valkey | 6.0.2 | Caching, distributed locks |
| MinIO | minio | 7.2.4 | Object storage |
| MySQL | pymysql | 1.1.1 | Relational data |

### Storage Dependency Flow

```mermaid
graph LR
    subgraph Application
        A[RAGFlow Backend]
    end

    subgraph VectorDB
        B[Elasticsearch]
        C[OpenSearch]
        D[Infinity]
    end

    subgraph RelationalDB
        E[MySQL]
    end

    subgraph Cache
        F[Redis/Valkey]
    end

    subgraph ObjectStore
        G[MinIO]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
    A --> G
```

## External Service Dependencies

### Search & Web

| Package | Version | Purpose |
|---------|---------|---------|
| tavily-python | 0.5.1 | Web search tool |
| google-search-results | 2.4.2 | Google SERP |
| duckduckgo-search | >= 7.2.0 | DuckDuckGo search |
| Crawl4AI | >= 0.3.8 | Web crawling |
| selenium | 4.22.0 | Browser automation |

### Finance & Research

| Package | Version | Purpose |
|---------|---------|---------|
| yfinance | 0.2.65 | Yahoo Finance |
| akshare | >= 1.15.78 | Chinese financial data |
| scholarly | 1.7.11 | Google Scholar |
| arxiv | 2.1.3 | arXiv papers |
| wikipedia | 1.4.0 | Wikipedia API |

### Communication

| Package | Version | Purpose |
|---------|---------|---------|
| slack-sdk | 3.37.0 | Slack integration |
| discord-py | 2.3.2 | Discord bot |
| jira | 3.10.5 | Jira integration |
| atlassian-python-api | 4.0.7 | Atlassian APIs |

## Infrastructure Dependencies

### Docker Compose Services

```mermaid
graph TB
    subgraph DockerServices
        A[ragflow-server]
        B[mysql]
        C[es01/opensearch/infinity]
        D[redis]
        E[minio]
        F[ragflow-tei]
        G[sandbox-excutor]
        H[kibana]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
    A --> G
```

### Kubernetes/Helm Dependencies

- Kubernetes >= 1.19
- Helm >= 3.0
- PersistentVolumeClaim support
- Ingress controller (optional)

## Dependency Version Policies

### Pinning Strategy

| Category | Strategy | Example |
|----------|----------|---------|
| Core Framework | Exact version | flask==3.0.3 |
| LLM Providers | Minimum with ceiling | openai>=1.45.0 |
| Minor dependencies | Range | pandas>=2.2.0,<3.0.0 |
| Dev dependencies | Range | pytest>=8.3.5 |

### Update Frequency Recommendations

| Category | Frequency | Rationale |
|----------|-----------|-----------|
| Security patches | Weekly | Critical vulnerabilities |
| LLM SDKs | Monthly | API changes |
| UI frameworks | Quarterly | Breaking changes |
| Core framework | 6 months | Stability |

## Potential Issues

### Heavy Dependencies

| Package | Size | Alternative |
|---------|------|-------------|
| opencv-python | 50MB+ | opencv-python-headless (used) |
| onnxruntime-gpu | 200MB+ | CPU version for non-GPU |
| pytorch (implicit) | 500MB+ | Optional, for some models |

### Deprecation Warnings

- `selenium-wire` 5.1.0 - Uses deprecated APIs
- Some `numpy` usage may need updates for numpy 2.0

### License Considerations

All dependencies appear to be compatible with Apache 2.0 license. Notable licenses:
- Most packages: MIT, BSD, Apache 2.0
- NLTK: Apache 2.0
- OpenCV: Apache 2.0

## Dependency Update Checklist

When updating dependencies:

1. [ ] Check changelog for breaking changes
2. [ ] Run full test suite
3. [ ] Verify LLM provider compatibility
4. [ ] Test document parsing accuracy
5. [ ] Check frontend build
6. [ ] Verify Docker images build
7. [ ] Test Kubernetes deployment
8. [ ] Update documentation if needed
