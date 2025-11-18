# RAGFlow Backend API - Code Examples & Patterns

## Table of Contents
1. [Service Layer Examples](#service-layer-examples)
2. [API Endpoint Patterns](#api-endpoint-patterns)
3. [Authentication & Authorization](#authentication--authorization)
4. [Database Operations](#database-operations)
5. [Error Handling](#error-handling)
6. [Request Validation](#request-validation)

---

## Service Layer Examples

### Basic CRUD Operations

#### Read Example
```python
from api.db.services.knowledgebase_service import KnowledgebaseService

# Query with filters
kbs = KnowledgebaseService.query(tenant_id=user_id, status='1')

# Get single record
success, kb = KnowledgebaseService.get_by_id(kb_id)
if success:
    print(f"Knowledge Base: {kb.name}")

# Query with ordering
kbs = KnowledgebaseService.query(
    tenant_id=user_id,
    reverse=True,        # Descending order
    order_by='create_time'
)

# Get all with pagination
kbs = KnowledgebaseService.query(
    tenant_id=user_id,
    status='1'
).paginate(
    page_num=(page_number - 1) * items_per_page,
    paginate_by=items_per_page
)
```

#### Create Example
```python
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.misc_utils import get_uuid

# Insert new record (auto ID & timestamps)
kb = KnowledgebaseService.insert(
    id=get_uuid(),
    name="My Knowledge Base",
    tenant_id=user_id,
    created_by=user_id,
    description="Optional description",
    parser_id="default_parser",
    status='1'
)

# Insert multiple records
data = [
    {"id": get_uuid(), "name": "KB1", ...},
    {"id": get_uuid(), "name": "KB2", ...},
]
KnowledgebaseService.insert_many(data, batch_size=100)
```

#### Update Example
```python
from api.db.services.knowledgebase_service import KnowledgebaseService

# Update single record
num_updated = KnowledgebaseService.update_by_id(
    kb_id,
    {
        "name": "Updated Name",
        "description": "Updated description"
        # update_time and update_date auto-populated
    }
)

# Update multiple records
KnowledgebaseService.update_many_by_id([
    {"id": kb_id1, "name": "New Name 1"},
    {"id": kb_id2, "name": "New Name 2"}
])

# Update with filters
KnowledgebaseService.filter_update(
    filters=[Knowledgebase.tenant_id == user_id],
    update_data={"status": '0'}
)
```

#### Delete Example
```python
from api.db.services.knowledgebase_service import KnowledgebaseService

# Delete single record
num_deleted = KnowledgebaseService.delete_by_id(kb_id)

# Delete multiple records
num_deleted = KnowledgebaseService.delete_by_ids([kb_id1, kb_id2])

# Delete with filters
num_deleted = KnowledgebaseService.filter_delete(
    filters=[Knowledgebase.tenant_id == user_id, Knowledgebase.status == '0']
)
```

---

## API Endpoint Patterns

### Basic REST Endpoint

```python
from flask import request
from flask_login import login_required, current_user
from api.utils.api_utils import get_json_result, validate_request
from common.constants import RetCode
from api.db.services.knowledgebase_service import KnowledgebaseService

@manager.route('/detail', methods=['GET'])
@login_required
@validate_request("kb_id")
def get_detail():
    """Get knowledge base details"""
    kb_id = request.args.get("kb_id")
    
    # Get KB and verify ownership
    success, kb = KnowledgebaseService.get_by_id(kb_id)
    if not success:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Knowledge base not found"
        )
    
    # Check permission
    if kb.created_by != current_user.id:
        return get_json_result(
            code=RetCode.PERMISSION_ERROR,
            message="No permission to access this knowledge base"
        )
    
    # Return success response
    return get_json_result(data=kb.to_dict())
```

### Create Endpoint with Validation

```python
from flask import request
from flask_login import login_required, current_user
from api.utils.api_utils import (
    get_json_result,
    get_data_error_result,
    validate_request,
    not_allowed_parameters,
    server_error_response
)
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.misc_utils import get_uuid
from common.constants import RetCode

@manager.route('/create', methods=['POST'])
@login_required
@validate_request("name")  # Validates 'name' field exists
@not_allowed_parameters("id", "tenant_id", "created_by")  # Prevents injection
def create():
    """Create new knowledge base"""
    try:
        req = request.json
        
        # Additional validation
        if not isinstance(req["name"], str):
            return get_data_error_result(
                message="Dataset name must be string"
            )
        
        if req["name"].strip() == "":
            return get_data_error_result(
                message="Dataset name can't be empty"
            )
        
        # Create KB with service
        kb_data = {
            "id": get_uuid(),
            "name": req["name"],
            "description": req.get("description", ""),
            "tenant_id": current_user.id,
            "created_by": current_user.id,
            "parser_id": req.get("parser_id", "default"),
            "status": "1"
        }
        
        kb = KnowledgebaseService.insert(**kb_data)
        
        return get_json_result(data={"kb_id": kb.id})
    
    except Exception as e:
        return server_error_response(e)
```

### List Endpoint with Pagination

```python
from flask import request
from flask_login import login_required, current_user
from api.utils.api_utils import get_json_result, get_result
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.constants import StatusEnum

@manager.route('/list', methods=['POST'])
@login_required
def list_kbs():
    """List knowledge bases with pagination"""
    req = request.json
    
    page_number = req.get("page_number", 1)
    items_per_page = req.get("items_per_page", 20)
    keywords = req.get("keywords", "")
    orderby = req.get("orderby", "create_time")
    desc = req.get("desc", True)
    
    # Calculate offset
    offset = (page_number - 1) * items_per_page
    
    # Query with filters
    query = KnowledgebaseService.query(
        created_by=current_user.id,
        status=StatusEnum.VALID.value
    )
    
    # Add keyword filter if provided
    if keywords:
        query = query.where(Knowledgebase.name.contains(keywords))
    
    # Add sorting
    if desc:
        query = query.order_by(KnowledgebaseService.model.getter_by(orderby).desc())
    else:
        query = query.order_by(KnowledgebaseService.model.getter_by(orderby).asc())
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    kbs = query.offset(offset).limit(items_per_page)
    
    return get_result(
        data=[kb.to_dict() for kb in kbs],
        total=total
    )
```

### Action Endpoint (POST with side effects)

```python
from flask import request
from flask_login import login_required, current_user
from api.utils.api_utils import get_json_result
from api.db.services.document_service import DocumentService
from api.db.services.task_service import TaskService
from common.constants import TaskStatus, PipelineTaskType
from common.misc_utils import get_uuid

@manager.route('/run', methods=['POST'])
@login_required
def run_document():
    """Trigger document parsing"""
    req = request.json
    doc_id = req.get("doc_id")
    
    # Verify document exists and user has access
    success, doc = DocumentService.get_by_id(doc_id)
    if not success:
        return get_json_result(
            code=RetCode.DATA_ERROR,
            message="Document not found"
        )
    
    # Create parsing task
    task = TaskService.insert(
        id=get_uuid(),
        doc_id=doc_id,
        kb_id=doc.kb_id,
        type=PipelineTaskType.PARSE,
        status=TaskStatus.RUNNING.value,
        progress=0
    )
    
    return get_json_result(data={"task_id": task.id})
```

---

## Authentication & Authorization

### Session-Based Authentication (Web UI)

```python
from flask_login import login_required, current_user
from api.utils.api_utils import get_json_result
from api.db.services.user_service import UserService
from common.constants import RetCode
from werkzeug.security import check_password_hash

@manager.route('/login', methods=['POST'])
def login():
    """User login with email and password"""
    email = request.json.get("email")
    password = request.json.get("password")
    
    # Query user by email
    user = UserService.query_user(email, password)
    if not user:
        return get_json_result(
            code=RetCode.AUTHENTICATION_ERROR,
            message="Invalid email or password"
        )
    
    # Update last login time
    UserService.update_by_id(
        user.id,
        {"last_login_time": datetime.now()}
    )
    
    # Return user object (Flask-Login handles session)
    return get_json_result(data={
        "user_id": user.id,
        "email": user.email,
        "access_token": user.access_token
    })
```

### Token-Based Authentication (API)

```python
from api.utils.api_utils import token_required, get_json_result
from api.db.services.knowledgebase_service import KnowledgebaseService

@manager.route('/chats', methods=['POST'])
@token_required  # Validates Bearer token and sets tenant_id kwarg
def create_chat(tenant_id):
    """Create chat with token authentication"""
    req = request.json
    
    # tenant_id automatically set from APIToken.tenant_id
    kbs = KnowledgebaseService.query(
        tenant_id=tenant_id,
        status='1'
    )
    
    return get_json_result(data=[kb.to_dict() for kb in kbs])
```

### Permission Checking

```python
from api.common.check_team_permission import check_kb_team_permission
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.constants import RetCode

@manager.route('/delete', methods=['POST'])
@login_required
def delete_kb():
    """Delete knowledge base with permission check"""
    kb_id = request.json.get("kb_id")
    
    # Get KB
    success, kb = KnowledgebaseService.get_by_id(kb_id)
    if not success:
        return get_json_result(code=RetCode.DATA_ERROR)
    
    # Check if user has permission
    if not check_kb_team_permission(kb, current_user.id):
        return get_json_result(
            code=RetCode.PERMISSION_ERROR,
            message="No permission to delete this knowledge base"
        )
    
    # Delete KB
    KnowledgebaseService.delete_by_id(kb_id)
    
    return get_json_result(data=True)
```

---

## Database Operations

### Transaction with Atomic Operations

```python
from api.db.db_models import DB
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.document_service import DocumentService

@manager.route('/batch_create', methods=['POST'])
@login_required
def batch_create():
    """Create KB and documents atomically"""
    try:
        with DB.atomic():  # Transaction starts
            # Create KB
            kb = KnowledgebaseService.insert(
                id=get_uuid(),
                name="New KB",
                tenant_id=current_user.id,
                created_by=current_user.id,
                status='1'
            )
            
            # Create documents
            docs = []
            for i in range(3):
                doc = DocumentService.insert(
                    id=get_uuid(),
                    kb_id=kb.id,
                    name=f"Document {i+1}",
                    status='1'
                )
                docs.append(doc)
            
            # All succeed or all fail
            return get_json_result(data={
                "kb_id": kb.id,
                "doc_count": len(docs)
            })
    
    except Exception as e:
        # Transaction automatically rolled back
        return server_error_response(e)
```

### Distributed Locking

```python
from api.db.db_models import DB
from api.db.services.knowledgebase_service import KnowledgebaseService

@manager.route('/update_progress', methods=['POST'])
@DB.lock("update_progress_lock", timeout=30)
def update_progress():
    """Update with distributed lock for concurrency control"""
    # This method blocks other calls with same lock
    # Prevents race conditions
    
    kb_id = request.json.get("kb_id")
    
    kb = KnowledgebaseService.query(id=kb_id)[0]
    kb.chunk_num += 1
    
    KnowledgebaseService.update_by_id(
        kb_id,
        {"chunk_num": kb.chunk_num}
    )
    
    return get_json_result(data={"chunk_num": kb.chunk_num})
```

### Batch Operations

```python
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.time_utils import current_timestamp, datetime_format
from datetime import datetime

@manager.route('/import_kbs', methods=['POST'])
def import_kbs():
    """Import multiple knowledge bases"""
    req = request.json
    kbs_data = req.get("kbs", [])
    
    # Prepare data for batch insert
    for kb_data in kbs_data:
        kb_data["id"] = get_uuid()
        kb_data["tenant_id"] = current_user.id
        kb_data["created_by"] = current_user.id
        kb_data["create_time"] = current_timestamp()
        kb_data["create_date"] = datetime_format(datetime.now())
        kb_data["update_time"] = current_timestamp()
        kb_data["update_date"] = datetime_format(datetime.now())
        kb_data["status"] = "1"
    
    # Insert all at once
    KnowledgebaseService.insert_many(kbs_data, batch_size=100)
    
    return get_json_result(data={"count": len(kbs_data)})
```

---

## Error Handling

### Standard Error Response Pattern

```python
from api.utils.api_utils import (
    get_json_result,
    get_data_error_result,
    get_error_data_result,
    server_error_response
)
from common.constants import RetCode

@manager.route('/validate', methods=['POST'])
@login_required
def validate():
    """Demonstrate different error responses"""
    try:
        req = request.json
        
        # Missing field error
        if "field1" not in req:
            return get_data_error_result(
                message="field1 is required"
            )
        
        # Validation error
        if not isinstance(req["field1"], str):
            return get_error_data_result(
                message="field1 must be string",
                code=RetCode.ARGUMENT_ERROR
            )
        
        # Permission error
        if not user_has_permission():
            return get_json_result(
                code=RetCode.PERMISSION_ERROR,
                message="You don't have permission"
            )
        
        # Success
        return get_json_result(data={"status": "ok"})
    
    except Exception as e:
        # Global error handler
        return server_error_response(e)
```

### Custom Error Codes

```python
from common.constants import RetCode

# Use appropriate error codes:
RetCode.SUCCESS = 0                      # Success
RetCode.ARGUMENT_ERROR = 101             # Bad input
RetCode.DATA_ERROR = 102                 # Missing data
RetCode.OPERATING_ERROR = 103            # Operation failed
RetCode.PERMISSION_ERROR = 108           # No permission
RetCode.AUTHENTICATION_ERROR = 109       # Not authenticated
RetCode.UNAUTHORIZED = 401               # Unauthorized
RetCode.FORBIDDEN = 403                  # Forbidden
RetCode.NOT_FOUND = 404                  # Not found
RetCode.SERVER_ERROR = 500               # Server error

return get_json_result(
    code=RetCode.OPERATING_ERROR,
    message="Could not complete operation"
)
```

---

## Request Validation

### Decorator-Based Validation

```python
from api.utils.api_utils import (
    validate_request,
    not_allowed_parameters
)

@manager.route('/update', methods=['POST'])
@login_required
@validate_request("kb_id", "name")        # Requires these fields
@not_allowed_parameters("id", "created_by")  # Prevents these fields
def update():
    """Update with validation"""
    req = request.json
    # At this point we know:
    # - kb_id exists
    # - name exists
    # - id and created_by don't exist
    
    kb_id = req["kb_id"]
    name = req["name"]
    
    return get_json_result(data={"updated": True})
```

### Custom Field Validation

```python
from api.constants import DATASET_NAME_LIMIT

@manager.route('/create', methods=['POST'])
@validate_request("name")
def create():
    """Custom validation for fields"""
    req = request.json
    name = req["name"]
    
    # Type validation
    if not isinstance(name, str):
        return get_data_error_result(
            message="Name must be string"
        )
    
    # Empty check
    if name.strip() == "":
        return get_data_error_result(
            message="Name can't be empty"
        )
    
    # Length validation
    if len(name.encode("utf-8")) > DATASET_NAME_LIMIT:
        return get_data_error_result(
            message=f"Name too long (max {DATASET_NAME_LIMIT} bytes)"
        )
    
    # Continue processing
    return get_json_result(data={"status": "ok"})
```

### Request Type Validation

```python
@manager.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle multipart form data"""
    # Form data access
    kb_id = request.form.get("kb_id")
    
    # File access
    if "file" not in request.files:
        return get_json_result(
            code=RetCode.ARGUMENT_ERROR,
            message="No file provided"
        )
    
    files = request.files.getlist("file")
    
    for file in files:
        if file.filename == "":
            return get_json_result(
                code=RetCode.ARGUMENT_ERROR,
                message="Empty filename"
            )
        
        # Process file
        ...
    
    return get_json_result(data={"count": len(files)})
```

---

## Advanced Patterns

### Response with Total Count

```python
from api.utils.api_utils import get_result

@manager.route('/list', methods=['POST'])
@login_required
def list_items():
    """Return paginated list with total count"""
    req = request.json
    page = req.get("page_number", 1)
    per_page = req.get("items_per_page", 20)
    
    # Get total count
    total = KnowledgebaseService.query(
        tenant_id=current_user.id
    ).count()
    
    # Get paginated items
    items = KnowledgebaseService.query(
        tenant_id=current_user.id,
        reverse=True,
        order_by="create_time"
    ).offset((page-1)*per_page).limit(per_page)
    
    return get_result(
        data=[item.to_dict() for item in items],
        total=total
    )
```

### Bulk Operations

```python
from api.db.services.knowledgebase_service import KnowledgebaseService

@manager.route('/delete_bulk', methods=['POST'])
@login_required
def delete_bulk():
    """Delete multiple items"""
    req = request.json
    kb_ids = req.get("kb_ids", [])
    
    # Verify ownership of all KBs
    kbs = KnowledgebaseService.get_by_ids(kb_ids)
    for kb in kbs:
        if kb.created_by != current_user.id:
            return get_json_result(
                code=RetCode.PERMISSION_ERROR,
                message="You don't own all selected knowledge bases"
            )
    
    # Delete all
    deleted = KnowledgebaseService.delete_by_ids(kb_ids)
    
    return get_json_result(data={"deleted_count": deleted})
```

---

For comprehensive API patterns and detailed implementation guide, see:
- `/home/user/ragflow/API_ARCHITECTURE_ANALYSIS.md` - Full architecture analysis
- `/home/user/ragflow/API_QUICK_REFERENCE.md` - Quick reference

