# -*- coding: utf-8 -*-
"""S3 五门禁 Skill。"""
from __future__ import annotations

from typing import Any

from app.services.ai_review.issue_schema import AiReviewIssue


def build_gates_v2(
    issues: list[AiReviewIssue],
    *,
    dimensions: list[dict[str, Any]] | None = None,
    read_through: dict[str, Any] | None = None,
    checklist_coverage: list[list[dict[str, Any]]] | None = None,
    review_completeness: str = "full",
) -> dict[str, dict[str, str]]:
    """v2：结合 checklist_coverage 与 completeness。"""
    gates = build_gates(
        issues,
        dimensions=dimensions,
        read_through=read_through,
    )

    cov_lists = checklist_coverage or []
    flat_cov = [item for sub in cov_lists for item in sub if isinstance(item, dict)]

    validity_fails = sum(
        1 for c in flat_cov
        if c.get("status") == "fail" and _cov_gate(c, "gate_validity")
    )
    if validity_fails and gates["gate_validity"]["status"] == "pass":
        gates["gate_validity"] = {
            "status": "warn",
            "summary": f"清单效力项 {validity_fails} 项未通过",
        }

    consistency_fails = sum(
        1 for c in flat_cov if c.get("status") == "fail" and _cov_gate(c, "gate_consistency")
    )
    if consistency_fails:
        gates["gate_consistency"] = {
            "status": "warn",
            "summary": f"一致性清单 {consistency_fails} 项待处理",
        }

    if review_completeness != "full":
        gates["gate_output"] = {
            "status": "warn" if review_completeness == "partial" else "fail",
            "summary": "审查未完整完成，请法务重点复核",
        }

    return gates


def _cov_gate(item: dict, gate_id: str) -> bool:
    """简化：按 item_id 范围推断 gate（完整版可查 checklist JSON）。"""
    iid = item.get("item_id")
    if iid is None:
        return False
    try:
        n = int(iid)
    except (TypeError, ValueError):
        return False
    if gate_id == "gate_validity":
        return n <= 20
    if gate_id == "gate_consistency":
        return n >= 40
    return False


def build_gates(
    issues: list[AiReviewIssue],
    *,
    dimensions: list[dict[str, Any]] | None = None,
    read_through: dict[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    """根据 issues 与维度分计算五门禁。"""
    dimensions = dimensions or []
    high_critical = sum(1 for i in issues if i.risk_level in ("high", "critical"))
    medium_plus = sum(1 for i in issues if i.risk_level in ("medium", "high", "critical"))

    gate_blocked = any(
        i.gate_id == "gate_validity" and i.risk_level in ("high", "critical")
        for i in issues
        if i.source == "rule"
    )

    low_dim = [
        d for d in dimensions
        if isinstance(d, dict) and float(d.get("score") or 100) < 50
    ]
    validity_status = "fail" if gate_blocked else ("warn" if low_dim else "pass")
    clause_status = "fail" if high_critical else ("warn" if medium_plus else "pass")

    subject_status = "pass"
    if read_through and "待" in (read_through.get("parties") or ""):
        subject_status = "warn"

    return {
        "gate_validity": {
            "status": validity_status,
            "summary": "效力/合规项需关注" if validity_status != "pass" else "未发现效力致命问题",
        },
        "gate_subject": {
            "status": subject_status,
            "summary": (read_through or {}).get("parties") or "主体信息待法务核对",
        },
        "gate_clause": {
            "status": clause_status,
            "summary": f"{medium_plus} 项条款风险待处理" if medium_plus else "条款风险可控",
        },
        "gate_consistency": {
            "status": "warn" if any(i.gate_id == "gate_consistency" for i in issues) else "pass",
            "summary": "形式/一致性检查见规则项" if medium_plus else "一致性待确认",
        },
        "gate_output": {
            "status": "pending",
            "summary": "待法务确认后输出终稿",
        },
    }


def compute_gates_from_payload(payload: dict) -> dict[str, dict[str, str]]:
    """兼容旧调用：从 review payload 计算五门禁。"""
    clause_reviews = payload.get("clause_reviews") or []
    issues: list[AiReviewIssue] = []
    for row in clause_reviews:
        if isinstance(row, AiReviewIssue):
            issues.append(row)
        elif isinstance(row, dict):
            issues.append(AiReviewIssue.model_validate(row))
    summary = payload.get("summary") or {}
    if isinstance(summary, str):
        summary = {}
    return build_gates(
        issues,
        dimensions=summary.get("dimensions") or [],
        read_through=summary.get("read_through"),
    )
