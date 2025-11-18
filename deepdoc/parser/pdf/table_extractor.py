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
"""Table detection and parsing module.

This module detects and extracts tables from PDF pages.
"""

import logging
import re
from typing import List, Tuple

import numpy as np
from PIL import Image

from deepdoc.parser.pdf.models import BoundingBox, Table
from deepdoc.vision import Recognizer, TableStructureRecognizer


class TableExtractor:
    """Extract tables from PDF pages."""

    def __init__(self):
        """Initialize the table extractor with table structure recognizer."""
        self.tbl_det = TableStructureRecognizer()

    def extract(
        self,
        page_images: List[Image.Image],
        page_layouts: List[List[dict]],
        boxes: List[dict],
        page_cum_height: np.ndarray,
        zoomin: int = 3,
    ) -> Tuple[List[dict], List[dict]]:
        """Extract tables from pages.

        Args:
            page_images: List of page images.
            page_layouts: Layout info per page.
            boxes: Flattened text boxes with layout info.
            page_cum_height: Cumulative page heights.
            zoomin: Zoom factor.

        Returns:
            Tuple of (table components, updated boxes with table tags).
        """
        logging.debug("Table processing...")

        imgs = []
        pos = []
        tbcnt = [0]
        MARGIN = 10

        assert len(page_layouts) == len(page_images)

        # Collect table regions for processing
        for p, tbls in enumerate(page_layouts):
            tbls = [f for f in tbls if f.get("type") == "table"]
            tbcnt.append(len(tbls))

            if not tbls:
                continue

            for tb in tbls:
                left = (tb["x0"] - MARGIN) * zoomin
                top = (tb["top"] - MARGIN) * zoomin
                right = (tb["x1"] + MARGIN) * zoomin
                bott = (tb["bottom"] + MARGIN) * zoomin

                pos.append((left, top))
                imgs.append(page_images[p].crop((left, top, right, bott)))

        assert len(page_images) == len(tbcnt) - 1

        if not imgs:
            return [], boxes

        # Run table structure recognition
        recos = self.tbl_det(imgs)
        tbcnt = np.cumsum(tbcnt)

        tb_cpns = []
        for i in range(len(tbcnt) - 1):  # for page
            pg = []
            for j, tb_items in enumerate(recos[tbcnt[i] : tbcnt[i + 1]]):  # for table
                poss = pos[tbcnt[i] : tbcnt[i + 1]]
                for it in tb_items:  # for table components
                    it["x0"] = it["x0"] + poss[j][0]
                    it["x1"] = it["x1"] + poss[j][0]
                    it["top"] = it["top"] + poss[j][1]
                    it["bottom"] = it["bottom"] + poss[j][1]

                    for n in ["x0", "x1", "top", "bottom"]:
                        it[n] /= zoomin

                    it["top"] += page_cum_height[i]
                    it["bottom"] += page_cum_height[i]
                    it["pn"] = i
                    it["layoutno"] = j
                    pg.append(it)
            tb_cpns.extend(pg)

        # Tag boxes with table structure info
        boxes = self._tag_table_structure(boxes, tb_cpns)

        return tb_cpns, boxes

    def _tag_table_structure(
        self, boxes: List[dict], tb_cpns: List[dict]
    ) -> List[dict]:
        """Tag boxes with table structure information (R, H, C, SP).

        Args:
            boxes: Text boxes.
            tb_cpns: Table components.

        Returns:
            Updated boxes with table tags.
        """

        def gather(kwd, fzy=10, ption=0.6):
            eles = Recognizer.sort_Y_firstly(
                [r for r in tb_cpns if re.match(kwd, r.get("label", ""))], fzy
            )
            eles = Recognizer.layouts_cleanup(boxes, eles, 5, ption)
            return Recognizer.sort_Y_firstly(eles, 0)

        # Gather table components
        headers = gather(r".*header$")
        rows = gather(r".* (row|header)")
        spans = gather(r".*spanning")
        clmns = sorted(
            [r for r in tb_cpns if re.match(r"table column$", r.get("label", ""))],
            key=lambda x: (x.get("pn", 0), x.get("layoutno", 0), x.get("x0", 0)),
        )
        clmns = Recognizer.layouts_cleanup(boxes, clmns, 5, 0.5)

        # Tag each box
        for b in boxes:
            if b.get("layout_type", "") != "table":
                continue

            # Row tag
            ii = Recognizer.find_overlapped_with_threshold(b, rows, thr=0.3)
            if ii is not None:
                b["R"] = ii
                b["R_top"] = rows[ii]["top"]
                b["R_bott"] = rows[ii]["bottom"]

            # Header tag
            ii = Recognizer.find_overlapped_with_threshold(b, headers, thr=0.3)
            if ii is not None:
                b["H_top"] = headers[ii]["top"]
                b["H_bott"] = headers[ii]["bottom"]
                b["H_left"] = headers[ii]["x0"]
                b["H_right"] = headers[ii]["x1"]
                b["H"] = ii

            # Column tag
            ii = Recognizer.find_horizontally_tightest_fit(b, clmns)
            if ii is not None:
                b["C"] = ii
                b["C_left"] = clmns[ii]["x0"]
                b["C_right"] = clmns[ii]["x1"]

            # Spanning cell tag
            ii = Recognizer.find_overlapped_with_threshold(b, spans, thr=0.3)
            if ii is not None:
                b["H_top"] = spans[ii]["top"]
                b["H_bott"] = spans[ii]["bottom"]
                b["H_left"] = spans[ii]["x0"]
                b["H_right"] = spans[ii]["x1"]
                b["SP"] = ii

        return boxes

    def to_table_objects(
        self,
        table_data: List[Tuple],
        page_cum_height: np.ndarray,
    ) -> List[Table]:
        """Convert extracted table data to Table objects.

        Args:
            table_data: List of (image, html) tuples with positions.
            page_cum_height: Cumulative page heights.

        Returns:
            List of Table objects.
        """
        tables = []
        for (img, html), positions in table_data:
            if not positions:
                continue

            # Get bounding box from positions
            pn, left, right, top, bott = positions[0]

            table = Table(
                bbox=BoundingBox(x0=left, y0=top, x1=right, y1=bott),
                html=html if isinstance(html, str) else "",
                page_num=pn,
                image=img,
            )
            tables.append(table)

        return tables
