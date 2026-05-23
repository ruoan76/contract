"""
风险预警 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.db.database import get_db
from app.models.contract import User
from app.schemas.contract import RiskHandleRequest
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", summary="风险列表")
async def list_risks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: Optional[str] = None,
    status: Optional[str] = None,
    contract_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取风险预警列表"""
    from app.models.contract import RiskAlert, Contract
    
    conditions = []
    if level:
        conditions.append(RiskAlert.alert_level == level)
    if status:
        conditions.append(RiskAlert.status == status)
    if contract_id:
        conditions.append(RiskAlert.contract_id == contract_id)
    
    query = (
        select(RiskAlert, Contract)
        .join(Contract, RiskAlert.contract_id == Contract.id)
        .where(*conditions)
        .order_by(RiskAlert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    result = await db.execute(query)
    items = result.all()
    
    # 总数
    count_query = select(func.count()).select_from(RiskAlert).where(*conditions)
    total = await db.scalar(count_query)
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": alert.id,
                    "contract_id": alert.contract_id,
                    "contract_no": contract.contract_no,
                    "type": alert.alert_type,
                    "level": alert.alert_level,
                    "title": alert.title,
                    "message": alert.message,
                    "source": alert.source,
                    "status": alert.status,
                    "created_at": alert.created_at,
                }
                for alert, contract in items
            ]
        }
    }


@router.get("/{risk_id}", summary="风险详情")
async def get_risk(
    risk_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取风险预警详情"""
    from app.models.contract import RiskAlert
    
    result = await db.execute(
        select(RiskAlert).where(RiskAlert.id == risk_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="风险预警不存在")
    
    return {
        "code": 200,
        "data": {
            "id": alert.id,
            "contract_id": alert.contract_id,
            "type": alert.alert_type,
            "level": alert.alert_level,
            "title": alert.title,
            "message": alert.message,
            "source": alert.source,
            "source_detail": alert.source_detail,
            "status": alert.status,
            "related_clause": alert.related_clause,
            "legal_basis": alert.legal_basis,
            "handler_id": alert.handler_id,
            "handle_comment": alert.handle_comment,
            "handle_time": alert.handle_time,
            "created_at": alert.created_at,
        }
    }


@router.post("/{risk_id}/handle", summary="处理风险")
async def handle_risk(
    risk_id: int,
    handle_in: RiskHandleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """处理风险预警"""
    from app.models.contract import RiskAlert
    from datetime import datetime
    
    result = await db.execute(
        select(RiskAlert).where(RiskAlert.id == risk_id)
    )
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="风险预警不存在")
    
    alert.status = handle_in.status
    alert.handler_id = user.id
    alert.handle_comment = handle_in.comment
    alert.handle_time = datetime.now()
    
    await db.flush()
    
    return {"code": 200, "message": "处理成功"}


@router.get("/statistics", summary="风险统计")
async def get_risk_statistics(
    db: AsyncSession = Depends(get_db),
):
    """获取风险统计"""
    from app.models.contract import RiskAlert
    
    # 按等级统计
    result = await db.execute(
        select(RiskAlert.alert_level, func.count())
        .group_by(RiskAlert.alert_level)
    )
    by_level = {row[0]: row[1] for row in result.all()}
    
    # 按状态统计
    result = await db.execute(
        select(RiskAlert.status, func.count())
        .group_by(RiskAlert.status)
    )
    by_status = {row[0]: row[1] for row in result.all()}
    
    # 按来源统计
    result = await db.execute(
        select(RiskAlert.source, func.count())
        .group_by(RiskAlert.source)
    )
    by_source = {row[0]: row[1] for row in result.all()}
    
    return {
        "code": 200,
        "data": {
            "total": sum(by_level.values()),
            "by_level": by_level,
            "by_status": by_status,
            "by_source": by_source,
        }
    }
