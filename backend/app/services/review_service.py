"""
评审域服务
"""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractVersion, AIReview
from app.models.review import ReviewSession, ReviewOpinion
from app.services.contract_state import (
    AI_READY_STATUSES,
    REVIEW_ROLE_APPROVAL_STATUS,
    approval_status_after_review_role,
    transition_contract,
)
from app.core.config import settings
from app.services.ai_review_issue_service import list_top_issues_for_contract
from app.services.audit_service import log_action

# 各流程类型所需评审角色
REVIEW_ROLES_BY_FLOW = {
    "simple": ["legal"],
    "standard": ["legal", "finance", "executive"],
    "large_amount": ["legal", "finance", "executive"],
    "special": ["legal", "finance", "executive"],
}

# 评审顺序（门禁校验用）
REVIEW_ROLE_ORDER = ["legal", "finance", "executive"]


def _required_roles(flow_type: str) -> list[str]:
    return REVIEW_ROLES_BY_FLOW.get(flow_type or "standard", ["legal"])


def _infer_flow_type(contract: Contract) -> str:
    amount = contract.amount or 0
    if amount < 100_000:
        return "simple"
    if amount >= 1_000_000:
        return "large_amount"
    return "standard"


async def _get_latest_ai(db: AsyncSession, contract_id: int) -> Optional[AIReview]:
    result = await db.execute(
        select(AIReview)
        .where(AIReview.contract_id == contract_id)
        .order_by(AIReview.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_or_create_session(
    db: AsyncSession, contract_id: int, flow_type: str
) -> ReviewSession:
    result = await db.execute(
        select(ReviewSession)
        .where(ReviewSession.contract_id == contract_id, ReviewSession.status == "pending")
        .order_by(ReviewSession.created_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session:
        return session
    session = ReviewSession(contract_id=contract_id, flow_type=flow_type, status="pending")
    db.add(session)
    await db.flush()
    return session


async def _get_approved_roles_in_session(db: AsyncSession, session_id: int) -> set[str]:
    result = await db.execute(
        select(ReviewOpinion.role).where(
            ReviewOpinion.session_id == session_id,
            ReviewOpinion.action == "approve",
        )
    )
    return set(result.scalars().all())


def _validate_review_sequence(role: str, approved_roles: set[str], required_roles: list[str]) -> None:
    """校验评审顺序：finance 需 legal；executive 需 legal + finance。"""
    if role not in required_roles:
        raise HTTPException(status_code=400, detail=f"当前流程不允许 {role} 评审")

    if role == "finance" and "legal" not in approved_roles:
        raise HTTPException(status_code=400, detail="请先完成法务评审")
    if role == "executive":
        if "legal" not in approved_roles:
            raise HTTPException(status_code=400, detail="请先完成法务评审")
        if "finance" in required_roles and "finance" not in approved_roles:
            raise HTTPException(status_code=400, detail="请先完成财务评审")


async def _get_current_version_id(db: AsyncSession, contract: Contract) -> Optional[int]:
    """当前合同版本 ID（优先 current_version_id，否则取最新版本）。"""
    if contract.current_version_id:
        return contract.current_version_id
    result = await db.execute(
        select(ContractVersion.id)
        .where(ContractVersion.contract_id == contract.id)
        .order_by(ContractVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _ensure_ai_gate(db: AsyncSession, contract_id: int) -> None:
    """法务评审前须完成 AI 审查，且审查版本与当前合同版本一致。"""
    ready, message = await _check_ai_gate(db, contract_id)
    if not ready:
        raise HTTPException(status_code=400, detail=message)


async def _check_ai_gate(db: AsyncSession, contract_id: int) -> tuple[bool, str]:
    """返回 (是否满足门禁, 提示文案)。"""
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    ai = await _get_latest_ai(db, contract_id)
    if not ai:
        return False, "请先完成 AI 审查后再提交评审"

    if ai.review_status == "reviewing":
        return False, "AI 审查进行中，请稍后再提交评审"
    if ai.review_status == "failed":
        return False, "AI 审查失败，请重新触发审查后再提交评审"
    if ai.review_status not in AI_READY_STATUSES:
        return False, "请先完成 AI 审查后再提交评审"

    if settings.AI_REQUIRE_CONFIRM and ai.review_status not in ("reviewed", "confirmed"):
        return False, "请先确认 AI 审查报告后再提交评审"

    current_version_id = await _get_current_version_id(db, contract)
    if current_version_id and ai.version_id != current_version_id:
        return False, "合同内容已修订，请重新触发 AI 审查后再提交评审"

    return True, ""


async def get_pending_reviews(
    db: AsyncSession,
    role: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """评审中心待办：审批已通过、评审未完成，按待完成角色过滤。"""
    result = await db.execute(
        select(Contract)
        .where(Contract.status == "approved")
        .order_by(Contract.updated_at.desc())
    )
    matched = []
    for c in result.scalars().all():
        flow_type = _infer_flow_type(c)
        required = _required_roles(flow_type)
        session_result = await db.execute(
            select(ReviewSession)
            .where(
                ReviewSession.contract_id == c.id,
                ReviewSession.status.in_(["pending", "completed"]),
            )
            .order_by(ReviewSession.created_at.desc())
            .limit(1)
        )
        session = session_result.scalar_one_or_none()
        if session and session.status == "completed":
            continue

        approved_roles: set[str] = set()
        if session:
            approved_roles = await _get_approved_roles_in_session(db, session.id)

        pending_roles = [r for r in required if r not in approved_roles]
        if not pending_roles:
            if session and session.status == "pending":
                session.status = "completed"
            continue

        if role and role not in pending_roles:
            continue

        matched.append(
            {
                "contract_id": c.id,
                "contract_no": c.contract_no,
                "title": c.title,
                "amount": c.amount,
                "flow_type": flow_type,
                "required_roles": required,
                "pending_roles": pending_roles,
                "status": c.status,
                "approval_status": c.approval_status,
            }
        )

    total = len(matched)
    start = (page - 1) * page_size
    items = matched[start : start + page_size]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_review_workspace(db: AsyncSession, contract_id: int) -> dict:
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    ai_summary = None
    review = await _get_latest_ai(db, contract_id)
    if review:
        import json as _json

        clause_reviews = []
        if review.clause_reviews:
            try:
                clause_reviews = _json.loads(review.clause_reviews)
            except (_json.JSONDecodeError, TypeError):
                clause_reviews = []

        high_clauses = [
            c
            for c in clause_reviews
            if isinstance(c, dict)
            and c.get("risk_level") in ("high", "critical", "medium")
        ][:5]

        ai_summary = {
            "review_id": review.review_id,
            "risk_level": review.overall_risk_level,
            "risk_score": review.overall_risk_score,
            "review_status": review.review_status,
            "recommendation": review.recommendation,
            "version_id": review.version_id,
            "model_version": review.model_version,
            "top_clauses": high_clauses,
        }

    ai_issues = await list_top_issues_for_contract(db, contract_id, limit=20)

    opinions_result = await db.execute(
        select(ReviewOpinion)
        .where(ReviewOpinion.contract_id == contract_id)
        .order_by(ReviewOpinion.created_at)
    )
    opinions = [
        {
            "id": o.id,
            "role": o.role,
            "action": o.action,
            "comment": o.comment,
            "reviewer_name": o.reviewer_name,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in opinions_result.scalars().all()
    ]

    flow_type = _infer_flow_type(contract)
    ai_ready, ai_gate_message = await _check_ai_gate(db, contract_id)

    return {
        "contract": {
            "id": contract.id,
            "contract_no": contract.contract_no,
            "title": contract.title,
            "status": contract.status,
            "amount": contract.amount,
            "flow_type": flow_type,
        },
        "ai_summary": ai_summary,
        "ai_issues": ai_issues,
        "opinions": opinions,
        "required_roles": _required_roles(flow_type),
        "ai_gate": {"ready": ai_ready, "message": ai_gate_message or None},
    }


async def submit_opinion(
    db: AsyncSession,
    contract_id: int,
    role: str,
    action: str,
    comment: Optional[str],
    reviewer_id: int,
    reviewer_name: str,
) -> dict:
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    if contract.status not in ("approved", "executing", "sealed"):
        raise HTTPException(status_code=400, detail="仅审批通过后的合同可提交评审")

    flow_type = _infer_flow_type(contract)
    required = _required_roles(flow_type)
    if role not in required:
        raise HTTPException(status_code=400, detail=f"流程 {flow_type} 不允许 {role} 评审")

    await _ensure_ai_gate(db, contract_id)

    session = await _get_or_create_session(db, contract_id, flow_type)
    approved_roles = await _get_approved_roles_in_session(db, session.id)

    if role in approved_roles:
        raise HTTPException(status_code=400, detail=f"{role} 评审已完成，不可重复提交")

    _validate_review_sequence(role, approved_roles, required)

    opinion = ReviewOpinion(
        contract_id=contract_id,
        session_id=session.id,
        role=role,
        action=action,
        comment=comment,
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
    )
    db.add(opinion)
    await db.flush()

    if action == "approve":
        approved_roles.add(role)
        contract.approval_status = approval_status_after_review_role(
            role, required, approved_roles
        )
        if approved_roles >= set(required):
            session.status = "completed"
            contract.approval_status = "seal_pending"
    elif action == "reject":
        contract.approval_status = "rejected"

    await log_action(
        db=db,
        user_id=reviewer_id,
        action=f"review_{action}",
        resource_type="contract",
        resource_id=contract_id,
        detail={"role": role, "comment": comment},
    )
    return {
        "opinion_id": opinion.id,
        "role": role,
        "action": action,
        "session_status": session.status,
    }


async def return_for_revision(
    db: AsyncSession,
    contract_id: int,
    role: str,
    comment: Optional[str],
    user_id: int,
    username: str,
) -> dict:
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    session = await _get_or_create_session(db, contract_id, "return")
    session.status = "returned"
    db.add(
        ReviewOpinion(
            contract_id=contract_id,
            session_id=session.id,
            role=role,
            action="return",
            comment=comment,
            reviewer_id=user_id,
            reviewer_name=username,
        )
    )
    await transition_contract(db, contract, "draft", approval_status="returned")
    from app.services.notification_events import notify_review_returned

    await notify_review_returned(db, contract.creator_id, contract_id, comment)
    await log_action(
        db=db,
        user_id=user_id,
        action="review_return",
        resource_type="contract",
        resource_id=contract_id,
        detail={"comment": comment},
    )
    return {"contract_id": contract_id, "status": "draft"}


async def submit_revision(
    db: AsyncSession,
    contract_id: int,
    content: Optional[str],
    change_description: Optional[str],
    title: Optional[str],
    user_id: int,
) -> dict:
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    if contract.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"仅草稿状态可提交修订（当前：{contract.status}，需先完成法务退回）",
        )

    ver_result = await db.execute(
        select(func.max(ContractVersion.version)).where(
            ContractVersion.contract_id == contract_id
        )
    )
    max_ver = ver_result.scalar() or 0
    new_ver = ContractVersion(
        contract_id=contract_id,
        version=max_ver + 1,
        title=title or contract.title,
        content=content or contract.content,
        change_description=change_description,
        creator_id=user_id,
    )
    db.add(new_ver)
    await db.flush()
    if content:
        contract.content = content
    if title:
        contract.title = title
    contract.current_version_id = new_ver.id
    contract.approval_status = "pending"
    await db.flush()
    return {
        "contract_id": contract_id,
        "version": new_ver.version,
        "version_id": new_ver.id,
    }


async def get_review_history(db: AsyncSession, contract_id: int) -> dict:
    result = await db.execute(
        select(ReviewOpinion)
        .where(ReviewOpinion.contract_id == contract_id)
        .order_by(ReviewOpinion.created_at)
    )
    opinions = [
        {
            "id": o.id,
            "role": o.role,
            "action": o.action,
            "comment": o.comment,
            "reviewer_name": o.reviewer_name,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in result.scalars().all()
    ]
    return {"contract_id": contract_id, "opinions": opinions}
