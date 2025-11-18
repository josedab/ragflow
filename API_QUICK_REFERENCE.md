# RAGFlow Backend API - Quick Reference Guide

## Core Framework
- **Framework**: Flask 2.x
- **ORM**: Peewee (MySQL/PostgreSQL)
- **Authentication**: Flask-Login + JWT
- **Documentation**: Flasgger (Swagger UI at `/apidocs/`)

## API Endpoints Summary

| Module | Endpoints | Key Operations |
|--------|-----------|-----------------|
| **Knowledge Base** | 25 | create, list, detail, rm, tags, knowledge_graph, graphrag, raptor |
| **Document** | 18 | upload, web_crawl, create, list, filter, run, rm, thumbnails |
| **Dialog** | 5 | set, get, list, next, rm |
| **Conversation** | 12 | message/new, message/list, change_like, update |
| **Canvas** | 21 | templates, set, get, completion, rerun, cancel, debug |
| **File** | 10 | upload, list, rm, rename, mv, get |
| **User** | 15 | login, logout, register, info, setting, oauth, forget |
| **LLM** | 8 | factories, set_api_key, add_llm, delete_llm, my_llms |
| **Connector** | 10 | set, list, get, logs, resume, rebuild, rm |
| **SDK** | 65+ | chats, datasets, documents, files, agents |

## URL Patterns

```
Standard endpoints:      /v1/{module}/{action}
SDK endpoints:          /api/v1/{resource}
Swagger UI:             /apidocs/
OpenAPI schema:         /apispec.json
OpenAI-compatible chat: /api/v1/chats_openai/{chat_id}/chat/completions
```

## Authentication Methods

### Web UI (Session-based)
```bash
POST /v1/user/login
Content-Type: application/json
{
  "email": "user@example.com",
  "password": "password"
}
# Response includes JWT token in User.access_token
```

### API (Token-based)
```bash
GET /v1/kb/list
Authorization: Bearer {API_TOKEN}
# Token from APIToken table with Bearer scheme
```

## Standard Response Format

### Success (code: 0)
```json
{
  "code": 0,
  "data": {...} | [...],
  "message": "success"
}
```

### Error (code: non-zero)
```json
{
  "code": 102,
  "message": "Error description"
}
```

## Error Codes
- `0` - SUCCESS
- `10` - NOT_EFFECTIVE
- `100` - EXCEPTION_ERROR
- `101` - ARGUMENT_ERROR
- `102` - DATA_ERROR
- `103` - OPERATING_ERROR
- `108` - PERMISSION_ERROR
- `109` - AUTHENTICATION_ERROR
- `401` - UNAUTHORIZED
- `403` - FORBIDDEN
- `404` - NOT_FOUND
- `500` - SERVER_ERROR

## Request Validation Decorators

```python
@manager.route('/endpoint', methods=['POST'])
@login_required                          # Requires authenticated user
@validate_request("field1", "field2")   # Validates required fields
@not_allowed_parameters("id", "tenant_id")  # Prevents field injection
def endpoint():
    pass
```

## Common Query Parameters

```
?page_number=1
?items_per_page=20
?orderby=create_time
?desc=true
?keywords=search_term
```

## Database Models - Key Tables

### User Management
- `User` - User accounts and authentication
- `Tenant` - Organization/workspace
- `UserTenant` - Multi-tenancy mapping
- `APIToken` - API key tokens
- `InvitationCode` - Invitation codes

### Knowledge Base
- `Knowledgebase` - KB config and metadata
- `Document` - Documents in KB
- `File` - File storage (hierarchical)
- `File2Document` - Document-file mapping
- `Task` - Async parsing/processing tasks

### Chat/Dialog
- `Dialog` - Chat configuration
- `Conversation` - Chat message history
- `API4Conversation` - SDK conversation history

### Configuration
- `LLMFactories` - Available LLM vendors
- `LLM` - LLM models catalog
- `TenantLLM` - Tenant-specific LLM config
- `Connector` - Data source connectors
- `UserCanvas` - Agent/workflow definitions

## Service Layer Pattern

```python
from api.db.services.knowledgebase_service import KnowledgebaseService

# All services inherit from CommonService
KnowledgebaseService.query(id=kb_id)              # Query with filters
KnowledgebaseService.get_by_id(kb_id)            # Get by ID
KnowledgebaseService.insert(**data)              # Create new
KnowledgebaseService.update_by_id(kb_id, data)  # Update
KnowledgebaseService.delete_by_id(kb_id)        # Delete
KnowledgebaseService.get_by_ids([ids])          # Batch get
```

## Permission Model

```python
TenantPermission = {
    'me': 'Private to creator',
    'team': 'Shared with team'
}

UserTenantRole = {
    'owner': 'Full control',
    'admin': 'Admin access',
    'normal': 'Regular member',
    'invite': 'Pending invitation'
}
```

## Authorization Pattern

```python
def check_kb_team_permission(kb, user_id):
    # 1. Check if user is creator
    if kb.tenant_id == user_id:
        return True
    
    # 2. Check if shared and user in same team
    if kb.permission == 'team':
        return user_id in get_team_members(kb.tenant_id)
    
    return False
```

## Common Field Types

```python
create_time    # BigIntegerField - Unix timestamp (sortable)
create_date    # DateTimeField - Human-readable date
update_time    # BigIntegerField - Unix timestamp
update_date    # DateTimeField - Human-readable date
status         # CharField - '0'=invalid, '1'=valid (soft delete)
id             # CharField - UUID (32 hex chars)
```

## File Upload Pattern

```bash
POST /v1/document/upload
Content-Type: multipart/form-data

Form parameters:
- kb_id: Knowledge base ID
- file: File to upload (multipart)

Response:
{
  "code": 0,
  "data": [
    {
      "id": "document_id",
      "name": "filename.pdf",
      "size": 1024
    }
  ]
}
```

## Pagination Response

```json
{
  "code": 0,
  "data": [...],
  "total_datasets": 47
}
```

## Database Connection Management

```python
# Auto-managed by @DB.connection_context() decorator
# Connection pooling with configurable pool size
# Automatic retry with exponential backoff
# Distributed locking support for concurrent ops

@DB.connection_context()
def method():
    pass

@DB.lock("lock_name", timeout=60)
def critical_section():
    pass
```

## Environment Configuration

```bash
DATABASE_TYPE=mysql|postgres
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USER=user
DATABASE_PASSWORD=password
DATABASE_NAME=ragflow

HOST_IP=0.0.0.0
HOST_PORT=8000

MAX_CONTENT_LENGTH=1073741824  # 1GB
DISABLE_SDK=false

SECRET_KEY=your_secret_key
```

## Testing Authentication

```bash
# Get API token
curl http://localhost:8000/v1/user/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"pass"}'

# Use token for API calls
curl http://localhost:8000/v1/kb/list \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check token format and expiration |
| 103 OPERATING_ERROR | Check permissions and ownership |
| 102 DATA_ERROR | Validate required fields in request |
| Database connection timeout | Check pooling config and db_max_connections |
| Soft delete not working | Remember to filter status='1' in queries |

---

For detailed analysis, see: `/home/user/ragflow/API_ARCHITECTURE_ANALYSIS.md`
