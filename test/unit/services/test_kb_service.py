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
Unit tests for KnowledgebaseService.

Tests cover knowledge base creation, retrieval, updating, deletion,
access control, and parser configuration management.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestKnowledgebaseServiceParsing:
    """Tests for parsing-related methods."""

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.get_by_kb_id")
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.query")
    @patch("api.db.db_models.DB.connection_context")
    def test_is_parsed_done_returns_true_when_complete(self, mock_context, mock_query, mock_get_docs):
        """Test is_parsed_done returns True when all documents are parsed."""
        from api.db.services.knowledgebase_service import KnowledgebaseService
        from common.constants import TaskStatus

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        # Mock KB exists
        mock_kb = MagicMock()
        mock_kb.name = "Test KB"
        mock_query.return_value = [mock_kb]

        # Mock documents - all done
        mock_get_docs.return_value = ([
            {"name": "doc1.pdf", "run": TaskStatus.DONE.value, "chunk_num": 10},
            {"name": "doc2.pdf", "run": TaskStatus.DONE.value, "chunk_num": 5},
        ], 2)

        result, error = KnowledgebaseService.is_parsed_done("kb-001")

        assert result is True
        assert error is None

    @pytest.mark.p1
    @patch("api.db.services.document_service.DocumentService.get_by_kb_id")
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.query")
    @patch("api.db.db_models.DB.connection_context")
    def test_is_parsed_done_returns_false_when_running(self, mock_context, mock_query, mock_get_docs):
        """Test is_parsed_done returns False when documents are still running."""
        from api.db.services.knowledgebase_service import KnowledgebaseService
        from common.constants import TaskStatus

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_kb = MagicMock()
        mock_kb.name = "Test KB"
        mock_query.return_value = [mock_kb]

        mock_get_docs.return_value = ([
            {"name": "doc1.pdf", "run": TaskStatus.RUNNING.value, "chunk_num": 0},
        ], 1)

        result, error = KnowledgebaseService.is_parsed_done("kb-001")

        assert result is False
        assert "still being parsed" in error

    @pytest.mark.p2
    @patch("api.db.services.document_service.DocumentService.get_by_kb_id")
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.query")
    @patch("api.db.db_models.DB.connection_context")
    def test_is_parsed_done_returns_false_when_unstarted(self, mock_context, mock_query, mock_get_docs):
        """Test is_parsed_done returns False when documents haven't started."""
        from api.db.services.knowledgebase_service import KnowledgebaseService
        from common.constants import TaskStatus

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_kb = MagicMock()
        mock_kb.name = "Test KB"
        mock_query.return_value = [mock_kb]

        mock_get_docs.return_value = ([
            {"name": "doc1.pdf", "run": TaskStatus.UNSTART.value, "chunk_num": 0},
        ], 1)

        result, error = KnowledgebaseService.is_parsed_done("kb-001")

        assert result is False
        assert "not been parsed" in error

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.query")
    @patch("api.db.db_models.DB.connection_context")
    def test_is_parsed_done_returns_false_when_kb_not_found(self, mock_context, mock_query):
        """Test is_parsed_done returns False when KB not found."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query.return_value = []

        result, error = KnowledgebaseService.is_parsed_done("nonexistent")

        assert result is False
        assert "not found" in error


class TestKnowledgebaseServiceAccessControl:
    """Tests for access control methods."""

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_accessible4deletion_returns_true_for_owner(self, mock_context, mock_model):
        """Test accessible4deletion returns True for KB owner."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.paginate.return_value.dicts.return_value = [{"id": "kb-001"}]
        mock_model.select.return_value.where.return_value = mock_query

        result = KnowledgebaseService.accessible4deletion("kb-001", "user-001")

        assert result is True

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_accessible4deletion_returns_false_for_non_owner(self, mock_context, mock_model):
        """Test accessible4deletion returns False for non-owner."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.paginate.return_value.dicts.return_value = []
        mock_model.select.return_value.where.return_value = mock_query

        result = KnowledgebaseService.accessible4deletion("kb-001", "other-user")

        assert result is False


class TestKnowledgebaseServiceQueries:
    """Tests for query methods."""

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_by_tenant_ids_returns_kbs(self, mock_context, mock_model):
        """Test get_by_tenant_ids returns knowledge bases."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.paginate.return_value = mock_query
        mock_query.dicts.return_value = [
            {"id": "kb-1", "name": "KB 1"},
            {"id": "kb-2", "name": "KB 2"}
        ]
        mock_model.select.return_value.join.return_value.where.return_value = mock_query

        kbs, count = KnowledgebaseService.get_by_tenant_ids(
            joined_tenant_ids=["tenant-001"],
            user_id="user-001",
            page_number=1,
            items_per_page=10,
            orderby="create_time",
            desc=True,
            keywords=""
        )

        assert count == 2
        assert len(kbs) == 2

    @pytest.mark.p2
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_by_tenant_ids_with_keywords(self, mock_context, mock_model):
        """Test get_by_tenant_ids filters by keywords."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.paginate.return_value = mock_query
        mock_query.dicts.return_value = [{"id": "kb-1", "name": "Test KB"}]
        mock_model.select.return_value.join.return_value.where.return_value = mock_query

        kbs, count = KnowledgebaseService.get_by_tenant_ids(
            joined_tenant_ids=["tenant-001"],
            user_id="user-001",
            page_number=1,
            items_per_page=10,
            orderby="create_time",
            desc=True,
            keywords="Test"
        )

        assert count == 1
        assert kbs[0]["name"] == "Test KB"

    @pytest.mark.p2
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_kb_ids(self, mock_context, mock_model):
        """Test get_kb_ids returns KB IDs for tenant."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_kb1 = MagicMock()
        mock_kb1.id = "kb-1"
        mock_kb2 = MagicMock()
        mock_kb2.id = "kb-2"

        mock_model.select.return_value.where.return_value = [mock_kb1, mock_kb2]

        result = KnowledgebaseService.get_kb_ids("tenant-001")

        assert len(result) == 2
        assert "kb-1" in result
        assert "kb-2" in result


class TestKnowledgebaseServiceDetail:
    """Tests for detail retrieval methods."""

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_detail_returns_kb_info(self, mock_context, mock_model):
        """Test get_detail returns KB details."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.join.return_value.where.return_value.dicts.return_value = [{
            "id": "kb-001",
            "name": "Test KB",
            "doc_num": 10,
            "token_num": 5000,
            "chunk_num": 100
        }]
        mock_model.select.return_value = mock_query

        result = KnowledgebaseService.get_detail("kb-001")

        assert result is not None
        assert result["id"] == "kb-001"
        assert result["name"] == "Test KB"
        assert result["doc_num"] == 10

    @pytest.mark.p2
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_get_detail_returns_none_for_nonexistent(self, mock_context, mock_model):
        """Test get_detail returns None for nonexistent KB."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.join.return_value.where.return_value.dicts.return_value = []
        mock_model.select.return_value = mock_query

        result = KnowledgebaseService.get_detail("nonexistent")

        assert result is None


class TestKnowledgebaseServiceDocuments:
    """Tests for document-related methods."""

    @pytest.mark.p2
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_list_documents_by_ids(self, mock_context, mock_model):
        """Test list_documents_by_ids returns document IDs."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_query = MagicMock()
        mock_query.dicts.return_value = [
            {"document_id": "doc-1"},
            {"document_id": "doc-2"},
            {"document_id": "doc-3"}
        ]
        mock_model.select.return_value.join.return_value.where.return_value = mock_query

        result = KnowledgebaseService.list_documents_by_ids(["kb-001", "kb-002"])

        assert len(result) == 3
        assert "doc-1" in result
        assert "doc-2" in result
        assert "doc-3" in result


class TestKnowledgebaseServiceAtomicOperations:
    """Tests for atomic counter operations."""

    @pytest.mark.p1
    @patch("api.db.services.knowledgebase_service.KnowledgebaseService.model")
    @patch("api.db.db_models.DB.connection_context")
    def test_atomic_increase_doc_num_by_id(self, mock_context, mock_model):
        """Test atomic document count increment."""
        from api.db.services.knowledgebase_service import KnowledgebaseService

        mock_context.return_value.__enter__ = MagicMock()
        mock_context.return_value.__exit__ = MagicMock(return_value=False)

        mock_update_chain = MagicMock()
        mock_update_chain.where.return_value.execute.return_value = 1
        mock_model.update.return_value = mock_update_chain

        result = KnowledgebaseService.atomic_increase_doc_num_by_id("kb-001")

        assert result == 1
        mock_model.update.assert_called_once()
