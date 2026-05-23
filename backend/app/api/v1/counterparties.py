"""
相对方管理 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_role
from app.db.database import get_db
from app.exceptions import BusinessError
from app.models.contract import User
from app.schemas.counterparty import CounterpartyCreate, CounterpartyUpdate
from app.services.counterparty_service import (
    add_to_blacklist,
    create_counterparty,
    get_counterparty,
    list_counterparties,
    update_counterparty,
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", summary="相对方列表")
async def list_cp(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    is_blacklist: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    data = await list_counterparties(
        db, page=page, page_size=page_size, keyword=keyword, is_blacklist=is_blacklist
    )
    return {"code": 200, "data": data}


@router.get("/{cp_id}", summary="相对方详情")
async def get_cp(cp_id: int, db: AsyncSession = Depends(get_db)):
    try:
        data = await get_counterparty(db, cp_id)
        return {"code": 200, "data": data}
    except BusinessError:
        raise HTTPException(status_code=404, detail="相对方不存在")


@router.post("/", summary="创建相对方")
async def create_cp(
    body: CounterpartyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await create_counterparty(db, body.model_dump())
        return {"code": 200, "data": data}
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{cp_id}", summary="更新相对方")
async def update_cp(
    cp_id: int,
    body: CounterpartyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await update_counterparty(db, cp_id, body.model_dump(exclude_unset=True))
        return {"code": 200, "data": data}
    except BusinessError:
        raise HTTPException(status_code=404, detail="相对方不存在")


@router.post("/{cp_id}/blacklist", summary="加入黑名单")
async def blacklist_cp(
    cp_id: int,
    body: dict,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    reason = body.get("reason", "违规合作")
    try:
        data = await add_to_blacklist(db, cp_id, reason)
        return {"code": 200, "data": data}
    except BusinessError:
        raise HTTPException(status_code=404, detail="相对方不存在")
