# -*- coding: utf-8 -*-
"""扫描件 PDF OCR — 多引擎 + PyMuPDF 渲染"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

import fitz
import numpy as np

from app.core.config import settings
from app.services.ai_review.ocr_engine import OcrPageResult, get_ocr_engine
from app.services.ai_review.ocr_layout import (
    LayoutResult,
    layout_ocr_blocks_with_meta,
    ocr_results_to_raw_text,
)
from app.services.ai_review.ocr_preprocess import preprocess_for_ocr
from app.services.ai_review.vlm_page_fallback import maybe_correct_page_text

logger = logging.getLogger(__name__)


def _render_matrix() -> fitz.Matrix:
    dpi = max(72, int(settings.AI_OCR_DPI))
    scale = dpi / 72
    return fitz.Matrix(scale, scale)


def _pixmap_to_rgb_array(pix: fitz.Pixmap) -> np.ndarray:
    channels = pix.n
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, channels
    )
    if channels == 4:
        arr = arr[:, :, :3]
    return arr


def _layout_page(
    image: np.ndarray,
    easy_format: list[tuple[Any, str, float]],
    *,
    min_conf: float,
) -> LayoutResult:
    """按配置选择 heuristic 或 ppstructure 排版。"""
    mode = (settings.AI_OCR_LAYOUT or "heuristic").strip().lower()
    if mode == "ppstructure":
        from app.services.ai_review.ocr_layout_ppstructure import layout_with_ppstructure

        pp_result = layout_with_ppstructure(image, easy_format, min_conf=min_conf)
        if pp_result is not None and pp_result.text.strip():
            return pp_result
        logger.debug("ppstructure 不可用或结果为空，使用 heuristic")
    return layout_ocr_blocks_with_meta(easy_format, min_conf=min_conf)


def _layout_result_to_meta(
    layout: LayoutResult,
    page_result: OcrPageResult,
    *,
    llm_corrected: bool = False,
) -> dict[str, Any]:
    layout_lines = [
        {"text": ln.text, "bbox": ln.bbox}
        for ln in layout.lines
        if ln.text.strip()
    ]
    needs_review = page_result.needs_review or layout.layout_suspect
    return {
        "avg_confidence": page_result.avg_confidence,
        "needs_review": needs_review,
        "engine": page_result.engine,
        "column_count": layout.column_count,
        "layout_suspect": layout.layout_suspect,
        "layout_quality_score": layout.layout_quality_score,
        "layout_lines": layout_lines,
        "llm_corrected": llm_corrected,
    }


def _recognize_page(pix: fitz.Pixmap) -> tuple[str, str, OcrPageResult, dict[str, Any]]:
    """OCR 单页，返回 (排版后, 排版前, 页元数据, 扩展 meta)。"""
    engine = get_ocr_engine()
    arr = preprocess_for_ocr(_pixmap_to_rgb_array(pix))
    page_result = engine.recognize(arr)
    min_conf = float(settings.AI_OCR_MIN_CONFIDENCE)
    easy_format = page_result.to_easyocr_format()
    layout = _layout_page(arr, easy_format, min_conf=min_conf)
    raw = ocr_results_to_raw_text(easy_format, min_conf=min_conf)
    meta = _layout_result_to_meta(layout, page_result)
    return layout.text, raw, page_result, meta


async def _ocr_pixmap_async(pix: fitz.Pixmap) -> tuple[str, str, OcrPageResult, dict[str, Any]]:
    loop = asyncio.get_event_loop()
    layout_text, raw_text, page_result, meta = await loop.run_in_executor(
        None, _recognize_page, pix
    )
    should_correct = settings.AI_OCR_VLM_FALLBACK and (
        meta.get("needs_review")
        or meta.get("layout_suspect")
    )
    if should_correct:
        png_bytes = pix.tobytes("png")
        corrected, changed = await maybe_correct_page_text(
            layout_text,
            avg_confidence=page_result.avg_confidence,
            image_bytes=png_bytes,
            layout_suspect=bool(meta.get("layout_suspect")),
        )
        if changed:
            layout_text = corrected
            meta["llm_corrected"] = True
            meta["layout_suspect"] = False
    return layout_text, raw_text, page_result, meta


def _ocr_pixmap(pix: fitz.Pixmap) -> tuple[str, str]:
    """同步 OCR（兼容旧调用）。"""
    layout, raw, _meta, _extra = _recognize_page(pix)
    return layout, raw


async def ocr_pdf_page_indices_async(
    pdf_path: str | Path,
    page_indices: list[int],
    *,
    max_pages: Optional[int] = None,
    raw_pages_out: Optional[list[str]] = None,
    page_meta_out: Optional[list[dict]] = None,
) -> list[str]:
    """异步 OCR 指定页（含排版可疑时的 LLM 兜底）。"""
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
                if raw_pages_out is not None:
                    raw_pages_out.append("")
                if page_meta_out is not None:
                    page_meta_out.append({})
                continue
            page = doc[idx]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            layout_text, raw_text, page_result, extra = await _ocr_pixmap_async(pix)
            page_texts.append(layout_text)
            if raw_pages_out is not None:
                raw_pages_out.append(raw_text)
            if page_meta_out is not None:
                page_meta_out.append(extra)
            logger.info(
                "OCR 进度: %s/%s 页 (pdf page %s, engine=%s, conf=%.2f, suspect=%s)",
                seq + 1,
                total,
                idx + 1,
                page_result.engine,
                page_result.avg_confidence,
                extra.get("layout_suspect"),
            )
        return page_texts
    finally:
        doc.close()


def ocr_pdf_page_indices(
    pdf_path: str | Path,
    page_indices: list[int],
    *,
    max_pages: Optional[int] = None,
    raw_pages_out: Optional[list[str]] = None,
    page_meta_out: Optional[list[dict]] = None,
) -> list[str]:
    """对指定页索引 OCR（同步，无 LLM 兜底）。"""
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
                if raw_pages_out is not None:
                    raw_pages_out.append("")
                if page_meta_out is not None:
                    page_meta_out.append({})
                continue
            page = doc[idx]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            layout_text, raw_text, page_result, extra = _recognize_page(pix)
            page_texts.append(layout_text)
            if raw_pages_out is not None:
                raw_pages_out.append(raw_text)
            if page_meta_out is not None:
                page_meta_out.append(extra)
            logger.info(
                "OCR 进度: %s/%s 页 (pdf page %s, engine=%s, conf=%.2f)",
                seq + 1,
                total,
                idx + 1,
                page_result.engine,
                page_result.avg_confidence,
            )
        return page_texts
    finally:
        doc.close()


async def ocr_pdf_pages_async(
    pdf_path: str | Path,
    *,
    max_pages: Optional[int] = None,
    raw_pages_out: Optional[list[str]] = None,
    page_meta_out: Optional[list[dict]] = None,
) -> list[str]:
    """对 PDF 每页异步 OCR。"""
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

    return await ocr_pdf_page_indices_async(
        path,
        indices,
        max_pages=limit,
        raw_pages_out=raw_pages_out,
        page_meta_out=page_meta_out,
    )


def ocr_pdf_pages(
    pdf_path: str | Path,
    *,
    max_pages: Optional[int] = None,
    raw_pages_out: Optional[list[str]] = None,
    page_meta_out: Optional[list[dict]] = None,
) -> list[str]:
    """对 PDF 每页渲染为图并 OCR，返回每页文本列表。"""
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

    return ocr_pdf_page_indices(
        path,
        indices,
        max_pages=limit,
        raw_pages_out=raw_pages_out,
        page_meta_out=page_meta_out,
    )


def ocr_image_array(image: np.ndarray, engine_name: str | None = None) -> OcrPageResult:
    """对 numpy 图像直接 OCR（基准测试用）。"""
    from app.services.ai_review.ocr_engine import get_ocr_engine

    engine = get_ocr_engine(engine_name)
    processed = preprocess_for_ocr(image)
    return engine.recognize(processed)
