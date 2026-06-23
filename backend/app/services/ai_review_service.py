"""
AI审查服务 - 工作流协调层
注意：此服务是AI审查的orchestrator，不包含审查引擎本身
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.contract import AIReview, ContractVersion

from app.services.ai_review.context_loader import load_review_context
from app.services.ai_review.issue_schema import AiReviewIssue
from app.services.ai_review.runner import apply_payload_to_ai_review, run_contract_ai_review
from app.services.ai_review.orchestrator import build_mock_payload
from app.services.ai_review.mlx_health import check_mlx_reachable, mlx_unavailable_detail
from app.services.ai_review_issue_service import replace_review_issues

logger = logging.getLogger(__name__)


async def _review_created_at_iso(db: AsyncSession, ai_review: AIReview) -> str | None:
    """flush 后读取 server default 字段，避免 async 懒加载 MissingGreenlet。"""
    await db.refresh(ai_review, attribute_names=["created_at"])
    return ai_review.created_at.isoformat() if ai_review.created_at else None

def _get_celery_review_task():
    """延迟导入 Celery 任务，避免与 ai_review_tasks 循环依赖导致静默降级为 stub。"""
    from app.celery_tasks.ai_review_tasks import execute_contract_review
    return execute_contract_review


def _celery_async_result(task_id: str):
    from app.celery_tasks import celery_app
    return celery_app.AsyncResult(task_id)


async def persist_review_result(
    db: AsyncSession,
    ai_review: AIReview,
    payload: dict,
    contract_id: int,
    version_id: int,
) -> None:
    """写入审查结果与 issue 明细。"""
    apply_payload_to_ai_review(ai_review, payload)
    raw_issues = payload.get("issues") or []
    issues: list[AiReviewIssue] = []
    for item in raw_issues:
        if isinstance(item, AiReviewIssue):
            issues.append(item)
        elif isinstance(item, dict):
            issues.append(AiReviewIssue.model_validate(item))
    if not issues and payload.get("clause_reviews"):
        for row in payload["clause_reviews"]:
            issues.append(AiReviewIssue.model_validate(row))
    await replace_review_issues(
        db, ai_review.review_id, contract_id, version_id, issues
    )
    await db.flush()


async def _ensure_no_parallel_review(
    db: AsyncSession,
    contract_id: int,
    version_id: int,
) -> None:
    """同合同版本已有 reviewing 时拒绝重复触发。"""
    result = await db.execute(
        select(AIReview).where(
            AIReview.contract_id == contract_id,
            AIReview.version_id == version_id,
            AIReview.review_status == "reviewing",
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该版本审查进行中，请稍候")


async def start_review(
    db: AsyncSession,
    contract_id: int,
    version_id: int,
    user_id: int,
    username: str = None,
) -> dict:
    """
    启动AI审查
    
    Args:
        db: 数据库会话
        contract_id: 合同ID
        version_id: 合同版本ID
        user_id: 发起人ID
        username: 发起人姓名 (可选)
        
    Returns:
        审查任务信息dict
    """
    # 查询版本
    version_result = await db.execute(
        select(ContractVersion).where(
            ContractVersion.id == version_id,
            ContractVersion.contract_id == contract_id
        )
    )
    version = version_result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="合同版本不存在")

    await _ensure_no_parallel_review(db, contract_id, version_id)

    # 生成 review_id
    review_id = f"REV-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    
    # 创建审查记录
    ai_review = AIReview(
        contract_id=contract_id,
        version_id=version_id,
        review_id=review_id,
        review_status="pending",
    )
    db.add(ai_review)
    await db.flush()

    # Mock 模式：Orchestrator 统一 Schema
    if settings.AI_REVIEW_MOCK:
        payload = build_mock_payload()
        await persist_review_result(db, ai_review, payload, contract_id, version_id)
        return {
            "review_id": review_id,
            "contract_id": contract_id,
            "version_id": version_id,
            "status": "ai_done",
            "user_id": user_id,
            "username": username,
            "created_at": await _review_created_at_iso(db, ai_review),
        }

    # 本地 MLX：同步调用引擎（无需 Redis/Celery）
    if settings.AI_REVIEW_SYNC:
        from app.models.contract import Contract

        contract_result = await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = contract_result.scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=404, detail="合同不存在")

        text = (version.content or contract.content or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="合同内容为空")

        mlx_ok, mlx_reason = await check_mlx_reachable()
        if not mlx_ok:
            ai_review.review_status = "failed"
            await db.flush()
            raise HTTPException(
                status_code=503,
                detail=mlx_unavailable_detail(mlx_reason),
            )

        ai_review.review_status = "reviewing"
        await db.flush()
        try:
            ctx = await load_review_context(
                db,
                contract_id=contract_id,
                contract_type=contract.contract_type,
                amount=contract.amount,
                counterparty_name=contract.counterparty_name,
            )
            payload = await run_contract_ai_review(
                text,
                contract_type=ctx.contract_type,
                amount=ctx.amount,
                profile_key=ctx.profile_key,
                counterparty_blacklisted=ctx.counterparty_blacklisted,
            )
            await persist_review_result(
                db, ai_review, payload, contract_id, version_id
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Sync AI review failed: %s", exc, exc_info=True)
            ai_review.review_status = "failed"
            await db.flush()
            raise HTTPException(
                status_code=503,
                detail=f"AI 审查失败，请确认 MLX 服务已启动（{settings.AI_BASE_URL}）: {exc}",
            ) from exc

        return {
            "review_id": review_id,
            "contract_id": contract_id,
            "version_id": version_id,
            "status": "ai_done",
            "user_id": user_id,
            "username": username,
            "created_at": await _review_created_at_iso(db, ai_review),
        }

    # 调用 Celery 异步任务
    try:
        celery_result = _get_celery_review_task().delay(contract_id, version_id, review_id)
        task_id = celery_result.id if hasattr(celery_result, "id") else celery_result
    except Exception as e:
        logger.error("Failed to dispatch Celery task: %s", e, exc_info=True)
        ai_review.review_status = "failed"
        await db.flush()
        hint = (
            "异步审查不可用：请确认 Redis 与 Celery worker 已启动，"
            "或在本机 .env 设置 AI_REVIEW_SYNC=1 走同步 MLX。"
        )
        detail = f"{hint} ({e})" if settings.DEBUG else "AI审查服务暂时不可用，请检查 Redis/Celery 或改用同步审查"
        raise HTTPException(status_code=503, detail=detail) from e
    
    # 更新审查记录
    ai_review.review_status = "reviewing"
    ai_review.celery_task_id = task_id
    await db.flush()
    
    return {
        "review_id": review_id,
        "contract_id": contract_id,
        "version_id": version_id,
        "task_id": task_id,
        "status": "reviewing",
        "user_id": user_id,
        "username": username,
        "created_at": await _review_created_at_iso(db, ai_review),
    }


async def get_review_status(
    db: AsyncSession,
    review_id: str,
) -> dict:
    """
    获取审查状态
    
    Args:
        db: 数据库会话
        review_id: 审查ID
        
    Returns:
        审查状态dict
    """
    # 查询审查记录
    review_result = await db.execute(
        select(AIReview).where(AIReview.review_id == review_id)
    )
    review = review_result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    
    # 查询Celery状态（如果任务正在执行）
    status = review.review_status

    if status == "reviewing" and review.celery_task_id:
        try:
            celery_result = _celery_async_result(review.celery_task_id)
            if celery_result.ready():
                if not celery_result.successful():
                    status = "failed"
        except Exception:
            pass
    
    return {
        "review_id": review.review_id,
        "status": status,
        "review_status": review.review_status,
        "overall_risk_level": review.overall_risk_level,
        "overall_risk_score": review.overall_risk_score,
    }


async def get_review_result(
    db: AsyncSession,
    review_id: str,
) -> dict:
    """
    获取审查结果
    
    Args:
        db: 数据库会话
        review_id: 审查ID
        
    Returns:
        审查结果dict
    """
    # 查询审查记录
    review_result = await db.execute(
        select(AIReview).where(AIReview.review_id == review_id)
    )
    review = review_result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    
    # 校验状态
    if review.review_status not in ["completed", "reviewed", "confirmed", "ai_done"]:
        raise HTTPException(
            status_code=400,
            detail=f"审查尚未完成，当前状态: {review.review_status}"
        )
    
    return {
        "review_id": review.review_id,
        "contract_id": review.contract_id,
        "version_id": review.version_id,
        "status": review.review_status,
        "overall_risk_level": review.overall_risk_level,
        "overall_risk_score": review.overall_risk_score,
        "recommendation": review.recommendation,
        "clause_reviews": review.clause_reviews,
        "rule_violations": review.rule_violations,
        "summary": review.summary,
        "model_version": review.model_version,
        "review_duration_seconds": review.review_duration_seconds,
        "reviewer_id": review.reviewer_id,
        "created_at": (await _review_created_at_iso(db, review)),
    }


async def retry_review(
    db: AsyncSession,
    review_id: str,
    user_id: int,
) -> dict:
    """
    重试失败的审查
    
    Args:
        db: 数据库会话
        review_id: 审查ID
        user_id: 重试发起人ID
        
    Returns:
        新的审查任务信息dict
    """
    # 查询审查记录
    review_result = await db.execute(
        select(AIReview).where(AIReview.review_id == review_id)
    )
    review = review_result.scalar_one_or_none()
    
    if not review:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    
    # 校验状态
    if review.review_status != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"仅失败的审查可重试，当前状态: {review.review_status}"
        )
    
    # 生成新的 review 记录（不 mutate 原 review_id）
    new_review_id = f"REV-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    new_review = AIReview(
        contract_id=review.contract_id,
        version_id=review.version_id,
        review_id=new_review_id,
        review_status="pending",
    )
    db.add(new_review)
    await db.flush()

    try:
        celery_result = _get_celery_review_task().delay(
            review.contract_id, review.version_id, new_review_id
        )
        task_id = celery_result.id if hasattr(celery_result, "id") else celery_result
    except Exception as e:
        logger.error("Failed to dispatch retry Celery task: %s", e)
        new_review.review_status = "failed"
        await db.flush()
        raise HTTPException(status_code=503, detail="AI审查服务暂时不可用") from e

    new_review.review_status = "reviewing"
    new_review.celery_task_id = task_id
    await db.flush()

    return {
        "review_id": new_review_id,
        "contract_id": review.contract_id,
        "version_id": review.version_id,
        "task_id": task_id,
        "status": "reviewing",
        "user_id": user_id,
        "message": "审查重试已启动",
    }


async def submit_feedback(
    db: AsyncSession,
    review_id: str,
    feedback_type: str,
    comment: Optional[str] = None,
) -> dict:
    """误报/漏报反馈，写入 summary JSON。"""
    import json as _json

    result = await db.execute(select(AIReview).where(AIReview.review_id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="审查记录不存在")

    summary = {}
    if review.summary:
        try:
            summary = _json.loads(review.summary)
        except _json.JSONDecodeError:
            summary = {"raw": review.summary}
    feedbacks = summary.get("feedbacks", [])
    feedbacks.append({"type": feedback_type, "comment": comment})
    summary["feedbacks"] = feedbacks
    review.summary = _json.dumps(summary, ensure_ascii=False)
    await db.flush()
    return {"review_id": review_id, "feedbacks": feedbacks}


async def confirm_review(
    db: AsyncSession,
    review_id: str,
    reviewer_id: int,
) -> dict:
    """法务确认 AI 报告。"""
    result = await db.execute(select(AIReview).where(AIReview.review_id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    if review.review_status not in ("ai_done", "reviewed", "confirmed"):
        raise HTTPException(
            status_code=400,
            detail=f"当前状态不可确认: {review.review_status}",
        )
    review.review_status = "reviewed"
    review.reviewer_id = reviewer_id
    await db.flush()
    return {
        "review_id": review_id,
        "review_status": review.review_status,
        "reviewer_id": reviewer_id,
    }
