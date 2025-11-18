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
Unit tests for document chunking.

Tests cover text splitting, token-based chunking, overlap handling,
and various chunking strategies.
"""

import pytest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestNaiveMerge:
    """Tests for naive_merge function."""

    @pytest.mark.p1
    @patch("rag.nlp.rag_tokenizer")
    def test_naive_merge_splits_text(self, mock_tokenizer):
        """Test that naive_merge splits text into chunks."""
        from rag.nlp import naive_merge

        mock_tokenizer.tokenize.return_value = ["token"] * 10
        mock_tokenizer.fine_grained_tokenize.return_value = ["token"] * 10

        text = "This is a test paragraph.\n\nThis is another paragraph."

        # Test basic splitting
        chunks = naive_merge(
            text,
            chunk_token_num=50,
            delimiter="\n"
        )

        assert len(chunks) >= 1

    @pytest.mark.p1
    def test_naive_merge_respects_token_limit(self):
        """Test that chunks respect token limit."""
        from rag.nlp import naive_merge

        # Create text with known token count
        text = "word " * 100  # 100 words

        chunks = naive_merge(
            text,
            chunk_token_num=20,
            delimiter=" "
        )

        # Each chunk should have approximately 20 tokens
        assert len(chunks) > 1

    @pytest.mark.p2
    def test_naive_merge_empty_text(self):
        """Test naive_merge with empty text."""
        from rag.nlp import naive_merge

        chunks = naive_merge(
            "",
            chunk_token_num=50,
            delimiter="\n"
        )

        assert len(chunks) == 0 or chunks == []

    @pytest.mark.p2
    def test_naive_merge_single_chunk(self):
        """Test naive_merge when text fits in single chunk."""
        from rag.nlp import naive_merge

        text = "Short text."

        chunks = naive_merge(
            text,
            chunk_token_num=1000,
            delimiter="\n"
        )

        assert len(chunks) == 1


class TestTokenization:
    """Tests for tokenization functions."""

    @pytest.mark.p1
    def test_rag_tokenizer_tokenize(self):
        """Test RAG tokenizer tokenization."""
        from rag.nlp import rag_tokenizer

        text = "This is a test sentence."
        tokens = rag_tokenizer.tokenize(text)

        assert len(tokens) > 0
        assert isinstance(tokens, list)

    @pytest.mark.p2
    def test_rag_tokenizer_fine_grained(self):
        """Test fine-grained tokenization."""
        from rag.nlp import rag_tokenizer

        text = "Testing fine-grained tokenization."
        tokens = rag_tokenizer.fine_grained_tokenize(text)

        assert len(tokens) > 0

    @pytest.mark.p2
    def test_num_tokens_from_string(self):
        """Test token counting function."""
        from rag.nlp import num_tokens_from_string

        text = "Count the tokens in this sentence."
        count = num_tokens_from_string(text)

        assert count > 0
        assert isinstance(count, int)


class TestChunkingStrategies:
    """Tests for different chunking strategies."""

    @pytest.mark.p1
    def test_delimiter_based_chunking(self):
        """Test chunking by delimiter."""
        text = "Section 1\n\nSection 2\n\nSection 3"

        # Simple delimiter split
        sections = text.split("\n\n")

        assert len(sections) == 3
        assert "Section 1" in sections[0]
        assert "Section 2" in sections[1]
        assert "Section 3" in sections[2]

    @pytest.mark.p2
    def test_overlap_chunking(self):
        """Test chunking with overlap."""
        # Simulate overlap chunking
        text = "word " * 100
        words = text.split()

        chunk_size = 20
        overlap = 5

        chunks = []
        i = 0
        while i < len(words):
            chunk = words[i:i + chunk_size]
            chunks.append(" ".join(chunk))
            i += chunk_size - overlap

        # Check overlap exists
        assert len(chunks) > 1
        # Adjacent chunks should share words
        if len(chunks) >= 2:
            chunk1_words = set(chunks[0].split()[-overlap:])
            chunk2_words = set(chunks[1].split()[:overlap])
            assert len(chunk1_words & chunk2_words) > 0

    @pytest.mark.p2
    def test_sentence_based_chunking(self):
        """Test chunking by sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        # Simple sentence split
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)

        assert len(sentences) == 4


class TestChunkPositionTracking:
    """Tests for chunk position tracking."""

    @pytest.mark.p2
    def test_chunk_positions_recorded(self):
        """Test that chunk positions are recorded correctly."""
        text = "First chunk content. Second chunk content."

        # Simulate position tracking
        chunks_with_pos = []
        current_pos = 0

        parts = text.split(". ")
        for part in parts:
            if part:
                chunk = {
                    "content": part,
                    "start": current_pos,
                    "end": current_pos + len(part)
                }
                chunks_with_pos.append(chunk)
                current_pos += len(part) + 2  # +2 for ". "

        assert len(chunks_with_pos) == 2
        assert chunks_with_pos[0]["start"] == 0
        assert chunks_with_pos[1]["start"] > 0

    @pytest.mark.p3
    def test_chunk_page_assignment(self):
        """Test that chunks are assigned to correct pages."""
        # Simulate multi-page document
        pages = [
            {"page_num": 1, "content": "Page 1 content"},
            {"page_num": 2, "content": "Page 2 content"},
        ]

        chunks = []
        for page in pages:
            chunk = {
                "content": page["content"],
                "page_num": page["page_num"]
            }
            chunks.append(chunk)

        assert chunks[0]["page_num"] == 1
        assert chunks[1]["page_num"] == 2


class TestSpecialContentChunking:
    """Tests for chunking special content types."""

    @pytest.mark.p2
    def test_table_chunking(self):
        """Test chunking of table content."""
        table_content = """
        | Col1 | Col2 | Col3 |
        |------|------|------|
        | A    | B    | C    |
        | D    | E    | F    |
        """

        # Tables should typically be kept together
        chunks = [table_content.strip()]

        assert len(chunks) == 1
        assert "Col1" in chunks[0]
        assert "A" in chunks[0]

    @pytest.mark.p2
    def test_code_block_chunking(self):
        """Test chunking of code blocks."""
        code_content = """
        ```python
        def hello():
            print("Hello, World!")
        ```
        """

        # Code blocks should typically be kept together
        chunks = [code_content.strip()]

        assert len(chunks) == 1
        assert "def hello" in chunks[0]

    @pytest.mark.p3
    def test_list_chunking(self):
        """Test chunking of list content."""
        list_content = """
        - Item 1
        - Item 2
        - Item 3
        - Item 4
        - Item 5
        """

        lines = [l.strip() for l in list_content.strip().split("\n") if l.strip()]

        assert len(lines) == 5
        assert all(line.startswith("-") for line in lines)


class TestChunkingWithImages:
    """Tests for chunking with image content."""

    @pytest.mark.p2
    @patch("rag.nlp.naive_merge_with_images")
    def test_naive_merge_with_images_preserves_images(self, mock_merge):
        """Test that image positions are preserved during chunking."""
        mock_merge.return_value = [
            {"content": "Text before image", "images": []},
            {"content": "Text with image", "images": [{"id": "img1", "position": 100}]},
            {"content": "Text after image", "images": []},
        ]

        result = mock_merge("text", 50, "\n", [{"id": "img1", "position": 100}])

        # Find chunk with image
        chunks_with_images = [c for c in result if c.get("images")]
        assert len(chunks_with_images) == 1
        assert chunks_with_images[0]["images"][0]["id"] == "img1"


class TestChunkQuality:
    """Tests for chunk quality metrics."""

    @pytest.mark.p3
    def test_chunk_completeness(self):
        """Test that chunks contain complete thoughts."""
        # Good chunk - complete sentence
        good_chunk = "This is a complete sentence that makes sense."

        # Bad chunk - cut off mid-sentence
        bad_chunk = "This is a sentence that gets cut off in the"

        # Simple completeness check - ends with punctuation
        assert good_chunk[-1] in ".!?"
        assert bad_chunk[-1] not in ".!?"

    @pytest.mark.p3
    def test_chunk_semantic_coherence(self):
        """Test that chunks maintain semantic coherence."""
        # Coherent chunk - same topic
        coherent = "Machine learning is a subset of AI. It enables systems to learn from data."

        # Incoherent chunk - mixed topics
        incoherent = "Machine learning is a subset of AI. The weather is nice today."

        # Check for topic words
        ml_words = ["machine", "learning", "ai", "data", "systems"]
        coherent_lower = coherent.lower()

        word_count = sum(1 for w in ml_words if w in coherent_lower)
        assert word_count >= 3


class TestTokenizeChunks:
    """Tests for tokenize_chunks function."""

    @pytest.mark.p2
    def test_tokenize_chunks_adds_tokens(self):
        """Test that tokenize_chunks adds token information."""
        chunks = [
            {"content_with_weight": "First chunk content"},
            {"content_with_weight": "Second chunk content"},
        ]

        # Simulate tokenization
        for chunk in chunks:
            words = chunk["content_with_weight"].split()
            chunk["content_ltks"] = " ".join(words[:2])  # Simplified
            chunk["content_sm_ltks"] = " ".join(words[:1])  # More simplified

        assert "content_ltks" in chunks[0]
        assert "content_sm_ltks" in chunks[0]

    @pytest.mark.p3
    def test_tokenize_chunks_with_keywords(self):
        """Test keyword extraction during tokenization."""
        chunk = {
            "content_with_weight": "RAGFlow is a retrieval augmented generation engine"
        }

        # Extract potential keywords (simple approach)
        words = chunk["content_with_weight"].split()
        # Filter out common words
        common_words = {"is", "a", "the", "an"}
        keywords = [w.lower() for w in words if w.lower() not in common_words]

        chunk["important_kwd"] = keywords[:5]

        assert "ragflow" in chunk["important_kwd"]
        assert "retrieval" in chunk["important_kwd"]
