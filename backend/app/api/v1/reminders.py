"""到期提醒 API"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contract import Contract, User
from app.services.notification_service import create_notification
from app.utils.auth import get_current_user
from app.utils.feishu import send_feishu_webhook

router = APIRouter()


class ExpirationReminderRequest(BaseModel):
    """到期提醒请求"""

    days_ahead: int = Field(30, ge=1, le=365, description="提前多少天提醒")
    contract_ids: Optional[list[int]] = Field(None, description="指定合同 ID，为空则扫描即将到期合同")
    user_ids: Optional[list[int]] = Field(None, description="通知接收人，为空则通知合同创建人")


@router.post("/expiration", summary="合同到期提醒")
async def create_expiration_reminders(
    body: ExpirationReminderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """扫描即将到期合同，创建站内通知并可选推送飞书。"""
    today = date.today()
    deadline = today + timedelta(days=body.days_ahead)

    query = select(Contract).where(
        Contract.end_date.isnot(None),
        Contract.end_date >= today,
        Contract.end_date <= deadline,
        Contract.status.in_(["executing", "approved", "signed"]),
    )
    if body.contract_ids:
        query = query.where(Contract.id.in_(body.contract_ids))

    result = await db.execute(query)
    contracts = result.scalars().all()

    notifications_created: list[dict] = []
    for contract in contracts:
        target_users = body.user_ids or [contract.creator_id]
        days_left = (contract.end_date - today).days if contract.end_date else body.days_ahead
        title = f"合同即将到期：{contract.title}"
        message = (
            f"合同 {contract.contract_no} 将于 {contract.end_date} 到期"
            f"（剩余 {days_left} 天），请及时处理续签或归档。"
        )
        for uid in set(target_users):
            if not uid:
                continue
            n = await create_notification(
                db=db,
                user_id=uid,
                title=title,
                message=message,
                resource_type="contract",
                resource_id=contract.id,
                channel="system",
            )
            notifications_created.append(n)

            # WebSocket 广播（若已连接客户端）
            try:
                from app.api.v1.ws_notifications import broadcast_notification

                await broadcast_notification(
                    {
                        "type": "expiration_reminder",
                        "user_id": uid,
                        "notification": n,
                    }
                )
            except Exception:
                pass

        await send_feishu_webhook(
            f"{message}\n合同 ID: {contract.id}",
            title="合同到期提醒",
        )

    await db.flush()

    return {
        "code": 200,
        "data": {
            "contracts_scanned": len(contracts),
            "notifications_created": len(notifications_created),
            "items": notifications_created,
        },
    }
