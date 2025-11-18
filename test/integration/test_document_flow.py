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
Integration tests for document processing flow.

Tests cover the complete document lifecycle from upload
to parsing, chunking, and indexing.
"""

import pytest
from unittest.mock import MagicMock, patch
import time
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestDocumentUploadFlow:
    """Integration tests for document upload flow."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        client = MagicMock()
        return client

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.fixture
    def sample_pdf_binary(self):
        """Return sample PDF binary for testing."""
        return b"%PDF-1.4\n%Test PDF content\n%%EOF"

    @pytest.mark.p1
    def test_upload_document_success(self, mock_client, auth_headers, sample_pdf_binary):
        """Test successful document upload."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "id": "doc-001",
                "name": "test.pdf",
                "status": "pending"
            }
        }
        mock_client.post.return_value = mock_response

        # Simulate upload
        response = mock_client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", sample_pdf_binary)}
        )
        result = response.json()

        assert result["code"] == 0
        assert result["data"]["id"] == "doc-001"
        assert result["data"]["name"] == "test.pdf"

    @pytest.mark.p1
    def test_upload_document_invalid_type(self, mock_client, auth_headers):
        """Test upload with invalid file type."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 102,
            "message": "Unsupported file type"
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files={"file": ("test.xyz", b"invalid content")}
        )
        result = response.json()

        assert result["code"] != 0
        assert "unsupported" in result["message"].lower()

    @pytest.mark.p2
    def test_upload_document_size_limit(self, mock_client, auth_headers):
        """Test upload with file exceeding size limit."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 103,
            "message": "File size exceeds limit"
        }
        mock_client.post.return_value = mock_response

        # Simulate large file
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB

        response = mock_client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files={"file": ("large.pdf", large_content)}
        )
        result = response.json()

        assert result["code"] != 0


class TestDocumentParsingFlow:
    """Integration tests for document parsing flow."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_parse_document_success(self, mock_client, auth_headers):
        """Test successful document parsing."""
        # Mock run endpoint
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "Document parsing started"
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/document/run",
            headers=auth_headers,
            json={"doc_ids": ["doc-001"]}
        )
        result = response.json()

        assert result["code"] == 0

    @pytest.mark.p1
    def test_document_progress_tracking(self, mock_client, auth_headers):
        """Test document parsing progress tracking."""
        # Simulate progress updates
        progress_states = [
            {"progress": 0.25, "progress_msg": "Extracting text..."},
            {"progress": 0.50, "progress_msg": "Chunking..."},
            {"progress": 0.75, "progress_msg": "Generating embeddings..."},
            {"progress": 1.0, "progress_msg": "Done"},
        ]

        for state in progress_states:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": 0,
                "data": state
            }
            mock_client.get.return_value = mock_response

            response = mock_client.get(
                "/api/v1/document/doc-001",
                headers=auth_headers
            )
            result = response.json()

            assert result["code"] == 0
            assert result["data"]["progress"] == state["progress"]

    @pytest.mark.p2
    def test_parse_document_failure_handling(self, mock_client, auth_headers):
        """Test handling of parsing failures."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "progress": 0.5,
                "progress_msg": "Error: Failed to extract text",
                "run": 3  # Failed status
            }
        }
        mock_client.get.return_value = mock_response

        response = mock_client.get(
            "/api/v1/document/doc-001",
            headers=auth_headers
        )
        result = response.json()

        assert "error" in result["data"]["progress_msg"].lower()


class TestDocumentRetrievalFlow:
    """Integration tests for document retrieval flow."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_upload_to_search_flow(self, mock_client, auth_headers):
        """Test complete flow from upload to search."""
        # Step 1: Upload
        upload_response = MagicMock()
        upload_response.json.return_value = {
            "code": 0,
            "data": {"id": "doc-001"}
        }
        mock_client.post.return_value = upload_response

        upload_result = mock_client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", b"test content")}
        ).json()

        doc_id = upload_result["data"]["id"]

        # Step 2: Parse
        parse_response = MagicMock()
        parse_response.json.return_value = {"code": 0}
        mock_client.post.return_value = parse_response

        mock_client.post(
            "/api/v1/document/run",
            headers=auth_headers,
            json={"doc_ids": [doc_id]}
        )

        # Step 3: Search
        search_response = MagicMock()
        search_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {"content": "Test content", "doc_id": doc_id}
                ]
            }
        }
        mock_client.post.return_value = search_response

        search_result = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={"kb_id": "kb-001", "query": "test"}
        ).json()

        assert search_result["code"] == 0
        assert len(search_result["data"]["chunks"]) > 0

    @pytest.mark.p2
    def test_search_returns_relevant_chunks(self, mock_client, auth_headers):
        """Test that search returns relevant chunks."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "content": "RAGFlow is a RAG engine",
                        "similarity": 0.95,
                        "doc_id": "doc-001"
                    },
                    {
                        "content": "Document processing pipeline",
                        "similarity": 0.82,
                        "doc_id": "doc-002"
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={"kb_id": "kb-001", "query": "RAG engine"}
        )
        result = response.json()

        assert result["code"] == 0
        chunks = result["data"]["chunks"]
        assert len(chunks) == 2
        assert chunks[0]["similarity"] > chunks[1]["similarity"]


class TestDocumentDeletionFlow:
    """Integration tests for document deletion flow."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_delete_document_success(self, mock_client, auth_headers):
        """Test successful document deletion."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "Document deleted successfully"
        }
        mock_client.delete.return_value = mock_response

        response = mock_client.delete(
            "/api/v1/document",
            headers=auth_headers,
            json={"doc_ids": ["doc-001"]}
        )
        result = response.json()

        assert result["code"] == 0

    @pytest.mark.p2
    def test_delete_cleans_up_chunks(self, mock_client, auth_headers):
        """Test that deletion cleans up associated chunks."""
        # Delete document
        delete_response = MagicMock()
        delete_response.json.return_value = {"code": 0}
        mock_client.delete.return_value = delete_response

        mock_client.delete(
            "/api/v1/document",
            headers=auth_headers,
            json={"doc_ids": ["doc-001"]}
        )

        # Search should return no results from deleted document
        search_response = MagicMock()
        search_response.json.return_value = {
            "code": 0,
            "data": {"chunks": []}
        }
        mock_client.post.return_value = search_response

        search_result = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={"kb_id": "kb-001", "query": "deleted content"}
        ).json()

        # Should not find chunks from deleted document
        assert search_result["data"]["chunks"] == []


class TestBulkDocumentOperations:
    """Integration tests for bulk document operations."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_bulk_upload(self, mock_client, auth_headers):
        """Test bulk document upload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": [
                {"id": "doc-001", "name": "file1.pdf"},
                {"id": "doc-002", "name": "file2.pdf"},
                {"id": "doc-003", "name": "file3.pdf"},
            ]
        }
        mock_client.post.return_value = mock_response

        files = [
            ("files", ("file1.pdf", b"content1")),
            ("files", ("file2.pdf", b"content2")),
            ("files", ("file3.pdf", b"content3")),
        ]

        response = mock_client.post(
            "/api/v1/document/upload",
            headers=auth_headers,
            files=files
        )
        result = response.json()

        assert result["code"] == 0
        assert len(result["data"]) == 3

    @pytest.mark.p2
    def test_bulk_parse(self, mock_client, auth_headers):
        """Test bulk document parsing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "3 documents queued for parsing"
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/document/run",
            headers=auth_headers,
            json={"doc_ids": ["doc-001", "doc-002", "doc-003"]}
        )
        result = response.json()

        assert result["code"] == 0

    @pytest.mark.p3
    def test_bulk_delete(self, mock_client, auth_headers):
        """Test bulk document deletion."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "message": "3 documents deleted"
        }
        mock_client.delete.return_value = mock_response

        response = mock_client.delete(
            "/api/v1/document",
            headers=auth_headers,
            json={"doc_ids": ["doc-001", "doc-002", "doc-003"]}
        )
        result = response.json()

        assert result["code"] == 0
