# -*- coding: utf-8 -*-
"""OCR 检测框版面重建 — 分栏、阅读顺序、行合并、段落空行。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from app.core.config import settings
from app.services.ai_review.heading_utils import HEADING_LINE_START_RE

_CLAUSE_HEADING_RE = HEADING_LINE_START_RE
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ASCII_RE = re.compile(r"[A-Za-z0-9]")

# 法律序言常见逆序信号（排版可疑检测）
_LEGAL_REF_RE = re.compile(r"根据《[^》]+》")
_CONSENSUS_RE = re.compile(r"协商一致")


@dataclass(frozen=True)
class _OcrBlock:
    cx: float
    cy: float
    height: float
    width: float
    text: str
    bbox: tuple[tuple[float, float], ...]


@dataclass
class LayoutLine:
    """排版后的单行（含合并 bbox，供 DocumentJSON）。"""

    text: str
    cy: float
    min_cx: float
    bbox: list[list[float]] | None = None


@dataclass
class LayoutResult:
    text: str
    column_count: int = 1
    layout_suspect: bool = False
    layout_quality_score: float = 1.0
    lines: list[LayoutLine] = field(default_factory=list)


def _bbox_metrics(bbox: Sequence[Sequence[float]]) -> tuple[float, float, float, float, tuple[tuple[float, float], ...]]:
    xs = [float(p[0]) for p in bbox]
    ys = [float(p[1]) for p in bbox]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    height = max(ys) - min(ys) if ys else 0.0
    width = max(xs) - min(xs) if xs else 0.0
    poly = tuple((float(p[0]), float(p[1])) for p in bbox)
    return cx, cy, max(height, 1.0), max(width, 1.0), poly


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
        cx, cy, height, width, poly = _bbox_metrics(bbox)
        blocks.append(
            _OcrBlock(cx=cx, cy=cy, height=height, width=width, text=cleaned, bbox=poly)
        )
    return blocks


def _merge_bbox(blocks: Sequence[_OcrBlock]) -> list[list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for b in blocks:
        for x, y in b.bbox:
            xs.append(x)
            ys.append(y)
    if not xs:
        return []
    return [
        [min(xs), min(ys)],
        [max(xs), min(ys)],
        [max(xs), max(ys)],
        [min(xs), max(ys)],
    ]


def _needs_space_between(prev: _OcrBlock, cur: _OcrBlock) -> bool:
    gap = cur.cx - prev.cx
    avg_h = (prev.height + cur.height) / 2
    if gap > avg_h * 0.85:
        return True
    prev_t, cur_t = prev.text, cur.text
    if _ASCII_RE.search(prev_t) or _ASCII_RE.search(cur_t):
        if prev_t and cur_t:
            if prev_t[-1].isalnum() and cur_t[0].isalnum():
                return True
            if prev_t[-1] in ",，;；:：" or cur_t[0] in "（(":
                return False
        return bool(_ASCII_RE.search(prev_t[-1:]) or _ASCII_RE.search(cur_t[:1]))
    return False


def _join_line_text(blocks: list[_OcrBlock]) -> str:
    ordered = sorted(blocks, key=lambda b: b.cx)
    if not ordered:
        return ""
    parts = [ordered[0].text]
    for i in range(1, len(ordered)):
        prev, cur = ordered[i - 1], ordered[i]
        if _needs_space_between(prev, cur):
            parts.append(" ")
        parts.append(cur.text)
    return "".join(parts)


def _split_columns(
    blocks: list[_OcrBlock],
    *,
    column_gap_ratio: float,
) -> list[list[_OcrBlock]]:
    if len(blocks) < 3:
        return [blocks]
    cxs = sorted(b.cx for b in blocks)
    span = cxs[-1] - cxs[0]
    if span <= 1:
        return [blocks]

    best_gap = 0.0
    split_at: float | None = None
    for i in range(len(cxs) - 1):
        gap = cxs[i + 1] - cxs[i]
        if gap > best_gap:
            best_gap = gap
            split_at = (cxs[i] + cxs[i + 1]) / 2

    min_gap = span * column_gap_ratio
    if split_at is None or best_gap < min_gap:
        return [blocks]

    left = [b for b in blocks if b.cx < split_at]
    right = [b for b in blocks if b.cx >= split_at]
    if not left or not right:
        return [blocks]
    return [left, right]


def _group_lines_in_column(
    blocks: list[_OcrBlock],
    *,
    line_threshold: float,
) -> list[list[_OcrBlock]]:
    if not blocks:
        return []
    ordered = sorted(blocks, key=lambda b: (b.cy, b.cx))
    groups: list[list[_OcrBlock]] = [[ordered[0]]]
    line_cy = ordered[0].cy
    for block in ordered[1:]:
        if abs(block.cy - line_cy) <= line_threshold:
            groups[-1].append(block)
            line_cy = sum(b.cy for b in groups[-1]) / len(groups[-1])
        else:
            groups.append([block])
            line_cy = block.cy
    return groups


def _lines_from_groups(
    line_groups: list[list[_OcrBlock]],
) -> list[LayoutLine]:
    lines: list[LayoutLine] = []
    for group in line_groups:
        cy = sum(b.cy for b in group) / len(group)
        min_cx = min(b.cx for b in group)
        text = _join_line_text(group)
        lines.append(
            LayoutLine(
                text=text,
                cy=cy,
                min_cx=min_cx,
                bbox=_merge_bbox(group) or None,
            )
        )
    lines.sort(key=lambda ln: (ln.cy, ln.min_cx))
    return lines


def _merge_continuation_lines(
    lines: list[LayoutLine],
    *,
    paragraph_threshold: float,
    indent_ratio: float = 0.35,
) -> list[LayoutLine]:
    if len(lines) < 2:
        return lines

    merged: list[LayoutLine] = [lines[0]]
    for line in lines[1:]:
        prev = merged[-1]
        cy_delta = line.cy - prev.cy
        if cy_delta > paragraph_threshold:
            merged.append(line)
            continue
        if _CLAUSE_HEADING_RE.match(line.text.strip()):
            merged.append(line)
            continue
        avg_h = paragraph_threshold / 1.6
        indent = line.min_cx - prev.min_cx
        if cy_delta <= paragraph_threshold and indent > avg_h * indent_ratio:
            prev.text = prev.text.rstrip() + line.text.lstrip()
            prev.cy = (prev.cy + line.cy) / 2
            if line.bbox and prev.bbox:
                prev.bbox = _merge_bbox_from_polys(prev.bbox, line.bbox)
            continue
        merged.append(line)
    return merged


def _merge_bbox_from_polys(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    xs = [p[0] for p in a + b]
    ys = [p[1] for p in a + b]
    return [
        [min(xs), min(ys)],
        [max(xs), min(ys)],
        [max(xs), max(ys)],
        [min(xs), max(ys)],
    ]


def _lines_to_output_text(
    lines: list[LayoutLine],
    *,
    paragraph_threshold: float,
) -> str:
    output: list[str] = []
    prev_cy: float | None = None
    for line in lines:
        if prev_cy is not None and (line.cy - prev_cy) > paragraph_threshold:
            if output and output[-1] != "":
                output.append("")
        if _CLAUSE_HEADING_RE.match(line.text.strip()) and output and output[-1] != "":
            output.append("")
        output.append(line.text)
        prev_cy = line.cy
    return "\n".join(output)


def detect_layout_suspect(text: str) -> bool:
    """启发式：法律援引句与「协商一致」等语序颠倒。"""
    if not text or len(text) < 20:
        return False
    ref = _LEGAL_REF_RE.search(text)
    consensus = _CONSENSUS_RE.search(text)
    if ref and consensus and consensus.start() < ref.start():
        return True
    return False


def compute_layout_quality_score(
    text: str,
    *,
    column_count: int,
    block_count: int,
) -> float:
    score = 1.0
    if detect_layout_suspect(text):
        score -= 0.45
    if column_count >= 2 and block_count > 80:
        score -= 0.05
    if re.search(r"[\u4e00-\u9fff]\s+[\u4e00-\u9fff]", text):
        score -= 0.08
    return max(0.0, min(1.0, score))


def layout_ocr_blocks_with_meta(
    results: Sequence[Any],
    *,
    min_conf: float,
    line_merge_ratio: float | None = None,
    paragraph_gap_ratio: float | None = None,
    column_gap_ratio: float | None = None,
) -> LayoutResult:
    """
    分栏 → 行合并 → 续行拼接 → 段落空行，返回排版文本与质量元数据。
    """
    blocks = _parse_blocks(results, min_conf=min_conf)
    if not blocks:
        return LayoutResult(text="")

    line_merge_ratio = line_merge_ratio if line_merge_ratio is not None else float(
        settings.AI_OCR_LINE_MERGE_RATIO
    )
    paragraph_gap_ratio = paragraph_gap_ratio if paragraph_gap_ratio is not None else float(
        settings.AI_OCR_PARAGRAPH_GAP_RATIO
    )
    column_gap_ratio = column_gap_ratio if column_gap_ratio is not None else float(
        settings.AI_OCR_COLUMN_GAP_RATIO
    )

    avg_line_height = sum(b.height for b in blocks) / len(blocks)
    line_threshold = avg_line_height * line_merge_ratio
    paragraph_threshold = avg_line_height * paragraph_gap_ratio

    columns = _split_columns(blocks, column_gap_ratio=column_gap_ratio)
    all_lines: list[LayoutLine] = []
    for col_blocks in columns:
        groups = _group_lines_in_column(col_blocks, line_threshold=line_threshold)
        all_lines.extend(_lines_from_groups(groups))

    all_lines.sort(key=lambda ln: (ln.cy, ln.min_cx))
    all_lines = _merge_continuation_lines(
        all_lines,
        paragraph_threshold=paragraph_threshold,
    )
    text = _lines_to_output_text(all_lines, paragraph_threshold=paragraph_threshold)
    suspect = detect_layout_suspect(text)
    quality = compute_layout_quality_score(
        text,
        column_count=len(columns),
        block_count=len(blocks),
    )
    if suspect:
        quality = min(quality, 0.5)

    return LayoutResult(
        text=text,
        column_count=len(columns),
        layout_suspect=suspect,
        layout_quality_score=quality,
        lines=all_lines,
    )


def layout_ocr_blocks(
    results: Sequence[Any],
    *,
    min_conf: float,
    line_merge_ratio: float | None = None,
    paragraph_gap_ratio: float | None = None,
) -> str:
    """将 OCR 结果按版面重建为可读纯文本（兼容旧调用）。"""
    return layout_ocr_blocks_with_meta(
        results,
        min_conf=min_conf,
        line_merge_ratio=line_merge_ratio,
        paragraph_gap_ratio=paragraph_gap_ratio,
    ).text


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
