# Service Layer Standardization

This document describes the standardized service layer pattern implemented in RAGFlow.

## Overview

All service classes in RAGFlow now inherit from `BaseService`, which provides:

- Consistent exception-based error handling
- Type hints with generic support
- Built-in validation hooks
- Standard CRUD operations

## BaseService Class

The `BaseService` class is located at `api/db/services/base_service.py`.

### Exception Classes

```python
class BaseService:
    class ServiceError(Exception):
        """Base exception for all service errors."""
        pass

    class NotFoundError(ServiceError):
        """Raised when a requested resource is not found."""
        pass

    class ValidationError(ServiceError):
        """Raised when input validation fails."""
        pass

    class PermissionError(ServiceError):
        """Raised when access to a resource is denied."""
        pass
```

### Standard Methods

#### get_by_id_or_raise

Get a single record by ID, raising `NotFoundError` if not found.

```python
# Old pattern
e, doc = DocumentService.get_by_id(doc_id)
if not e:
    return error_response("Not found")

# New pattern
try:
    doc = DocumentService.get_by_id_or_raise(doc_id)
except DocumentService.NotFoundError as e:
    return get_json_result(code=404, message=str(e))
```

#### list_with_pagination

List records with pagination and filters.

```python
docs, total = DocumentService.list_with_pagination(
    page=1,
    size=20,
    order_by="create_time",
    reverse=True,
    kb_id="kb-123"
)
```

#### create_with_validation

Create a new record with validation.

```python
try:
    doc = DocumentService.create_with_validation(
        name="test.pdf",
        kb_id="kb-123",
        created_by="user-123"
    )
except DocumentService.ValidationError as e:
    return get_json_result(code=400, message=str(e))
```

#### update_with_validation

Update a record with validation.

```python
try:
    doc = DocumentService.update_with_validation(
        doc_id,
        name="new-name.pdf"
    )
except DocumentService.NotFoundError as e:
    return get_json_result(code=404, message=str(e))
except DocumentService.ValidationError as e:
    return get_json_result(code=400, message=str(e))
```

## Creating a New Service

To create a new service, inherit from `BaseService` and set the model:

```python
from api.db.services.base_service import BaseService
from api.db.db_models import MyModel

class MyService(BaseService[MyModel]):
    model = MyModel

    @classmethod
    def _validate_create(cls, data: dict):
        """Validate data before creating a record."""
        if not data.get('name'):
            raise cls.ValidationError("Name is required")

    @classmethod
    def _validate_update(cls, data: dict):
        """Validate data before updating a record."""
        pass  # Add custom validation as needed
```

## API Endpoint Pattern

API endpoints should catch service exceptions:

```python
@manager.route("/get/<doc_id>", methods=["GET"])
@login_required
def get(doc_id):
    try:
        doc = DocumentService.get_by_id_or_raise(doc_id)
        return get_json_result(data=doc.to_dict())
    except DocumentService.NotFoundError as e:
        return get_json_result(code=404, message=str(e))
    except DocumentService.ValidationError as e:
        return get_json_result(code=400, message=str(e))
    except Exception as e:
        logging.exception("get_document failed")
        return get_json_result(code=500, message="Internal error")
```

## Migrated Services

The following services have been migrated to use `BaseService`:

- `DocumentService`
- `KnowledgebaseService`
- `UserService`
- `TenantService`
- `UserTenantService`
- `DialogService`
- `CanvasTemplateService`
- `DataFlowTemplateService`
- `UserCanvasService`

## Backward Compatibility

The existing methods (like `get_by_id` returning tuples) remain available for backward compatibility. New code should use the standardized methods.

## Testing

Unit tests for the BaseService are located at:
`test/unit_test/api/db/services/test_base_service.py`

Run tests with:
```bash
pytest test/unit_test/api/db/services/test_base_service.py -v
```
