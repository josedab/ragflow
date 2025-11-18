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
"""Image extraction module.

This module extracts images and figures from PDF pages.
"""

from io import BytesIO
from typing import List, Tuple

import numpy as np
from PIL import Image

from deepdoc.parser.pdf.models import BoundingBox, Figure


class ImageExtractor:
    """Extract images from PDF pages."""

    def __init__(self):
        """Initialize the image extractor."""
        pass

    def extract_figures(
        self,
        page_images: List[Image.Image],
        page_layouts: List[List[dict]],
        page_cum_height: np.ndarray,
        zoomin: int = 3,
    ) -> List[Figure]:
        """Extract figures from pages based on layout detection.

        Args:
            page_images: List of page images.
            page_layouts: Layout info per page.
            page_cum_height: Cumulative page heights.
            zoomin: Zoom factor.

        Returns:
            List of Figure objects.
        """
        figures = []

        for p, layouts in enumerate(page_layouts):
            figure_layouts = [f for f in layouts if f.get("type") == "figure"]

            for fig in figure_layouts:
                # Get figure region with margin
                margin = 5
                left = max(0, (fig["x0"] - margin) * zoomin)
                top = max(0, (fig["top"] - margin) * zoomin)
                right = (fig["x1"] + margin) * zoomin
                bott = (fig["bottom"] + margin) * zoomin

                # Crop image
                img_crop = page_images[p].crop((left, top, right, bott))

                # Convert to bytes
                img_bytes = BytesIO()
                img_crop.save(img_bytes, format="PNG")

                figure = Figure(
                    bbox=BoundingBox(
                        x0=fig["x0"],
                        y0=fig["top"] + page_cum_height[p],
                        x1=fig["x1"],
                        y1=fig["bottom"] + page_cum_height[p],
                    ),
                    image=img_bytes.getvalue(),
                    page_num=p + 1,
                )
                figures.append(figure)

        return figures

    def crop_region(
        self,
        page_image: Image.Image,
        bbox: BoundingBox,
        zoomin: int = 3,
        margin: int = 5,
    ) -> bytes:
        """Crop a region from a page image.

        Args:
            page_image: Page image.
            bbox: Bounding box to crop.
            zoomin: Zoom factor.
            margin: Margin around the region.

        Returns:
            Cropped image as bytes.
        """
        left = max(0, (bbox.x0 - margin) * zoomin)
        top = max(0, (bbox.y0 - margin) * zoomin)
        right = (bbox.x1 + margin) * zoomin
        bott = (bbox.y1 + margin) * zoomin

        img_crop = page_image.crop((left, top, right, bott))

        img_bytes = BytesIO()
        img_crop.save(img_bytes, format="PNG")

        return img_bytes.getvalue()

    def crop_from_position_tag(
        self,
        page_images: List[Image.Image],
        position_tag: str,
        page_from: int = 0,
        zoomin: int = 3,
    ) -> Tuple[bytes, Tuple[int, float, float, float, float]]:
        """Crop image from a position tag.

        Args:
            page_images: List of page images.
            position_tag: Position tag in format @@page\tx0\tx1\ttop\tbottom##
            page_from: Starting page offset.
            zoomin: Zoom factor.

        Returns:
            Tuple of (image bytes, (page, x0, x1, top, bottom)).
        """
        # Parse position tag
        import re

        match = re.search(r"@@(\d+)\t([\d.]+)\t([\d.]+)\t([\d.]+)\t([\d.]+)##", position_tag)
        if not match:
            return None, None

        pn = int(match.group(1))
        x0 = float(match.group(2))
        x1 = float(match.group(3))
        top = float(match.group(4))
        bottom = float(match.group(5))

        # Adjust page number
        page_idx = pn - page_from
        if page_idx < 0 or page_idx >= len(page_images):
            return None, None

        # Crop
        bbox = BoundingBox(x0=x0, y0=top, x1=x1, y1=bottom)
        img_bytes = self.crop_region(page_images[page_idx], bbox, zoomin)

        return img_bytes, (pn, x0, x1, top, bottom)
