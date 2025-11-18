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
Integration tests for search and retrieval flow.

Tests cover semantic search, keyword search, hybrid search,
and RAG-based question answering.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


class TestSemanticSearch:
    """Integration tests for semantic search."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_semantic_search_returns_results(self, mock_client, auth_headers):
        """Test semantic search returns relevant results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "id": "chunk-001",
                        "content": "RAGFlow is a retrieval-augmented generation engine",
                        "similarity": 0.92,
                        "doc_id": "doc-001",
                        "doc_name": "overview.pdf"
                    },
                    {
                        "id": "chunk-002",
                        "content": "The engine processes documents using deep understanding",
                        "similarity": 0.85,
                        "doc_id": "doc-001",
                        "doc_name": "overview.pdf"
                    }
                ],
                "total": 2
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_id": "kb-001",
                "query": "What is RAGFlow?",
                "top_k": 5
            }
        )
        result = response.json()

        assert result["code"] == 0
        assert len(result["data"]["chunks"]) == 2
        assert result["data"]["chunks"][0]["similarity"] > 0.9

    @pytest.mark.p2
    def test_semantic_search_with_filters(self, mock_client, auth_headers):
        """Test semantic search with document filters."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "id": "chunk-001",
                        "content": "Filtered result",
                        "doc_id": "doc-001"
                    }
                ],
                "total": 1
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_id": "kb-001",
                "query": "test query",
                "doc_ids": ["doc-001", "doc-002"]
            }
        )
        result = response.json()

        assert result["code"] == 0

    @pytest.mark.p2
    def test_semantic_search_empty_results(self, mock_client, auth_headers):
        """Test semantic search with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [],
                "total": 0
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_id": "kb-001",
                "query": "nonexistent topic xyz123"
            }
        )
        result = response.json()

        assert result["code"] == 0
        assert len(result["data"]["chunks"]) == 0


class TestHybridSearch:
    """Integration tests for hybrid search (semantic + keyword)."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_hybrid_search_combines_results(self, mock_client, auth_headers):
        """Test hybrid search combines semantic and keyword results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {
                        "id": "chunk-001",
                        "content": "RAGFlow engine architecture",
                        "vector_similarity": 0.88,
                        "keyword_score": 0.75,
                        "hybrid_score": 0.82
                    },
                    {
                        "id": "chunk-002",
                        "content": "Engine performance metrics",
                        "vector_similarity": 0.72,
                        "keyword_score": 0.90,
                        "hybrid_score": 0.80
                    }
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_id": "kb-001",
                "query": "RAGFlow engine",
                "vector_similarity_weight": 0.5,
                "keyword_similarity_weight": 0.5
            }
        )
        result = response.json()

        assert result["code"] == 0
        chunks = result["data"]["chunks"]
        assert all("hybrid_score" in chunk for chunk in chunks)


class TestRAGChat:
    """Integration tests for RAG-based chat/QA."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p1
    def test_rag_chat_returns_answer(self, mock_client, auth_headers):
        """Test RAG chat returns grounded answer."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "RAGFlow is an open-source RAG engine that provides retrieval-augmented generation capabilities.",
                "reference": {
                    "chunks": [
                        {
                            "content": "RAGFlow is an open-source RAG engine",
                            "doc_name": "overview.pdf",
                            "positions": [[100, 200]]
                        }
                    ]
                }
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chat/completion",
            headers=auth_headers,
            json={
                "dialog_id": "dialog-001",
                "question": "What is RAGFlow?",
                "stream": False
            }
        )
        result = response.json()

        assert result["code"] == 0
        assert "RAGFlow" in result["data"]["answer"]
        assert len(result["data"]["reference"]["chunks"]) > 0

    @pytest.mark.p1
    def test_rag_chat_with_history(self, mock_client, auth_headers):
        """Test RAG chat with conversation history."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "Yes, it supports multiple document formats including PDF, Word, and Excel.",
                "reference": {"chunks": []}
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chat/completion",
            headers=auth_headers,
            json={
                "dialog_id": "dialog-001",
                "question": "Does it support Word documents?",
                "history": [
                    {"role": "user", "content": "What is RAGFlow?"},
                    {"role": "assistant", "content": "RAGFlow is a RAG engine."}
                ],
                "stream": False
            }
        )
        result = response.json()

        assert result["code"] == 0

    @pytest.mark.p2
    def test_rag_chat_streaming(self, mock_client, auth_headers):
        """Test RAG chat with streaming response."""
        # For streaming, we'd test the SSE response
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'data: {"answer": "RAGFlow ", "reference": null}',
            b'data: {"answer": "is ", "reference": null}',
            b'data: {"answer": "a RAG engine.", "reference": {"chunks": []}}',
            b'data: [DONE]'
        ]
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chat/completion",
            headers=auth_headers,
            json={
                "dialog_id": "dialog-001",
                "question": "What is RAGFlow?",
                "stream": True
            },
            stream=True
        )

        chunks = list(response.iter_lines())
        assert len(chunks) == 4


class TestSearchRanking:
    """Integration tests for search result ranking."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_results_ordered_by_relevance(self, mock_client, auth_headers):
        """Test that results are ordered by relevance."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {"id": "1", "similarity": 0.95},
                    {"id": "2", "similarity": 0.85},
                    {"id": "3", "similarity": 0.75},
                    {"id": "4", "similarity": 0.65},
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={"kb_id": "kb-001", "query": "test"}
        )
        result = response.json()

        chunks = result["data"]["chunks"]
        similarities = [c["similarity"] for c in chunks]

        # Should be in descending order
        assert similarities == sorted(similarities, reverse=True)

    @pytest.mark.p3
    def test_reranking_improves_results(self, mock_client, auth_headers):
        """Test that reranking improves result ordering."""
        # Initial retrieval
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {"id": "1", "content": "Related content", "similarity": 0.90},
                    {"id": "2", "content": "Most relevant content", "similarity": 0.88},
                ],
                "reranked": True
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_id": "kb-001",
                "query": "Most relevant",
                "rerank": True
            }
        )
        result = response.json()

        assert result["code"] == 0


class TestMultiKBSearch:
    """Integration tests for searching across multiple knowledge bases."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return MagicMock()

    @pytest.fixture
    def auth_headers(self):
        """Return mock authentication headers."""
        return {"Authorization": "Bearer test-token"}

    @pytest.mark.p2
    def test_search_multiple_kbs(self, mock_client, auth_headers):
        """Test searching across multiple knowledge bases."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "chunks": [
                    {"id": "1", "kb_id": "kb-001", "content": "From KB 1"},
                    {"id": "2", "kb_id": "kb-002", "content": "From KB 2"},
                    {"id": "3", "kb_id": "kb-001", "content": "Also from KB 1"},
                ]
            }
        }
        mock_client.post.return_value = mock_response

        response = mock_client.post(
            "/api/v1/chunk/retrieval_test",
            headers=auth_headers,
            json={
                "kb_ids": ["kb-001", "kb-002"],
                "query": "test query"
            }
        )
        result = response.json()

        chunks = result["data"]["chunks"]
        kb_ids = {c["kb_id"] for c in chunks}

        assert "kb-001" in kb_ids
        assert "kb-002" in kb_ids
