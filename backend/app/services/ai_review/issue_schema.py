# -*- coding: utf-8 -*-
"""AI 审查 Issue 统一 Schema（Mock / 规则 / LLM 共用）。"""
from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.config import settings

# 条款 section_type → contract-review-pro dimension
DIMENSION_ALIASES: dict[str, str] = {
    "compliance": "compliance_check",
    "definitions": "compliance_check",
    "rights_obligations": "compliance_check",
    "risk": "risk_assessment",
    "breach": "risk_assessment",
    "dispute": "risk_assessment",
    "termination": "risk_assessment",
    "force_majeure": "risk_assessment",
    "financial": "finance_check",
    "capability": "performance_check",
    "performance_check": "performance_check",
    "anomaly": "anomaly_detection",
    "anomaly_detection": "anomaly_detection",
    "finance_check": "finance_check",
    "risk_assessment": "risk_assessment",
    "compliance_check": "compliance_check",
    "other": "compliance_check",
}

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def normalize_dimension(value: str | None) -> str:
    key = (value or "other").lower()
    return DIMENSION_ALIASES.get(key, "compliance_check")


class AiReviewIssue(BaseModel):
    """单条审查发现。"""

    clause: str = Field(default="", description="条款引用/标题")
    clause_id: str = Field(default="", description="条款 ID")
    clause_ref: str = Field(default="", description="条款引用别名")
    dimension: str = Field(default="compliance_check")
    label_id: Optional[str] = None
    label_name: Optional[str] = None
    gate_id: Optional[str] = None
    cuad_code: Optional[str] = None
    risk_level: str = Field(default="medium")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    title: str = Field(default="")
    description: str = Field(default="")
    suggestion: str = Field(default="")
    legal_basis: Optional[str] = None
    revision_method: str = Field(default="comment")
    exposure_summary: Optional[str] = None
    source: str = Field(default="llm", description="llm | rule | rag")
    needs_research: bool = False
    rule_id: Optional[str] = None
    issues: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: Optional[str] = None
    evidence_quote: Optional[str] = None
    snippet_id: Optional[str] = None
    checklist_item_id: Optional[int] = None

    def model_dump_public(self) -> dict[str, Any]:
        """写入 clause_reviews JSON 的 dict。"""
        d = self.model_dump(exclude_none=False)
        clause = d.get("clause") or d.get("clause_ref") or d.get("title") or ""
        d["clause"] = clause
        if not d.get("clause_ref"):
            d["clause_ref"] = clause
        return d


def demo_issue_to_schema(raw: dict[str, Any]) -> AiReviewIssue:
    """DEMO_ISSUES 项 → AiReviewIssue。"""
    return AiReviewIssue(
        clause=raw.get("clause_ref") or raw.get("title") or "",
        clause_ref=raw.get("clause_ref") or "",
        dimension=normalize_dimension(raw.get("dimension")),
        label_id=raw.get("label_id"),
        label_name=raw.get("label_name"),
        gate_id=raw.get("gate_id"),
        cuad_code=raw.get("cuad_code"),
        risk_level=raw.get("risk_level") or "medium",
        confidence=float(raw.get("confidence") or 0.7),
        title=raw.get("title") or "",
        description=raw.get("description") or "",
        suggestion=raw.get("description") or "",
        legal_basis=raw.get("legal_basis"),
        revision_method=raw.get("revision_method") or "comment",
        source="mock",
    )


def _normalize_text(text: str) -> str:
    """去标点与空白，便于跨段去重。"""
    t = re.sub(r"[\s\W_]+", "", (text or "").lower())
    return t[:60]


def _dedup_key(item: AiReviewIssue) -> str:
    """去重键：维度 + 归一化标题/描述/证据 + label。"""
    dim = normalize_dimension(item.dimension)
    if item.checklist_item_id is not None:
        return f"ck:{item.checklist_item_id}"
    if item.rule_id:
        return f"rule:{item.rule_id}"
    title_n = _normalize_text(item.title or item.clause or "")
    desc_n = _normalize_text(item.description or "")
    evidence_n = _normalize_text(item.evidence_quote or "")
    label = item.label_id or ""
    if label and title_n:
        return f"{dim}|label:{label}|{title_n}"
    return f"{dim}|{title_n}|{desc_n}|{evidence_n}|{label}"


def merge_issues(*groups: list[AiReviewIssue]) -> list[AiReviewIssue]:
    """合并多源 issue，去重后按风险排序。"""
    dedup: dict[str, AiReviewIssue] = {}
    for group in groups:
        for item in group:
            key = _dedup_key(item)
            existing = dedup.get(key)
            if existing is None:
                dedup[key] = item
            elif RISK_ORDER.get(item.risk_level, 0) > RISK_ORDER.get(existing.risk_level, 0):
                dedup[key] = item
    merged = list(dedup.values())
    merged.sort(
        key=lambda x: (RISK_ORDER.get(x.risk_level, 0), x.confidence),
        reverse=True,
    )
    return merged


def cap_issues_by_dimension(
    issues: list[AiReviewIssue],
    *,
    max_per_dim: int | None = None,
) -> list[AiReviewIssue]:
    """每维保留 top-N（按风险与置信度），规则类 issue 不受限。"""
    limit = max_per_dim if max_per_dim is not None else settings.AI_REVIEW_MAX_ISSUES_PER_DIM
    rules = [i for i in issues if i.source == "rule" or i.rule_id]
    rest = [i for i in issues if i not in rules]
    by_dim: dict[str, list[AiReviewIssue]] = {}
    for item in rest:
        dim = normalize_dimension(item.dimension)
        by_dim.setdefault(dim, []).append(item)
    capped: list[AiReviewIssue] = list(rules)
    for dim_items in by_dim.values():
        dim_items.sort(
            key=lambda x: (RISK_ORDER.get(x.risk_level, 0), x.confidence),
            reverse=True,
        )
        capped.extend(dim_items[:limit])
    capped.sort(
        key=lambda x: (RISK_ORDER.get(x.risk_level, 0), x.confidence),
        reverse=True,
    )
    return capped


def issues_to_clause_reviews_json(issues: list[AiReviewIssue]) -> list[dict[str, Any]]:
    return [i.model_dump_public() for i in issues]


def issues_to_rule_violations(issues: list[AiReviewIssue]) -> list[dict[str, Any]]:
    """规则类 issue 转为 rule_violations 表格式（兼容旧 UI）。"""
    rows = []
    for i in issues:
        if i.source != "rule" and not i.rule_id:
            continue
        rows.append(
            {
                "rule_id": i.rule_id or "RULE",
                "rule_name": i.title or i.label_name or "规则命中",
                "severity": i.risk_level,
                "message": i.description or i.suggestion,
            }
        )
    return rows


def apply_high_risk_guardrail(issues: list[AiReviewIssue]) -> list[AiReviewIssue]:
    """无 legal_basis 的高风险降级或标记待研究。"""
    out: list[AiReviewIssue] = []
    for item in issues:
        if item.risk_level in ("high", "critical") and not item.legal_basis:
            if item.source == "rule":
                out.append(item)
                continue
            item.risk_level = "medium"
            item.needs_research = True
            item.confidence = min(item.confidence, 0.65)
        out.append(item)
    return out
