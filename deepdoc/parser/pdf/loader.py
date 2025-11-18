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
"""PDF loading and page iteration module.

This module provides lazy loading of PDF pages to reduce memory usage.
"""

import logging
import re
import sys
import threading
from io import BytesIO
from typing import Iterator, List, Optional, Tuple, Union

import numpy as np
import pdfplumber
from PIL import Image
from pypdf import PdfReader as pdf2_read

# Thread lock for pdfplumber operations
LOCK_KEY_PDFPLUMBER = "global_shared_lock_pdfplumber"
if LOCK_KEY_PDFPLUMBER not in sys.modules:
    sys.modules[LOCK_KEY_PDFPLUMBER] = threading.Lock()


class PDFLoader:
    """Load PDF and iterate pages with lazy loading."""

    def __init__(
        self,
        source: Union[str, bytes],
        page_from: int = 0,
        page_to: int = 299,
        zoomin: int = 3,
    ):
        """Initialize the PDF loader.

        Args:
            source: Either a file path or binary PDF content.
            page_from: Starting page index (0-based).
            page_to: Ending page index (exclusive).
            zoomin: Zoom factor for image resolution.
        """
        self.source = source
        self.page_from = page_from
        self.page_to = page_to
        self.zoomin = zoomin

        self._pdf = None
        self._page_images: List[Image.Image] = []
        self._page_chars: List[List[dict]] = []
        self._total_pages = 0
        self._outlines: List[Tuple[str, int]] = []
        self._is_english = False

        self._load()

    def _has_color(self, char: dict) -> bool:
        """Check if a character has color (not pure white/gray)."""
        if char.get("ncs", "") == "DeviceGray":
            stroking = char.get("stroking_color")
            non_stroking = char.get("non_stroking_color")
            if stroking and stroking[0] == 1 and non_stroking and non_stroking[0] == 1:
                if re.match(r"[a-zT_\[\]\(\)-]+", char.get("text", "")):
                    return False
        return True

    def _load(self):
        """Load PDF pages and extract basic information."""
        try:
            with sys.modules[LOCK_KEY_PDFPLUMBER]:
                if isinstance(self.source, str):
                    pdf = pdfplumber.open(self.source)
                else:
                    pdf = pdfplumber.open(BytesIO(self.source))

                self._pdf = pdf
                self._total_pages = len(pdf.pages)

                # Adjust page range
                actual_page_to = min(self.page_to, self._total_pages)

                # Extract page images
                self._page_images = [
                    p.to_image(resolution=72 * self.zoomin, antialias=True).annotated
                    for p in pdf.pages[self.page_from:actual_page_to]
                ]

                # Extract characters from each page
                try:
                    self._page_chars = [
                        [c for c in page.dedupe_chars().chars if self._has_color(c)]
                        for page in pdf.pages[self.page_from:actual_page_to]
                    ]
                except Exception as e:
                    logging.warning(
                        f"Failed to extract characters for pages {self.page_from}-{actual_page_to}: {e}"
                    )
                    self._page_chars = [[] for _ in range(actual_page_to - self.page_from)]

        except Exception:
            logging.exception("PDFLoader _load")
            self._page_images = []
            self._page_chars = []

        # Load outlines
        self._load_outlines()

        # Detect language
        self._detect_language()

    def _load_outlines(self):
        """Load PDF outlines/bookmarks."""
        self._outlines = []
        try:
            if isinstance(self.source, str):
                pdf = pdf2_read(self.source)
            else:
                pdf = pdf2_read(BytesIO(self.source))

            with pdf:
                outlines = pdf.outline

                def dfs(arr, depth):
                    for a in arr:
                        if isinstance(a, dict):
                            self._outlines.append((a.get("/Title", ""), depth))
                        elif isinstance(a, list):
                            dfs(a, depth + 1)

                dfs(outlines, 0)

        except Exception as e:
            logging.warning(f"Outlines exception: {e}")

        if not self._outlines:
            logging.debug("No outlines found in PDF")

    def _detect_language(self):
        """Detect if the document is primarily English."""
        import random

        is_english_list = []
        for i in range(len(self._page_chars)):
            chars = self._page_chars[i]
            if chars:
                sample = random.choices(chars, k=min(100, len(chars)))
                text = "".join([c["text"] for c in sample])
                is_english = bool(
                    re.search(r"[a-zA-Z0-9,/¸;:'\[\]\(\)!@#$%^&*\"?<>._-]{30,}", text)
                )
            else:
                is_english = False
            is_english_list.append(is_english)

        # Majority vote
        english_count = sum(1 if e else 0 for e in is_english_list)
        self._is_english = english_count > len(self._page_images) / 2

    def __iter__(self) -> Iterator[Tuple[int, Image.Image, List[dict]]]:
        """Iterate over pages with page number, image, and characters.

        Yields:
            Tuple of (page_number, page_image, page_characters)
        """
        for i, (img, chars) in enumerate(zip(self._page_images, self._page_chars)):
            yield i, img, chars

    def get_page(self, page_num: int) -> Tuple[Image.Image, List[dict]]:
        """Get a specific page by number.

        Args:
            page_num: Page number (0-based within loaded range).

        Returns:
            Tuple of (page_image, page_characters)
        """
        if page_num < 0 or page_num >= len(self._page_images):
            raise IndexError(f"Page {page_num} out of range")
        return self._page_images[page_num], self._page_chars[page_num]

    @property
    def page_count(self) -> int:
        """Number of loaded pages."""
        return len(self._page_images)

    @property
    def total_pages(self) -> int:
        """Total number of pages in the PDF."""
        return self._total_pages

    @property
    def page_images(self) -> List[Image.Image]:
        """List of page images."""
        return self._page_images

    @property
    def page_chars(self) -> List[List[dict]]:
        """List of character dictionaries per page."""
        return self._page_chars

    @property
    def outlines(self) -> List[Tuple[str, int]]:
        """PDF outlines/bookmarks."""
        return self._outlines

    @property
    def is_english(self) -> bool:
        """Whether the document appears to be primarily English."""
        return self._is_english

    def get_page_heights(self) -> List[float]:
        """Get heights of all pages.

        Returns:
            List of page heights.
        """
        return [img.size[1] / self.zoomin for img in self._page_images]

    def get_cumulative_heights(self) -> np.ndarray:
        """Get cumulative page heights for coordinate transformation.

        Returns:
            Array of cumulative heights starting with 0.
        """
        heights = [0] + self.get_page_heights()
        return np.cumsum(heights)

    def get_mean_char_heights(self) -> List[float]:
        """Get mean character height for each page.

        Returns:
            List of mean character heights.
        """
        heights = []
        for chars in self._page_chars:
            if chars:
                char_heights = [c["height"] for c in chars if "height" in c]
                heights.append(np.median(char_heights) if char_heights else 0)
            else:
                heights.append(0)
        return heights

    def get_mean_char_widths(self) -> List[float]:
        """Get mean character width for each page.

        Returns:
            List of mean character widths.
        """
        widths = []
        for chars in self._page_chars:
            if chars:
                char_widths = [c["width"] for c in chars if "width" in c]
                widths.append(np.median(char_widths) if char_widths else 8)
            else:
                widths.append(8)
        return widths

    def close(self):
        """Close the PDF file."""
        if self._pdf:
            self._pdf.close()
            self._pdf = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def get_total_pages(source: Union[str, bytes]) -> int:
        """Get total number of pages without fully loading the PDF.

        Args:
            source: File path or binary content.

        Returns:
            Total number of pages.
        """
        try:
            with sys.modules[LOCK_KEY_PDFPLUMBER]:
                if isinstance(source, str):
                    pdf = pdfplumber.open(source)
                else:
                    pdf = pdfplumber.open(BytesIO(source))
            total = len(pdf.pages)
            pdf.close()
            return total
        except Exception:
            logging.exception("get_total_pages")
            return 0
