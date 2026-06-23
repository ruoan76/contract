# -*- coding: utf-8 -*-
"""AI 审查 Issue 持久化与查询。"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_review_issue import AIReviewIssue as AIReviewIssueORM
from app.services.ai_review.issue_schema import AiReviewIssue


def _issue_to_orm(
    review_id: str,
    contract_id: int,
    version_id: int,
    item: AiReviewIssue,
) -> AIReviewIssueORM:
    d = item.model_dump_public()
    return AIReviewIssueORM(
        review_id=review_id,
        contract_id=contract_id,
        version_id=version_id,
        clause=d.get("clause") or "",
        clause_id=d.get("clause_id") or "",
        clause_ref=d.get("clause_ref") or "",
        dimension=d.get("dimension") or "compliance_check",
        label_id=d.get("label_id"),
        label_name=d.get("label_name"),
        gate_id=d.get("gate_id"),
        cuad_code=d.get("cuad_code"),
        risk_level=d.get("risk_level") or "medium",
        confidence=float(d.get("confidence") or 0.7),
        title=d.get("title") or "",
        description=d.get("description") or d.get("suggestion") or "",
        suggestion=d.get("suggestion") or "",
        legal_basis=d.get("legal_basis"),
        revision_method=d.get("revision_method") or "comment",
        exposure_summary=d.get("exposure_summary"),
        source=d.get("source") or "llm",
        needs_research=1 if d.get("needs_research") else 0,
        rule_id=d.get("rule_id"),
        human_status="pending",
    )


async def replace_review_issues(
    db: AsyncSession,
    review_id: str,
    contract_id: int,
    version_id: int,
    issues: list[AiReviewIssue],
) -> None:
    """写入审查 issue 列表（先删后插）。"""
    await db.execute(delete(AIReviewIssueORM).where(AIReviewIssueORM.review_id == review_id))
    for item in issues:
        if isinstance(item, dict):
            item = AiReviewIssue.model_validate(item)
        db.add(_issue_to_orm(review_id, contract_id, version_id, item))
    await db.flush()


async def list_review_issues(
    db: AsyncSession,
    review_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(AIReviewIssueORM)
        .where(AIReviewIssueORM.review_id == review_id)
        .order_by(AIReviewIssueORM.id)
        .offset(offset)
        .limit(limit)
    )
    rows = []
    for row in result.scalars().all():
        rows.append(
            {
                "id": row.id,
                "review_id": row.review_id,
                "clause": row.clause,
                "clause_ref": row.clause_ref,
                "dimension": row.dimension,
                "label_id": row.label_id,
                "label_name": row.label_name,
                "gate_id": row.gate_id,
                "risk_level": row.risk_level,
                "confidence": row.confidence,
                "title": row.title,
                "description": row.description,
                "suggestion": row.suggestion,
                "legal_basis": row.legal_basis,
                "revision_method": row.revision_method,
                "source": row.source,
                "needs_research": bool(row.needs_research),
                "human_status": row.human_status,
                "human_comment": row.human_comment,
            }
        )
    return rows


async def list_top_issues_for_contract(
    db: AsyncSession,
    contract_id: int,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """最新审查的 issue，按风险排序。"""
    from app.models.contract import AIReview

    rev_result = await db.execute(
        select(AIReview.review_id)
        .where(AIReview.contract_id == contract_id)
        .order_by(AIReview.created_at.desc())
        .limit(1)
    )
    review_id = rev_result.scalar_one_or_none()
    if not review_id:
        return []

    result = await db.execute(
        select(AIReviewIssueORM)
        .where(AIReviewIssueORM.review_id == review_id)
        .order_by(AIReviewIssueORM.id)
    )
    items = list(result.scalars().all())
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    items.sort(key=lambda x: order.get(x.risk_level or "low", 0), reverse=True)
    return [
        {
            "id": row.id,
            "clause": row.clause,
            "risk_level": row.risk_level,
            "dimension": row.dimension,
            "suggestion": row.suggestion,
            "description": row.description,
            "legal_basis": row.legal_basis,
            "revision_method": row.revision_method,
            "human_status": row.human_status,
            "label_id": row.label_id,
            "source": row.source,
        }
        for row in items[:limit]
    ]


async def update_issue_human_status(
    db: AsyncSession,
    issue_id: int,
    human_status: str,
    human_comment: Optional[str] = None,
) -> dict[str, Any]:
    result = await db.execute(
        select(AIReviewIssueORM).where(AIReviewIssueORM.id == issue_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise ValueError("Issue 不存在")
    row.human_status = human_status
    if human_comment is not None:
        row.human_comment = human_comment
    if human_status in ("false_positive", "confirmed"):
        from app.services.ai_review.config_admin_service import record_issue_feedback

        await record_issue_feedback(db, row, human_status)
    await db.flush()
    return {"id": row.id, "human_status": row.human_status, "human_comment": row.human_comment}
