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
"""Text extraction with position information.

This module extracts text blocks from PDF pages with their positions and styling.
"""

import logging
import re
from timeit import default_timer as timer
from typing import List, Optional

import numpy as np
from PIL import Image

from deepdoc.parser.pdf.models import BoundingBox, TextBlock
from deepdoc.vision import OCR, Recognizer


class TextExtractor:
    """Extract text with position information from PDF pages."""

    def __init__(self):
        """Initialize the text extractor with OCR support."""
        self.ocr = OCR()

    def extract(
        self,
        page_num: int,
        page_image: Image.Image,
        page_chars: List[dict],
        mean_height: float,
        zoomin: int = 3,
        device_id: Optional[int] = None,
    ) -> List[TextBlock]:
        """Extract text blocks from a page.

        Args:
            page_num: Page number (1-based).
            page_image: Page image for OCR.
            page_chars: Character dictionaries from pdfplumber.
            mean_height: Mean character height for the page.
            zoomin: Zoom factor used for the image.
            device_id: GPU device ID for OCR.

        Returns:
            List of TextBlock objects with extracted text and positions.
        """
        start = timer()

        # Detect text regions using OCR
        img_np = np.array(page_image)
        bxs = self.ocr.detect(img_np, device_id)
        logging.info(f"TextExtractor detecting boxes cost ({timer() - start}s)")

        if not bxs:
            return []

        start = timer()

        # Convert OCR results to text blocks
        bxs = [(line[0], line[1][0]) for line in bxs]
        blocks = Recognizer.sort_Y_firstly(
            [
                {
                    "x0": b[0][0] / zoomin,
                    "x1": b[1][0] / zoomin,
                    "top": b[0][1] / zoomin,
                    "text": "",
                    "txt": t,
                    "bottom": b[-1][1] / zoomin,
                    "chars": [],
                    "page_number": page_num,
                }
                for b, t in bxs
                if b[0][0] <= b[1][0] and b[0][1] <= b[-1][1]
            ],
            mean_height / 3 if mean_height > 0 else 10,
        )

        # Merge characters into detected boxes
        lefted_chars = []
        for c in page_chars:
            ii = Recognizer.find_overlapped(c, blocks)
            if ii is None:
                lefted_chars.append(c)
                continue

            ch = c["bottom"] - c["top"]
            bh = blocks[ii]["bottom"] - blocks[ii]["top"]
            if abs(ch - bh) / max(ch, bh) >= 0.7 and c["text"] != " ":
                lefted_chars.append(c)
                continue

            blocks[ii]["chars"].append(c)

        # Merge character text within each block
        for b in blocks:
            if not b["chars"]:
                del b["chars"]
                continue

            m_ht = np.mean([c["height"] for c in b["chars"]])
            for c in Recognizer.sort_Y_firstly(b["chars"], m_ht):
                if c["text"] == " " and b["text"]:
                    if re.match(r"[0-9a-zA-Zа-яА-Я,.?;:!%%]", b["text"][-1]):
                        b["text"] += " "
                else:
                    b["text"] += c["text"]
            del b["chars"]

        logging.info(f"TextExtractor sorting {len(page_chars)} chars cost {timer() - start}s")

        # Recognize text for empty boxes using OCR
        start = timer()
        boxes_to_reg = []
        for b in blocks:
            if not b["text"]:
                left = b["x0"] * zoomin
                right = b["x1"] * zoomin
                top = b["top"] * zoomin
                bott = b["bottom"] * zoomin
                b["box_image"] = self.ocr.get_rotate_crop_image(
                    img_np,
                    np.array(
                        [[left, top], [right, top], [right, bott], [left, bott]],
                        dtype=np.float32,
                    ),
                )
                boxes_to_reg.append(b)
            if "txt" in b:
                del b["txt"]

        if boxes_to_reg:
            texts = self.ocr.recognize_batch([b["box_image"] for b in boxes_to_reg], device_id)
            for i in range(len(boxes_to_reg)):
                boxes_to_reg[i]["text"] = texts[i]
                del boxes_to_reg[i]["box_image"]

        logging.info(f"TextExtractor recognize {len(blocks)} boxes cost {timer() - start}s")

        # Filter out empty blocks
        blocks = [b for b in blocks if b["text"]]

        # Update mean height if needed
        if mean_height == 0 and blocks:
            mean_height = np.median([b["bottom"] - b["top"] for b in blocks])

        # Convert to TextBlock objects
        text_blocks = []
        for b in blocks:
            text_blocks.append(
                TextBlock(
                    text=b["text"],
                    bbox=BoundingBox(
                        x0=b["x0"],
                        y0=b["top"],
                        x1=b["x1"],
                        y1=b["bottom"],
                    ),
                    page_num=b["page_number"],
                )
            )

        return text_blocks, lefted_chars

    def preprocess_chars(self, chars: List[dict], is_english: bool) -> List[dict]:
        """Preprocess characters for better text extraction.

        Args:
            chars: Character dictionaries from pdfplumber.
            is_english: Whether the document is primarily English.

        Returns:
            Preprocessed character list.
        """
        if is_english:
            return []

        # Add spaces between alphanumeric characters if needed
        j = 0
        while j + 1 < len(chars):
            if (
                chars[j]["text"]
                and chars[j + 1]["text"]
                and re.match(r"[0-9a-zA-Z,.:;!%]+", chars[j]["text"] + chars[j + 1]["text"])
                and chars[j + 1]["x0"] - chars[j]["x1"]
                >= min(chars[j + 1]["width"], chars[j]["width"]) / 2
            ):
                chars[j]["text"] += " "
            j += 1

        return chars

    def extract_from_dict(self, blocks: List[dict]) -> List[TextBlock]:
        """Convert dictionary blocks to TextBlock objects.

        Args:
            blocks: List of block dictionaries.

        Returns:
            List of TextBlock objects.
        """
        text_blocks = []
        for b in blocks:
            text_blocks.append(
                TextBlock(
                    text=b.get("text", ""),
                    bbox=BoundingBox(
                        x0=b.get("x0", 0),
                        y0=b.get("top", 0),
                        x1=b.get("x1", 0),
                        y1=b.get("bottom", 0),
                    ),
                    page_num=b.get("page_number", 0),
                    layout_type=b.get("layout_type", "text"),
                    layoutno=b.get("layoutno", ""),
                    col_id=b.get("col_id", 0),
                )
            )
        return text_blocks
