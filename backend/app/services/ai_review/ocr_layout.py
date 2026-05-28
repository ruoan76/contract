# -*- coding: utf-8 -*-
"""OCR 检测框版面重建 — 阅读顺序排序、行合并、段落空行。"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from app.services.ai_review.heading_utils import HEADING_LINE_START_RE

# 条款/章节行首（段落空行用）
_CLAUSE_HEADING_RE = HEADING_LINE_START_RE


@dataclass(frozen=True)
class _OcrBlock:
    cx: float
    cy: float
    height: float
    text: str


def _bbox_metrics(bbox: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    xs = [float(p[0]) for p in bbox]
    ys = [float(p[1]) for p in bbox]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    height = max(ys) - min(ys) if ys else 0.0
    return cx, cy, max(height, 1.0)


def _parse_blocks(
    results: Sequence[Any],
    *,
    min_conf: float,
) -> list[_OcrBlock]:
    blocks: list[_OcrBlock] = []
    for item in results:
        if len(item) < 3:
            continue
        bbox, text, conf = item[0], item[1], item[2]
        if not text or float(conf) < min_conf:
            continue
        cleaned = str(text).strip()
        if not cleaned:
            continue
        cx, cy, height = _bbox_metrics(bbox)
        blocks.append(_OcrBlock(cx=cx, cy=cy, height=height, text=cleaned))
    blocks.sort(key=lambda b: (b.cy, b.cx))
    return blocks


def ocr_results_to_raw_text(
    results: Sequence[Any],
    *,
    min_conf: float,
) -> str:
    """排版前：按检测顺序逐块换行（兼容旧行为）。"""
    parts: list[str] = []
    for item in results:
        if len(item) < 3:
            continue
        _bbox, text, conf = item[0], item[1], item[2]
        if not text or float(conf) < min_conf:
            continue
        parts.append(str(text).strip())
    return "\n".join(parts)


def layout_ocr_blocks(
    results: Sequence[Any],
    *,
    min_conf: float,
    line_merge_ratio: float = 0.55,
    paragraph_gap_ratio: float = 1.6,
) -> str:
    """
    将 EasyOCR 结果按版面重建为可读纯文本。

    1. bbox 中心从上到下、从左到右排序
    2. 垂直距离接近的块合并为同一行
    3. 行间距过大时插入段落空行；条款标题前强制空行
    """
    blocks = _parse_blocks(results, min_conf=min_conf)
    if not blocks:
        return ""

    avg_line_height = sum(b.height for b in blocks) / len(blocks)
    line_threshold = avg_line_height * line_merge_ratio
    paragraph_threshold = avg_line_height * paragraph_gap_ratio

    line_groups: list[list[_OcrBlock]] = [[blocks[0]]]
    line_cy = blocks[0].cy

    for block in blocks[1:]:
        if abs(block.cy - line_cy) <= line_threshold:
            line_groups[-1].append(block)
            line_cy = sum(b.cy for b in line_groups[-1]) / len(line_groups[-1])
        else:
            line_groups.append([block])
            line_cy = block.cy

    lines: list[tuple[float, str]] = []
    for group in line_groups:
        group.sort(key=lambda b: b.cx)
        cy = sum(b.cy for b in group) / len(group)
        lines.append((cy, " ".join(b.text for b in group)))

    output: list[str] = []
    prev_cy: float | None = None
    for cy, line_text in lines:
        if prev_cy is not None and (cy - prev_cy) > paragraph_threshold:
            if output and output[-1] != "":
                output.append("")
        if _CLAUSE_HEADING_RE.match(line_text.strip()) and output and output[-1] != "":
            output.append("")
        output.append(line_text)
        prev_cy = cy

    return "\n".join(output)
