# -*- coding: utf-8 -*-
"""EasyOCR 引擎实现。"""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from app.core.config import settings
from app.services.ai_review.ocr_engine import OcrBlock, OcrPageResult, _page_meta

logger = logging.getLogger(__name__)


def _use_mps() -> bool:
    if not settings.AI_OCR_USE_MPS:
        return False
    try:
        import torch

        return bool(torch.backends.mps.is_available())
    except Exception:
        return False


@lru_cache(maxsize=1)
def _get_reader():
    import easyocr

    use_gpu = _use_mps()
    logger.info("正在加载 EasyOCR ch_sim+en（gpu=%s）…", use_gpu)
    return easyocr.Reader(["ch_sim", "en"], gpu=use_gpu)


class EasyOcrEngine:
    name = "easyocr"

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        reader = _get_reader()
        min_conf = float(settings.AI_OCR_MIN_CONFIDENCE)
        results = reader.readtext(image, detail=1, paragraph=False)
        blocks: list[OcrBlock] = []
        for item in results:
            if len(item) < 3:
                continue
            bbox, text, conf = item[0], item[1], item[2]
            if not text or float(conf) < min_conf:
                continue
            blocks.append(
                OcrBlock(
                    bbox=[[float(p[0]), float(p[1])] for p in bbox],
                    text=str(text).strip(),
                    confidence=float(conf),
                )
            )
        return _page_meta(blocks, self.name)
