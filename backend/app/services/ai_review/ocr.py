# -*- coding: utf-8 -*-
"""扫描件 PDF OCR — EasyOCR + PyMuPDF 渲染"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import fitz

from app.core.config import settings

logger = logging.getLogger(__name__)

# 渲染 DPI（150–200 兼顾速度与识别率）
_OCR_RENDER_DPI = 175
_OCR_MATRIX = fitz.Matrix(_OCR_RENDER_DPI / 72, _OCR_RENDER_DPI / 72)


@lru_cache(maxsize=1)
def _get_reader():
    """懒加载 EasyOCR Reader（首次加载较慢）。"""
    import easyocr

    logger.info("正在加载 EasyOCR 模型 ch_sim+en …")
    return easyocr.Reader(["ch_sim", "en"], gpu=False)


def _ocr_pixmap(pix: fitz.Pixmap) -> str:
    """对 PyMuPDF 渲染页做 OCR。"""
    import numpy as np

    reader = _get_reader()
    channels = pix.n
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, channels
    )
    if channels == 4:
        arr = arr[:, :, :3]
    results = reader.readtext(arr)
    parts: list[str] = []
    for item in results:
        if len(item) >= 2 and item[1]:
            parts.append(str(item[1]).strip())
    return "\n".join(parts)


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
        page_texts: list[str] = []
        for idx in range(page_count):
            page = doc[idx]
            pix = page.get_pixmap(matrix=_OCR_MATRIX, alpha=False)
            text = _ocr_pixmap(pix)
            page_texts.append(text)
            logger.info("OCR 进度: %s/%s 页", idx + 1, page_count)
        return page_texts
    finally:
        doc.close()
