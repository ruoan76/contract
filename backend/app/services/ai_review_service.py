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

logger = logging.getLogger(__name__)

# 导入Celery任务 - 假设已定义
# from app.celery_tasks.ai_review_tasks import execute_review_task

# 为了代码可运行，这里使用动态导入
try:
    from app.celery_tasks.ai_review_tasks import execute_contract_review as execute_review_task
except ImportError:
    class execute_review_task:
        @staticmethod
        def delay(contract_id: int, version_id: int) -> str:
            return f"celery_task_{uuid.uuid4().hex[:8]}"
        
        @staticmethod
        def AsyncResult(task_id: str):
            return CeleryAsyncResult(task_id)


class CeleryAsyncResult:
    """模拟 Celery AsyncResult"""
    def __init__(self, task_id: str):
        self.id = task_id
        self._status = "PENDING"
        self._result = None
    
    @property
    def status(self) -> str:
        return self._status
    
    @property
    def result(self):
        return self._result
    
    def ready(self) -> bool:
        return self._status in ["SUCCESS", "FAILURE"]
    
    def successful(self) -> bool:
        return self._status == "SUCCESS"


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

    # Mock 模式：同步执行审查
    if settings.AI_REVIEW_MOCK:
        import json as _json
        ai_review.review_status = "ai_done"
        ai_review.overall_risk_level = "medium"
        ai_review.overall_risk_score = 65.0
        ai_review.recommendation = "建议关注付款条款"
        ai_review.clause_reviews = _json.dumps([], ensure_ascii=False)
        ai_review.rule_violations = _json.dumps([], ensure_ascii=False)
        ai_review.summary = _json.dumps({"mock": True}, ensure_ascii=False)
        ai_review.model_version = "mock"
        await db.flush()
        return {
            "review_id": review_id,
            "contract_id": contract_id,
            "version_id": version_id,
            "status": "ai_done",
            "user_id": user_id,
            "username": username,
            "created_at": ai_review.created_at.isoformat() if ai_review.created_at else None,
        }
    
    # 调用Celery异步任务
    try:
        celery_result = execute_review_task.delay(contract_id, version_id)
        task_id = celery_result.id if hasattr(celery_result, "id") else celery_result
    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}")
        # 如果 Celery 不可用，设置为失败状态
        ai_review.review_status = "failed"
        await db.flush()
        raise HTTPException(status_code=503, detail="AI审查服务暂时不可用")
    
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
        "created_at": ai_review.created_at.isoformat() if ai_review.created_at else None,
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
    
    if status == "reviewing" and hasattr(review, "celery_task_id") and review.celery_task_id:
        try:
            celery_result = execute_review_task.AsyncResult(review.celery_task_id)
            if celery_result.ready():
                if celery_result.successful():
                    status = "completed"
                else:
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
        "created_at": review.created_at.isoformat() if review.created_at else None,
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
    
    # 生成新的 review_id
    new_review_id = f"REV-{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    
    # 更新审查记录
    review.review_id = new_review_id
    review.review_status = "pending"
    review.celery_task_id = None
    await db.flush()
    
    # 调用Celery异步任务
    try:
        celery_result = execute_review_task.delay(review.contract_id, review.version_id)
        task_id = celery_result.id if hasattr(celery_result, "id") else celery_result
    except Exception as e:
        logger.error(f"Failed to dispatch retry Celery task: {e}")
        raise HTTPException(status_code=503, detail="AI审查服务暂时不可用")
    
    # 更新状态为reviewing
    review.review_status = "reviewing"
    review.celery_task_id = task_id
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
