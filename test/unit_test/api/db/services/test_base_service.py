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
Unit tests for the BaseService class.

These tests verify the functionality of the standardized service layer pattern,
including exception handling, validation, and CRUD operations.
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from api.db.services.base_service import BaseService


class TestBaseServiceExceptions:
    """Test custom exception classes in BaseService."""

    def test_service_error_is_exception(self):
        """Test that ServiceError is a valid exception."""
        assert issubclass(BaseService.ServiceError, Exception)

    def test_not_found_error_inherits_service_error(self):
        """Test that NotFoundError inherits from ServiceError."""
        assert issubclass(BaseService.NotFoundError, BaseService.ServiceError)

    def test_validation_error_inherits_service_error(self):
        """Test that ValidationError inherits from ServiceError."""
        assert issubclass(BaseService.ValidationError, BaseService.ServiceError)

    def test_permission_error_inherits_service_error(self):
        """Test that PermissionError inherits from ServiceError."""
        assert issubclass(BaseService.PermissionError, BaseService.ServiceError)

    def test_can_raise_not_found_error(self):
        """Test that NotFoundError can be raised with message."""
        with pytest.raises(BaseService.NotFoundError) as exc_info:
            raise BaseService.NotFoundError("Test not found")
        assert str(exc_info.value) == "Test not found"

    def test_can_raise_validation_error(self):
        """Test that ValidationError can be raised with message."""
        with pytest.raises(BaseService.ValidationError) as exc_info:
            raise BaseService.ValidationError("Invalid input")
        assert str(exc_info.value) == "Invalid input"

    def test_can_catch_service_error_from_subclass(self):
        """Test that ServiceError can catch subclass exceptions."""
        with pytest.raises(BaseService.ServiceError):
            raise BaseService.NotFoundError("Should be caught")


class TestBaseServiceValidation:
    """Test validation methods in BaseService."""

    def test_validate_create_default_passes(self):
        """Test that default _validate_create passes without error."""
        # Default implementation should not raise
        BaseService._validate_create({})

    def test_validate_update_default_passes(self):
        """Test that default _validate_update passes without error."""
        # Default implementation should not raise
        BaseService._validate_update({})


class TestConcreteServiceInheritance:
    """Test that services correctly inherit from BaseService."""

    def test_document_service_inherits_base(self):
        """Test DocumentService inherits from BaseService."""
        from api.db.services.document_service import DocumentService
        assert issubclass(DocumentService, BaseService)

    def test_knowledgebase_service_inherits_base(self):
        """Test KnowledgebaseService inherits from BaseService."""
        from api.db.services.knowledgebase_service import KnowledgebaseService
        assert issubclass(KnowledgebaseService, BaseService)

    def test_user_service_inherits_base(self):
        """Test UserService inherits from BaseService."""
        from api.db.services.user_service import UserService
        assert issubclass(UserService, BaseService)

    def test_tenant_service_inherits_base(self):
        """Test TenantService inherits from BaseService."""
        from api.db.services.user_service import TenantService
        assert issubclass(TenantService, BaseService)

    def test_dialog_service_inherits_base(self):
        """Test DialogService inherits from BaseService."""
        from api.db.services.dialog_service import DialogService
        assert issubclass(DialogService, BaseService)

    def test_canvas_service_inherits_base(self):
        """Test UserCanvasService inherits from BaseService."""
        from api.db.services.canvas_service import UserCanvasService
        assert issubclass(UserCanvasService, BaseService)


class TestServiceValidationMethods:
    """Test that services have validation methods."""

    def test_document_service_has_validation(self):
        """Test DocumentService has validation methods."""
        from api.db.services.document_service import DocumentService

        # Test _validate_create
        with pytest.raises(DocumentService.ValidationError):
            DocumentService._validate_create({})  # Missing name

        with pytest.raises(DocumentService.ValidationError):
            DocumentService._validate_create({'name': 'test'})  # Missing kb_id

    def test_knowledgebase_service_has_validation(self):
        """Test KnowledgebaseService has validation methods."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        # Test _validate_create
        with pytest.raises(KnowledgebaseService.ValidationError):
            KnowledgebaseService._validate_create({})  # Missing name

    def test_user_service_has_validation(self):
        """Test UserService has validation methods."""
        from api.db.services.user_service import UserService

        # Test _validate_create
        with pytest.raises(UserService.ValidationError):
            UserService._validate_create({})  # Missing email

    def test_dialog_service_has_validation(self):
        """Test DialogService has validation methods."""
        from api.db.services.dialog_service import DialogService

        # Test _validate_create
        with pytest.raises(DialogService.ValidationError):
            DialogService._validate_create({})  # Missing name

    def test_canvas_service_has_validation(self):
        """Test UserCanvasService has validation methods."""
        from api.db.services.canvas_service import UserCanvasService

        # Test _validate_create
        with pytest.raises(UserCanvasService.ValidationError):
            UserCanvasService._validate_create({})  # Missing title


class TestBaseServiceUtilityMethods:
    """Test utility methods in BaseService."""

    def test_to_dict_with_dict_method(self):
        """Test to_dict calls object's to_dict if available."""
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {'id': '123', 'name': 'test'}

        result = BaseService.to_dict(mock_obj)
        assert result == {'id': '123', 'name': 'test'}
        mock_obj.to_dict.assert_called_once()

    def test_to_dict_list_converts_all(self):
        """Test to_dict_list converts all objects."""
        mock_objs = [
            MagicMock(to_dict=MagicMock(return_value={'id': '1'})),
            MagicMock(to_dict=MagicMock(return_value={'id': '2'})),
        ]

        result = BaseService.to_dict_list(mock_objs)
        assert len(result) == 2
        assert result[0] == {'id': '1'}
        assert result[1] == {'id': '2'}


class TestExceptionMessages:
    """Test that exception messages are properly formatted."""

    def test_not_found_error_format(self):
        """Test NotFoundError message formatting."""
        error = BaseService.NotFoundError("User not found: abc123")
        assert "User not found: abc123" in str(error)

    def test_validation_error_format(self):
        """Test ValidationError message formatting."""
        error = BaseService.ValidationError("Email is required")
        assert "Email is required" in str(error)

    def test_permission_error_format(self):
        """Test PermissionError message formatting."""
        error = BaseService.PermissionError("Access denied")
        assert "Access denied" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
