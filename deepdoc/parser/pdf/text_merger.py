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
"""Text block merging module.

This module merges adjacent text blocks using learned models.
"""

import logging
import os
import re
from collections import Counter, defaultdict
from typing import List

import numpy as np
import xgboost as xgb
from huggingface_hub import snapshot_download

from common.file_utils import get_project_base_directory
from common.misc_utils import pip_install_torch
from deepdoc.parser.pdf.models import TextBlock
from rag.nlp import rag_tokenizer


class TextMerger:
    """Merge text blocks using learned model."""

    def __init__(self):
        """Initialize the text merger with XGBoost model."""
        self.updown_cnt_mdl = xgb.Booster()

        try:
            pip_install_torch()
            import torch.cuda

            if torch.cuda.is_available():
                self.updown_cnt_mdl.set_param({"device": "cuda"})
        except Exception:
            logging.info("No torch found for text merger.")

        try:
            model_dir = os.path.join(get_project_base_directory(), "rag/res/deepdoc")
            self.updown_cnt_mdl.load_model(
                os.path.join(model_dir, "updown_concat_xgb.model")
            )
        except Exception:
            model_dir = snapshot_download(
                repo_id="InfiniFlow/text_concat_xgb_v1.0",
                local_dir=os.path.join(get_project_base_directory(), "rag/res/deepdoc"),
                local_dir_use_symlinks=False,
            )
            self.updown_cnt_mdl.load_model(
                os.path.join(model_dir, "updown_concat_xgb.model")
            )

    def merge(
        self,
        boxes: List[dict],
        mean_height: List[float],
        mean_width: List[float],
        is_english: bool,
        page_images: List = None,
        zoomin: int = 3,
    ) -> List[dict]:
        """Merge text blocks.

        Args:
            boxes: List of text box dictionaries.
            mean_height: Mean character height per page.
            mean_width: Mean character width per page.
            is_english: Whether document is primarily English.
            page_images: Page images for width calculation.
            zoomin: Zoom factor.

        Returns:
            Merged text boxes.
        """
        # Assign columns first
        boxes = self._assign_column(boxes, page_images, zoomin)

        # Horizontal merge
        boxes = self._text_merge_horizontal(boxes, mean_height)

        # Vertical merge
        boxes = self._naive_vertical_merge(boxes, mean_height, mean_width, is_english)

        # Final reading order
        boxes = self._final_reading_order_merge(boxes, page_images, zoomin)

        return boxes

    def _assign_column(
        self, boxes: List[dict], page_images: List = None, zoomin: int = 3
    ) -> List[dict]:
        """Assign column IDs to boxes.

        Args:
            boxes: Text boxes.
            page_images: Page images for width calculation.
            zoomin: Zoom factor.

        Returns:
            Boxes with col_id assigned.
        """
        if not boxes:
            return boxes

        if all("col_id" in b for b in boxes):
            return boxes

        by_page = defaultdict(list)
        for b in boxes:
            by_page[b["page_number"]].append(b)

        page_info = {}
        counter = Counter()

        for pg, bxs in by_page.items():
            if not bxs:
                page_info[pg] = {"page_w": 1.0, "left_edge": 0.0, "cand": 1}
                counter[1] += 1
                continue

            if page_images and len(page_images) >= pg:
                page_w = page_images[pg - 1].size[0] / max(1, zoomin)
                left_edge = 0.0
            else:
                xs0 = [box["x0"] for box in bxs]
                xs1 = [box["x1"] for box in bxs]
                left_edge = float(min(xs0))
                page_w = max(1.0, float(max(xs1) - left_edge))

            widths = [max(1.0, (box["x1"] - box["x0"])) for box in bxs]
            median_w = float(np.median(widths)) if widths else 1.0

            raw_cols = int(page_w / max(1.0, median_w))
            cand = raw_cols

            page_info[pg] = {"page_w": page_w, "left_edge": left_edge, "cand": cand}
            counter[cand] += 1

        global_cols = counter.most_common(1)[0][0]
        logging.debug(f"Global column_num decided by majority: {global_cols}")

        for pg, bxs in by_page.items():
            if not bxs:
                continue

            page_w = page_info[pg]["page_w"]
            left_edge = page_info[pg]["left_edge"]

            if global_cols == 1:
                for box in bxs:
                    box["col_id"] = 0
                continue

            for box in bxs:
                w = box["x1"] - box["x0"]
                if w >= 0.8 * page_w:
                    box["col_id"] = 0
                    continue
                cx = 0.5 * (box["x0"] + box["x1"])
                norm_cx = (cx - left_edge) / page_w
                norm_cx = max(0.0, min(norm_cx, 0.999999))
                box["col_id"] = int(min(global_cols - 1, norm_cx * global_cols))

        return boxes

    def _text_merge_horizontal(
        self, boxes: List[dict], mean_height: List[float]
    ) -> List[dict]:
        """Merge adjacent boxes horizontally.

        Args:
            boxes: Text boxes.
            mean_height: Mean character height per page.

        Returns:
            Horizontally merged boxes.
        """
        i = 0
        while i < len(boxes) - 1:
            b = boxes[i]
            b_ = boxes[i + 1]

            if b["page_number"] != b_["page_number"] or b.get("col_id") != b_.get(
                "col_id"
            ):
                i += 1
                continue

            if b.get("layoutno", "0") != b_.get("layoutno", "1") or b.get(
                "layout_type", ""
            ) in ["table", "figure", "equation"]:
                i += 1
                continue

            page_idx = b["page_number"] - 1
            mh = mean_height[page_idx] if page_idx < len(mean_height) else 10

            y_dis = (b_["top"] + b_["bottom"] - b["top"] - b["bottom"]) / 2
            if abs(y_dis) < mh / 3:
                # Merge
                boxes[i]["x1"] = b_["x1"]
                boxes[i]["top"] = (b["top"] + b_["top"]) / 2
                boxes[i]["bottom"] = (b["bottom"] + b_["bottom"]) / 2
                boxes[i]["text"] += b_["text"]
                boxes.pop(i + 1)
                continue

            i += 1

        return boxes

    def _naive_vertical_merge(
        self,
        boxes: List[dict],
        mean_height: List[float],
        mean_width: List[float],
        is_english: bool,
    ) -> List[dict]:
        """Merge boxes vertically using simple heuristics.

        Args:
            boxes: Text boxes.
            mean_height: Mean character height per page.
            mean_width: Mean character width per page.
            is_english: Whether document is English.

        Returns:
            Vertically merged boxes.
        """
        grouped = defaultdict(list)
        for b in boxes:
            grouped[(b["page_number"], b.get("col_id", 0))].append(b)

        merged_boxes = []
        for (pg, col), bxs in grouped.items():
            bxs = sorted(bxs, key=lambda x: (x["top"], x["x0"]))
            if not bxs:
                continue

            page_idx = pg - 1
            mh = (
                mean_height[page_idx]
                if page_idx < len(mean_height)
                else (np.median([b["bottom"] - b["top"] for b in bxs]) or 10)
            )
            mw = mean_width[page_idx] if page_idx < len(mean_width) else 8

            i = 0
            while i + 1 < len(bxs):
                b = bxs[i]
                b_ = bxs[i + 1]

                if b["page_number"] < b_["page_number"] and re.match(
                    r"[0-9  \u2022\u4e00\u2014-]+$", b["text"]
                ):
                    bxs.pop(i)
                    continue

                if not b["text"].strip():
                    bxs.pop(i)
                    continue

                if not b["text"].strip() or b.get("layoutno") != b_.get("layoutno"):
                    i += 1
                    continue

                if b_["top"] - b["bottom"] > mh * 1.5:
                    i += 1
                    continue

                overlap = max(0, min(b["x1"], b_["x1"]) - max(b["x0"], b_["x0"]))
                if overlap / max(1, min(b["x1"] - b["x0"], b_["x1"] - b_["x0"])) < 0.3:
                    i += 1
                    continue

                # Features for concatenation
                concatting_feats = [
                    b["text"].strip()[-1] in ",;:'\"\uff0c\u3001\u2018\u2019\u0022\uff1b\uff1a-",
                    len(b["text"].strip()) > 1
                    and b["text"].strip()[-2] in ",;:'\"\uff0c\u2018\u2019\u3001\uff1b\uff1a",
                    b_["text"].strip()
                    and b_["text"].strip()[0] in "\u3002\uff1b\uff1f\uff01?\uff09),\uff0c\u3001\uff1a",
                ]

                # Features for not concatenating
                feats = [
                    b.get("layoutno", 0) != b_.get("layoutno", 0),
                    b["text"].strip()[-1] in "\u3002\uff1f\uff01?",
                    is_english and b["text"].strip()[-1] in ".!?",
                    b["page_number"] == b_["page_number"]
                    and b_["top"] - b["bottom"] > mh * 1.5,
                    b["page_number"] < b_["page_number"]
                    and abs(b["x0"] - b_["x0"]) > mw * 4,
                ]

                # Split features
                detach_feats = [b["x1"] < b_["x0"], b["x0"] > b_["x1"]]

                if (any(feats) and not any(concatting_feats)) or any(detach_feats):
                    i += 1
                    continue

                # Merge
                b["text"] = (b["text"].rstrip() + " " + b_["text"].lstrip()).strip()
                b["bottom"] = b_["bottom"]
                b["x0"] = min(b["x0"], b_["x0"])
                b["x1"] = max(b["x1"], b_["x1"])
                bxs.pop(i + 1)

            merged_boxes.extend(bxs)

        return sorted(
            merged_boxes,
            key=lambda x: (x["page_number"], x.get("col_id", 0), x["top"]),
        )

    def _final_reading_order_merge(
        self, boxes: List[dict], page_images: List = None, zoomin: int = 3
    ) -> List[dict]:
        """Arrange boxes in final reading order.

        Args:
            boxes: Text boxes.
            page_images: Page images.
            zoomin: Zoom factor.

        Returns:
            Boxes in reading order.
        """
        if not boxes:
            return boxes

        boxes = self._assign_column(boxes, page_images, zoomin)

        pages = defaultdict(lambda: defaultdict(list))
        for b in boxes:
            pg = b["page_number"]
            col = b.get("col_id", 0)
            pages[pg][col].append(b)

        result = []
        for pg in sorted(pages.keys()):
            cols = pages[pg]
            for col in sorted(cols.keys()):
                col_boxes = sorted(cols[col], key=lambda x: x["top"])
                result.extend(col_boxes)

        return result

    def _updown_concat_features(self, up: dict, down: dict) -> List:
        """Generate features for up/down concatenation decision.

        Args:
            up: Upper text box.
            down: Lower text box.

        Returns:
            Feature vector.
        """
        w = max(self._char_width(up), self._char_width(down))
        h = max(self._height(up), self._height(down))
        y_dis = (down["top"] + down["bottom"] - up["top"] - up["bottom"]) / 2

        LEN = 6
        tks_down = rag_tokenizer.tokenize(down["text"][:LEN]).split()
        tks_up = rag_tokenizer.tokenize(up["text"][-LEN:]).split()

        tks_all = up["text"][-LEN:].strip()
        if re.match(r"[a-zA-Z0-9]+", up["text"][-1] + down["text"][0]):
            tks_all += " "
        tks_all += down["text"][:LEN].strip()
        tks_all = rag_tokenizer.tokenize(tks_all).split()

        fea = [
            up.get("R", -1) == down.get("R", -1),
            y_dis / h if h > 0 else 0,
            down["page_number"] - up["page_number"],
            up.get("layout_type") == down.get("layout_type"),
            up.get("layout_type") == "text",
            down.get("layout_type") == "text",
            up.get("layout_type") == "table",
            down.get("layout_type") == "table",
            bool(re.search(r"([。？！；!?;+)）]|[a-z]\.)$", up["text"])),
            bool(re.search(r"[，：'"、0-9（+-]$", up["text"])),
            bool(re.search(r"(^.?[/,?;:\]，。；：'"？！》】）-])", down["text"])),
            bool(re.match(r"[\(（][^\(\)（）]+[）\)]$", up["text"])),
            bool(re.search(r"[，,][^。.]+$", up["text"])),
            bool(re.search(r"[，,][^。.]+$", up["text"])),
            bool(
                re.search(r"[\(（][^\)）]+$", up["text"])
                and re.search(r"[\)）]", down["text"])
            ),
            self._match_proj(down),
            bool(re.match(r"[A-Z]", down["text"])),
            bool(re.match(r"[A-Z]", up["text"][-1])),
            bool(re.match(r"[a-z0-9]", up["text"][-1])),
            bool(re.match(r"[0-9.%,-]+$", down["text"])),
            (
                up["text"].strip()[-2:] == down["text"].strip()[-2:]
                if len(up["text"].strip()) > 1 and len(down["text"].strip()) > 1
                else False
            ),
            up["x0"] > down["x1"],
            (
                abs(self._height(up) - self._height(down))
                / min(self._height(up), self._height(down))
                if min(self._height(up), self._height(down)) > 0
                else 0
            ),
            self._x_dis(up, down) / max(w, 0.000001),
            (
                (len(up["text"]) - len(down["text"]))
                / max(len(up["text"]), len(down["text"]))
                if max(len(up["text"]), len(down["text"])) > 0
                else 0
            ),
            len(tks_all) - len(tks_up) - len(tks_down),
            len(tks_down) - len(tks_up),
            tks_down[-1] == tks_up[-1] if tks_down and tks_up else False,
            max(down.get("in_row", 0), up.get("in_row", 0)),
            abs(down.get("in_row", 0) - up.get("in_row", 0)),
            len(tks_down) == 1 and rag_tokenizer.tag(tks_down[0]).find("n") >= 0,
            len(tks_up) == 1 and rag_tokenizer.tag(tks_up[0]).find("n") >= 0,
        ]
        return fea

    def _char_width(self, c: dict) -> float:
        """Calculate character width."""
        return (c["x1"] - c["x0"]) / max(len(c.get("text", "")), 1)

    def _height(self, c: dict) -> float:
        """Calculate box height."""
        return c["bottom"] - c["top"]

    def _x_dis(self, a: dict, b: dict) -> float:
        """Calculate horizontal distance between boxes."""
        return min(
            abs(a["x1"] - b["x0"]),
            abs(a["x0"] - b["x1"]),
            abs(a["x0"] + a["x1"] - b["x0"] - b["x1"]) / 2,
        )

    def _match_proj(self, b: dict) -> bool:
        """Check if text matches projection patterns."""
        proj_patt = [
            r"第[零一二三四五六七八九十百]+章",
            r"第[零一二三四五六七八九十百]+[条节]",
            r"[零一二三四五六七八九十百]+[、是 　]",
            r"[\(（][零一二三四五六七八九十百]+[）\)]",
            r"[\(（][0-9]+[）\)]",
            r"[0-9]+(、|\.[　 ]|）|\.[^0-9./a-zA-Z_%><-]{4,})",
            r"[0-9]+\.[0-9.]+(、|\.[ 　])",
            r"[⚫•➢①② ]",
        ]
        return any(re.match(p, b.get("text", "")) for p in proj_patt)
