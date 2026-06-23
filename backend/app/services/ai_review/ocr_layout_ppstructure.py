# -*- coding: utf-8 -*-
"""PP-Structure 版面分析（可选依赖，未安装时回退 heuristic）。"""
from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np

from app.services.ai_review.ocr_layout import layout_ocr_blocks_with_meta, LayoutResult

logger = logging.getLogger(__name__)


def layout_with_ppstructure(
    image: np.ndarray,
    easy_format: Sequence[Any],
    *,
    min_conf: float,
) -> LayoutResult | None:
    """
    尝试 PaddleOCR 结构化版面；失败或未安装时返回 None，由调用方回退 heuristic。
    """
    try:
        from paddleocr import PPStructure  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("未安装 paddleocr，ppstructure 回退 heuristic")
        return None

    try:
        engine = PPStructure(show_log=False, lang="ch")
        result = engine(image)
    except Exception as exc:
        logger.warning("PP-Structure 版面分析失败，回退 heuristic: %s", exc)
        return None

    if not result:
        return None

    parts: list[str] = []
    for region in result:
        if not isinstance(region, dict):
            continue
        res = region.get("res")
        if isinstance(res, list):
            for line in res:
                if isinstance(line, dict) and line.get("text"):
                    parts.append(str(line["text"]).strip())
                elif isinstance(line, (list, tuple)) and len(line) >= 2:
                    parts.append(str(line[1]).strip())
        elif isinstance(res, dict) and res.get("html"):
            continue
        elif region.get("type") == "table":
            continue

    if parts:
        text = "\n".join(p for p in parts if p)
        base = layout_ocr_blocks_with_meta(easy_format, min_conf=min_conf)
        if text.strip():
            merged = text if not base.text.strip() else f"{text}\n\n{base.text}"
            return LayoutResult(
                text=merged.strip(),
                column_count=base.column_count,
                layout_suspect=base.layout_suspect,
                layout_quality_score=base.layout_quality_score,
                lines=base.lines,
            )
    return layout_ocr_blocks_with_meta(easy_format, min_conf=min_conf)
