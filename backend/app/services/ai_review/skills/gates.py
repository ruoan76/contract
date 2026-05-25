# -*- coding: utf-8 -*-
"""S3 五门禁 Skill。"""
from __future__ import annotations

from typing import Any

from app.services.ai_review.issue_schema import AiReviewIssue


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
