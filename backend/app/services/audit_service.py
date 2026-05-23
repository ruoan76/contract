"""
审计日志服务
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: int,
    detail: Optional[dict] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    """
    记录审计日志
    
    Args:
        user_id: 用户ID
        action: 操作动作
        resource_type: 资源类型
        resource_id: 资源ID
        detail: 操作详情
        db: 数据库会话（可选）
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=json.dumps(detail or {}, ensure_ascii=False, default=str),
        )
        session.add(audit_log)
        await session.flush()
    finally:
        if use_own_session:
            await session.close()


async def get_audit_logs(
    user_id: int,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Optional[AsyncSession] = None,
) -> list:
    """
    获取审计日志列表
    
    Args:
        user_id: 用户ID
        resource_type: 资源类型（可选）
        action: 操作动作（可选）
        page: 页码
        page_size: 每页数量
        db: 数据库会话（可选）
        
    Returns:
        list 审计日志列表
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        conditions = [AuditLog.user_id == user_id]
        
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if action:
            conditions.append(AuditLog.action == action)
        
        # 查询总数
        count_query = select(func.count()).select_from(AuditLog).where(*conditions)
        total = await session.scalar(count_query)
        
        # 查询列表
        query = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(query)
        logs = result.scalars().all()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "resource_name": log.resource_name,
                    "detail": json.loads(log.detail) if log.detail else {},
                    "status": log.status,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        }
    finally:
        if use_own_session:
            await session.close()
