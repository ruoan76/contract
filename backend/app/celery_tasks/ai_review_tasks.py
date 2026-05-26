"""
AI 审查异步任务
"""
import asyncio
import logging
from datetime import datetime

from celery import Task
from sqlalchemy import select

from app.celery_tasks import celery_app
from app.db.database import async_session, reset_async_engine
from app.exceptions import BusinessError
from app.models.contract import Contract, ContractVersion, AIReview
from app.services.ai_review.context_loader import load_review_context
from app.services.ai_review.runner import run_contract_ai_review
from app.services.ai_review_service import persist_review_result
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)


async def _execute_contract_review_async(
    contract_id: int,
    version_id: int,
    review_id: str,
) -> dict:
    async with async_session() as session:
        review_result = await session.execute(
            select(AIReview).where(AIReview.review_id == review_id)
        )
        ai_review = review_result.scalar_one_or_none()
        if not ai_review:
            raise BusinessError(f"AIReview {review_id} not found")

        contract_result = await session.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = contract_result.scalar_one_or_none()
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")

        version_result = await session.execute(
            select(ContractVersion).where(ContractVersion.id == version_id)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise BusinessError(f"ContractVersion {version_id} not found")

        text = (version.content or contract.content or "").strip()
        ai_review.review_status = "reviewing"
        await session.flush()

        started = datetime.now()
        ctx = await load_review_context(
            session,
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
        payload["review_duration_seconds"] = int(
            (datetime.now() - started).total_seconds()
        )
        await persist_review_result(
            session, ai_review, payload, contract_id, version_id
        )

        await log_action(
            user_id=contract.creator_id,
            action="ai_review_completed",
            resource_type="contract",
            resource_id=contract_id,
            detail={
                "review_id": ai_review.review_id,
                "risk_level": ai_review.overall_risk_level,
                "risk_score": ai_review.overall_risk_score,
            },
            db=session,
        )

        await session.commit()
        await session.refresh(ai_review)

        return {
            "review_id": ai_review.review_id,
            "contract_id": contract_id,
            "version_id": version_id,
            "overall_risk_level": ai_review.overall_risk_level,
            "overall_risk_score": ai_review.overall_risk_score,
            "recommendation": ai_review.recommendation,
            "review_duration_seconds": ai_review.review_duration_seconds,
            "review_status": ai_review.review_status,
        }


@celery_app.task(
    name="ai_review.contract_review",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def execute_contract_review(
    self: Task,
    contract_id: int,
    version_id: int,
    review_id: str,
) -> dict:
    """Celery sync wrapper — 内部 asyncio.run 执行异步审查。"""
    reset_async_engine()
    try:
        return asyncio.run(
            _execute_contract_review_async(contract_id, version_id, review_id)
        )
    except Exception as exc:
        logger.error("AI review failed for contract %s: %s", contract_id, exc)
        try:
            reset_async_engine()
            asyncio.run(_mark_review_failed(review_id))
        except Exception:
            logger.exception("Failed to mark review %s as failed", review_id)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise BusinessError(f"AI review failed: {exc}") from exc


async def _mark_review_failed(review_id: str) -> None:
    async with async_session() as session:
        result = await session.execute(
            select(AIReview).where(AIReview.review_id == review_id)
        )
        ai_review = result.scalar_one_or_none()
        if ai_review:
            ai_review.review_status = "failed"
            await session.commit()
