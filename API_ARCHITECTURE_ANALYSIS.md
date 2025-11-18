# RAGFlow Backend API Architecture Analysis Report

## Executive Summary

RAGFlow is a full-stack RAG (Retrieval-Augmented Generation) engine with a Flask-based REST API backend. The architecture follows a modular service-layer pattern with comprehensive database models, authentication mechanisms, and error handling strategies. The API supports both web-based UI interactions and programmatic SDK access through token-based authentication.

---

## 1. FLASK APP STRUCTURE (`api/apps/`)

### 1.1 App Initialization (`api/apps/__init__.py`)

**Framework & Configuration:**
- Uses **Flask** with **Flasgger** for Swagger/OpenAPI documentation
- **Peewee ORM** for database operations (supports MySQL and PostgreSQL)
- **Flask-Login** with custom JWT-based session serialization
- **CORS** enabled with credentials support
- Custom JSON encoder for special type serialization

**Key Features:**
- Dynamic blueprint registration system
- Automatic API documentation generation at `/apidocs/`
- File-based session management
- Custom request error handler
- 1GB default upload size limit (configurable via `MAX_CONTENT_LENGTH`)

**Authentication Flow:**
```
Request Headers → load_user() → JWT deserialization → UserService.query() → User object
```
- Uses `itsdangerous.URLSafeTimedSerializer` for JWT token handling
- Access tokens stored in `User.access_token` field
- Token validation includes length and format checks (min 32 chars)

### 1.2 Flask Blueprint Registration Pattern

**Dynamic Module Loading:**
```python
# api/apps/__init__.py (lines 99-142)
- Scans for *_app.py files in api/apps/
- Scans for */sdk/*.py files in api/apps/sdk/
- Creates Flask blueprints dynamically
- Auto-registers with appropriate URL prefixes
```

**URL Prefix Pattern:**
- Standard apps: `/v1/{app_name}` (e.g., `/v1/kb`, `/v1/dialog`)
- SDK apps: `/api/v1` (e.g., `/api/v1/chats`, `/api/v1/datasets`)

### 1.3 API Endpoints by Module

#### **Knowledge Base Management** (`kb_app.py`) - 25 endpoints
- `/v1/kb/create` - Create knowledge base
- `/v1/kb/update` - Update knowledge base
- `/v1/kb/list` - List knowledge bases
- `/v1/kb/detail` - Get knowledge base details
- `/v1/kb/rm` - Delete knowledge base
- `/v1/kb/<kb_id>/tags` - Get KB tags
- `/v1/kb/<kb_id>/knowledge_graph` - GET/DELETE knowledge graph
- `/v1/kb/run_graphrag` - Run graph RAG
- `/v1/kb/run_raptor` - Run RAPTOR clustering

#### **Document Management** (`document_app.py`) - 18 endpoints
- `/v1/document/upload` - Upload documents
- `/v1/document/web_crawl` - Web crawl documents
- `/v1/document/create` - Create document entry
- `/v1/document/list` - List documents
- `/v1/document/filter` - Filter documents
- `/v1/document/run` - Parse document
- `/v1/document/rm` - Delete document
- `/v1/document/thumbnails` - Get thumbnails
- `/v1/document/change_parser` - Change parser
- `/v1/document/image/<image_id>` - Get image

#### **Dialog/Chat Management** (`dialog_app.py`) - 5 endpoints
- `/v1/dialog/set` - Create/update dialog
- `/v1/dialog/get` - Get dialog
- `/v1/dialog/list` - List dialogs
- `/v1/dialog/next` - Get next response
- `/v1/dialog/rm` - Delete dialog

#### **Conversation Management** (`conversation_app.py`) - 12 endpoints
- `/v1/conversation/message/new` - Create new conversation
- `/v1/conversation/message/list` - List messages
- `/v1/conversation/message/change_like` - Rate message
- `/v1/conversation/message/update` - Update message

#### **Canvas/Agent Workflows** (`canvas_app.py`) - 21 endpoints
- `/v1/canvas/templates` - Get templates
- `/v1/canvas/set` - Create/update canvas
- `/v1/canvas/get/<canvas_id>` - Get canvas
- `/v1/canvas/completion` - Run canvas
- `/v1/canvas/rerun` - Rerun canvas
- `/v1/canvas/cancel/<task_id>` - Cancel task
- `/v1/canvas/reset` - Reset canvas
- `/v1/canvas/debug` - Debug canvas
- `/v1/canvas/getlistversion/<canvas_id>` - Get versions

#### **File Management** (`file_app.py`) - 10 endpoints
- `/v1/file/upload` - Upload file
- `/v1/file/list` - List files
- `/v1/file/rm` - Delete file
- `/v1/file/rename` - Rename file
- `/v1/file/mv` - Move file
- `/v1/file/get/<file_id>` - Get file

#### **User & Authentication** (`user_app.py`) - 15 endpoints
- `/v1/user/login` - User login
- `/v1/user/logout` - User logout
- `/v1/user/register` - Register new user
- `/v1/user/info` - Get user info
- `/v1/user/setting` - Update user settings
- `/v1/user/oauth/callback/<channel>` - OAuth callback
- `/v1/user/forget/otp` - Password reset OTP
- `/v1/user/forget` - Password reset

#### **LLM Configuration** (`llm_app.py`) - 8 endpoints
- `/v1/llm/factories` - Get LLM factories
- `/v1/llm/set_api_key` - Configure API keys
- `/v1/llm/add_llm` - Add LLM model
- `/v1/llm/delete_llm` - Delete LLM
- `/v1/llm/my_llms` - List user's LLMs

#### **Data Connector** (`connector_app.py`) - 10 endpoints
- `/v1/connector/set` - Create connector
- `/v1/connector/list` - List connectors
- `/v1/connector/<connector_id>` - Get connector
- `/v1/connector/<connector_id>/logs` - Get sync logs
- `/v1/connector/<connector_id>/resume` - Resume sync
- `/v1/connector/<connector_id>/rebuild` - Rebuild connector

#### **SDK Endpoints** (`api/apps/sdk/`) - 65+ endpoints
- **chat.py**: `/api/v1/chats` (create chat)
- **dataset.py**: `/api/v1/datasets` (manage datasets)
- **doc.py**: `/api/v1/documents` (manage documents)
- **files.py**: `/api/v1/files` (manage files)
- **session.py**: 22 conversation endpoints
- **agents.py**: Agent management endpoints
- **dify_retrieval.py**: Dify integration endpoint

---

## 2. DATABASE LAYER (`api/db/`)

### 2.1 Database Models Architecture

**Connection Management:**
- Uses `peewee` ORM with pooled connections
- Supports MySQL and PostgreSQL via configuration
- Implements connection retry mechanism with exponential backoff
- Database lock support for concurrent operations

**Base Model Structure:**
```python
class BaseModel(Model):
    create_time = BigIntegerField()  # Unix timestamp
    create_date = DateTimeField()     # Human-readable datetime
    update_time = BigIntegerField()
    update_date = DateTimeField()
    
    # Custom field types:
    - JSONField() - JSON serialization
    - ListField() - JSON array serialization
    - SerializedField() - Pickle or JSON serialization
    - LongTextField() - LONGTEXT (MySQL) or TEXT (PostgreSQL)
```

### 2.2 Core Database Models

#### **User Management Models**
```
User
├── id (varchar, PK)
├── access_token (indexed)
├── email (indexed)
├── password (hashed)
├── nickname
├── avatar (base64)
├── language, color_schema, timezone
├── last_login_time
├── is_authenticated, is_active, is_anonymous
├── is_superuser
└── status (soft delete)

Tenant
├── id (varchar, PK)
├── name
├── public_key
├── llm_id, embd_id, asr_id, img2txt_id, rerank_id
├── parser_ids
├── credit (integer)
└── status

UserTenant (Multi-tenancy)
├── user_id (FK → User)
├── tenant_id (FK → Tenant)
├── role (owner|admin|normal|invite)
├── invited_by
└── status
```

#### **Knowledge Base Models**
```
Knowledgebase
├── id (varchar, PK)
├── name (indexed)
├── description
├── embd_id, parser_id, rerank_id
├── chunk_num (integer)
├── created_by (indexed)
├── tenant_id (indexed)
├── permission (me|team)
└── status

Document
├── id (varchar, PK)
├── kb_id (FK, indexed)
├── name
├── type (pdf|doc|visual|aural|virtual)
├── parser_config (JSON)
├── chunk_num
├── parser_id
└── status

File
├── id (varchar, PK)
├── name
├── tenant_id
├── type (folder|file)
├── size
└── parent_id (self-referential)

File2Document (Junction)
├── id (varchar, PK)
├── file_id (indexed)
├── document_id (indexed)
└── status
```

#### **Dialog & Conversation Models**
```
Dialog (Chat Configuration)
├── id (varchar, PK)
├── tenant_id (indexed)
├── name
├── description
├── kb_ids (JSON list)
├── llm_id
├── llm_setting (JSON)
├── prompt_config (JSON)
├── top_n, top_k
├── rerank_id
└── status

Conversation
├── id (varchar, PK)
├── dialog_id (indexed)
├── name
├── message (JSON)
├── reference (JSON)
└── user_id (indexed)

API4Conversation (SDK Conversations)
├── id (varchar, PK)
├── dialog_id (indexed)
├── user_id (indexed)
├── message, reference (JSON)
├── tokens, duration
├── thumb_up (rating)
└── dsl (JSON)
```

#### **LLM Configuration Models**
```
LLMFactories
├── name (varchar, PK)
├── logo (base64)
├── tags
├── rank
└── status

LLM
├── fid, llm_name (Composite PK)
├── model_type (chat|embedding|speech2text|image2text)
├── max_tokens
├── tags
├── is_tools (boolean)
└── status

TenantLLM (Tenant-specific LLM config)
├── tenant_id, llm_name, llm_factory (Composite PK)
├── api_key (encrypted)
├── model_type
├── base_url
└── status
```

#### **Canvas/Workflow Models**
```
UserCanvas
├── id (varchar, PK)
├── tenant_id (indexed)
├── name
├── dsl (JSON - workflow definition)
├── sort_order
└── status

CanvasTemplate
├── id (varchar, PK)
├── name
├── category (agent_canvas|dataflow_canvas)
├── dsl (JSON)
└── status

UserCanvasVersion
├── id (varchar, PK)
├── user_canvas_id (indexed)
├── dsl (JSON)
└── version_num
```

#### **API & Auth Models**
```
APIToken
├── tenant_id (PK part)
├── token (PK part, indexed)
├── dialog_id
├── source (none|agent|dialog)
└── beta

InvitationCode
├── id (varchar, PK)
├── code (indexed)
├── user_id
├── tenant_id
└── status

Task (Async Tasks)
├── id (varchar, PK)
├── kb_id, doc_id
├── type (Parse|Download|RAPTOR|GraphRAG)
├── status (running|success|fail)
├── progress (0-100)
└── created_by
```

#### **Connector Models**
```
Connector
├── id (varchar, PK)
├── tenant_id (indexed)
├── name
├── class_name (Python class)
├── config (JSON - auth credentials, settings)
├── kb_ids (JSON list)
└── status

Connector2Kb (Junction)
├── kb_id, connector_id (Composite PK)
├── permissions (JSON)
└── status

SyncLogs
├── id (varchar, PK)
├── connector_id (indexed)
├── doc_id
├── status
└── error_message
```

### 2.3 Service Layer Architecture

**Base Service Pattern:**
```python
class CommonService:
    model = None  # Set by subclasses
    
    # Standard CRUD operations decorated with @DB.connection_context()
    - query(**kwargs) → list of records
    - get(**kwargs) → single record
    - get_by_id(id) → (success, record)
    - insert(**kwargs) → new record with auto ID & timestamps
    - update_by_id(id, data) → update count
    - delete_by_id(id) → delete count
```

**Service Inheritance Hierarchy:**
```
CommonService
├── UserService
│   └── query() - Custom validation for access_token
├── TenantService
│   └── get_joined_tenants_by_user_id()
├── KnowledgebaseService
│   ├── accessible4deletion()
│   ├── is_parsed_done()
│   └── get_by_tenant_ids()
├── DocumentService
│   ├── get_by_kb_id()
│   └── update_progress()
├── DialogService
├── ConversationService
├── CanvasService
├── ConnectorService
├── FileService
└── [20+ other specialized services]
```

**Service Method Patterns:**
```python
# Read operations
@DB.connection_context()
def query(cls, **kwargs):
    # Flexible filtering with ordering and column selection

# Write operations  
@DB.connection_context()
@DB.lock("lock_name", timeout=60)  # Distributed lock for concurrency
def update_by_id(cls, pid, data):
    # Auto-updates update_time and update_date

# Batch operations
@DB.connection_context()
def insert_many(cls, data_list, batch_size=100):
    # Uses DB.atomic() for transactions
```

---

## 3. ARCHITECTURE PATTERNS

### 3.1 Design Patterns

**Service Layer Pattern:**
- Separates business logic from HTTP handlers
- Services encapsulate database operations
- Common base class provides standard CRUD
- Connection context management for pooled connections

**Repository Pattern:**
- CommonService acts as data access layer
- Query methods support dynamic filtering
- Composite keys supported via peewee

**Decorator-Based Access Control:**
```python
@manager.route('/list', methods=['POST'])
@login_required                          # Requires User session
@validate_request("kb_id")              # Validates JSON/form fields
@not_allowed_parameters(...)            # Prevents field injection
def list_kb():
    current_user.id              # Available via Flask-Login
```

**Factory Pattern:**
- LLM and embedding models dynamically loaded
- Tenant-specific LLM configurations
- Parser implementations loaded by type

### 3.2 Error Handling Architecture

**Global Error Handler:**
```python
# api/apps/__init__.py line 82
app.errorhandler(Exception)(server_error_response)
```

**Error Response Format:**
```json
{
  "code": <RetCode>,
  "message": "<error_message>",
  "data": null  // Optional
}
```

**RetCode Enum:**
```python
class RetCode(IntEnum):
    SUCCESS = 0
    NOT_EFFECTIVE = 10
    EXCEPTION_ERROR = 100
    ARGUMENT_ERROR = 101
    DATA_ERROR = 102
    OPERATING_ERROR = 103
    PERMISSION_ERROR = 108
    AUTHENTICATION_ERROR = 109
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500
```

**Error Handling Strategies:**
1. **Request Validation**: `@validate_request(*args)` decorator
2. **Parameter Sanitization**: `@not_allowed_parameters()` prevents injection
3. **Exception Serialization**: Converts non-JSON objects to strings
4. **Database Retry**: Automatic retry with exponential backoff for connection errors

### 3.3 Authentication & Authorization

**Authentication Mechanisms:**

1. **Web UI Authentication (Session-based):**
   - Email + password login
   - JWT token stored in session
   - Token stored in User.access_token
   - Session-based via Flask-Login

2. **SDK Authentication (Token-based):**
   - API key tokens in APIToken table
   - Authorization header: `Bearer <token>`
   - Tenant-scoped access via APIToken.tenant_id
   - Token can be dialog-specific

3. **OAuth Integration:**
   - GitHub OAuth
   - Feishu (DingTalk) OAuth
   - OIDC support

**Authorization Levels:**

```python
class TenantPermission(StrEnum):
    ME = 'me'         # Private to creator
    TEAM = 'team'     # Shared with team tenants

class UserTenantRole(StrEnum):
    OWNER = 'owner'       # Full control
    ADMIN = 'admin'       # Administrative access
    NORMAL = 'normal'     # Regular member
    INVITE = 'invite'     # Invited (pending)
```

**Permission Check Pattern:**
```python
def check_kb_team_permission(kb, user_id):
    # 1. Check if user is creator
    if kb.tenant_id == user_id:
        return True
    
    # 2. Check if shared with team and user in same tenant
    if kb.permission == TenantPermission.TEAM:
        joined_tenants = TenantService.get_joined_tenants_by_user_id(user_id)
        return any(t.tenant_id == kb.tenant_id for t in joined_tenants)
    
    return False
```

### 3.4 Request Validation Pipeline

**Decorator Chain:**
```python
@manager.route('/update', methods=['POST'])
@login_required
@validate_request("kb_id", "name")
@not_allowed_parameters("id", "tenant_id", "created_by")
def update():
    # 1. Check if user authenticated
    # 2. Validate required fields exist
    # 3. Ensure sensitive fields not modified
    # 4. Process request
```

**Validation Functions:**
```python
def validate_request(*args, **kwargs):
    # Checks JSON/form for required fields
    # Validates field values match expected values/types
    
def not_allowed_parameters(*params):
    # Prevents injection of protected fields
    # Common: id, tenant_id, created_by, create_time, update_time
    
def active_required(f):
    # Ensures user is active (not soft-deleted)
```

---

## 4. API PATTERNS & CONVENTIONS

### 4.1 Standard Response Format

**Success Response:**
```json
{
  "code": 0,
  "data": {...} | [...] | null,
  "message": "Optional message"
}
```

**Error Response:**
```json
{
  "code": <error_code>,
  "message": "Error description"
}
```

**Paginated Response:**
```json
{
  "code": 0,
  "data": [...],
  "total_datasets": 47
}
```

### 4.2 HTTP Method Conventions

- **GET**: Retrieve resources (list, detail, get)
- **POST**: Create resources, submit actions (create, delete, run)
- **PUT**: Update/resume operations
- **DELETE**: Delete resources

### 4.3 Request Body Format

**JSON Format (POST):**
```python
@manager.route('/set', methods=['POST'])
def set_dialog():
    req = request.json  # Automatically parsed by Flask
    # Custom parser: Request.json = property(lambda self: self.get_json(force=True, silent=True))
```

**Form Data Format:**
```python
@manager.route('/upload', methods=['POST'])
def upload():
    kb_id = request.form.get("kb_id")
    files = request.files.getlist("file")
```

### 4.4 Pagination Pattern

**Query Parameters:**
```
GET /v1/kb/list?page_number=1&items_per_page=20&orderby=create_time&desc=true&keywords=search
```

**Service Implementation:**
```python
def get_by_tenant_ids(cls, tenant_ids, user_id, 
                      page_number, items_per_page,
                      orderby, desc, keywords):
    # Offset: (page_number - 1) * items_per_page
    # Order: desc=True → ORDER BY DESC
```

### 4.5 DateTime Handling

**Dual Timestamp Storage:**
- `create_time` - Unix timestamp (BigInteger, sortable)
- `create_date` - Human-readable DateTime
- Auto-populated by BaseModel._normalize_data()

**Conversion Functions:**
```python
from common.time_utils import:
    - current_timestamp() → Unix timestamp
    - timestamp_to_date(ts) → DateTime
    - datetime_format(dt) → Formatted string
    - date_string_to_timestamp(str) → Unix timestamp
```

---

## 5. API DOCUMENTATION

### 5.1 Swagger/Flasgger Integration

**Configuration:**
```python
swagger_config = {
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "endpoint": "apispec",
    "route": "/apispec.json"
}
```

**Auto-Generated Documentation:**
- Endpoint: `/apidocs/` - Interactive Swagger UI
- JSON Schema: `/apispec.json`
- Automatic from Flask routes and docstrings

### 5.2 OpenAPI Compatibility

The API follows OpenAI-compatible format for chat endpoints:
- **Endpoint**: `/api/v1/chats_openai/{chat_id}/chat/completions`
- **Format**: OpenAI Chat Completion API compatible
- **Streaming**: SSE (Server-Sent Events) support

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/chats_openai/{chat_id}/chat/completions \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model",
    "messages": [{"role": "user", "content": "Question"}],
    "stream": true
  }'
```

---

## 6. CODE QUALITY OBSERVATIONS

### 6.1 Strengths

1. **Comprehensive Error Handling**
   - Global exception handler with detailed logging
   - Specific error codes for different failure scenarios
   - Graceful degradation with fallback responses

2. **Database Resilience**
   - Connection pooling with configurable pool size
   - Automatic retry with exponential backoff
   - Distributed locking for concurrent operations
   - Transaction support via DB.atomic()

3. **Security Measures**
   - Access token validation with format checks (min 32 chars)
   - Password hashing with werkzeug
   - Token-based API authentication
   - Parameter injection prevention via @not_allowed_parameters
   - Permission checks for team vs private resources

4. **Modular Architecture**
   - Dynamic blueprint registration reduces boilerplate
   - Service layer separation of concerns
   - Extensible ORM-based models
   - Plugin system for LLM factories

5. **API Documentation**
   - Automatic Swagger/OpenAPI generation
   - Human-readable error messages
   - Standard response format across all endpoints
   - OpenAI-compatible interface for chat

### 6.2 Potential Issues & Inconsistencies

1. **Token Validation Warnings:**
   ```python
   # UserService.query() has multiple safeguards (lines 47-63)
   # - Checks for empty/None tokens
   # - Validates token length > 32 chars
   # - Rejects "INVALID_" prefixed tokens
   # CONCERN: Returns dummy records instead of None → potential for logic bugs
   ```

2. **Error Response Inconsistency:**
   - Some endpoints return `get_json_result(code=..., message=..., data=None)`
   - Others return `get_error_data_result(message=..., code=...)`
   - Different function signatures for same purpose

3. **Soft Delete Pattern:**
   - Uses `status` field (0=invalid, 1=valid) instead of dedicated `deleted_at`
   - Queries must always check status = '1'
   - Easy to forget this filter in custom queries

4. **Missing Rate Limiting:**
   - No request rate limiting decorator
   - Token endpoints could be vulnerable to brute force

5. **Audit Logging:**
   - No audit trail for sensitive operations (delete, permission changes)
   - Only timestamp tracking, no operation logging

6. **Query Complexity:**
   - Some service methods have 7+ parameters
   - Pagination logic mixed with filtering logic
   - Could benefit from query builder pattern

7. **API Key Handling:**
   ```python
   # APIToken uses composite key (tenant_id, token)
   # Allows multiple tokens per tenant - acceptable
   # But tokens not scoped by permission/expiry
   ```

### 6.3 Good Practices Observed

1. **Type Hints**: Presence of field type hints in models
2. **Docstrings**: Service methods have detailed docstrings
3. **Transactions**: Critical operations wrapped in DB.atomic()
4. **Connection Management**: Proper context managers for DB connections
5. **Configuration Management**: Environment-based configuration
6. **Logging**: Comprehensive logging at all levels

---

## 7. DATABASE SCHEMA STATISTICS

**Total Models**: 28 database models
**Total Tables**: 28 database tables

**Model Categories:**
- User & Auth: 5 models (User, Tenant, UserTenant, InvitationCode, APIToken)
- Knowledge Base: 5 models (KB, Document, File, File2Document, Task)
- Conversation: 3 models (Dialog, Conversation, API4Conversation)
- LLM: 3 models (LLMFactories, LLM, TenantLLM)
- Canvas: 3 models (UserCanvas, CanvasTemplate, UserCanvasVersion)
- Connector: 3 models (Connector, Connector2KB, SyncLogs)
- Other: 3 models (Search, PipelineOperationLog, TenantLangfuse)

---

## 8. SERVICE LAYER SUMMARY

**Total Service Classes**: 20+

**Key Services:**
1. **UserService** - User authentication and profile management
2. **TenantService** - Multi-tenant organization
3. **KnowledgebaseService** - KB lifecycle and access control
4. **DocumentService** - Document parsing and tracking
5. **DialogService** - Chat configuration management
6. **ConversationService** - Chat history management
7. **CanvasService** - Workflow/agent management
8. **ConnectorService** - Data source connectors
9. **FileService** - File storage and organization
10. **LLMService** - LLM factory and model configuration

**Service Features:**
- Automatic CRUD operations from CommonService
- Specialized methods for business logic
- Database context and lock decorators
- Batch operation support
- Pagination support

---

## 9. DEPLOYMENT CONSIDERATIONS

**Configuration Files:**
- `docker/.env` - Environment variables
- `docker/service_conf.yaml.template` - Service configuration
- `pyproject.toml` - Python dependencies

**Database Support:**
- MySQL (primary)
- PostgreSQL (secondary)
- Elasticsearch/Infinity (document storage)
- Redis (caching and distributed locks)

**Key Environment Variables:**
- `DATABASE_TYPE` - mysql|postgres
- `DATABASE` - Connection details
- `HOST_IP`, `HOST_PORT` - Server binding
- `DISABLE_SDK` - Disable SDK endpoints
- `MAX_CONTENT_LENGTH` - Upload limit

---

## 10. SECURITY SUMMARY

**Authentication:**
- Web: Session + JWT tokens
- API: Bearer token (APIToken)
- OAuth: GitHub, Feishu, OIDC

**Authorization:**
- User-based (creator only)
- Team-based (shared within tenant)
- Role-based (owner, admin, normal)

**Data Protection:**
- Passwords hashed with werkzeug.security
- API keys stored in dedicated table
- Soft deletes prevent data loss
- Transaction support for atomic operations

**Vulnerabilities Addressed:**
- Parameter injection via @not_allowed_parameters
- Token validation with length/format checks
- Permission checks on all sensitive operations
- Global exception handler prevents information leakage

