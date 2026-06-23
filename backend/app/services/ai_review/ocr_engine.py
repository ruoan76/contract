# -*- coding: utf-8 -*-
"""OCR 引擎抽象与工厂。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol, Sequence

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OcrBlock:
    bbox: list[list[float]]
    text: str
    confidence: float


@dataclass
class OcrPageResult:
    blocks: list[OcrBlock] = field(default_factory=list)
    avg_confidence: float = 0.0
    needs_review: bool = False
    engine: str = ""

    def to_easyocr_format(self) -> list[tuple[Any, str, float]]:
        """转换为 ocr_layout 兼容格式 (bbox, text, conf)。"""
        return [(b.bbox, b.text, b.confidence) for b in self.blocks]


class OcrEngine(Protocol):
    name: str

    def recognize(self, image: np.ndarray) -> OcrPageResult:
        """识别单页图像。"""


def _page_meta(blocks: Sequence[OcrBlock], engine: str) -> OcrPageResult:
    if not blocks:
        return OcrPageResult(blocks=[], avg_confidence=0.0, needs_review=True, engine=engine)
    confs = [b.confidence for b in blocks]
    avg = sum(confs) / len(confs)
    min_conf = float(settings.AI_OCR_MIN_CONFIDENCE)
    review_threshold = float(settings.AI_OCR_NEEDS_REVIEW_CONF)
    low_ratio = sum(1 for c in confs if c < min_conf) / len(confs)
    needs_review = avg < review_threshold or low_ratio > 0.35
    return OcrPageResult(
        blocks=list(blocks),
        avg_confidence=avg,
        needs_review=needs_review,
        engine=engine,
    )


@lru_cache(maxsize=2)
def _load_engine(name: str) -> OcrEngine:
    normalized = (name or "rapidocr").lower().strip()
    if normalized == "easyocr":
        from app.services.ai_review.engines.easyocr_engine import EasyOcrEngine

        return EasyOcrEngine()
    if normalized == "rapidocr":
        from app.services.ai_review.engines.rapidocr_engine import RapidOcrEngine

        return RapidOcrEngine()
    raise ValueError(f"不支持的 OCR 引擎: {name}")


def get_ocr_engine(name: str | None = None) -> OcrEngine:
    """按配置返回 OCR 引擎实例。"""
    engine_name = name or settings.AI_OCR_ENGINE
    return _load_engine(engine_name)


def clear_engine_cache() -> None:
    _load_engine.cache_clear()
