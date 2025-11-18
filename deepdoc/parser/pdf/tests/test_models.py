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
"""Tests for data models."""

import pytest

from deepdoc.parser.pdf.models import (
    BoundingBox,
    Figure,
    LayoutElement,
    PageResult,
    ParseResult,
    Table,
    TextBlock,
)


class TestBoundingBox:
    """Tests for BoundingBox class."""

    def test_create_bounding_box(self):
        """Test basic bounding box creation."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 50

    def test_width_height(self):
        """Test width and height calculations."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        assert bbox.width == 90
        assert bbox.height == 30

    def test_area(self):
        """Test area calculation."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        assert bbox.area == 90 * 30

    def test_contains(self):
        """Test contains method."""
        outer = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        inner = BoundingBox(x0=10, y0=10, x1=50, y1=50)
        outside = BoundingBox(x0=150, y0=150, x1=200, y1=200)

        assert outer.contains(inner)
        assert not inner.contains(outer)
        assert not outer.contains(outside)

    def test_overlaps(self):
        """Test overlaps method."""
        box1 = BoundingBox(x0=0, y0=0, x1=50, y1=50)
        box2 = BoundingBox(x0=25, y0=25, x1=75, y1=75)
        box3 = BoundingBox(x0=100, y0=100, x1=150, y1=150)

        assert box1.overlaps(box2)
        assert box2.overlaps(box1)
        assert not box1.overlaps(box3)

    def test_intersection_area(self):
        """Test intersection area calculation."""
        box1 = BoundingBox(x0=0, y0=0, x1=50, y1=50)
        box2 = BoundingBox(x0=25, y0=25, x1=75, y1=75)
        box3 = BoundingBox(x0=100, y0=100, x1=150, y1=150)

        assert box1.intersection_area(box2) == 25 * 25
        assert box1.intersection_area(box3) == 0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        d = bbox.to_dict()
        assert d == {"x0": 10, "top": 20, "x1": 100, "bottom": 50}

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {"x0": 10, "top": 20, "x1": 100, "bottom": 50}
        bbox = BoundingBox.from_dict(d)
        assert bbox.x0 == 10
        assert bbox.y0 == 20
        assert bbox.x1 == 100
        assert bbox.y1 == 50


class TestTextBlock:
    """Tests for TextBlock class."""

    def test_create_text_block(self):
        """Test basic text block creation."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        block = TextBlock(
            text="Hello World",
            bbox=bbox,
            font="Arial",
            size=12.0,
            page_num=1,
        )
        assert block.text == "Hello World"
        assert block.font == "Arial"
        assert block.size == 12.0
        assert block.page_num == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        block = TextBlock(
            text="Test",
            bbox=bbox,
            page_num=1,
            layout_type="text",
        )
        d = block.to_dict()
        assert d["text"] == "Test"
        assert d["page_number"] == 1
        assert d["layout_type"] == "text"

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "text": "Test",
            "x0": 10,
            "top": 20,
            "x1": 100,
            "bottom": 50,
            "page_number": 1,
            "layout_type": "title",
        }
        block = TextBlock.from_dict(d)
        assert block.text == "Test"
        assert block.bbox.x0 == 10
        assert block.page_num == 1
        assert block.layout_type == "title"


class TestLayoutElement:
    """Tests for LayoutElement class."""

    def test_create_layout_element(self):
        """Test basic layout element creation."""
        bbox = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        element = LayoutElement(
            type="table",
            bbox=bbox,
            confidence=0.95,
            page_num=1,
        )
        assert element.type == "table"
        assert element.confidence == 0.95
        assert element.page_num == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        bbox = BoundingBox(x0=0, y0=0, x1=100, y1=100)
        element = LayoutElement(
            type="figure",
            bbox=bbox,
            confidence=0.85,
            page_num=2,
        )
        d = element.to_dict()
        assert d["type"] == "figure"
        assert d["score"] == 0.85
        assert d["page_number"] == 2


class TestTable:
    """Tests for Table class."""

    def test_create_table(self):
        """Test basic table creation."""
        bbox = BoundingBox(x0=0, y0=0, x1=200, y1=100)
        table = Table(
            bbox=bbox,
            html="<table><tr><td>Cell</td></tr></table>",
            page_num=1,
        )
        assert table.html
        assert table.page_num == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        bbox = BoundingBox(x0=0, y0=0, x1=200, y1=100)
        table = Table(
            bbox=bbox,
            html="<table></table>",
            page_num=1,
            caption="Table 1",
        )
        d = table.to_dict()
        assert d["html"] == "<table></table>"
        assert d["caption"] == "Table 1"


class TestPageResult:
    """Tests for PageResult class."""

    def test_create_page_result(self):
        """Test basic page result creation."""
        result = PageResult(
            page_num=1,
            width=612.0,
            height=792.0,
        )
        assert result.page_num == 1
        assert len(result.text_blocks) == 0
        assert len(result.tables) == 0

    def test_to_legacy_format(self):
        """Test conversion to legacy format."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        block = TextBlock(text="Test", bbox=bbox, page_num=1)
        result = PageResult(
            page_num=1,
            text_blocks=[block],
        )
        legacy = result.to_legacy_format()
        assert len(legacy) == 1
        assert legacy[0]["text"] == "Test"


class TestParseResult:
    """Tests for ParseResult class."""

    def test_create_parse_result(self):
        """Test basic parse result creation."""
        result = ParseResult()
        assert len(result.pages) == 0

    def test_get_all_text_blocks(self):
        """Test getting all text blocks."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        block1 = TextBlock(text="Page 1", bbox=bbox, page_num=1)
        block2 = TextBlock(text="Page 2", bbox=bbox, page_num=2)

        page1 = PageResult(page_num=1, text_blocks=[block1])
        page2 = PageResult(page_num=2, text_blocks=[block2])

        result = ParseResult(pages=[page1, page2])
        all_blocks = result.get_all_text_blocks()

        assert len(all_blocks) == 2
        assert all_blocks[0].text == "Page 1"
        assert all_blocks[1].text == "Page 2"

    def test_to_legacy_format(self):
        """Test conversion to legacy format."""
        bbox = BoundingBox(x0=10, y0=20, x1=100, y1=50)
        block = TextBlock(text="Test", bbox=bbox, page_num=1)
        page = PageResult(page_num=1, text_blocks=[block])
        result = ParseResult(pages=[page])

        sections, tables = result.to_legacy_format()
        assert len(sections) == 1
        assert sections[0][0] == "Test"
        assert "@@1" in sections[0][1]
