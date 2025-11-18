# Understanding RAGFlow: Architecture and Core Concepts

**Reading time:** 12 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- RAGFlow's modular monolith architecture and why it was chosen
- Core abstractions and how they interact
- Key design decisions with their trade-offs
- Data flow from document upload to chat response

---

## Introduction

RAGFlow is an open-source RAG (Retrieval-Augmented Generation) engine that prioritizes "deep document understanding" over simple text extraction. With 260k+ lines of code across Python backend and TypeScript frontend, it's a substantial system worth understanding architecturally.

In this post, we'll explore how RAGFlow is structured, why certain decisions were made, and how the pieces fit together. Whether you're evaluating RAGFlow for your project or preparing to contribute, this architectural overview will give you the mental model you need.

---

## The Big Picture: Modular Monolith

RAGFlow follows a **modular monolith** architecture—a single deployable application with clear internal module boundaries, backed by distributed data services.

```
┌─────────────────────────────────────────────────────────────┐
│                    RAGFlow Monolith                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  API Layer  │  │ RAG Pipeline│  │ Agent System│         │
│  │  (Flask)    │  │  (deepdoc)  │  │ (workflows) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│  ┌───────────────────────┼───────────────────────────────┐ │
│  │              Service Layer (Peewee ORM)               │ │
│  └───────────────────────┬───────────────────────────────┘ │
└──────────────────────────┼──────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───┴───┐  ┌───────────────┴────────────┐  ┌─────┴────┐
│ MySQL │  │ Elasticsearch/Infinity     │  │  Redis   │
│(meta) │  │ (vectors + full-text)      │  │ (cache)  │
└───────┘  └────────────────────────────┘  └──────────┘
```

### Why Modular Monolith?

**Trade-off: Simplicity over microservices complexity**

RAGFlow could have been built as microservices—separate services for parsing, embedding, search, etc. Instead, the team chose a monolith because:

1. **Simpler deployment**: One container to manage, easier for self-hosting
2. **Lower latency**: No network hops between parsing and indexing
3. **Easier debugging**: Stack traces span the full operation
4. **Team size**: Works well for teams under 50 engineers

The "modular" part comes from clear package boundaries. The `rag/`, `agent/`, and `api/` directories are cohesive modules that could theoretically be extracted into services later.

---

## Core Architectural Layers

### 1. API Layer (Flask)

The API layer is built with Flask, organized into blueprints by domain:

```python
# api/apps/__init__.py (simplified)
from flask import Flask

app = Flask(__name__)

# Register blueprints
from api.apps.kb_app import manager as kb_manager
from api.apps.dialog_app import manager as dialog_manager
from api.apps.document_app import manager as document_manager

app.register_blueprint(kb_manager, url_prefix='/api/v1/kb')
app.register_blueprint(dialog_manager, url_prefix='/api/v1/dialog')
app.register_blueprint(document_manager, url_prefix='/api/v1/document')
```

**Code reference:** [api/apps/__init__.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/apps/__init__.py)

Each blueprint owns its domain:
- **kb_app**: Knowledge base CRUD
- **dialog_app**: Chat application management
- **document_app**: Document upload and processing
- **canvas_app**: Agent workflow operations
- **file_app**: File storage management

**Key Design Choice: REST with Standard Response Format**

All endpoints return a consistent JSON structure:

```python
{
    "code": 0,           # 0 = success, non-zero = error
    "message": "success",
    "data": { ... }      # Response payload
}
```

This consistency makes client integration predictable, though it differs from pure REST conventions where HTTP status codes convey success/failure.

### 2. Service Layer (Peewee ORM)

Between the API and database sits a service layer that encapsulates business logic:

```python
# api/db/services/document_service.py (simplified)
class DocumentService(CommonService):
    model = Document

    @classmethod
    @DB.connection_context()
    def get_by_kb_id(cls, kb_id, page, size, order_by, descend, keywords):
        docs = cls.model.select().where(cls.model.kb_id == kb_id)
        if keywords:
            docs = docs.where(cls.model.name.contains(keywords))
        # ... pagination, ordering
        return list(docs), total
```

**Code reference:** [api/db/services/document_service.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/db/services/document_service.py)

**Why Peewee instead of SQLAlchemy?**

Trade-off: Simplicity over features

- Peewee has a smaller API surface
- Explicit connection context management
- Good enough for CRUD operations
- Less "magic" than SQLAlchemy's ORM

### 3. RAG Pipeline (Document Processing)

The heart of RAGFlow is its document processing pipeline:

```
Document Upload
    ↓
Parser Selection (based on file type + configuration)
    ↓
Content Extraction + Layout Recognition
    ↓
Chunking (naive/hierarchical/tree)
    ↓
Embedding Generation
    ↓
Indexing (Elasticsearch/Infinity)
```

We'll explore this deeply in Blog 2, but here's the key abstraction:

```python
# rag/app/naive.py (simplified)
def chunk(filename, binary, callback, **kwargs):
    """Main entry point for document processing"""
    # 1. Detect format and select parser
    parser = get_parser(filename, kwargs.get('parser_id'))

    # 2. Parse document into sections
    sections = parser(filename, binary)

    # 3. Apply chunking strategy
    chunks = chunking(sections,
                      chunk_token_num=kwargs.get('chunk_token_num', 512),
                      delimiter=kwargs.get('delimiter', '\n'))

    # 4. Generate embeddings
    embeddings = embed_model.encode([c['content'] for c in chunks])

    return chunks, embeddings
```

**Code reference:** [rag/app/naive.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/app/naive.py)

### 4. Agent System (Workflows)

The agent system provides visual workflow building with a DAG execution model:

```python
# agent/component/base.py (simplified)
class ComponentBase:
    component_name = "base"

    def _run(self, history, **kwargs):
        """Execute this component"""
        raise NotImplementedError

    def output(self, **kwargs):
        """Get component outputs for downstream"""
        return self._output
```

Components connect via edges that define data flow. Variables use pattern matching for late binding:

```python
# Pattern: {{component_id@variable_name}}
input_text = "The context is: {{retrieval_0@content}}"
```

**Code reference:** [agent/component/](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/agent/component/)

---

## Data Model

RAGFlow uses 28 database models organized around these core entities:

### Multi-Tenancy Model

```
Tenant (1) ──── (N) User
   │
   ├── (N) Knowledgebase
   │         ├── (N) Document
   │         │         └── (N) Chunk
   │         └── (N) File
   │
   ├── (N) Dialog (Chat App)
   │         └── (N) Conversation
   │                   └── (N) Message
   │
   └── (N) Canvas (Agent Workflow)
```

**Key Design Decision: Tenant as Account**

Rather than a separate User and Organization model, RAGFlow uses Tenant as the top-level account entity. A User belongs to a Tenant and can be invited to other Tenants' teams.

```python
# api/db/db_models.py (simplified)
class Tenant(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=100)
    llm_id = CharField(max_length=128)  # Default LLM
    embd_id = CharField(max_length=128)  # Default embedding
    # ... quotas, settings

class User(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32)  # Parent tenant
    email = CharField(max_length=255, unique=True)
```

**Code reference:** [api/db/db_models.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/db/db_models.py)

### Soft Delete Pattern

All models use status flags instead of hard deletes:

```python
class Document(DataBaseModel):
    status = CharField(max_length=1, default='1')  # '1' = active, '0' = deleted
```

This preserves audit trails and allows recovery, but requires filtering deleted records in every query—a trade-off between data safety and query complexity.

---

## Configuration Management

RAGFlow uses a layered configuration approach:

### Layer 1: Environment Variables

```bash
# docker/.env
DOC_ENGINE=elasticsearch  # or 'infinity'
MYSQL_HOST=mysql
REDIS_HOST=redis
```

### Layer 2: YAML Template

```yaml
# docker/service_conf.yaml.template
mysql:
  host: ${MYSQL_HOST:-mysql}
  port: ${MYSQL_PORT:-3306}
  user: ${MYSQL_USER:-root}
  password: ${MYSQL_PASSWORD}
  database: ${MYSQL_DATABASE:-ragflow}
```

### Layer 3: Runtime Config

```python
# api/db/runtime_config.py
class RuntimeConfig:
    DEBUG = False
    JOB_SERVER_HOST = None
    HTTP_PORT = None

    @classmethod
    def init_config(cls, **kwargs):
        for k, v in kwargs.items():
            setattr(cls, k, v)
```

**Why this layering?**

- Environment variables are standard for container orchestration
- YAML template allows complex nested configuration
- Runtime config enables programmatic overrides

---

## Data Flow: Upload to Chat Response

Let's trace a complete flow to see how components interact:

### 1. Document Upload

```
User → POST /api/v1/document/upload
    → file_app.upload()
    → MinIO.put_object()
    → DocumentService.insert()
    → Task.insert() (background job)
```

### 2. Document Processing (Background)

```
Task Runner → rag/app/naive.chunk()
    → deepdoc.parser.pdf_parser()
    → rag.nlp.chunking()
    → embedding_model.encode()
    → es_conn.insert() (index chunks)
    → DocumentService.update_status()
```

### 3. Chat Query

```
User → POST /api/v1/conversation/completion
    → dialog_app.completion()
    → rag.nlp.search.Dealer.search()  (hybrid search)
    → rerank_model.similarity()       (optional reranking)
    → chat_model.chat()               (LLM with context)
    → SSE stream → User
```

This separation of upload (sync), processing (async), and query (sync) enables responsive UX while handling heavy document processing in the background.

---

## Cross-Cutting Concerns

### Authentication

RAGFlow supports multiple auth methods:

1. **Session-based**: Flask-Login with cookies
2. **Token-based**: API keys in Authorization header
3. **OAuth**: GitHub, Google, etc.

```python
# api/apps/user_app.py (simplified)
@manager.route('/login', methods=['POST'])
def login():
    user = UserService.authenticate(email, password)
    if user:
        login_user(user)  # Flask-Login
        return get_json_result(data=user.to_dict())
```

### Error Handling

API endpoints wrap operations with consistent error handling:

```python
@manager.route('/create', methods=['POST'])
def create():
    try:
        # ... business logic
        return get_json_result(data=result)
    except Exception as e:
        return get_json_result(code=500, message=str(e))
```

### Distributed Locking

For operations that must be singleton across instances:

```python
# rag/utils/redis_conn.py
class RedisDistributedLock:
    def __init__(self, name, lock_value, timeout=60):
        self.name = f"lock:{name}"
        self.lock_value = lock_value
        self.timeout = timeout

    def acquire(self):
        return REDIS_CONN.set(self.name, self.lock_value,
                              nx=True, ex=self.timeout)
```

**Code reference:** [rag/utils/redis_conn.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/utils/redis_conn.py)

---

## Trade-offs Summary

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Architecture | Modular monolith | Simpler deployment vs microservice flexibility |
| ORM | Peewee | Simplicity vs SQLAlchemy features |
| API Style | REST + status codes in body | Consistency vs REST conventions |
| Soft Delete | Status flags | Data safety vs query complexity |
| Multi-tenancy | Tenant = Account | Simple model vs org hierarchies |
| Config | Env → YAML → Runtime | Flexibility vs complexity |

---

## Key Takeaways

1. **RAGFlow is a modular monolith** with clear internal boundaries, backed by distributed data services.

2. **The service layer pattern** encapsulates business logic and database operations, making the API layer thin.

3. **Document processing is async**—upload returns immediately, processing happens in background tasks.

4. **Multi-tenancy is first-class** with Tenant as the top-level entity owning all resources.

5. **Configuration is layered** from environment variables through YAML templates to runtime config.

---

## What's Next

In [Blog 2: Deep Dive into Document Processing](./02-deep-dive-document-processing.md), we'll explore the PDF parser, layout recognition, and chunking strategies that make RAGFlow's "deep document understanding" possible.

---

## Further Reading

- [Repository Structure](../initial-analysis/repository-structure.md)
- [Dependency Graph](../initial-analysis/dependency-graph.md)
- [RFC-0001: Service Layer Standardization](../rfcs/RFC-0001-service-layer-standardization.md)
