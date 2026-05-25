"""
AI 审查异步任务
"""
import logging
from datetime import datetime

from celery import Task
from sqlalchemy import select

from app.celery_tasks import celery_app
from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import Contract, ContractVersion, AIReview
from app.services.ai_review.runner import run_contract_ai_review
from app.services.ai_review_service import persist_review_result
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)


@celery_app.task(
    name="ai_review.contract_review",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
async def execute_contract_review(
    self: Task,
    contract_id: int,
    version_id: int,
    review_id: str,
) -> dict:
    """
    执行合同 AI 审查任务（更新 start_review 已创建的记录）。

    Args:
        contract_id: 合同 ID
        version_id: 合同版本 ID
        review_id: 审查记录 ID（与 ai_reviews.review_id 一致）
    """
    async with async_session() as session:
        try:
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
            payload = await run_contract_ai_review(
                text,
                contract_type=contract.contract_type or "other",
                amount=contract.amount,
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

        except Exception as exc:
            logger.error("AI review failed for contract %s: %s", contract_id, exc)
            try:
                review_result = await session.execute(
                    select(AIReview).where(AIReview.review_id == review_id)
                )
                ai_review = review_result.scalar_one_or_none()
                if ai_review:
                    ai_review.review_status = "failed"
                    await session.commit()
            except Exception:
                await session.rollback()

            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc) from exc
            raise BusinessError(f"AI review failed: {exc}") from exc
