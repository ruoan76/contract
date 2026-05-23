"""
JWT 认证工具

使用 python-jose 实现 token 签发与解码。
提供 FastAPI Depends 友好的 get_current_user 依赖。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.utils.exceptions import AuthError

security = HTTPBearer()


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """签发 access token。

    Args:
        data: payload 字典，通常包含 user_id 等身份信息。
        expires_delta: 过期时长，默认使用配置中的 ACCESS_TOKEN_EXPIRE_MINUTES。
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def     decode_token(token: str) -> dict[str, Any]:
    """解码并校验 JWT token。

    校验失败时抛出 AuthError。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AuthError(
            code=status.HTTP_401_UNAUTHORIZED,
            message=f"无效的认证凭据: {exc}",
        ) from exc

    user_id = payload.get("user_id")
    if user_id is None:
        raise AuthError(message="Token 中缺少 user_id")

    return payload


def extract_user_id(token: str) -> int | str:
    """从 token 中提取 user_id。

    快捷方法，适用于只需获取用户 ID 的场景。
    """
    payload = decode_token(token)
    return payload["user_id"]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """FastAPI 依赖：从请求 token 中获取当前用户 payload。

    使用方式:
        @router.get("/me")
        async def read_me(user: dict = Depends(get_current_user)):
            return user
    """
    token = credentials.credentials
    return decode_token(token)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int | str:
    """FastAPI 依赖：从请求 token 中直接提取 user_id。

    使用方式:
        @router.get("/me")
        async def read_me(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}
    """
    return extract_user_id(credentials.credentials)
