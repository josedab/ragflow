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
"""Modular PDF parser with parallel processing support.

This module provides a modular, testable PDF parser that can process
pages in parallel for improved performance.
"""

import logging
from timeit import default_timer as timer
from typing import Callable, List, Optional, Tuple, Union

import numpy as np
import trio

from common import settings
from deepdoc.parser.pdf.image_extractor import ImageExtractor
from deepdoc.parser.pdf.layout_analyzer import LayoutAnalyzer
from deepdoc.parser.pdf.loader import PDFLoader
from deepdoc.parser.pdf.models import (
    BoundingBox,
    Figure,
    LayoutElement,
    PageResult,
    ParseResult,
    Table,
    TextBlock,
)
from deepdoc.parser.pdf.ocr_handler import OCRHandler
from deepdoc.parser.pdf.table_extractor import TableExtractor
from deepdoc.parser.pdf.text_merger import TextMerger

# Re-export models for convenience
__all__ = [
    "PDFParser",
    "BoundingBox",
    "TextBlock",
    "LayoutElement",
    "Table",
    "Figure",
    "PageResult",
    "ParseResult",
]


class PDFParser:
    """Main PDF parser with parallel processing support.

    This class coordinates all the modular components to parse PDFs
    and extract structured content.
    """

    def __init__(self, config: Optional[dict] = None, model_species: Optional[str] = None):
        """Initialize the PDF parser.

        Args:
            config: Optional configuration dictionary.
            model_species: Optional model species for domain-specific recognition.
        """
        self.config = config or {}
        self.model_species = model_species

        # Initialize components
        self.ocr_handler = OCRHandler()
        self.layout_analyzer = LayoutAnalyzer(model_species)
        self.table_extractor = TableExtractor()
        self.text_merger = TextMerger()
        self.image_extractor = ImageExtractor()

        # State
        self.page_from = 0
        self.boxes = []
        self.page_images = []
        self.page_layout = []
        self.page_cum_height = np.array([0])
        self.mean_height = []
        self.mean_width = []
        self.is_english = False

    async def parse(
        self,
        source: Union[str, bytes],
        page_from: int = 0,
        page_to: int = 299,
        zoomin: int = 3,
        callback: Optional[Callable] = None,
    ) -> ParseResult:
        """Parse PDF with parallel page processing.

        Args:
            source: File path or binary PDF content.
            page_from: Starting page index.
            page_to: Ending page index.
            zoomin: Zoom factor for resolution.
            callback: Progress callback function.

        Returns:
            ParseResult with structured content.
        """
        start = timer()

        # Load PDF
        loader = PDFLoader(source, page_from, page_to, zoomin)
        self.page_from = page_from
        self.page_images = loader.page_images
        self.is_english = loader.is_english
        self.mean_height = loader.get_mean_char_heights()
        self.mean_width = loader.get_mean_char_widths()
        self.page_cum_height = loader.get_cumulative_heights()

        if callback:
            callback(0.1, f"PDF loaded ({timer() - start:.2f}s)")

        # Process pages with OCR
        start = timer()
        all_boxes = []

        async with trio.open_nursery() as nursery:
            results = [None] * loader.page_count

            if self.ocr_handler.parallel_limiter:
                # Parallel processing with limiters
                for i, (page_num, img, chars) in enumerate(loader):
                    # Preprocess chars
                    if self.is_english:
                        chars = []

                    device_id = i % settings.PARALLEL_DEVICES
                    limiter = self.ocr_handler.parallel_limiter[device_id]

                    nursery.start_soon(
                        self._process_page_ocr,
                        i,
                        page_num + 1,
                        img,
                        chars,
                        zoomin,
                        device_id,
                        limiter,
                        results,
                        callback,
                        loader.page_count,
                    )
                    await trio.sleep(0.1)
            else:
                # Sequential processing
                for i, (page_num, img, chars) in enumerate(loader):
                    if self.is_english:
                        chars = []

                    boxes, _ = self.ocr_handler.process(
                        page_num + 1, img, chars, self.mean_height[i], zoomin, 0
                    )
                    results[i] = boxes

                    if callback and i % 6 == 5:
                        callback((i + 1) * 0.3 / loader.page_count)

        # Flatten results
        for page_boxes in results:
            if page_boxes:
                all_boxes.extend(page_boxes)

        self.boxes = all_boxes
        logging.info(f"OCR processing {loader.page_count} pages cost {timer() - start}s")

        if callback:
            callback(0.4, f"OCR finished ({timer() - start:.2f}s)")

        # Layout analysis
        start = timer()
        if self.boxes:
            # Convert to list of lists per page
            boxes_by_page = [[] for _ in range(loader.page_count)]
            for b in self.boxes:
                page_idx = b["page_number"] - 1
                if 0 <= page_idx < len(boxes_by_page):
                    boxes_by_page[page_idx].append(b)

            self.boxes, self.page_layout = self.layout_analyzer.analyze(
                self.page_images, boxes_by_page, zoomin
            )

            # Add cumulative heights
            self.boxes = self.layout_analyzer.add_cumulative_heights(
                self.boxes, self.page_cum_height
            )

        if callback:
            callback(0.6, f"Layout analysis ({timer() - start:.2f}s)")

        # Table extraction
        start = timer()
        if self.boxes and self.page_layout:
            _, self.boxes = self.table_extractor.extract(
                self.page_images,
                self.page_layout,
                self.boxes,
                self.page_cum_height,
                zoomin,
            )

        if callback:
            callback(0.8, f"Table analysis ({timer() - start:.2f}s)")

        # Text merging
        start = timer()
        if self.boxes:
            self.boxes = self.text_merger.merge(
                self.boxes,
                self.mean_height,
                self.mean_width,
                self.is_english,
                self.page_images,
                zoomin,
            )

        if callback:
            callback(0.9, f"Text merged ({timer() - start:.2f}s)")

        # Build result
        result = self._build_result(loader, zoomin)

        if callback:
            callback(1.0, "Parsing complete")

        return result

    async def _process_page_ocr(
        self,
        idx: int,
        page_num: int,
        img,
        chars: List[dict],
        zoomin: int,
        device_id: int,
        limiter,
        results: List,
        callback: Optional[Callable],
        total_pages: int,
    ):
        """Process a single page with OCR asynchronously."""
        boxes, _ = await self.ocr_handler.process_async(
            page_num, img, chars, self.mean_height[idx], zoomin, device_id, limiter
        )
        results[idx] = boxes

        if callback and idx % 6 == 5:
            callback((idx + 1) * 0.3 / total_pages)

    def parse_sync(
        self,
        source: Union[str, bytes],
        page_from: int = 0,
        page_to: int = 299,
        zoomin: int = 3,
        callback: Optional[Callable] = None,
    ) -> ParseResult:
        """Synchronous wrapper for parse.

        Args:
            source: File path or binary PDF content.
            page_from: Starting page index.
            page_to: Ending page index.
            zoomin: Zoom factor.
            callback: Progress callback.

        Returns:
            ParseResult with structured content.
        """
        return trio.run(self.parse, source, page_from, page_to, zoomin, callback)

    def _build_result(self, loader: PDFLoader, zoomin: int) -> ParseResult:
        """Build ParseResult from processed data.

        Args:
            loader: PDF loader with page data.
            zoomin: Zoom factor.

        Returns:
            ParseResult object.
        """
        pages = []

        # Group boxes by page
        boxes_by_page = {}
        for b in self.boxes:
            pn = b.get("page_number", 1)
            if pn not in boxes_by_page:
                boxes_by_page[pn] = []
            boxes_by_page[pn].append(b)

        # Group layouts by page
        layouts_by_page = {}
        if self.page_layout:
            for i, layouts in enumerate(self.page_layout):
                layouts_by_page[i + 1] = layouts

        # Build page results
        for i in range(loader.page_count):
            page_num = i + 1

            # Get text blocks for this page
            page_boxes = boxes_by_page.get(page_num, [])
            text_blocks = []
            for b in page_boxes:
                text_blocks.append(
                    TextBlock(
                        text=b.get("text", ""),
                        bbox=BoundingBox(
                            x0=b.get("x0", 0),
                            y0=b.get("top", 0),
                            x1=b.get("x1", 0),
                            y1=b.get("bottom", 0),
                        ),
                        page_num=page_num,
                        layout_type=b.get("layout_type", "text"),
                        layoutno=b.get("layoutno", ""),
                        col_id=b.get("col_id", 0),
                    )
                )

            # Get layout elements for this page
            page_layouts = layouts_by_page.get(page_num, [])
            layout_elements = []
            for layout in page_layouts:
                layout_elements.append(
                    LayoutElement(
                        type=layout.get("type", "unknown"),
                        bbox=BoundingBox(
                            x0=layout.get("x0", 0),
                            y0=layout.get("top", 0),
                            x1=layout.get("x1", 0),
                            y1=layout.get("bottom", 0),
                        ),
                        confidence=layout.get("score", 0.0),
                        page_num=page_num,
                    )
                )

            page_result = PageResult(
                page_num=page_num,
                text_blocks=text_blocks,
                layout_elements=layout_elements,
                width=loader.page_images[i].size[0] / zoomin if i < len(loader.page_images) else 0,
                height=loader.page_images[i].size[1] / zoomin if i < len(loader.page_images) else 0,
            )
            pages.append(page_result)

        return ParseResult(
            pages=pages,
            metadata={
                "total_pages": loader.total_pages,
                "is_english": loader.is_english,
                "outlines": loader.outlines,
            },
        )

    def __call__(
        self,
        fnm: Union[str, bytes],
        need_image: bool = True,
        zoomin: int = 3,
        return_html: bool = False,
    ) -> Tuple[List, List]:
        """Legacy interface for backwards compatibility.

        Args:
            fnm: File name or binary content.
            need_image: Whether to include images.
            zoomin: Zoom factor.
            return_html: Whether to return HTML for tables.

        Returns:
            Tuple of (sections, tables) in legacy format.
        """
        result = self.parse_sync(fnm, zoomin=zoomin)
        return result.to_legacy_format()


class LegacyPDFParser:
    """Compatibility wrapper for the legacy RAGFlowPdfParser interface."""

    def __init__(self, **kwargs):
        """Initialize with legacy interface."""
        model_species = kwargs.get("model_speciess")
        self.new_parser = PDFParser(model_species=model_species)

    def __call__(
        self,
        fnm: Union[str, bytes],
        need_image: bool = True,
        zoomin: int = 3,
        return_html: bool = False,
    ) -> Tuple[List, List]:
        """Parse PDF using legacy interface.

        Args:
            fnm: File name or binary content.
            need_image: Whether to include images.
            zoomin: Zoom factor.
            return_html: Whether to return HTML.

        Returns:
            Tuple of (sections, tables).
        """
        result = self.new_parser.parse_sync(fnm, zoomin=zoomin)
        return result.to_legacy_format()

    @staticmethod
    def total_page_number(fnm, binary=None):
        """Get total page count."""
        return PDFLoader.get_total_pages(binary if binary else fnm)
