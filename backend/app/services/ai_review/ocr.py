# -*- coding: utf-8 -*-
"""扫描件 PDF OCR — EasyOCR + PyMuPDF 渲染"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import fitz
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


def _render_matrix() -> fitz.Matrix:
    dpi = max(72, int(settings.AI_OCR_DPI))
    scale = dpi / 72
    return fitz.Matrix(scale, scale)


@lru_cache(maxsize=1)
def _get_reader():
    """懒加载 EasyOCR Reader（首次加载较慢）。"""
    import easyocr

    logger.info("正在加载 EasyOCR 模型 ch_sim+en …")
    return easyocr.Reader(["ch_sim", "en"], gpu=False)


def _preprocess_rgb(arr: np.ndarray) -> np.ndarray:
    """轻量预处理：灰度 + CLAHE 对比度增强，提升扫描件识别率。"""
    if not settings.AI_OCR_PREPROCESS:
        return arr
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV 不可用，跳过 OCR 预处理")
        return arr

    if arr.ndim == 3 and arr.shape[2] >= 3:
        gray = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2GRAY)
    elif arr.ndim == 2:
        gray = arr
    else:
        return arr

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)


def _ocr_pixmap(pix: fitz.Pixmap) -> str:
    """对 PyMuPDF 渲染页做 OCR，过滤低置信度块。"""
    reader = _get_reader()
    channels = pix.n
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, channels
    )
    if channels == 4:
        arr = arr[:, :, :3]

    arr = _preprocess_rgb(arr)
    min_conf = float(settings.AI_OCR_MIN_CONFIDENCE)
    results = reader.readtext(arr, detail=1, paragraph=False)

    parts: list[str] = []
    for item in results:
        if len(item) < 3:
            continue
        _bbox, text, conf = item[0], item[1], item[2]
        if not text or float(conf) < min_conf:
            continue
        parts.append(str(text).strip())
    return "\n".join(parts)


def ocr_pdf_page_indices(
    pdf_path: str | Path,
    page_indices: list[int],
    *,
    max_pages: Optional[int] = None,
) -> list[str]:
    """
    对指定页索引 OCR，返回与 page_indices 等长的文本列表。

    Raises:
        ValueError: 页数超过限制
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {pdf_path}")
    if not page_indices:
        return []

    limit = max_pages if max_pages is not None else settings.AI_OCR_MAX_PAGES
    doc = fitz.open(str(path))
    matrix = _render_matrix()
    try:
        page_count = len(doc)
        if page_count > limit:
            raise ValueError(
                f"PDF 共 {page_count} 页，超过 OCR 上限 {limit} 页，请拆分或调大 AI_OCR_MAX_PAGES"
            )

        page_texts: list[str] = []
        total = len(page_indices)
        for seq, idx in enumerate(page_indices):
            if idx < 0 or idx >= page_count:
                page_texts.append("")
                continue
            page = doc[idx]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            text = _ocr_pixmap(pix)
            page_texts.append(text)
            logger.info("OCR 进度: %s/%s 页 (pdf page %s)", seq + 1, total, idx + 1)
        return page_texts
    finally:
        doc.close()


def ocr_pdf_pages(
    pdf_path: str | Path,
    *,
    max_pages: Optional[int] = None,
) -> list[str]:
    """
    对 PDF 每页渲染为图并 OCR，返回每页文本列表。

    Raises:
        ValueError: 页数超过限制
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {pdf_path}")

    limit = max_pages if max_pages is not None else settings.AI_OCR_MAX_PAGES
    doc = fitz.open(str(path))
    try:
        page_count = len(doc)
        if page_count > limit:
            raise ValueError(
                f"PDF 共 {page_count} 页，超过 OCR 上限 {limit} 页，请拆分或调大 AI_OCR_MAX_PAGES"
            )
        indices = list(range(page_count))
    finally:
        doc.close()

    return ocr_pdf_page_indices(path, indices, max_pages=limit)
