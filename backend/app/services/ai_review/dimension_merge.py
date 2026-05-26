# -*- coding: utf-8 -*-
"""多段合同审查 — 五维评分与清单覆盖合并。"""
from __future__ import annotations

from typing import Any

from app.services.ai_review.ai_engine import DimensionScore

_STATUS_ORDER = {"ok": 0, "degraded": 1, "failed": 2}
_COV_STATUS_ORDER = {"pass": 0, "unknown": 1, "fail": 2}


def _worst_status(a: str, b: str) -> str:
    return a if _STATUS_ORDER.get(a, 0) >= _STATUS_ORDER.get(b, 0) else b


def _worst_cov_status(a: str, b: str) -> str:
    return a if _COV_STATUS_ORDER.get(a, 0) >= _COV_STATUS_ORDER.get(b, 0) else b


def merge_dimension_scores(
    segment_results: list[list[DimensionScore]],
) -> list[DimensionScore]:
    """
    合并各分段的五维结果。
    status: failed > degraded > ok；score 取各段最大值。
    """
    if not segment_results:
        return []
    if len(segment_results) == 1:
        return list(segment_results[0])

    by_dim: dict[str, DimensionScore] = {}
    for seg_idx, dims in enumerate(segment_results):
        for ds in dims:
            existing = by_dim.get(ds.dimension)
            if existing is None:
                by_dim[ds.dimension] = ds.model_copy(deep=True)
                continue
            merged = existing.model_copy(deep=True)
            merged.status = _worst_status(existing.status, ds.status)
            merged.score = max(existing.score, ds.score)
            merged.summary = ds.summary if ds.status == "failed" else existing.summary
            if ds.error_type and _STATUS_ORDER.get(ds.status, 0) >= _STATUS_ORDER.get(
                existing.status, 0
            ):
                merged.error_type = ds.error_type
            merged.issues = existing.issues + ds.issues
            merged.checklist_coverage = _merge_checklist_coverage(
                existing.checklist_coverage,
                ds.checklist_coverage,
            )
            by_dim[ds.dimension] = merged

    order = ["compliance", "risk", "financial", "capability", "anomaly"]
    ordered = [by_dim[d] for d in order if d in by_dim]
    for d, v in by_dim.items():
        if d not in order:
            ordered.append(v)
    return ordered


def _merge_checklist_coverage(
    a: list[dict[str, Any]],
    b: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """按 item_id 合并 checklist_coverage，fail 优先。"""
    by_id: dict[Any, dict[str, Any]] = {}
    for item in a + b:
        if not isinstance(item, dict):
            continue
        iid = item.get("item_id")
        if iid is None:
            continue
        prev = by_id.get(iid)
        if prev is None:
            by_id[iid] = dict(item)
            continue
        st = _worst_cov_status(
            str(prev.get("status") or "unknown").lower(),
            str(item.get("status") or "unknown").lower(),
        )
        note = item.get("note") if st == str(item.get("status") or "").lower() else prev.get("note")
        by_id[iid] = {**prev, **item, "status": st, "note": note or prev.get("note")}
    return sorted(by_id.values(), key=lambda x: x.get("item_id", 0))


def per_segment_status_summary(
    segment_results: list[list[DimensionScore]],
) -> list[dict[str, Any]]:
    """各段维度状态摘要，供 completeness_detail。"""
    out: list[dict[str, Any]] = []
    for idx, dims in enumerate(segment_results):
        out.append(
            {
                "segment_index": idx,
                "dimensions": {d.dimension: d.status for d in dims},
            }
        )
    return out
