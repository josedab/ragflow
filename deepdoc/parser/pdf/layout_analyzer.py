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
"""Layout recognition module.

This module analyzes page layout to identify semantic regions like
text, titles, tables, figures, etc.
"""

import logging
import os
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

from deepdoc.parser.pdf.models import BoundingBox, LayoutElement
from deepdoc.vision import AscendLayoutRecognizer, LayoutRecognizer


class LayoutAnalyzer:
    """Analyze page layout using ONNX model."""

    def __init__(self, model_species: Optional[str] = None):
        """Initialize the layout analyzer.

        Args:
            model_species: Optional model species for domain-specific recognition.
        """
        layout_recognizer_type = os.getenv("LAYOUT_RECOGNIZER_TYPE", "onnx").lower()

        if layout_recognizer_type not in ["onnx", "ascend"]:
            raise RuntimeError("Unsupported layout recognizer type.")

        if model_species:
            recognizer_domain = f"layout.{model_species}"
        else:
            recognizer_domain = "layout"

        if layout_recognizer_type == "ascend":
            logging.debug("Using Ascend LayoutRecognizer")
            self.layouter = AscendLayoutRecognizer(recognizer_domain)
        else:  # onnx
            logging.debug("Using Onnx LayoutRecognizer")
            self.layouter = LayoutRecognizer(recognizer_domain)

    def analyze(
        self,
        page_images: List[Image.Image],
        boxes: List[List[dict]],
        zoomin: int = 3,
        drop: bool = True,
    ) -> Tuple[List[dict], List[List[dict]]]:
        """Analyze layout of pages.

        Args:
            page_images: List of page images.
            boxes: List of text box lists per page.
            zoomin: Zoom factor used for images.
            drop: Whether to drop boxes outside detected layouts.

        Returns:
            Tuple of (flattened boxes with layout info, layout info per page)
        """
        assert len(page_images) == len(boxes)

        # Run layout recognition
        flattened_boxes, page_layouts = self.layouter(
            page_images, boxes, zoomin, drop=drop
        )

        return flattened_boxes, page_layouts

    def add_cumulative_heights(
        self, boxes: List[dict], page_cum_height: np.ndarray
    ) -> List[dict]:
        """Add cumulative heights to box coordinates.

        Args:
            boxes: List of box dictionaries.
            page_cum_height: Cumulative page heights.

        Returns:
            Updated boxes with cumulative height offsets.
        """
        for box in boxes:
            page_num = box.get("page_number", 1) - 1
            if page_num < len(page_cum_height):
                box["top"] += page_cum_height[page_num]
                box["bottom"] += page_cum_height[page_num]
        return boxes

    def to_layout_elements(
        self, page_layouts: List[List[dict]], page_cum_height: np.ndarray
    ) -> List[List[LayoutElement]]:
        """Convert page layouts to LayoutElement objects.

        Args:
            page_layouts: Layout dictionaries per page.
            page_cum_height: Cumulative page heights.

        Returns:
            List of LayoutElement lists per page.
        """
        result = []
        for i, layouts in enumerate(page_layouts):
            page_elements = []
            for layout in layouts:
                # Adjust coordinates with cumulative height
                top = layout.get("top", 0)
                bottom = layout.get("bottom", 0)
                if i < len(page_cum_height):
                    top += page_cum_height[i]
                    bottom += page_cum_height[i]

                element = LayoutElement(
                    type=layout.get("type", "unknown"),
                    bbox=BoundingBox(
                        x0=layout.get("x0", 0),
                        y0=top,
                        x1=layout.get("x1", 0),
                        y1=bottom,
                    ),
                    confidence=layout.get("score", 0.0),
                    page_num=i + 1,
                    layoutno=layout.get("layoutno", ""),
                )
                page_elements.append(element)
            result.append(page_elements)
        return result
