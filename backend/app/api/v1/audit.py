"""
审计日志 API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.db.database import get_db
from app.models.contract import AuditLog, User
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", summary="操作日志")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取审计日志列表"""
    conditions = [AuditLog.user_id == user.id]

    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    if start_date:
        try:
            conditions.append(AuditLog.created_at >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            conditions.append(AuditLog.created_at <= datetime.fromisoformat(end_date))
        except ValueError:
            pass

    count_query = select(func.count()).select_from(AuditLog).where(*conditions)
    total = await db.scalar(count_query)

    query = (
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "code": 200,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "username": log.username or "system",
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "resource_name": log.resource_name,
                    "detail": log.detail,
                    "ip_address": log.ip_address,
                    "status": log.status,
                    "created_at": log.created_at,
                }
                for log in logs
            ],
        },
    }
