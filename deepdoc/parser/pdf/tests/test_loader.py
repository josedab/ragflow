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
"""Tests for PDF loader module."""

import os

import pytest

from deepdoc.parser.pdf.loader import PDFLoader


class TestPDFLoader:
    """Tests for PDFLoader class."""

    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF file."""
        # Use existing test file in the repository
        return "/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_load_pdf_from_path(self, test_pdf_path):
        """Test loading PDF from file path."""
        loader = PDFLoader(test_pdf_path)
        assert loader.page_count > 0
        assert loader.total_pages > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_load_pdf_from_bytes(self, test_pdf_path):
        """Test loading PDF from bytes."""
        with open(test_pdf_path, "rb") as f:
            binary = f.read()
        loader = PDFLoader(binary)
        assert loader.page_count > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_page_iteration(self, test_pdf_path):
        """Test iterating over pages."""
        loader = PDFLoader(test_pdf_path)
        page_count = 0
        for i, img, chars in loader:
            page_count += 1
            assert img is not None
        assert page_count == loader.page_count

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_get_page(self, test_pdf_path):
        """Test getting specific page."""
        loader = PDFLoader(test_pdf_path)
        if loader.page_count > 0:
            img, chars = loader.get_page(0)
            assert img is not None

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_get_page_heights(self, test_pdf_path):
        """Test getting page heights."""
        loader = PDFLoader(test_pdf_path)
        heights = loader.get_page_heights()
        assert len(heights) == loader.page_count
        assert all(h > 0 for h in heights)

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_get_cumulative_heights(self, test_pdf_path):
        """Test getting cumulative heights."""
        loader = PDFLoader(test_pdf_path)
        cum_heights = loader.get_cumulative_heights()
        assert len(cum_heights) == loader.page_count + 1
        assert cum_heights[0] == 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_context_manager(self, test_pdf_path):
        """Test using loader as context manager."""
        with PDFLoader(test_pdf_path) as loader:
            assert loader.page_count > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_page_range(self, test_pdf_path):
        """Test loading specific page range."""
        loader = PDFLoader(test_pdf_path, page_from=0, page_to=1)
        assert loader.page_count <= 1

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_get_total_pages_static(self, test_pdf_path):
        """Test static method to get total pages."""
        total = PDFLoader.get_total_pages(test_pdf_path)
        assert total > 0


class TestPDFLoaderEdgeCases:
    """Test edge cases for PDFLoader."""

    def test_get_page_invalid_index(self):
        """Test getting page with invalid index."""
        # This test would need a real PDF file
        pass

    def test_empty_pdf(self):
        """Test handling of empty/invalid PDF."""
        # This test would need specific test files
        pass
