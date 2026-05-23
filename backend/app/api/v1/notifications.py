"""
通知 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contract import User
from app.services.notification_service import list_notifications, mark_notification_read
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", summary="通知列表")
async def notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await list_notifications(
        db, user_id=user.id, page=page, page_size=page_size, unread_only=unread_only
    )
    return {"code": 200, "data": data}


@router.patch("/{notification_id}/read", summary="标记已读")
async def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await mark_notification_read(db, notification_id, user.id)
    return {"code": 200, "data": data}
