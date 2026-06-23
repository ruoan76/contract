# -*- coding: utf-8 -*-
"""OCR 图像预处理 — CLAHE、倾斜校正、自适应二值化。"""
from __future__ import annotations

import logging

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


def preprocess_for_ocr(arr: np.ndarray) -> np.ndarray:
    """扫描件预处理流水线，输出 RGB uint8 数组。"""
    if not settings.AI_OCR_PREPROCESS:
        return _ensure_rgb(arr)

    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV 不可用，跳过 OCR 预处理")
        return _ensure_rgb(arr)

    rgb = _ensure_rgb(arr)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    if settings.AI_OCR_DESKEW:
        gray = _deskew(gray, cv2)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    if settings.AI_OCR_ADAPTIVE_THRESHOLD:
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        enhanced = binary

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)


def _ensure_rgb(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 2:
        import cv2

        return cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
    if arr.shape[2] >= 3:
        return arr[:, :, :3]
    return arr


def _deskew(gray: np.ndarray, cv2) -> np.ndarray:
    """轻量倾斜校正：基于轮廓最小外接矩形。"""
    try:
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        coords = cv2.findNonZero(255 - thresh)
        if coords is None:
            return gray
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5 or abs(angle) > 15:
            return gray
        h, w = gray.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(
            gray,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception as exc:
        logger.debug("倾斜校正跳过: %s", exc)
        return gray
