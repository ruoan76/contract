"""
Dependency injection utilities for FastAPI.

Provides reusable dependency functions:
- get_current_active_user: Get authenticated, active user
- check_permission: Role-based permission check
"""
from typing import Optional

from fastapi import Depends, HTTPException, status

from app.core.security import (
    get_current_user,
    get_current_active_user as security_get_current_active_user,
    check_permission as security_check_permission,
)
from app.db.database import get_db
from app.models.contract import User
from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Get the current active user from the request.

    This is a convenience wrapper that ensures:
    1. User is authenticated
    2. User account is active

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active User object

    Raises:
        HTTPException: If user is not authenticated or not active
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return current_user


async def check_permission(
    role_code: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Check if the current user has the required role.

    Args:
        role_code: Required role code (e.g., "admin", "manager")
        current_user: User from get_current_active_user dependency
        db: Database session

    Returns:
        User object if role matches

    Raises:
        HTTPException: If user doesn't have required role
    """
    from app.models.contract import Role

    if current_user.role_id:
        role = await db.get(Role, current_user.role_id)
        if role and role.code == role_code:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Requires role: {role_code}",
    )


async def require_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Require admin role for endpoint access.
    """
    from app.models.contract import Role

    if current_user.role_id:
        role = await db.get(Role, current_user.role_id)
        if role and role.code == "admin":
            return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


__all__ = [
    "get_current_active_user",
    "check_permission",
    "require_admin",
]
