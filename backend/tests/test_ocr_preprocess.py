# -*- coding: utf-8 -*-
"""OCR 预处理单测。"""
from __future__ import annotations

import numpy as np

from app.services.ai_review.ocr_preprocess import preprocess_for_ocr


def test_preprocess_returns_rgb() -> None:
    gray = np.full((64, 64), 128, dtype=np.uint8)
    out = preprocess_for_ocr(gray)
    assert out.ndim == 3
    assert out.shape[2] == 3


def test_preprocess_rgb_passthrough_shape() -> None:
    rgb = np.zeros((32, 32, 3), dtype=np.uint8)
    out = preprocess_for_ocr(rgb)
    assert out.shape == rgb.shape
