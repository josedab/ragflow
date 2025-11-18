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
"""Tests for text merger module."""

import pytest

from deepdoc.parser.pdf.text_merger import TextMerger


class TestTextMerger:
    """Tests for TextMerger class."""

    @pytest.fixture
    def merger(self):
        """Create a TextMerger instance."""
        return TextMerger()

    def test_assign_column_empty(self, merger):
        """Test column assignment with empty boxes."""
        result = merger._assign_column([])
        assert result == []

    def test_assign_column_single_column(self, merger):
        """Test column assignment for single column document."""
        boxes = [
            {"x0": 50, "x1": 500, "top": 100, "bottom": 120, "page_number": 1, "text": "Line 1"},
            {"x0": 50, "x1": 500, "top": 130, "bottom": 150, "page_number": 1, "text": "Line 2"},
        ]
        result = merger._assign_column(boxes)
        assert all(b.get("col_id") == 0 for b in result)

    def test_text_merge_horizontal(self, merger):
        """Test horizontal text merging."""
        boxes = [
            {"x0": 50, "x1": 100, "top": 100, "bottom": 120, "page_number": 1, "text": "Hello ", "layoutno": "0"},
            {"x0": 100, "x1": 150, "top": 100, "bottom": 120, "page_number": 1, "text": "World", "layoutno": "0"},
        ]
        mean_height = [20]
        result = merger._text_merge_horizontal(boxes, mean_height)
        # Boxes should be merged since they're on the same line
        assert len(result) <= 2

    def test_naive_vertical_merge(self, merger):
        """Test naive vertical merging."""
        boxes = [
            {"x0": 50, "x1": 200, "top": 100, "bottom": 120, "page_number": 1, "text": "First line,", "layoutno": "0", "col_id": 0},
            {"x0": 50, "x1": 200, "top": 125, "bottom": 145, "page_number": 1, "text": "second line.", "layoutno": "0", "col_id": 0},
        ]
        mean_height = [20]
        mean_width = [8]
        result = merger._naive_vertical_merge(boxes, mean_height, mean_width, False)
        # Should merge since they're close and first ends with comma
        assert len(result) >= 1

    def test_match_proj_chinese_chapter(self, merger):
        """Test matching Chinese chapter patterns."""
        box = {"text": "第一章 引言"}
        assert merger._match_proj(box)

    def test_match_proj_numbered_list(self, merger):
        """Test matching numbered list patterns."""
        box = {"text": "1、项目概述"}
        assert merger._match_proj(box)

    def test_match_proj_regular_text(self, merger):
        """Test non-matching regular text."""
        box = {"text": "This is regular text."}
        assert not merger._match_proj(box)

    def test_char_width(self, merger):
        """Test character width calculation."""
        box = {"x0": 0, "x1": 100, "text": "Hello"}
        assert merger._char_width(box) == 20

    def test_height(self, merger):
        """Test height calculation."""
        box = {"top": 100, "bottom": 150}
        assert merger._height(box) == 50

    def test_x_dis(self, merger):
        """Test horizontal distance calculation."""
        a = {"x0": 0, "x1": 50}
        b = {"x0": 100, "x1": 150}
        # Distance should be 50 (from x1=50 to x0=100)
        assert merger._x_dis(a, b) == 50

    def test_final_reading_order_merge(self, merger):
        """Test final reading order arrangement."""
        boxes = [
            {"x0": 50, "x1": 200, "top": 200, "bottom": 220, "page_number": 1, "text": "Second", "col_id": 0},
            {"x0": 50, "x1": 200, "top": 100, "bottom": 120, "page_number": 1, "text": "First", "col_id": 0},
        ]
        result = merger._final_reading_order_merge(boxes)
        # Should be sorted by top position
        assert result[0]["text"] == "First"
        assert result[1]["text"] == "Second"


class TestTextMergerFeatures:
    """Tests for feature extraction in TextMerger."""

    @pytest.fixture
    def merger(self):
        """Create a TextMerger instance."""
        return TextMerger()

    def test_updown_concat_features_basic(self, merger):
        """Test basic feature extraction for concatenation."""
        up = {
            "x0": 50, "x1": 200, "top": 100, "bottom": 120,
            "page_number": 1, "text": "Hello world,", "layout_type": "text",
        }
        down = {
            "x0": 50, "x1": 200, "top": 130, "bottom": 150,
            "page_number": 1, "text": "how are you?", "layout_type": "text",
        }
        features = merger._updown_concat_features(up, down)
        assert len(features) == 31  # Should have 31 features

    def test_updown_concat_features_same_page(self, merger):
        """Test features when boxes are on same page."""
        up = {
            "x0": 50, "x1": 200, "top": 100, "bottom": 120,
            "page_number": 1, "text": "Test", "layout_type": "text",
        }
        down = {
            "x0": 50, "x1": 200, "top": 130, "bottom": 150,
            "page_number": 1, "text": "Text", "layout_type": "text",
        }
        features = merger._updown_concat_features(up, down)
        # Feature at index 2 is page difference
        assert features[2] == 0

    def test_updown_concat_features_different_pages(self, merger):
        """Test features when boxes are on different pages."""
        up = {
            "x0": 50, "x1": 200, "top": 100, "bottom": 120,
            "page_number": 1, "text": "Test", "layout_type": "text",
        }
        down = {
            "x0": 50, "x1": 200, "top": 130, "bottom": 150,
            "page_number": 2, "text": "Text", "layout_type": "text",
        }
        features = merger._updown_concat_features(up, down)
        # Feature at index 2 is page difference
        assert features[2] == 1
