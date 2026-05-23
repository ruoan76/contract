"""
归档台账 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import date, timedelta

from app.db.database import get_db
from app.models.contract import User
from app.services.archive_service import archive_contract, get_archive_records
from app.utils.auth import get_current_user

router = APIRouter()


@router.post("/{contract_id}/archive", summary="归档合同")
async def archive(
    contract_id: int,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """归档合同"""
    location = body.get("archive_location")
    
    if not location:
        return {"code": 400, "message": "归档位置不能为空"}
    
    result = await archive_contract(
        contract_id=contract_id,
        location=location,
        archived_by=user.id,
        db=db,
    )
    return {"code": 200, "message": "归档成功", "data": result}


@router.get("/ledger", summary="合同台账")
async def get_contract_ledger(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取合同台账"""
    from app.models.contract import Contract
    
    conditions = [Contract.archive_date.isnot(None)]
    
    if contract_type:
        conditions.append(Contract.contract_type == contract_type)
    if status:
        conditions.append(Contract.status == status)
    if keyword:
        conditions.extend([
            Contract.title.contains(keyword),
            Contract.counterparty_name.contains(keyword),
            Contract.contract_no.contains(keyword),
        ])
    
    # 总数
    count_query = select(func.count()).select_from(Contract).where(*conditions)
    total = await db.scalar(count_query)
    
    # 分页
    query = (
        select(Contract)
        .where(*conditions)
        .order_by(Contract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    contracts = result.scalars().all()
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": c.id,
                    "contract_no": c.contract_no,
                    "title": c.title,
                    "contract_type": c.contract_type,
                    "counterparty_name": c.counterparty_name,
                    "amount": c.amount,
                    "status": c.status,
                    "start_date": c.start_date,
                    "end_date": c.end_date,
                    "risk_level": c.risk_level,
                    "created_at": c.created_at,
                    "archive_date": c.archive_date,
                    "archive_location": c.archive_location,
                }
                for c in contracts
            ]
        }
    }


@router.get("/expired", summary="到期合同")
async def get_expired_contracts(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """获取即将到期合同"""
    from app.models.contract import Contract
    
    today = date.today()
    future_date = today + timedelta(days=days)
    
    result = await db.execute(
        select(Contract)
        .where(Contract.end_date <= future_date)
        .where(Contract.end_date >= today)
        .where(Contract.status.in_(["approved", "sealed"]))
        .where(Contract.archive_date.isnot(None))
        .order_by(Contract.end_date)
    )
    contracts = result.scalars().all()
    
    return {
        "code": 200,
        "data": {
            "total": len(contracts),
            "items": [
                {
                    "id": c.id,
                    "contract_no": c.contract_no,
                    "title": c.title,
                    "end_date": c.end_date,
                    "days_remaining": (c.end_date - today).days,
                    "counterparty_name": c.counterparty_name,
                }
                for c in contracts
            ]
        }
    }
