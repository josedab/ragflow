# Patterns and Practices in RAGFlow

**Reading time:** 9 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- Design patterns used throughout the codebase
- Service layer inheritance and code reuse
- Error handling and resilience strategies
- Security patterns and best practices

---

## Introduction

Understanding the patterns in a codebase helps you contribute effectively. RAGFlow employs several well-known patterns adapted to its needs. This post documents these patterns so you can follow conventions when adding features.

---

## Pattern 1: Factory Pattern for LLM Providers

RAGFlow supports 50+ LLM providers through a factory pattern with dynamic registration.

### Implementation

```python
# rag/llm/__init__.py
MODULE_MAPPING = {
    "chat_model": ChatModel,
    "embedding_model": EmbeddingModel,
    "rerank_model": RerankModel,
}

def get_model(model_type, factory_name, **kwargs):
    """Factory function to instantiate models"""
    model_class = MODULE_MAPPING[model_type]

    # Find registered class by factory name
    for cls in model_class.__subclasses__():
        if hasattr(cls, '_FACTORY_NAME'):
            if cls._FACTORY_NAME == factory_name:
                return cls(**kwargs)

    raise ValueError(f"Unknown factory: {factory_name}")
```

### Provider Registration

Each provider class registers with a factory name:

```python
# rag/llm/chat_model.py
class OpenAIChat(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name

class AnthropicChat(Base):
    _FACTORY_NAME = "Anthropic"
    # ...
```

**Why this pattern?**

- **Extensibility**: Add providers without modifying core code
- **Configuration-driven**: Provider selection from database
- **Loose coupling**: API layer doesn't know specific providers

**Code reference:** [rag/llm/__init__.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/__init__.py)

---

## Pattern 2: Service Layer Inheritance

All database services inherit from a common base class:

### Base Service

```python
# api/db/services/common_service.py
class CommonService:
    model = None  # Subclass must define

    @classmethod
    @DB.connection_context()
    def get_by_id(cls, obj_id):
        return cls.model.select().where(
            cls.model.id == obj_id
        ).first()

    @classmethod
    @DB.connection_context()
    def insert(cls, **kwargs):
        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def update_by_id(cls, obj_id, **kwargs):
        return cls.model.update(kwargs).where(
            cls.model.id == obj_id
        ).execute()

    @classmethod
    @DB.connection_context()
    def delete_by_id(cls, obj_id):
        return cls.model.delete().where(
            cls.model.id == obj_id
        ).execute()
```

### Concrete Service

```python
# api/db/services/document_service.py
class DocumentService(CommonService):
    model = Document

    @classmethod
    @DB.connection_context()
    def get_by_kb_id(cls, kb_id, page, size):
        """Domain-specific query method"""
        query = cls.model.select().where(
            cls.model.kb_id == kb_id,
            cls.model.status != StatusEnum.DELETED
        )
        return query.paginate(page, size)
```

**Benefits:**

- **DRY**: Common CRUD operations defined once
- **Consistency**: All services use same connection pattern
- **Extension**: Add domain methods in subclasses

**Code reference:** [api/db/services/common_service.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/db/services/common_service.py)

---

## Pattern 3: Decorator-Based Access Control

Authentication and authorization use decorators for clean separation:

### Authentication Decorator

```python
# api/utils/api_utils.py
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return get_json_result(
                code=401,
                message="Authentication required"
            )
        return func(*args, **kwargs)
    return decorated_function
```

### Token Validation

```python
def validate_token(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return get_json_result(code=401, message="Invalid token format")

        token = auth_header[7:]  # Strip 'Bearer '
        api_token = APIToken.verify(token)
        if not api_token:
            return get_json_result(code=401, message="Invalid token")

        # Inject token info into request context
        request.api_token = api_token
        return func(*args, **kwargs)
    return decorated_function
```

### Usage

```python
@manager.route('/list', methods=['GET'])
@login_required
def list_documents():
    # User is guaranteed authenticated here
    docs = DocumentService.get_by_user(current_user.id)
    return get_json_result(data=docs)

@manager.route('/external/list', methods=['GET'])
@validate_token
def external_list():
    # API token validated, available as request.api_token
    docs = DocumentService.get_by_tenant(request.api_token.tenant_id)
    return get_json_result(data=docs)
```

**Code reference:** [api/utils/api_utils.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/api/utils/api_utils.py)

---

## Pattern 4: Connection Context Manager

Database connections are managed with context managers for automatic cleanup:

```python
# api/db/__init__.py
class DB:
    @classmethod
    @contextmanager
    def connection_context(cls):
        """Ensure database connection for operation"""
        try:
            if cls.database.is_closed():
                cls.database.connect(reuse_if_open=True)
            yield
        except OperationalError as e:
            # Retry on connection errors
            cls.database.close()
            cls.database.connect()
            yield
        finally:
            if not cls.database.is_closed():
                cls.database.close()
```

This pattern ensures:
- Connections are available when needed
- Connections are released after use
- Connection errors trigger reconnection

---

## Pattern 5: Distributed Locking

For operations that must be singleton across instances:

```python
# rag/utils/redis_conn.py
class RedisDistributedLock:
    def __init__(self, name, lock_value, timeout=60):
        self.name = f"ragflow:lock:{name}"
        self.lock_value = lock_value
        self.timeout = timeout

    def acquire(self):
        """Try to acquire lock, return True if successful"""
        return REDIS_CONN.set(
            self.name,
            self.lock_value,
            nx=True,   # Only if not exists
            ex=self.timeout
        )

    def release(self):
        """Release lock only if we own it"""
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        return REDIS_CONN.eval(script, 1, self.name, self.lock_value)
```

### Usage

```python
# api/ragflow_server.py
def update_progress():
    lock = RedisDistributedLock("update_progress", str(uuid.uuid4()))

    while not stop_event.is_set():
        try:
            if lock.acquire():
                DocumentService.update_progress()
                lock.release()
        except Exception:
            logging.exception("update_progress failed")
        finally:
            lock.release()  # Ensure release
            stop_event.wait(6)
```

**Why this pattern?**

Multiple RAGFlow instances might run (for scaling). Only one should run certain background tasks.

**Code reference:** [rag/utils/redis_conn.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/utils/redis_conn.py)

---

## Pattern 6: Soft Delete

All major entities use soft delete instead of hard delete:

```python
# api/db/db_models.py
class Document(DataBaseModel):
    status = CharField(max_length=1, default='1')
    # '0' = deleted, '1' = active

# api/db/services/document_service.py
class DocumentService(CommonService):
    @classmethod
    def delete_by_id(cls, doc_id):
        """Soft delete - set status to deleted"""
        return cls.model.update(
            status=StatusEnum.DELETED
        ).where(
            cls.model.id == doc_id
        ).execute()

    @classmethod
    def get_active(cls, **filters):
        """Always filter out deleted records"""
        return cls.model.select().where(
            cls.model.status != StatusEnum.DELETED,
            **filters
        )
```

**Trade-offs:**

| Benefit | Cost |
|---------|------|
| Data recovery possible | Every query must filter status |
| Audit trail preserved | Database grows indefinitely |
| No cascade delete issues | Can confuse developers |

---

## Error Handling Patterns

### Consistent API Responses

```python
# api/utils/api_utils.py
def get_json_result(code=0, message="success", data=None):
    """Standard response format"""
    return jsonify({
        "code": code,
        "message": message,
        "data": data or {}
    })
```

### LLM Error Classification

```python
# rag/llm/chat_model.py
class LLMErrorCode(StrEnum):
    ERROR_RATE_LIMIT = "RATE_LIMIT_EXCEEDED"
    ERROR_QUOTA = "QUOTA_EXCEEDED"
    ERROR_AUTHENTICATION = "AUTH_ERROR"
    ERROR_TIMEOUT = "TIMEOUT"
    ERROR_CONTENT_FILTER = "CONTENT_FILTERED"
    ERROR_SERVER = "SERVER_ERROR"

def classify_error(exception):
    """Map exception to error code for handling"""
    msg = str(exception).lower()
    if "rate limit" in msg:
        return LLMErrorCode.ERROR_RATE_LIMIT
    if "quota" in msg or "insufficient" in msg:
        return LLMErrorCode.ERROR_QUOTA
    # ... more classifications
    return LLMErrorCode.ERROR_SERVER
```

### Retry with Backoff

```python
# rag/llm/chat_model.py
class Base:
    def _chat_with_retry(self, messages, **kwargs):
        max_retries = 5
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                return self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
            except Exception as e:
                error_code = classify_error(e)

                if error_code == LLMErrorCode.ERROR_RATE_LIMIT:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) * random.uniform(0.5, 1.5)
                    time.sleep(delay)
                elif error_code == LLMErrorCode.ERROR_QUOTA:
                    raise  # No point retrying
                else:
                    if attempt == max_retries - 1:
                        raise

        raise Exception("Max retries exceeded")
```

**Code reference:** [rag/llm/chat_model.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/llm/chat_model.py)

---

## Security Patterns

### Parameter Injection Prevention

```python
# api/apps/kb_app.py
@manager.route('/create', methods=['POST'])
def create_kb():
    req = request.json

    # Whitelist allowed parameters
    allowed_fields = ['name', 'description', 'language', 'embedding_model']
    kb_data = {k: v for k, v in req.items() if k in allowed_fields}

    # Validate types
    if not isinstance(kb_data.get('name'), str):
        return get_json_result(code=400, message="Invalid name")

    kb = KnowledgebaseService.create(**kb_data)
    return get_json_result(data=kb.to_dict())
```

### Token Format Validation

```python
# api/db/services/api_token_service.py
def validate_token_format(token):
    """Validate token structure before database lookup"""
    if not token or len(token) != 64:
        return False
    if not re.match(r'^[a-zA-Z0-9]+$', token):
        return False
    return True
```

### Permission Checking

```python
# api/utils/api_utils.py
def check_permission(resource_id, user_id, required_permission):
    """Check if user has permission on resource"""
    # Owner always has access
    if resource.created_by == user_id:
        return True

    # Check team sharing
    share = TeamShareService.get(resource_id, user_id)
    if share and share.permission >= required_permission:
        return True

    return False
```

---

## Testing Patterns

### Test Markers

```python
# pytest markers in pyproject.toml
[tool.pytest.ini_options]
markers = [
    "p1: high priority test cases",
    "p2: medium priority test cases",
    "p3: low priority test cases",
]
```

### Usage

```python
# test/testcases/test_document_api.py
import pytest

@pytest.mark.p1
def test_upload_pdf():
    """Critical path - must always pass"""
    # ...

@pytest.mark.p2
def test_upload_large_file():
    """Important but not critical"""
    # ...

@pytest.mark.p3
def test_upload_edge_case():
    """Nice to have coverage"""
    # ...
```

Run specific priority:

```bash
pytest -m p1  # Only high priority
pytest -m "p1 or p2"  # High and medium
```

---

## Code Style Patterns

### Python Conventions

- **Line length**: 200 characters (configured in ruff)
- **Imports**: Standard library → third-party → local
- **Naming**: snake_case functions, CamelCase classes
- **Type hints**: Used in critical paths, optional elsewhere

### Docstrings

```python
def chunk_document(filename, binary, **kwargs):
    """
    Parse and chunk a document for RAG indexing.

    Args:
        filename: Original filename with extension
        binary: Raw file bytes
        **kwargs: Parser configuration (chunk_token_num, delimiter, etc.)

    Returns:
        List of chunk dictionaries with 'content', 'embedding', 'metadata'

    Raises:
        ParserError: If file format is unsupported
        ValueError: If configuration is invalid
    """
```

---

## Key Takeaways

1. **Factory pattern** enables 50+ LLM providers with configuration-driven selection.

2. **Service layer inheritance** provides DRY CRUD operations with consistent connection handling.

3. **Decorator-based auth** keeps business logic clean and security concerns separate.

4. **Distributed locking** enables multi-instance deployment safely.

5. **Soft delete** preserves audit trails but requires careful query filtering.

6. **Error classification** enables intelligent retry strategies for LLM calls.

---

## What's Next

In [Blog 4: LLM Integration](./04-llm-integration.md), we'll dive deeper into how RAGFlow's universal LLM abstraction layer works, including streaming, function calling, and error handling.

---

## Further Reading

- [RFC-0001: Service Layer Standardization](../rfcs/RFC-0001-service-layer-standardization.md)
- [Terminology Glossary](../initial-analysis/terminology-glossary.md)
