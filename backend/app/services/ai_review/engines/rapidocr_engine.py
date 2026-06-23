# -*- coding: utf-8 -*-
"""RapidOCR ONNX 引擎实现。"""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from app.core.config import settings
from app.services.ai_review.ocr_engine import OcrBlock, OcrPageResult, _page_meta

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_rapidocr():
    from rapidocr_onnxruntime import RapidOCR

    logger.info("正在加载 RapidOCR ONNX 模型…")
    return RapidOCR()


class RapidOcrEngine:
    name = "rapidocr"

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        engine = _get_rapidocr()
        min_conf = float(settings.AI_OCR_MIN_CONFIDENCE)
        result, _elapse = engine(image)
        blocks: list[OcrBlock] = []
        if not result:
            return _page_meta(blocks, self.name)

        for item in result:
            if len(item) < 3:
                continue
            bbox, text, score = item[0], item[1], item[2]
            conf = float(score)
            if not text or conf < min_conf:
                continue
            poly = [[float(p[0]), float(p[1])] for p in bbox]
            blocks.append(OcrBlock(bbox=poly, text=str(text).strip(), confidence=conf))
        return _page_meta(blocks, self.name)
