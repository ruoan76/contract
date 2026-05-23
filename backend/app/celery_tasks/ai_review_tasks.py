"""
AI 审查异步任务
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from celery import Task

from app.celery_tasks import celery_app
from app.core.config import settings
from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import Contract, ContractVersion, AIReview
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)


async def _call_ai_engine(contract_content: str, contract_no: str) -> dict:
    """
    调用 AI 引擎进行合同审查
    
    Args:
        contract_content: 合同内容
        contract_no: 合同编号
        
    Returns:
        dict AI 审查结果
    """
    """调用实际 AI 审查引擎"""
    # 这里仅仅是模拟
    return {
        "overall_risk_level": "low",
        "overall_risk_score": 15.0,
        "recommendation": "合同审查通过",
        "clause_reviews": [],
        "rule_violations": [],
        "summary": {
            "total_clauses": 0,
            "risk_clauses": 0,
            "suggestions": [],
        },
        "model_version": "qwen3.6-35B-A3B-4bit",
        "review_duration_seconds": 0,
    }


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
) -> dict:
    """
    执行合同 AI 审查任务
    
    Args:
        self: Celery task 实例
        contract_id: 合同ID
        version_id: 合同版本ID
        
    Returns:
        dict 审查结果
        
    Raises:
        BusinessError: 审查失败
    """
    from app.db.database import async_session
    
    # 使用独立试会话
    async with async_session() as session:
        try:
            # 查询合同
            from sqlalchemy import select
            from app.models.contract import Contract, ContractVersion
            
            result = await session.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = result.scalar_one_or_none()
            
            if not contract:
                raise BusinessError(f"Contract {contract_id} not found")
            
            # 查询版本
            result = await session.execute(
                select(ContractVersion).where(
                    ContractVersion.id == version_id
                )
            )
            version = result.scalar_one_or_none()
            
            if not version:
                raise BusinessError(f"ContractVersion {version_id} not found")
            
            # 调用 AI 引擎
            start_time = datetime.now()
            review_result = await _call_ai_engine(version.content or "", contract.contract_no)
            duration = (datetime.now() - start_time).total_seconds()
            
            # 保存审查结果
            ai_review = AIReview(
                contract_id=contract_id,
                version_id=version_id,
                review_id=f"REV-{contract.contract_no}-{version.version:04d}",
                overall_risk_level=review_result.get("overall_risk_level", "low"),
                overall_risk_score=review_result.get("overall_risk_score", 0.0),
                recommendation=review_result.get("recommendation", ""),
                clause_reviews=json.dumps(review_result.get("clause_reviews", []), ensure_ascii=False),
                rule_violations=json.dumps(review_result.get("rule_violations", []), ensure_ascii=False),
                summary=json.dumps(review_result.get("summary", {}), ensure_ascii=False),
                model_version=review_result.get("model_version", ""),
                review_duration_seconds=int(duration),
                review_status="ai_done",
            )
            session.add(ai_review)
            await session.flush()
            
            # 记录审计日志
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
                "created_at": ai_review.created_at.isoformat() if ai_review.created_at else None,
            }
            
        except Exception as exc:
            logger.error(f"AI review failed for contract {contract_id}: {exc}")
            # 重试机制
            if self.request.retries < self.max_retries:
                raise self.retry(exc=exc)
            raise BusinessError(f"AI review failed: {str(exc)}")
