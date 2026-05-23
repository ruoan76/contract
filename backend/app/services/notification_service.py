"""
通知服务
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Notification


async def create_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
) -> dict:
    n = Notification(
        user_id=user_id,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(n)
    await db.flush()
    return {
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


async def list_notifications(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> dict:
    conditions = [Notification.user_id == user_id]
    if unread_only:
        conditions.append(Notification.is_read == 0)
    total = await db.scalar(
        select(func.count()).select_from(Notification).where(*conditions)
    )
    result = await db.execute(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "resource_type": n.resource_type,
            "resource_id": n.resource_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in result.scalars().all()
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def mark_notification_read(db: AsyncSession, notification_id: int, user_id: int) -> dict:
    n = await db.get(Notification, notification_id)
    if not n or n.user_id != user_id:
        return {"success": False}
    n.is_read = 1
    await db.flush()
    return {"success": True, "id": notification_id}
