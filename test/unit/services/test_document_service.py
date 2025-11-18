#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
Unit tests for DocumentService.

Tests cover document creation, retrieval, updating, deletion,
and chunk management operations.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

# Import test utilities
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestDocumentServiceGetList:
    """Tests for DocumentService.get_list method."""

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_list_returns_documents(self, mock_context, mock_model):
        """Test that get_list returns paginated documents."""
        from api.db.services.document_service import DocumentService

        # Setup mock
        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.count.return_value = 2
        mock_query.paginate.return_value = mock_query
        mock_query.dicts.return_value = [
            {"id": "doc-1", "name": "test1.pdf"},
            {"id": "doc-2", "name": "test2.pdf"}
        ]

        mock_select = MagicMock(return_value=mock_query)
        mock_model.select = mock_select

        # Call the method
        with patch.object(DocumentService, 'get_cls_model_fields', return_value=[]):
            docs, count = DocumentService.get_list(
                kb_id="kb-001",
                page_number=1,
                items_per_page=10,
                orderby="create_time",
                desc=True,
                keywords="",
                id=None,
                name=None
            )

        # Assertions
        assert count == 2
        assert len(docs) == 2

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_list_with_keywords_filter(self, mock_context, mock_model):
        """Test that get_list filters by keywords."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.count.return_value = 1
        mock_query.paginate.return_value = mock_query
        mock_query.dicts.return_value = [{"id": "doc-1", "name": "test.pdf"}]
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_select = MagicMock(return_value=mock_query)
        mock_model.select = mock_select

        with patch.object(DocumentService, 'get_cls_model_fields', return_value=[]):
            docs, count = DocumentService.get_list(
                kb_id="kb-001",
                page_number=1,
                items_per_page=10,
                orderby="create_time",
                desc=True,
                keywords="test",
                id=None,
                name=None
            )

        assert count == 1


class TestDocumentServiceInsert:
    """Tests for DocumentService.insert method."""

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.atomic_increase_doc_num_by_id")
    @patch("api.db.services.document_service.DocumentService.save")
    @patch("api.db.db_models.DB.connection_context")
    def test_insert_creates_document(self, mock_context, mock_save, mock_increase):
        """Test that insert creates a document and increments KB count."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_save.return_value = True
        mock_increase.return_value = True

        doc_data = {
            "id": "doc-001",
            "name": "test.pdf",
            "kb_id": "kb-001",
            "created_by": "user-001",
            "location": "/tmp/test.pdf",
            "size": 1024,
            "type": "pdf",
            "suffix": "pdf",
            "status": "1",
            "run": "0",
            "progress": 0.0,
            "token_num": 0,
            "chunk_num": 0,
            "parser_id": "naive",
            "parser_config": {},
        }

        result = DocumentService.insert(doc_data)

        mock_save.assert_called_once()
        mock_increase.assert_called_once_with("kb-001")
        assert result.id == "doc-001"

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.save")
    @patch("api.db.db_models.DB.connection_context")
    def test_insert_raises_on_save_failure(self, mock_context, mock_save):
        """Test that insert raises RuntimeError on save failure."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_save.return_value = False

        doc_data = {
            "id": "doc-001",
            "name": "test.pdf",
            "kb_id": "kb-001",
        }

        with pytest.raises(RuntimeError, match="Database error"):
            DocumentService.insert(doc_data)


class TestDocumentServiceChunkManagement:
    """Tests for chunk number management methods."""

    @pytest.mark.p1
    @patch("api.db.db_models.Knowledgebase")
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_increment_chunk_num(self, mock_context, mock_model, mock_kb):
        """Test that increment_chunk_num updates document and KB counts."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        # Setup mock chain for document update
        mock_update_chain = MagicMock()
        mock_update_chain.where.return_value.execute.return_value = 1
        mock_model.update.return_value = mock_update_chain

        # Setup mock chain for KB update
        mock_kb_chain = MagicMock()
        mock_kb_chain.where.return_value.execute.return_value = 1
        mock_kb.update.return_value = mock_kb_chain

        result = DocumentService.increment_chunk_num(
            doc_id="doc-001",
            kb_id="kb-001",
            token_num=100,
            chunk_num=5,
            duration=1.5
        )

        assert result == 1
        mock_model.update.assert_called_once()
        mock_kb.update.assert_called_once()

    @pytest.mark.p2
    @patch("api.db.db_models.Knowledgebase")
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_decrement_chunk_num(self, mock_context, mock_model, mock_kb):
        """Test that decrement_chunk_num reduces counts."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_update_chain = MagicMock()
        mock_update_chain.where.return_value.execute.return_value = 1
        mock_model.update.return_value = mock_update_chain

        mock_kb_chain = MagicMock()
        mock_kb_chain.where.return_value.execute.return_value = 1
        mock_kb.update.return_value = mock_kb_chain

        result = DocumentService.decrement_chunk_num(
            doc_id="doc-001",
            kb_id="kb-001",
            token_num=50,
            chunk_num=3,
            duration=0.5
        )

        assert result == 1

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_decrement_chunk_num_raises_on_not_found(self, mock_context, mock_model):
        """Test that decrement raises LookupError when document not found."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_update_chain = MagicMock()
        mock_update_chain.where.return_value.execute.return_value = 0
        mock_model.update.return_value = mock_update_chain

        with pytest.raises(LookupError):
            DocumentService.decrement_chunk_num(
                doc_id="nonexistent",
                kb_id="kb-001",
                token_num=50,
                chunk_num=3,
                duration=0.5
            )


class TestDocumentServiceAccessControl:
    """Tests for document access control methods."""

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_tenant_id_returns_tenant(self, mock_context, mock_model):
        """Test that get_tenant_id returns the correct tenant ID."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.join.return_value.where.return_value.dicts.return_value = [
            {"tenant_id": "tenant-001"}
        ]
        mock_model.select.return_value = mock_query

        result = DocumentService.get_tenant_id("doc-001")

        assert result == "tenant-001"

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_tenant_id_returns_none_for_nonexistent(self, mock_context, mock_model):
        """Test that get_tenant_id returns None for nonexistent document."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.join.return_value.where.return_value.dicts.return_value = []
        mock_model.select.return_value = mock_query

        result = DocumentService.get_tenant_id("nonexistent")

        assert result is None


class TestDocumentServiceHealthCheck:
    """Tests for document health check methods."""

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.get_doc_count")
    @patch("api.db.db_models.DB.connection_context")
    def test_check_doc_health_passes_normal(self, mock_context, mock_count):
        """Test health check passes for normal conditions."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_count.return_value = 5

        with patch.dict(os.environ, {"MAX_FILE_NUM_PER_USER": "100"}):
            result = DocumentService.check_doc_health("tenant-001", "test.pdf")

        assert result is True

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.get_doc_count")
    @patch("api.db.db_models.DB.connection_context")
    def test_check_doc_health_fails_on_limit(self, mock_context, mock_count):
        """Test health check fails when file limit exceeded."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_count.return_value = 100

        with patch.dict(os.environ, {"MAX_FILE_NUM_PER_USER": "100"}):
            with pytest.raises(RuntimeError, match="Exceed the maximum file number"):
                DocumentService.check_doc_health("tenant-001", "test.pdf")

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.get_doc_count")
    @patch("api.db.db_models.DB.connection_context")
    def test_check_doc_health_fails_on_filename_too_long(self, mock_context, mock_count):
        """Test health check fails when filename is too long."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)
        mock_count.return_value = 5

        long_filename = "a" * 300 + ".pdf"  # Very long filename

        with patch.dict(os.environ, {"MAX_FILE_NUM_PER_USER": "100"}):
            with pytest.raises(RuntimeError, match="Exceed the maximum length"):
                DocumentService.check_doc_health("tenant-001", long_filename)


class TestDocumentServiceQueries:
    """Tests for various query methods."""

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_all_doc_ids_by_kb_ids(self, mock_context, mock_model):
        """Test retrieving all document IDs for given KB IDs."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value.limit.return_value.dicts.side_effect = [
            [{"id": "doc-1"}, {"id": "doc-2"}],
            []
        ]
        mock_model.select.return_value.where.return_value = mock_query

        result = DocumentService.get_all_doc_ids_by_kb_ids(["kb-001", "kb-002"])

        assert len(result) == 2
        assert result[0]["id"] == "doc-1"

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_knowledgebase_id(self, mock_context, mock_model):
        """Test retrieving KB ID for a document."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.dicts.return_value = [{"kb_id": "kb-001"}]
        mock_model.select.return_value.where.return_value = mock_query

        result = DocumentService.get_knowledgebase_id("doc-001")

        assert result == "kb-001"

    @pytest.mark.p3
    @patch("api.db.services.document_service.DocumentService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_count_by_kb_id(self, mock_context, mock_model):
        """Test counting documents in a KB."""
        from api.db.services.document_service import DocumentService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.count.return_value = 10
        mock_model.select.return_value.where.return_value = mock_query

        result = DocumentService.count_by_kb_id(
            kb_id="kb-001",
            keywords="",
            run_status=[],
            types=[]
        )

        assert result == 10
