# RFC-0001: Service Layer Standardization

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 3-5 days
**Priority:** P1 (Quick Win)

## Summary

Standardize the service layer pattern across all services to improve code consistency, reduce bugs, and make the codebase more maintainable.

## Motivation

The current service layer has inconsistencies:

1. **Inconsistent error handling**: Some services return None on error, others raise exceptions
2. **Mixed return types**: Some return models, others return dicts
3. **Inconsistent connection handling**: Some use `@DB.connection_context()`, others don't
4. **Missing validation**: Input validation varies by service

These inconsistencies make the codebase harder to maintain and contribute to.

## Detailed Design

### Standard Service Interface

```python
# api/db/services/base_service.py
from typing import TypeVar, Generic, Optional, List
from api.db.db_models import DataBaseModel

T = TypeVar('T', bound=DataBaseModel)

class BaseService(Generic[T]):
    model: T = None

    class ServiceError(Exception):
        """Base exception for service errors"""
        pass

    class NotFoundError(ServiceError):
        """Resource not found"""
        pass

    class ValidationError(ServiceError):
        """Input validation failed"""
        pass

    @classmethod
    @DB.connection_context()
    def get_by_id(cls, obj_id: str) -> Optional[T]:
        """Get single record by ID"""
        obj = cls.model.select().where(cls.model.id == obj_id).first()
        if not obj:
            raise cls.NotFoundError(f"{cls.model.__name__} not found: {obj_id}")
        return obj

    @classmethod
    @DB.connection_context()
    def list(cls, page: int = 1, size: int = 20, **filters) -> tuple[List[T], int]:
        """List with pagination and filters"""
        query = cls.model.select().where(cls.model.status != StatusEnum.DELETED)

        for key, value in filters.items():
            if hasattr(cls.model, key):
                query = query.where(getattr(cls.model, key) == value)

        total = query.count()
        items = list(query.paginate(page, size))
        return items, total

    @classmethod
    @DB.connection_context()
    def create(cls, **kwargs) -> T:
        """Create new record with validation"""
        cls._validate_create(kwargs)
        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def update(cls, obj_id: str, **kwargs) -> T:
        """Update record with validation"""
        obj = cls.get_by_id(obj_id)
        cls._validate_update(kwargs)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        obj.save()
        return obj

    @classmethod
    @DB.connection_context()
    def delete(cls, obj_id: str) -> bool:
        """Soft delete record"""
        return cls.model.update(
            status=StatusEnum.DELETED
        ).where(
            cls.model.id == obj_id
        ).execute() > 0

    @classmethod
    def _validate_create(cls, data: dict):
        """Override for custom validation"""
        pass

    @classmethod
    def _validate_update(cls, data: dict):
        """Override for custom validation"""
        pass
```

### Usage Example

```python
# api/db/services/document_service.py
class DocumentService(BaseService[Document]):
    model = Document

    @classmethod
    def _validate_create(cls, data: dict):
        if not data.get('name'):
            raise cls.ValidationError("Document name is required")
        if not data.get('kb_id'):
            raise cls.ValidationError("Knowledge base ID is required")

    @classmethod
    @DB.connection_context()
    def get_by_kb_id(cls, kb_id: str, page: int = 1, size: int = 20):
        """Domain-specific query"""
        return cls.list(page, size, kb_id=kb_id)
```

### API Layer Changes

```python
# api/apps/document_app.py
@manager.route('/get/<doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    try:
        doc = DocumentService.get_by_id(doc_id)
        return get_json_result(data=doc.to_dict())
    except DocumentService.NotFoundError as e:
        return get_json_result(code=404, message=str(e))
    except DocumentService.ValidationError as e:
        return get_json_result(code=400, message=str(e))
    except Exception as e:
        logging.exception("get_document failed")
        return get_json_result(code=500, message="Internal error")
```

## Example Usage

### Before

```python
# Inconsistent patterns
doc = DocumentService.get_by_id(doc_id)
if not doc:
    return get_json_result(code=404, message="Not found")

# Sometimes returns dict
kb_list = KnowledgebaseService.get_list(user_id)

# Sometimes raises
try:
    user = UserService.authenticate(email, password)
except Exception:
    return get_json_result(code=401)
```

### After

```python
# Consistent pattern everywhere
try:
    doc = DocumentService.get_by_id(doc_id)
    return get_json_result(data=doc.to_dict())
except DocumentService.NotFoundError:
    return get_json_result(code=404, message="Document not found")

# Consistent pagination
kbs, total = KnowledgebaseService.list(page=1, size=20, user_id=user_id)

# Consistent auth
try:
    user = UserService.authenticate(email, password)
except UserService.ValidationError:
    return get_json_result(code=401, message="Invalid credentials")
```

## Implementation Plan

### Phase 1: Foundation (Day 1-2)
1. Create `BaseService` class with standard interface
2. Create custom exception classes
3. Add type hints throughout

### Phase 2: Migration (Day 2-4)
1. Update `DocumentService` as reference implementation
2. Migrate remaining services:
   - `KnowledgebaseService`
   - `UserService`
   - `DialogService`
   - `CanvasService`
   - etc.
3. Update all API endpoints to use new patterns

### Phase 3: Testing (Day 4-5)
1. Add unit tests for `BaseService`
2. Verify all endpoints work correctly
3. Document the new patterns

## Backwards Compatibility

**Breaking changes:**
- Services now raise exceptions instead of returning None
- Return types are now typed models instead of mixed dict/model

**Migration:**
- API layer must catch new exceptions
- Remove null checks in favor of try/except

## Alternatives Considered

### 1. Keep Current Pattern
- **Pros:** No migration effort
- **Cons:** Continued inconsistency, harder to maintain

### 2. Full Repository Pattern
- **Pros:** More separation of concerns
- **Cons:** Overkill for current needs, more code

### 3. GraphQL
- **Pros:** Type-safe queries
- **Cons:** Major rewrite, different paradigm

## Open Questions

1. Should we add caching at the service layer?
2. Should validation be in service or separate validator classes?
3. Do we need audit logging in base service?

## Success Criteria

- [ ] All services inherit from `BaseService`
- [ ] 100% of endpoints use consistent error handling
- [ ] Type hints on all service methods
- [ ] Unit tests for base service
- [ ] Documentation updated

## Stakeholder Approvals

- [ ] Backend Lead
- [ ] Code Review
- [ ] QA Sign-off
