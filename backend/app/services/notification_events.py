"""
业务事件 → 通知写入（V1 Stretch：同步写入 notifications 表）
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import User, Role
from app.services.notification_service import create_notification


async def _user_id_by_role(db: AsyncSession, role_code: str) -> Optional[int]:
    result = await db.execute(
        select(User.id)
        .join(Role, User.role_id == Role.id)
        .where(Role.code == role_code, User.status == 1)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def notify_user(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
) -> None:
    if not user_id:
        return
    await create_notification(
        db,
        user_id=user_id,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )


async def notify_role(
    db: AsyncSession,
    role_code: str,
    title: str,
    message: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
) -> None:
    uid = await _user_id_by_role(db, role_code)
    if uid:
        await notify_user(db, uid, title, message, resource_type, resource_id)


async def notify_approval_pending(
    db: AsyncSession,
    approver_id: Optional[int],
    contract_id: int,
    contract_title: str,
) -> None:
    await notify_user(
        db,
        approver_id or 0,
        title="待办审批",
        message=f"合同「{contract_title}」待您审批",
        resource_type="contract",
        resource_id=contract_id,
    )


async def notify_review_returned(
    db: AsyncSession,
    creator_id: Optional[int],
    contract_id: int,
    comment: Optional[str] = None,
) -> None:
    await notify_user(
        db,
        creator_id or 0,
        title="评审退回",
        message=comment or f"合同 #{contract_id} 已被退回，请修订后重新提交",
        resource_type="contract",
        resource_id=contract_id,
    )


async def notify_seal_pending(db: AsyncSession, contract_id: int) -> None:
    await notify_role(
        db,
        "admin",
        title="用印待确认",
        message=f"合同 #{contract_id} 已申请用印，请确认",
        resource_type="contract",
        resource_id=contract_id,
    )


async def notify_archived(
    db: AsyncSession,
    creator_id: Optional[int],
    contract_id: int,
    location: str,
) -> None:
    await notify_user(
        db,
        creator_id or 0,
        title="归档完成",
        message=f"合同 #{contract_id} 已归档至 {location}",
        resource_type="contract",
        resource_id=contract_id,
    )
