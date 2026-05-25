# -*- coding: utf-8 -*-
"""AI 审查执行器 — 薄封装 Orchestrator，供 API / Celery 共用。"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    issues_to_clause_reviews_json,
    issues_to_rule_violations,
)
from app.services.ai_review.orchestrator import run_orchestrated_review

logger = logging.getLogger(__name__)


async def run_contract_ai_review(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
) -> dict[str, Any]:
    """
    执行完整审查 Session（S2→S3→S6→S5→反思→聚合）。

    Returns:
        可写入 AIReview 的 payload（含 issues 列表）
    """
    payload = await run_orchestrated_review(
        contract_text,
        contract_type=contract_type,
        amount=amount,
    )
    # 确保 clause_reviews 镜像存在
    if "issues" in payload and not payload.get("clause_reviews"):
        issues: list[AiReviewIssue] = payload["issues"]
        payload["clause_reviews"] = issues_to_clause_reviews_json(issues)
        payload["rule_violations"] = issues_to_rule_violations(issues)
    return payload


def apply_payload_to_ai_review(ai_review: Any, payload: dict) -> None:
    """将审查结果写入 ORM 对象。"""
    ai_review.review_status = "ai_done"
    ai_review.overall_risk_level = payload.get("overall_risk_level")
    ai_review.overall_risk_score = payload.get("overall_risk_score")
    ai_review.recommendation = payload.get("recommendation")
    ai_review.clause_reviews = json.dumps(
        payload.get("clause_reviews", []), ensure_ascii=False
    )
    ai_review.rule_violations = json.dumps(
        payload.get("rule_violations", []), ensure_ascii=False
    )
    ai_review.summary = json.dumps(payload.get("summary", {}), ensure_ascii=False)
    ai_review.model_version = payload.get("model_version") or ""
    ai_review.review_duration_seconds = payload.get("review_duration_seconds")


# 兼容旧测试：保留 gates 计算 re-export
from app.services.ai_review.skills.gates import compute_gates_from_payload  # noqa: E402
