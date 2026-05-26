# -*- coding: utf-8
"""长合同分段 — Map-Reduce 前置。"""
from __future__ import annotations

from app.core.config import settings
from app.services.ai_review.clause_parser import Clause


def should_segment(text: str) -> bool:
    return len((text or "").strip()) > settings.AI_REVIEW_SEGMENT_THRESHOLD


def segment_if_needed(
    text: str,
    clauses: list[Clause],
) -> list[tuple[str, list[Clause]]]:
    """
    返回 [(segment_text, segment_clauses), ...]。
    未超阈值时返回整份 [(text, clauses)]。
    """
    text = (text or "").strip()
    if not should_segment(text):
        return [(text, clauses)]

    max_size = settings.AI_REVIEW_SEGMENT_SIZE
    if clauses and len(clauses) > 1:
        return _segment_by_clauses(text, clauses, max_size)
    return _segment_by_window(text, max_size)


def _segment_by_clauses(
    text: str,
    clauses: list[Clause],
    max_size: int,
) -> list[tuple[str, list[Clause]]]:
    segments: list[tuple[str, list[Clause]]] = []
    batch: list[Clause] = []
    batch_len = 0

    for clause in clauses:
        clen = len(clause.content or "")
        if batch and batch_len + clen > max_size:
            seg_text = "\n\n".join(c.content for c in batch)
            segments.append((seg_text, list(batch)))
            batch = [clause]
            batch_len = clen
        else:
            batch.append(clause)
            batch_len += clen

    if batch:
        seg_text = "\n\n".join(c.content for c in batch)
        segments.append((seg_text, batch))

    return segments or [(text, clauses)]


def _segment_by_window(text: str, max_size: int) -> list[tuple[str, list[Clause]]]:
    overlap = 500
    segments: list[tuple[str, list[Clause]]] = []
    start = 0
    while start < len(text):
        end = min(start + max_size, len(text))
        chunk = text[start:end]
        segments.append((chunk, []))
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return segments
