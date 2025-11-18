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
"""OCR coordination module.

This module coordinates OCR operations for text extraction from images.
"""

import logging
import re
from timeit import default_timer as timer
from typing import List, Optional, Tuple

import numpy as np
import trio
from PIL import Image

from common import settings
from deepdoc.parser.pdf.models import BoundingBox, TextBlock
from deepdoc.vision import OCR, Recognizer


class OCRHandler:
    """Handle OCR operations for PDF pages."""

    def __init__(self):
        """Initialize the OCR handler."""
        self.ocr = OCR()

        # Set up parallel limiters if multiple devices available
        self.parallel_limiter = None
        if settings.PARALLEL_DEVICES > 1:
            self.parallel_limiter = [
                trio.CapacityLimiter(1) for _ in range(settings.PARALLEL_DEVICES)
            ]

    def process(
        self,
        page_num: int,
        page_image: Image.Image,
        page_chars: List[dict],
        mean_height: float,
        zoomin: int = 3,
        device_id: Optional[int] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Process a page with OCR.

        Args:
            page_num: Page number (1-based).
            page_image: Page image.
            page_chars: Characters from pdfplumber.
            mean_height: Mean character height.
            zoomin: Zoom factor.
            device_id: GPU device ID.

        Returns:
            Tuple of (text boxes, leftover characters).
        """
        start = timer()

        # Detect text regions
        img_np = np.array(page_image)
        bxs = self.ocr.detect(img_np, device_id)
        logging.info(f"OCRHandler detecting boxes cost ({timer() - start}s)")

        if not bxs:
            return [], []

        start = timer()

        # Convert to box format
        bxs = [(line[0], line[1][0]) for line in bxs]
        boxes = Recognizer.sort_Y_firstly(
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

        # Merge characters into boxes
        lefted_chars = []
        for c in page_chars:
            ii = Recognizer.find_overlapped(c, boxes)
            if ii is None:
                lefted_chars.append(c)
                continue

            ch = c["bottom"] - c["top"]
            bh = boxes[ii]["bottom"] - boxes[ii]["top"]
            if abs(ch - bh) / max(ch, bh) >= 0.7 and c["text"] != " ":
                lefted_chars.append(c)
                continue

            boxes[ii]["chars"].append(c)

        # Merge character text
        for b in boxes:
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

        logging.info(f"OCRHandler sorting {len(page_chars)} chars cost {timer() - start}s")

        # Recognize text for empty boxes
        start = timer()
        boxes_to_reg = []
        for b in boxes:
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
            texts = self.ocr.recognize_batch(
                [b["box_image"] for b in boxes_to_reg], device_id
            )
            for i in range(len(boxes_to_reg)):
                boxes_to_reg[i]["text"] = texts[i]
                del boxes_to_reg[i]["box_image"]

        logging.info(f"OCRHandler recognize {len(boxes)} boxes cost {timer() - start}s")

        # Filter empty boxes
        boxes = [b for b in boxes if b["text"]]

        return boxes, lefted_chars

    async def process_async(
        self,
        page_num: int,
        page_image: Image.Image,
        page_chars: List[dict],
        mean_height: float,
        zoomin: int = 3,
        device_id: Optional[int] = None,
        limiter: Optional[trio.CapacityLimiter] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Process a page with OCR asynchronously.

        Args:
            page_num: Page number (1-based).
            page_image: Page image.
            page_chars: Characters from pdfplumber.
            mean_height: Mean character height.
            zoomin: Zoom factor.
            device_id: GPU device ID.
            limiter: Trio capacity limiter for resource control.

        Returns:
            Tuple of (text boxes, leftover characters).
        """
        if limiter:
            async with limiter:
                return await trio.to_thread.run_sync(
                    lambda: self.process(
                        page_num, page_image, page_chars, mean_height, zoomin, device_id
                    )
                )
        else:
            return self.process(
                page_num, page_image, page_chars, mean_height, zoomin, device_id
            )

    def needs_ocr(self, text_blocks: List[TextBlock], page_chars: List[dict]) -> bool:
        """Determine if OCR is needed for a page.

        Args:
            text_blocks: Extracted text blocks.
            page_chars: Characters from pdfplumber.

        Returns:
            True if OCR should be performed.
        """
        # If we have no text blocks but have characters, OCR might help
        if not text_blocks and page_chars:
            return True

        # If we have very few text blocks compared to characters
        if len(text_blocks) < len(page_chars) / 100:
            return True

        return False
