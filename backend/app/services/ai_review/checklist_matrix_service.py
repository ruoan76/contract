# -*- coding: utf-8 -*-
"""审查清单矩阵 — 种子 + checklist_coverage + issues 聚合。"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from app.services.ai_review.seed_store import get_review_checklists

_COV_TO_CONCLUSION = {
    "pass": "pass",
    "fail": "fail",
    "unknown": "unknown",
    "attention": "attention",
}

_RISK_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _extract_coverage_map(summary: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """从 summary.dimensions 合并 checklist_coverage。"""
    cov_map: dict[int, dict[str, Any]] = {}
    for dim in summary.get("dimensions") or []:
        if not isinstance(dim, dict):
            continue
        for item in dim.get("checklist_coverage") or []:
            if not isinstance(item, dict):
                continue
            iid = item.get("item_id")
            if iid is None:
                continue
            try:
                key = int(iid)
            except (TypeError, ValueError):
                continue
            prev = cov_map.get(key)
            if prev is None:
                cov_map[key] = dict(item)
            else:
                st_new = str(item.get("status") or "unknown").lower()
                st_old = str(prev.get("status") or "unknown").lower()
                rank = {"pass": 0, "unknown": 1, "fail": 2}
                if rank.get(st_new, 0) >= rank.get(st_old, 0):
                    cov_map[key] = {**prev, **item}
    return cov_map


def _issues_by_checklist_id(clause_reviews: list[Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in clause_reviews:
        if not isinstance(row, dict):
            continue
        cid = row.get("checklist_item_id")
        if cid is None:
            continue
        try:
            key = int(cid)
        except (TypeError, ValueError):
            continue
        existing = out.get(key)
        if existing is None or _RISK_ORDER.get(row.get("risk_level"), 0) > _RISK_ORDER.get(
            existing.get("risk_level"), 0
        ):
            out[key] = row
    return out


def _issues_by_gate(clause_reviews: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """按 gate_id 分组 issue（无 checklist_item_id 时回退匹配）。"""
    by_gate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in clause_reviews:
        if not isinstance(row, dict) or row.get("checklist_item_id") is not None:
            continue
        gid = row.get("gate_id")
        if gid:
            by_gate[str(gid)].append(row)
    for gid in by_gate:
        by_gate[gid].sort(
            key=lambda x: _RISK_ORDER.get(str(x.get("risk_level") or "").lower(), 0),
            reverse=True,
        )
    return by_gate


def _category_keywords(category: str) -> list[str]:
    """从种子 category 提取匹配关键词。"""
    parts = re.split(r"[-—/]", category or "")
    return [p.strip() for p in parts if p.strip()]


def _pick_issue_for_seed(
    seed: dict[str, Any],
    issue_map: dict[int, dict[str, Any]],
    gate_issues: dict[str, list[dict[str, Any]]],
    category_high_issues: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """为清单项挑选最相关 issue。"""
    iid = seed.get("id")
    if iid is not None:
        try:
            hit = issue_map.get(int(iid))
            if hit:
                return hit
        except (TypeError, ValueError):
            pass
    gate_id = seed.get("gate_id")
    if gate_id and gate_id in gate_issues:
        return gate_issues[gate_id][0]
    cat = str(seed.get("category") or "")
    if cat in category_high_issues:
        return category_high_issues[cat][0]
    return None


def build_checklist_matrix(
    summary: dict[str, Any] | None,
    clause_reviews: list[Any] | None,
) -> dict[str, Any]:
    """
    构建清单矩阵：按 category 分组，每项含结论、风险、AI 建议、证据。
    """
    summary = summary or {}
    clause_reviews = clause_reviews or []
    cov_map = _extract_coverage_map(summary)
    issue_map = _issues_by_checklist_id(clause_reviews)
    gate_issues = _issues_by_gate(clause_reviews)

    try:
        seed_items = get_review_checklists().get("items", [])
    except Exception:
        seed_items = []

    category_high_issues: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in clause_reviews:
        if not isinstance(row, dict):
            continue
        rl = str(row.get("risk_level") or "").lower()
        if rl not in ("high", "critical"):
            continue
        text = " ".join(
            str(row.get(k) or "")
            for k in ("description", "title", "clause", "evidence_quote")
        )
        for seed in seed_items:
            cat = str(seed.get("category") or "")
            for kw in _category_keywords(cat):
                if kw and kw in text:
                    category_high_issues[cat].append(row)
                    break

    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    stats = {"total": 0, "pass": 0, "fail": 0, "unknown": 0, "attention": 0}
    risk_stats = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    mlx_evaluated = 0

    for seed in seed_items:
        iid = seed.get("id")
        if iid is None:
            continue
        try:
            item_id = int(iid)
        except (TypeError, ValueError):
            continue

        cov = cov_map.get(item_id, {})
        issue = _pick_issue_for_seed(
            seed, issue_map, gate_issues, category_high_issues
        )
        cov_status = str(cov.get("status") or "unknown").lower()
        if cov_status in ("pass", "fail"):
            mlx_evaluated += 1
        conclusion = _COV_TO_CONCLUSION.get(cov_status, "unknown")

        if issue:
            risk_level = issue.get("risk_level") or seed.get("risk_level") or "medium"
            if conclusion == "unknown":
                conclusion = "fail"
        elif conclusion == "unknown" and str(seed.get("category") or "") in category_high_issues:
            conclusion = "attention"
            issue = category_high_issues[str(seed.get("category") or "")][0]
            risk_level = issue.get("risk_level") or "high"
        else:
            risk_level = seed.get("risk_level") if conclusion == "fail" else "low"

        if conclusion == "pass":
            stats["pass"] += 1
        elif conclusion == "fail":
            stats["fail"] += 1
        elif conclusion == "attention":
            stats["attention"] += 1
        else:
            stats["unknown"] += 1
        stats["total"] += 1

        if conclusion != "pass":
            rl = str(risk_level or "medium").lower()
            if rl in risk_stats:
                risk_stats[rl] += 1

        ai_suggestion = ""
        evidence = ""
        if issue:
            ai_suggestion = issue.get("description") or issue.get("suggestion") or ""
            evidence = issue.get("evidence_quote") or issue.get("reasoning") or ""
        elif cov.get("note"):
            ai_suggestion = str(cov.get("note"))

        category = str(seed.get("category") or "其他")
        categories[category].append(
            {
                "id": item_id,
                "item": seed.get("item") or "",
                "description": seed.get("description") or "",
                "gate_id": seed.get("gate_id"),
                "conclusion": conclusion,
                "risk_level": risk_level,
                "ai_suggestion": ai_suggestion,
                "evidence": evidence,
            }
        )

    category_list = [
        {"name": name, "items": items}
        for name, items in sorted(categories.items(), key=lambda x: x[0])
    ]

    total = stats["total"] or 1
    coverage_rate = round((stats["pass"] + stats["fail"]) / total, 4)

    return {
        "total": stats["total"],
        "pass": stats["pass"],
        "fail": stats["fail"],
        "unknown": stats["unknown"],
        "attention": stats["attention"],
        "coverage_rate": coverage_rate,
        "mlx_evaluated_count": mlx_evaluated,
        "risk_stats": risk_stats,
        "categories": category_list,
    }
