# -*- coding: utf-8 -*-
"""AI 审查 Session 编排器 S1–S7（AI-1/AI-2）。"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.api.v1.ai_review_demo import DEMO_GATES, DEMO_ISSUES
from app.core.config import settings
from app.services.ai_review.ai_engine import ReviewResult, review_contract
from app.services.ai_review.clause_parser import parse_clauses
from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    apply_high_risk_guardrail,
    demo_issue_to_schema,
    issues_to_clause_reviews_json,
    issues_to_rule_violations,
    merge_issues,
    normalize_dimension,
)
from app.services.ai_review.rag_service import enrich_issues
from app.services.ai_review.rule_engine import run_rule_engine
from app.services.ai_review.skills.gates import build_gates
from app.services.ai_review.skills.read_through import run_read_through
from app.services.ai_review.skills.self_correction import run_self_correction

logger = logging.getLogger(__name__)


def _review_result_to_issues(result: ReviewResult) -> list[AiReviewIssue]:
    """LLM ReviewResult → AiReviewIssue 列表。"""
    issues: list[AiReviewIssue] = []
    for cr in result.clause_reviews:
        if not cr.issues and cr.risk_score < 30:
            continue
        primary = cr.issues[0] if cr.issues else None
        desc = primary.description if primary else "; ".join(cr.suggestions) or cr.title
        issues.append(
            AiReviewIssue(
                clause=cr.title or cr.clause_id,
                clause_id=cr.clause_id,
                clause_ref=cr.title or cr.clause_id,
                dimension=normalize_dimension(cr.section_type),
                gate_id="gate_clause",
                risk_level=cr.risk_level,
                confidence=round(max(0.0, min(1.0, (100.0 - cr.risk_score) / 100.0)), 2),
                title=cr.title,
                description=desc,
                suggestion="; ".join(cr.suggestions) if cr.suggestions else desc,
                revision_method="comment",
                source="llm",
                issues=[
                    {
                        "keyword": i.keyword,
                        "severity": i.severity,
                        "description": i.description,
                    }
                    for i in cr.issues
                ],
            )
        )
    return issues


def build_mock_payload() -> dict[str, Any]:
    """Mock 路径：DEMO 数据经统一 Schema。"""
    issues = [demo_issue_to_schema(i) for i in DEMO_ISSUES]
    issues = merge_issues(issues)
    summary = {
        "mock": True,
        "gates": DEMO_GATES,
        "read_through": {"overall": "Mock 通读摘要"},
    }
    return {
        "overall_risk_level": "medium",
        "overall_risk_score": 65.0,
        "recommendation": "建议关注付款条款",
        "issues": issues,
        "clause_reviews": issues_to_clause_reviews_json(issues),
        "rule_violations": issues_to_rule_violations(issues),
        "summary": summary,
        "model_version": "mock",
        "review_duration_seconds": 0,
    }


class AiReviewOrchestrator:
    """审查 Session 编排。"""

    async def run(
        self,
        contract_text: str,
        *,
        contract_type: str = "other",
        amount: Optional[float] = None,
    ) -> dict[str, Any]:
        if settings.AI_REVIEW_MOCK:
            return build_mock_payload()

        text = (contract_text or "").strip()
        if not text:
            raise ValueError("合同内容为空，无法执行 AI 审查")

        started = datetime.now()

        # S2 通读
        read_through = await run_read_through(text, contract_type=contract_type)

        # S3 规则
        rule_issues = run_rule_engine(text, contract_type=contract_type, amount=amount)

        # S6 五维 LLM
        clauses = await parse_clauses(text, contract_type=contract_type)
        result = await review_contract(text, clauses, contract_type)
        llm_issues = _review_result_to_issues(result)

        issues = merge_issues(rule_issues, llm_issues)

        # S5 RAG
        issues = enrich_issues(issues)

        # Self-correction + guardrail
        issues = await run_self_correction(issues, read_through)

        dimension_summary = [
            {
                "dimension": d.dimension,
                "score": d.score,
                "summary": d.summary,
            }
            for d in result.dimension_scores
        ]

        clause_reviews = issues_to_clause_reviews_json(issues)
        payload_for_gates = {"clause_reviews": clause_reviews, "summary": {"dimensions": dimension_summary}}
        gates = build_gates(issues, dimensions=dimension_summary, read_through=read_through)

        summary: dict[str, Any] = {
            "read_through": read_through,
            "dimensions": dimension_summary,
            "gates": gates,
            "issue_count": len(issues),
            "model_version": settings.AI_MODEL,
        }

        duration = int((datetime.now() - started).total_seconds())

        return {
            "overall_risk_level": result.overall_risk_level,
            "overall_risk_score": float(result.overall_risk_score),
            "recommendation": result.recommendation,
            "issues": issues,
            "clause_reviews": clause_reviews,
            "rule_violations": issues_to_rule_violations(issues),
            "summary": summary,
            "model_version": settings.AI_MODEL,
            "review_duration_seconds": duration,
        }


async def run_orchestrated_review(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
) -> dict[str, Any]:
    return await AiReviewOrchestrator().run(
        contract_text,
        contract_type=contract_type,
        amount=amount,
    )
