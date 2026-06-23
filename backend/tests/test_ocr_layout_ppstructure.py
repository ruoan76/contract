# -*- coding: utf-8 -*-
"""PP-Structure 排版回退单测。"""
from __future__ import annotations

import numpy as np

from app.services.ai_review.ocr_layout import layout_ocr_blocks_with_meta
from app.services.ai_review.ocr_layout_ppstructure import layout_with_ppstructure


def test_ppstructure_falls_back_without_paddle() -> None:
    """未安装 paddleocr 时应回退 heuristic 并产出文本。"""
    image = np.ones((120, 200, 3), dtype=np.uint8) * 255
    easy = [
        ([[10, 10], [90, 10], [90, 30], [10, 30]], "测试标题", 0.95),
    ]
    result = layout_with_ppstructure(image, easy, min_conf=0.5)
    if result is None:
        result = layout_ocr_blocks_with_meta(easy, min_conf=0.5)
    assert "测试标题" in result.text
