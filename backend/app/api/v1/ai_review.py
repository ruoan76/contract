"""
AI 审查 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.contract import User
from app.schemas.contract import AIReviewRequest, AIReviewResult
from app.services.ai_review_service import start_review, get_review_status, get_review_result, submit_feedback
from app.utils.auth import get_current_user
from app.exceptions import BusinessError

router = APIRouter()


@router.post("/review", summary="发起合同审查")
async def review_contract(
    body: AIReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发起 AI 合同审查"""
    from app.models.contract import Contract, ContractVersion
    
    # 获取合同
    result = await db.execute(
        select(Contract).where(Contract.id == body.contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    
    if not contract.content:
        raise HTTPException(status_code=400, detail="合同内容为空")
    
    # 获取当前版本
    result = await db.execute(
        select(ContractVersion)
        .where(ContractVersion.contract_id == contract.id)
        .order_by(ContractVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    
    if not version:
        raise HTTPException(status_code=404, detail="合同版本不存在")
    
    # 启动审查
    result = await start_review(
        db=db,
        contract_id=contract.id,
        version_id=version.id,
        user_id=user.id,
        username=user.username,
    )
    
    return {
        "code": 200,
        "data": {
            "review_id": result["review_id"],
            "status": result["status"],
            "estimated_seconds": 30,
        }
    }


@router.get("/{review_id}/result", summary="审查结果")
async def get_review_result_endpoint(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 审查结果"""
    try:
        # 先获取状态
        status_result = await get_review_status(db=db, review_id=review_id)
        
        if status_result["status"] == "pending":
            return {
                "code": 200,
                "data": {
                    "review_id": review_id,
                    "status": "pending",
                    "message": "审查尚未开始",
                }
            }
        
        if status_result["status"] == "reviewing":
            return {
                "code": 200,
                "data": {
                    "review_id": review_id,
                    "status": "reviewing",
                    "message": "审查进行中，请稍候...",
                }
            }
        
        # 获取完整结果
        result = await get_review_result(db=db, review_id=review_id)
        
        return {
            "code": 200,
            "data": {
                "review_id": result["review_id"],
                "status": result["status"],
                "overall": {
                    "risk_level": result["overall_risk_level"],
                    "risk_score": result["overall_risk_score"],
                    "recommendation": result["recommendation"],
                },
                "clauses": result.get("clause_reviews", []),
                "rule_violations": result.get("rule_violations", []),
                "summary": result.get("summary", {}),
                "review_time": result["created_at"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{review_id}/feedback", summary="审查反馈（误报/漏报）")
async def feedback(
    review_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback_type = body.get("type", "false_positive")
    comment = body.get("comment")
    data = await submit_feedback(db, review_id, feedback_type, comment)
    return {"code": 200, "data": data}


@router.get("/contracts/{contract_id}/latest-review", summary="最新审查结果")
async def get_latest_review(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取合同最新审查结果"""
    import json

    from app.models.contract import AIReview

    def _parse_json_field(raw: str | None):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    result = await db.execute(
        select(AIReview)
        .where(AIReview.contract_id == contract_id)
        .order_by(AIReview.created_at.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="暂无审查记录")

    return {
        "code": 200,
        "data": {
            "review_id": review.review_id,
            "review_status": review.review_status,
            "risk_level": review.overall_risk_level,
            "risk_score": review.overall_risk_score,
            "clause_reviews": _parse_json_field(review.clause_reviews),
            "summary": _parse_json_field(review.summary),
            "review_time": review.created_at,
        },
    }
