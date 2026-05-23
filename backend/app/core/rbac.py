"""
RBAC 依赖工厂 — 供 FastAPI Depends 按角色校验。
"""
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.contract import Role, User


async def get_user_role_code(db: AsyncSession, user: User) -> str | None:
    """解析用户角色 code。"""
    if not user.role_id:
        return None
    role = await db.get(Role, user.role_id)
    return role.code if role else None


async def assert_user_has_role(
    db: AsyncSession,
    user: User,
    role_code: str,
) -> None:
    """校验用户角色，不匹配则 403。"""
    actual = await get_user_role_code(db, user)
    if actual != role_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires role: {role_code}",
        )


def require_role(role_code: str) -> Callable:
    """单角色依赖工厂。"""

    async def _dependency(
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        await assert_user_has_role(db, user, role_code)
        return user

    return _dependency


def require_any_role(*role_codes: str) -> Callable:
    """多角色之一即可访问。"""

    allowed = frozenset(role_codes)

    async def _dependency(
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        actual = await get_user_role_code(db, user)
        if actual not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(sorted(allowed))}",
            )
        return user

    return _dependency


__all__ = [
    "assert_user_has_role",
    "get_user_role_code",
    "require_any_role",
    "require_role",
]
