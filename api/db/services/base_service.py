#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
Standardized service layer base class.

This module provides a BaseService class that standardizes the service layer pattern
across all services. It provides consistent error handling, return types, and
connection management.

Usage:
    class DocumentService(BaseService[Document]):
        model = Document

        @classmethod
        def _validate_create(cls, data: dict):
            if not data.get('name'):
                raise cls.ValidationError("Document name is required")
"""
from datetime import datetime
from typing import TypeVar, Generic, Optional, List, Tuple, Any, Dict

from api.db.db_models import DB
from api.db.services.common_service import CommonService
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, datetime_format
from common.constants import StatusEnum


# Type variable bound to BaseModel for generic type hints
T = TypeVar('T')


class BaseService(CommonService, Generic[T]):
    """Standardized base service class with consistent error handling.

    This class extends CommonService with standardized patterns for:
    - Exception-based error handling (instead of tuple returns)
    - Type-hinted methods with generic support
    - Built-in validation hooks
    - Consistent pagination interface

    Attributes:
        model: The Peewee model class that this service operates on.
               Must be set by subclasses.

    Exceptions:
        ServiceError: Base exception for all service errors
        NotFoundError: Raised when a resource is not found
        ValidationError: Raised when input validation fails
        PermissionError: Raised when access is denied

    Example:
        class UserService(BaseService[User]):
            model = User

            @classmethod
            def _validate_create(cls, data: dict):
                if not data.get('email'):
                    raise cls.ValidationError("Email is required")
    """

    model = None

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

    @classmethod
    @DB.connection_context()
    def get_by_id_or_raise(cls, obj_id: str) -> T:
        """Get a single record by ID, raising NotFoundError if not found.

        This method provides consistent exception-based error handling instead
        of returning tuples.

        Args:
            obj_id: The unique identifier of the record.

        Returns:
            The model instance if found.

        Raises:
            NotFoundError: If no record with the given ID exists.
        """
        obj = cls.model.get_or_none(cls.model.id == obj_id)
        if not obj:
            raise cls.NotFoundError(f"{cls.model.__name__} not found: {obj_id}")
        return obj

    @classmethod
    @DB.connection_context()
    def list_with_pagination(
        cls,
        page: int = 1,
        size: int = 20,
        order_by: str = "create_time",
        reverse: bool = True,
        **filters
    ) -> Tuple[List[T], int]:
        """List records with pagination and filters.

        This method provides a standardized way to retrieve paginated lists
        with optional filtering and sorting.

        Args:
            page: Page number (1-indexed). Defaults to 1.
            size: Number of records per page. Defaults to 20.
            order_by: Field name to sort by. Defaults to "create_time".
            reverse: If True, sort descending. Defaults to True.
            **filters: Additional filter conditions as keyword arguments.

        Returns:
            A tuple of (list of records, total count).

        Example:
            docs, total = DocumentService.list_with_pagination(
                page=1, size=20, kb_id="kb-123"
            )
        """
        query = cls.model.select()

        # Apply filters
        for key, value in filters.items():
            if hasattr(cls.model, key) and value is not None:
                query = query.where(getattr(cls.model, key) == value)

        # Get total count before pagination
        total = query.count()

        # Apply ordering
        if order_by and hasattr(cls.model, order_by):
            if reverse:
                query = query.order_by(getattr(cls.model, order_by).desc())
            else:
                query = query.order_by(getattr(cls.model, order_by).asc())

        # Apply pagination
        items = list(query.paginate(page, size))

        return items, total

    @classmethod
    @DB.connection_context()
    def create_with_validation(cls, **kwargs) -> T:
        """Create a new record with validation.

        This method creates a new record after running validation hooks.
        It automatically generates ID and timestamp fields.

        Args:
            **kwargs: Record field values as keyword arguments.

        Returns:
            The newly created model instance.

        Raises:
            ValidationError: If validation fails.
        """
        # Run validation
        cls._validate_create(kwargs)

        # Set automatic fields
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()
        kwargs["create_time"] = current_timestamp()
        kwargs["create_date"] = datetime_format(datetime.now())
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())

        # Create and save
        obj = cls.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    @classmethod
    @DB.connection_context()
    def update_with_validation(cls, obj_id: str, **kwargs) -> T:
        """Update a record with validation.

        This method updates an existing record after running validation hooks.
        It automatically updates timestamp fields.

        Args:
            obj_id: The unique identifier of the record to update.
            **kwargs: Field values to update.

        Returns:
            The updated model instance.

        Raises:
            NotFoundError: If the record is not found.
            ValidationError: If validation fails.
        """
        # Get existing record
        obj = cls.get_by_id_or_raise(obj_id)

        # Run validation
        cls._validate_update(kwargs)

        # Update timestamp fields
        kwargs["update_time"] = current_timestamp()
        kwargs["update_date"] = datetime_format(datetime.now())

        # Update fields
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        obj.save()
        return obj

    @classmethod
    @DB.connection_context()
    def soft_delete(cls, obj_id: str) -> bool:
        """Soft delete a record by setting its status to INVALID.

        This method performs a soft delete by updating the status field
        instead of physically removing the record.

        Args:
            obj_id: The unique identifier of the record to delete.

        Returns:
            True if the record was deleted, False otherwise.

        Note:
            This requires the model to have a 'status' field.
        """
        if not hasattr(cls.model, 'status'):
            # Fall back to hard delete if no status field
            return cls.model.delete().where(cls.model.id == obj_id).execute() > 0

        return cls.model.update(
            status=StatusEnum.INVALID.value,
            update_time=current_timestamp(),
            update_date=datetime_format(datetime.now())
        ).where(
            cls.model.id == obj_id
        ).execute() > 0

    @classmethod
    @DB.connection_context()
    def exists(cls, obj_id: str) -> bool:
        """Check if a record with the given ID exists.

        Args:
            obj_id: The unique identifier to check.

        Returns:
            True if the record exists, False otherwise.
        """
        return cls.model.select().where(cls.model.id == obj_id).exists()

    @classmethod
    @DB.connection_context()
    def count(cls, **filters) -> int:
        """Count records matching the given filters.

        Args:
            **filters: Filter conditions as keyword arguments.

        Returns:
            The number of matching records.
        """
        query = cls.model.select()
        for key, value in filters.items():
            if hasattr(cls.model, key) and value is not None:
                query = query.where(getattr(cls.model, key) == value)
        return query.count()

    @classmethod
    def _validate_create(cls, data: Dict[str, Any]) -> None:
        """Validate data before creating a record.

        Override this method in subclasses to implement custom validation
        logic for create operations.

        Args:
            data: Dictionary of field values to validate.

        Raises:
            ValidationError: If validation fails.
        """
        pass

    @classmethod
    def _validate_update(cls, data: Dict[str, Any]) -> None:
        """Validate data before updating a record.

        Override this method in subclasses to implement custom validation
        logic for update operations.

        Args:
            data: Dictionary of field values to validate.

        Raises:
            ValidationError: If validation fails.
        """
        pass

    @classmethod
    def to_dict(cls, obj: T) -> Dict[str, Any]:
        """Convert a model instance to a dictionary.

        Args:
            obj: The model instance to convert.

        Returns:
            Dictionary representation of the model.
        """
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return obj.__dict__.get("__data__", {})

    @classmethod
    def to_dict_list(cls, objs: List[T]) -> List[Dict[str, Any]]:
        """Convert a list of model instances to dictionaries.

        Args:
            objs: List of model instances to convert.

        Returns:
            List of dictionary representations.
        """
        return [cls.to_dict(obj) for obj in objs]
