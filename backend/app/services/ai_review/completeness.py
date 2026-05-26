# -*- coding: utf-8 -*-
"""审查完整度计算。"""
from __future__ import annotations

from typing import Any


def compute_completeness(
    *,
    s2_status: str,
    dimension_statuses: list[str],
    pipeline_exception: bool = False,
) -> tuple[str, dict[str, Any]]:
    """
    返回 (review_completeness, completeness_detail)。
    s2_status: ok | heuristic | failed
    dimension_statuses: 每维 ok | degraded | failed
    """
    detail: dict[str, Any] = {
        "s2_status": s2_status,
        "dimension_failures": [],
    }

    if pipeline_exception:
        detail["reason"] = "pipeline_exception"
        return "failed", detail

    dim_failures = [d for d in dimension_statuses if d in ("failed", "degraded")]
    detail["dimension_failures"] = dim_failures

    if any(d == "failed" for d in dimension_statuses):
        return "partial", detail

    if s2_status in ("heuristic", "failed"):
        return "partial", detail

    if any(d == "degraded" for d in dimension_statuses):
        return "partial", detail

    return "full", detail


def summarize_checklist_coverage(
    coverage_lists: list[list[dict[str, Any]]],
) -> dict[str, int]:
    """汇总各维度 checklist_coverage。"""
    total = pass_n = fail_n = unknown_n = 0
    for cov in coverage_lists:
        for item in cov:
            total += 1
            st = (item.get("status") or "unknown").lower()
            if st == "pass":
                pass_n += 1
            elif st == "fail":
                fail_n += 1
            else:
                unknown_n += 1
    return {"total": total, "pass": pass_n, "fail": fail_n, "unknown": unknown_n}
