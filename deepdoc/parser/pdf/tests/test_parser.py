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
"""Tests for main PDFParser class."""

import os

import pytest

from deepdoc.parser.pdf import (
    LegacyPDFParser,
    PDFParser,
    ParseResult,
)


class TestPDFParser:
    """Tests for PDFParser class."""

    @pytest.fixture
    def parser(self):
        """Create a PDFParser instance."""
        return PDFParser()

    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF file."""
        return "/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"

    def test_parser_initialization(self, parser):
        """Test parser initialization."""
        assert parser.ocr_handler is not None
        assert parser.layout_analyzer is not None
        assert parser.table_extractor is not None
        assert parser.text_merger is not None
        assert parser.image_extractor is not None

    def test_parser_with_config(self):
        """Test parser initialization with config."""
        config = {"some_option": "value"}
        parser = PDFParser(config=config)
        assert parser.config == config

    def test_parser_with_model_species(self):
        """Test parser initialization with model species."""
        parser = PDFParser(model_species="paper")
        assert parser.model_species == "paper"

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_parse_sync(self, parser, test_pdf_path):
        """Test synchronous parsing."""
        result = parser.parse_sync(test_pdf_path)
        assert isinstance(result, ParseResult)
        assert len(result.pages) > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_parse_with_callback(self, parser, test_pdf_path):
        """Test parsing with progress callback."""
        progress_values = []

        def callback(progress, message=None):
            progress_values.append(progress)

        result = parser.parse_sync(test_pdf_path, callback=callback)
        assert len(progress_values) > 0
        # Progress should be increasing
        assert all(p >= 0 and p <= 1 for p in progress_values)

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_parse_from_bytes(self, parser, test_pdf_path):
        """Test parsing from binary content."""
        with open(test_pdf_path, "rb") as f:
            binary = f.read()
        result = parser.parse_sync(binary)
        assert isinstance(result, ParseResult)
        assert len(result.pages) > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_legacy_call_interface(self, parser, test_pdf_path):
        """Test legacy __call__ interface."""
        sections, tables = parser(test_pdf_path)
        assert isinstance(sections, list)
        assert isinstance(tables, list)

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_parse_page_range(self, parser, test_pdf_path):
        """Test parsing specific page range."""
        result = parser.parse_sync(test_pdf_path, page_from=0, page_to=1)
        assert len(result.pages) <= 1

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_parse_result_metadata(self, parser, test_pdf_path):
        """Test that parse result contains metadata."""
        result = parser.parse_sync(test_pdf_path)
        assert "total_pages" in result.metadata
        assert "is_english" in result.metadata


class TestLegacyPDFParser:
    """Tests for LegacyPDFParser compatibility wrapper."""

    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF file."""
        return "/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"

    def test_legacy_parser_initialization(self):
        """Test legacy parser initialization."""
        parser = LegacyPDFParser()
        assert parser.new_parser is not None

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_legacy_parser_call(self, test_pdf_path):
        """Test legacy parser __call__ interface."""
        parser = LegacyPDFParser()
        sections, tables = parser(test_pdf_path)
        assert isinstance(sections, list)
        assert isinstance(tables, list)

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_total_page_number_static(self, test_pdf_path):
        """Test static total_page_number method."""
        total = LegacyPDFParser.total_page_number(test_pdf_path)
        assert total > 0

    @pytest.mark.skipif(
        not os.path.exists("/home/user/ragflow/sdk/python/test/test_sdk_api/test_data/test.pdf"),
        reason="Test PDF file not found"
    )
    def test_total_page_number_with_binary(self, test_pdf_path):
        """Test total_page_number with binary content."""
        with open(test_pdf_path, "rb") as f:
            binary = f.read()
        total = LegacyPDFParser.total_page_number(None, binary=binary)
        assert total > 0


class TestParseResultMethods:
    """Tests for ParseResult helper methods."""

    def test_get_all_text_blocks_empty(self):
        """Test getting text blocks from empty result."""
        result = ParseResult()
        blocks = result.get_all_text_blocks()
        assert len(blocks) == 0

    def test_get_all_tables_empty(self):
        """Test getting tables from empty result."""
        result = ParseResult()
        tables = result.get_all_tables()
        assert len(tables) == 0

    def test_get_all_figures_empty(self):
        """Test getting figures from empty result."""
        result = ParseResult()
        figures = result.get_all_figures()
        assert len(figures) == 0

    def test_to_legacy_format_empty(self):
        """Test converting empty result to legacy format."""
        result = ParseResult()
        sections, tables = result.to_legacy_format()
        assert sections == []
        assert tables == []
