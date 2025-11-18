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
"""Data models for the modular PDF parser.

This module defines the core data structures used across all PDF parsing modules.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class BoundingBox:
    """Represents a bounding box with coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """Calculate the width of the bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Calculate the height of the bounding box."""
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        """Calculate the area of the bounding box."""
        return self.width * self.height

    def contains(self, other: "BoundingBox") -> bool:
        """Check if this bounding box contains another."""
        return (
            self.x0 <= other.x0
            and self.y0 <= other.y0
            and self.x1 >= other.x1
            and self.y1 >= other.y1
        )

    def overlaps(self, other: "BoundingBox") -> bool:
        """Check if this bounding box overlaps with another."""
        return not (
            self.x1 < other.x0
            or self.x0 > other.x1
            or self.y1 < other.y0
            or self.y0 > other.y1
        )

    def intersection_area(self, other: "BoundingBox") -> float:
        """Calculate the intersection area with another bounding box."""
        if not self.overlaps(other):
            return 0.0
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        return (x1 - x0) * (y1 - y0)

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with legacy code."""
        return {
            "x0": self.x0,
            "top": self.y0,
            "x1": self.x1,
            "bottom": self.y1,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BoundingBox":
        """Create from dictionary with x0, top, x1, bottom keys."""
        return cls(
            x0=d.get("x0", 0),
            y0=d.get("top", 0),
            x1=d.get("x1", 0),
            y1=d.get("bottom", 0),
        )


@dataclass
class TextBlock:
    """Represents a text block with position and styling information."""
    text: str
    bbox: BoundingBox
    font: str = ""
    size: float = 0.0
    page_num: int = 0
    layout_type: str = "text"
    layoutno: str = ""
    col_id: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with legacy code."""
        result = self.bbox.to_dict()
        result.update({
            "text": self.text,
            "page_number": self.page_num,
            "layout_type": self.layout_type,
            "layoutno": self.layoutno,
            "col_id": self.col_id,
        })
        if self.font:
            result["fontname"] = self.font
        if self.size:
            result["size"] = self.size
        return result

    @classmethod
    def from_dict(cls, d: dict) -> "TextBlock":
        """Create from dictionary format."""
        return cls(
            text=d.get("text", ""),
            bbox=BoundingBox.from_dict(d),
            font=d.get("fontname", ""),
            size=d.get("size", 0.0),
            page_num=d.get("page_number", 0),
            layout_type=d.get("layout_type", "text"),
            layoutno=d.get("layoutno", ""),
            col_id=d.get("col_id", 0),
        )


@dataclass
class LayoutElement:
    """Represents a detected layout element on a page."""
    type: str  # text, title, table, figure, etc.
    bbox: BoundingBox
    confidence: float
    content: Any = None
    page_num: int = 0
    layoutno: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with legacy code."""
        result = self.bbox.to_dict()
        result.update({
            "type": self.type,
            "score": self.confidence,
            "page_number": self.page_num,
            "layoutno": self.layoutno,
        })
        return result

    @classmethod
    def from_dict(cls, d: dict) -> "LayoutElement":
        """Create from dictionary format."""
        return cls(
            type=d.get("type", ""),
            bbox=BoundingBox.from_dict(d),
            confidence=d.get("score", 0.0),
            page_num=d.get("page_number", 0),
            layoutno=d.get("layoutno", ""),
        )


@dataclass
class TableCell:
    """Represents a cell in a table."""
    row: int
    col: int
    text: str
    bbox: BoundingBox
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False


@dataclass
class Table:
    """Represents an extracted table."""
    bbox: BoundingBox
    cells: List[TableCell] = field(default_factory=list)
    html: str = ""
    page_num: int = 0
    caption: str = ""
    image: Optional[bytes] = None

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "bbox": self.bbox.to_dict(),
            "html": self.html,
            "page_number": self.page_num,
            "caption": self.caption,
        }


@dataclass
class Figure:
    """Represents an extracted figure/image."""
    bbox: BoundingBox
    image: bytes
    page_num: int = 0
    caption: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "bbox": self.bbox.to_dict(),
            "page_number": self.page_num,
            "caption": self.caption,
        }


@dataclass
class PageResult:
    """Results from processing a single page."""
    page_num: int
    text_blocks: List[TextBlock] = field(default_factory=list)
    layout_elements: List[LayoutElement] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0

    def to_legacy_format(self) -> List[dict]:
        """Convert to legacy tuple format for backwards compatibility."""
        result = []
        for block in self.text_blocks:
            result.append(block.to_dict())
        return result


@dataclass
class ParseResult:
    """Complete result from parsing a PDF document."""
    pages: List[PageResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def get_all_text_blocks(self) -> List[TextBlock]:
        """Get all text blocks from all pages."""
        blocks = []
        for page in self.pages:
            blocks.extend(page.text_blocks)
        return blocks

    def get_all_tables(self) -> List[Table]:
        """Get all tables from all pages."""
        tables = []
        for page in self.pages:
            tables.extend(page.tables)
        return tables

    def get_all_figures(self) -> List[Figure]:
        """Get all figures from all pages."""
        figures = []
        for page in self.pages:
            figures.extend(page.figures)
        return figures

    def to_legacy_format(self) -> tuple:
        """Convert to legacy format for backwards compatibility.

        Returns:
            Tuple of (sections, tables) where sections is a list of tuples
            and tables is a list of table data.
        """
        sections = []
        tables = []

        for page in self.pages:
            # Convert text blocks to sections
            for block in page.text_blocks:
                position_tag = f"@@{page.page_num}\t{block.bbox.x0}\t{block.bbox.x1}\t{block.bbox.y0}\t{block.bbox.y1}##"
                sections.append((block.text, position_tag))

            # Convert tables
            for table in page.tables:
                tables.append((table.image, table.html))

        return sections, tables
