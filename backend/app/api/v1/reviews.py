"""
评审域 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import assert_user_has_role
from app.db.database import get_db
from app.models.contract import User
from app.schemas.review import ReviewOpinionSubmit, ReviewReturnRequest
from app.services.review_service import (
    get_pending_reviews,
    get_review_history,
    get_review_workspace,
    return_for_revision,
    submit_opinion,
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/pending", summary="评审待办")
async def pending(
    role: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    data = await get_pending_reviews(db, role=role, page=page, page_size=page_size)
    return {"code": 200, "data": data}


@router.get("/contracts/{contract_id}", summary="评审工作台")
async def workspace(contract_id: int, db: AsyncSession = Depends(get_db)):
    data = await get_review_workspace(db, contract_id)
    return {"code": 200, "data": data}


@router.post("/contracts/{contract_id}/opinions", summary="提交评审意见")
async def opinions(
    contract_id: int,
    body: ReviewOpinionSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await assert_user_has_role(db, user, body.role)
    data = await submit_opinion(
        db,
        contract_id,
        body.role,
        body.action,
        body.comment,
        user.id,
        user.real_name,
    )
    return {"code": 200, "data": data}


@router.post("/contracts/{contract_id}/return", summary="退回修改")
async def return_contract(
    contract_id: int,
    body: ReviewReturnRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await return_for_revision(
        db, contract_id, body.role, body.comment, user.id, user.real_name
    )
    return {"code": 200, "data": data}


@router.get("/contracts/{contract_id}/history", summary="评审历史")
async def history(contract_id: int, db: AsyncSession = Depends(get_db)):
    data = await get_review_history(db, contract_id)
    return {"code": 200, "data": data}
