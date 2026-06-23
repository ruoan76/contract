# -*- coding: utf-8
"""AI 审查 KPI 聚合。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import AIReview
from app.models.ai_review_issue import AIReviewIssue
from app.models.ai_review_config import AIRuleFeedbackStat


async def get_metrics_summary(db: AsyncSession, *, days: int = 30) -> dict[str, Any]:
    """管理端 KPI 摘要。"""
    since = datetime.utcnow() - timedelta(days=days)

    total_q = await db.execute(
        select(func.count()).select_from(AIReview).where(AIReview.created_at >= since)
    )
    review_total = total_q.scalar() or 0

    done_q = await db.execute(
        select(func.count()).select_from(AIReview).where(
            AIReview.created_at >= since,
            AIReview.review_status == "ai_done",
        )
    )
    done_count = done_q.scalar() or 0

    failed_q = await db.execute(
        select(func.count()).select_from(AIReview).where(
            AIReview.created_at >= since,
            AIReview.review_status == "failed",
        )
    )
    failed_count = failed_q.scalar() or 0

    completion_rate = done_count / max(done_count + failed_count, 1)

    durations_q = await db.execute(
        select(AIReview.review_duration_seconds).where(
            AIReview.created_at >= since,
            AIReview.review_status == "ai_done",
            AIReview.review_duration_seconds.isnot(None),
        )
    )
    durations = sorted([d for (d,) in durations_q.all() if d is not None])
    p95 = durations[int(len(durations) * 0.95)] if durations else 0

    hc_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.risk_level.in_(("high", "critical")),
            AIReviewIssue.created_at >= since,
        )
    )
    hc_total = hc_q.scalar() or 0

    hc_basis_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.risk_level.in_(("high", "critical")),
            AIReviewIssue.created_at >= since,
            AIReviewIssue.legal_basis.isnot(None),
            AIReviewIssue.legal_basis != "",
        )
    )
    hc_with_basis = hc_basis_q.scalar() or 0

    hc_research_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.risk_level.in_(("high", "critical")),
            AIReviewIssue.created_at >= since,
            AIReviewIssue.needs_research == 1,
        )
    )
    hc_research = hc_research_q.scalar() or 0

    high_critical_with_basis_rate = (hc_with_basis + hc_research) / max(hc_total, 1)

    labeled_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.created_at >= since,
            AIReviewIssue.label_id.isnot(None),
            AIReviewIssue.label_id != "",
        )
    )
    labeled = labeled_q.scalar() or 0
    all_issues_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.created_at >= since,
        )
    )
    all_issues = all_issues_q.scalar() or 0
    label_id_coverage_rate = labeled / max(all_issues, 1)

    fp_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.created_at >= since,
            AIReviewIssue.human_status == "false_positive",
        )
    )
    fp_count = fp_q.scalar() or 0
    reviewed_q = await db.execute(
        select(func.count()).select_from(AIReviewIssue).where(
            AIReviewIssue.created_at >= since,
            AIReviewIssue.human_status != "pending",
        )
    )
    reviewed_human = reviewed_q.scalar() or 0
    false_positive_rate = fp_count / max(reviewed_human, 1)

    full_count = 0
    reviews = await db.execute(
        select(AIReview.summary).where(
            AIReview.created_at >= since,
            AIReview.review_status == "ai_done",
        )
    )
    for (summary_raw,) in reviews.all():
        try:
            summary = json.loads(summary_raw) if summary_raw else {}
            if summary.get("review_completeness") == "full":
                full_count += 1
        except json.JSONDecodeError:
            pass
    completeness_full_rate = full_count / max(done_count, 1)

    feedback_rows = (
        await db.execute(
            select(AIRuleFeedbackStat)
            .order_by(AIRuleFeedbackStat.fp_count.desc())
            .limit(10)
        )
    ).scalars().all()
    top_fp_rules = []
    top_confirm_rules = []
    for r in feedback_rows:
        total = (r.fp_count or 0) + (r.confirm_count or 0)
        fp_rate = (r.fp_count or 0) / max(total, 1)
        entry = {
            "rule_key": r.rule_key,
            "fp_count": r.fp_count or 0,
            "confirm_count": r.confirm_count or 0,
            "fp_rate": round(fp_rate, 4),
        }
        if (r.fp_count or 0) > 0:
            top_fp_rules.append(entry)
        if (r.confirm_count or 0) > 0:
            top_confirm_rules.append(entry)
    top_confirm_rules.sort(key=lambda x: x["confirm_count"], reverse=True)

    return {
        "period_days": days,
        "review_total": review_total,
        "completion_rate": round(completion_rate, 4),
        "p95_duration_seconds": p95,
        "high_critical_with_basis_rate": round(high_critical_with_basis_rate, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "label_id_coverage_rate": round(label_id_coverage_rate, 4),
        "completeness_full_rate": round(completeness_full_rate, 4),
        "top_false_positive_rules": top_fp_rules[:5],
        "top_confirmed_rules": top_confirm_rules[:5],
    }
