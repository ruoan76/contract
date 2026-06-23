# -*- coding: utf-8 -*-
"""OCR 引擎抽象单测（mock，不加载模型）。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from app.services.ai_review.ocr_engine import OcrBlock, OcrPageResult, get_ocr_engine


def test_page_meta_needs_review_on_low_conf() -> None:
    from app.services.ai_review.ocr_engine import _page_meta

    blocks = [
        OcrBlock(bbox=[[0, 0], [1, 0], [1, 1], [0, 1]], text="测试", confidence=0.3),
    ]
    result = _page_meta(blocks, "mock")
    assert result.needs_review is True
    assert result.avg_confidence == 0.3


def test_to_easyocr_format() -> None:
    page = OcrPageResult(
        blocks=[
            OcrBlock(
                bbox=[[0.0, 0.0], [10.0, 0.0], [10.0, 5.0], [0.0, 5.0]],
                text="合同",
                confidence=0.9,
            )
        ],
        avg_confidence=0.9,
        engine="mock",
    )
    fmt = page.to_easyocr_format()
    assert fmt[0][1] == "合同"
    assert fmt[0][2] == 0.9


@patch("app.services.ai_review.engines.rapidocr_engine._get_rapidocr")
def test_rapidocr_engine_recognize(mock_get) -> None:
    mock_engine = MagicMock()
    mock_engine.return_value = (
        [
            ([[0, 0], [10, 0], [10, 5], [0, 5]], "甲方", 0.88),
            ([[0, 10], [10, 10], [10, 15], [0, 15]], "乙方", 0.91),
        ],
        [0.1, 0.2],
    )
    mock_get.return_value = mock_engine

    from app.services.ai_review.ocr_engine import clear_engine_cache
    from app.services.ai_review.engines.rapidocr_engine import RapidOcrEngine

    clear_engine_cache()
    engine = RapidOcrEngine()
    result = engine.recognize(np.zeros((100, 100, 3), dtype=np.uint8))
    assert len(result.blocks) == 2
    assert result.engine == "rapidocr"


def test_get_ocr_engine_invalid() -> None:
    import pytest

    with pytest.raises(ValueError, match="不支持的 OCR 引擎"):
        get_ocr_engine("invalid")
