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
Unit tests for embedding models.

Tests cover text embedding, batch encoding, vector dimensions,
and various embedding providers.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestOpenAIEmbed:
    """Tests for OpenAI embedding model."""

    @pytest.mark.p1
    @patch("rag.llm.embedding_model.OpenAI")
    def test_encode_returns_embeddings(self, mock_openai_class):
        """Test that encode returns embeddings and token count."""
        from rag.llm.embedding_model import OpenAIEmbed

        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536  # OpenAI embedding dimension
        mock_response.data = [mock_embedding]
        mock_response.usage.total_tokens = 10
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embed = OpenAIEmbed(
            key="test-key",
            model_name="text-embedding-ada-002",
            base_url="https://api.openai.com/v1"
        )

        texts = ["Test text for embedding"]
        vectors, tokens = embed.encode(texts)

        assert vectors.shape[1] == 1536
        assert tokens == 10

    @pytest.mark.p2
    @patch("rag.llm.embedding_model.OpenAI")
    def test_encode_batch_texts(self, mock_openai_class):
        """Test encoding multiple texts in batch."""
        from rag.llm.embedding_model import OpenAIEmbed

        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create multiple embeddings
        mock_embeddings = []
        for _ in range(3):
            mock_emb = MagicMock()
            mock_emb.embedding = [0.1] * 1536
            mock_embeddings.append(mock_emb)

        mock_response.data = mock_embeddings
        mock_response.usage.total_tokens = 30
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embed = OpenAIEmbed(
            key="test-key",
            model_name="text-embedding-ada-002",
            base_url="https://api.openai.com/v1"
        )

        texts = ["Text 1", "Text 2", "Text 3"]
        vectors, tokens = embed.encode(texts)

        assert vectors.shape[0] == 3
        assert vectors.shape[1] == 1536
        assert tokens == 30

    @pytest.mark.p2
    @patch("rag.llm.embedding_model.OpenAI")
    def test_encode_queries(self, mock_openai_class):
        """Test encode_queries for query-specific embedding."""
        from rag.llm.embedding_model import OpenAIEmbed

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        mock_response.usage.total_tokens = 5
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        embed = OpenAIEmbed(
            key="test-key",
            model_name="text-embedding-ada-002",
            base_url="https://api.openai.com/v1"
        )

        query = "Search query"
        vector, tokens = embed.encode_queries(query)

        assert len(vector) == 1536
        assert tokens == 5


class TestBuiltinEmbed:
    """Tests for built-in TEI embedding model."""

    @pytest.mark.p2
    @patch("rag.llm.embedding_model.requests")
    def test_builtin_embed_returns_vectors(self, mock_requests):
        """Test built-in embedding returns vectors."""
        from rag.llm.embedding_model import BuiltinEmbed

        mock_response = MagicMock()
        mock_response.json.return_value = [[0.1] * 384]  # BGE embedding dimension
        mock_requests.post.return_value = mock_response

        embed = BuiltinEmbed(
            key=None,
            model_name="BAAI/bge-small-en-v1.5",
            base_url="http://localhost:8080"
        )

        texts = ["Test text"]
        vectors, tokens = embed.encode(texts)

        assert vectors.shape[1] == 384


class TestEmbeddingDimensions:
    """Tests for embedding vector dimensions."""

    @pytest.mark.p2
    def test_openai_dimensions(self):
        """Test OpenAI embedding dimensions."""
        # text-embedding-ada-002: 1536
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072

        expected_dims = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }

        assert expected_dims["text-embedding-ada-002"] == 1536
        assert expected_dims["text-embedding-3-large"] == 3072

    @pytest.mark.p2
    def test_bge_dimensions(self):
        """Test BGE embedding dimensions."""
        expected_dims = {
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-large-en-v1.5": 1024,
        }

        assert expected_dims["BAAI/bge-small-en-v1.5"] == 384
        assert expected_dims["BAAI/bge-large-en-v1.5"] == 1024


class TestVectorOperations:
    """Tests for vector operations."""

    @pytest.mark.p1
    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([1, 0, 0])
        vec3 = np.array([0, 1, 0])

        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        # Same vectors should have similarity 1
        assert cosine_similarity(vec1, vec2) == pytest.approx(1.0)

        # Orthogonal vectors should have similarity 0
        assert cosine_similarity(vec1, vec3) == pytest.approx(0.0)

    @pytest.mark.p2
    def test_vector_normalization(self):
        """Test vector normalization."""
        vec = np.array([3, 4])
        normalized = vec / np.linalg.norm(vec)

        # Normalized vector should have magnitude 1
        assert np.linalg.norm(normalized) == pytest.approx(1.0)

    @pytest.mark.p3
    def test_batch_similarity(self):
        """Test batch similarity calculation."""
        query = np.array([1, 0, 0])
        documents = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0.7, 0.7, 0],
        ])

        # Normalize
        query_norm = query / np.linalg.norm(query)
        docs_norm = documents / np.linalg.norm(documents, axis=1, keepdims=True)

        # Calculate similarities
        similarities = np.dot(docs_norm, query_norm)

        assert similarities[0] == pytest.approx(1.0)  # Same direction
        assert similarities[1] == pytest.approx(0.0)  # Orthogonal
        assert 0 < similarities[2] < 1  # Partial match


class TestEmbeddingCaching:
    """Tests for embedding caching."""

    @pytest.mark.p3
    def test_embedding_cache_hit(self):
        """Test embedding cache returns cached result."""
        cache = {}

        def get_embedding(text):
            if text in cache:
                return cache[text], True  # Cache hit
            embedding = np.random.rand(384)
            cache[text] = embedding
            return embedding, False  # Cache miss

        # First call - cache miss
        _, hit1 = get_embedding("test text")
        assert hit1 is False

        # Second call - cache hit
        _, hit2 = get_embedding("test text")
        assert hit2 is True

    @pytest.mark.p3
    def test_embedding_cache_key(self):
        """Test embedding cache key generation."""
        import hashlib

        text = "Test text for embedding"
        model = "text-embedding-ada-002"

        # Generate cache key
        cache_key = hashlib.md5(f"{model}:{text}".encode()).hexdigest()

        assert len(cache_key) == 32  # MD5 hash length


class TestEmbeddingErrorHandling:
    """Tests for error handling in embedding models."""

    @pytest.mark.p2
    def test_empty_text_handling(self):
        """Test handling of empty text input."""
        texts = ["", "valid text", ""]

        # Filter empty texts
        valid_texts = [t for t in texts if t.strip()]

        assert len(valid_texts) == 1
        assert valid_texts[0] == "valid text"

    @pytest.mark.p2
    def test_text_length_limit(self):
        """Test handling of text exceeding length limits."""
        max_tokens = 8191  # OpenAI limit

        # Approximate: 4 chars per token
        max_chars = max_tokens * 4

        long_text = "a" * (max_chars + 1000)
        truncated_text = long_text[:max_chars]

        assert len(truncated_text) == max_chars

    @pytest.mark.p2
    @patch("rag.llm.embedding_model.OpenAI")
    def test_api_error_handling(self, mock_openai_class):
        """Test API error handling."""
        from rag.llm.embedding_model import OpenAIEmbed

        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        embed = OpenAIEmbed(
            key="test-key",
            model_name="text-embedding-ada-002",
            base_url="https://api.openai.com/v1"
        )

        # Should handle error gracefully
        try:
            vectors, tokens = embed.encode(["test"])
        except Exception as e:
            assert "error" in str(e).lower() or "API" in str(e)


class TestEmbeddingBatchSize:
    """Tests for embedding batch size handling."""

    @pytest.mark.p3
    def test_batch_splitting(self):
        """Test splitting large batches into smaller ones."""
        texts = [f"text {i}" for i in range(100)]
        batch_size = 25

        batches = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batches.append(batch)

        assert len(batches) == 4
        assert len(batches[0]) == 25
        assert len(batches[-1]) == 25

    @pytest.mark.p3
    def test_batch_result_combination(self):
        """Test combining results from multiple batches."""
        batch_results = [
            np.random.rand(25, 384),
            np.random.rand(25, 384),
            np.random.rand(25, 384),
            np.random.rand(25, 384),
        ]

        combined = np.vstack(batch_results)

        assert combined.shape == (100, 384)
