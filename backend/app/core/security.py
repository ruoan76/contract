"""
Security module - JWT token handling, password hashing, authentication dependencies.

This module provides:
- JWT token generation and verification
- Password hashing using bcrypt
- Dependency functions for protected endpoints
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.contract import User

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for JWT token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/system/login",
    description="JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
)

# Token configuration
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT access token.

    Args:
        data: Dictionary containing token claims (e.g., {"sub": user_id, "role": "admin"})
        expires_delta: Optional timedelta for custom expiration

    Returns:
        Encoded JWT token string

    Example:
        ```python
        token = create_access_token({"sub": str(user.id), "role": "admin"})
        ```
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload dictionary

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise e


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string

    Example:
        ```python
        hashed = get_password_hash("my-secret-password")
        ```
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain: Plain text password to verify
        hashed: Hashed password to compare against

    Returns:
        True if password matches, False otherwise

    Example:
        ```python
        if verify_password("my-password", user.password_hash):
            # Password matches
        ```
    """
    return pwd_context.verify(plain, hashed)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.

    This function is designed to be used as a FastAPI dependency.
    It decodes the token and fetches the user from the database.

    Args:
        db: Database session (injected by FastAPI)
        token: JWT token from Authorization header (injected by FastAPI)

    Returns:
        User object if token is valid, None otherwise

    Raises:
        HTTPException: If token is invalid or user not found

    Example:
        ```python
        @app.get("/users/me")
        async def read_users_me(current_user: User = Depends(get_current_user)):
            return current_user
        ```
    """
    try:
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.get(User, int(user_id))
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return result
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Raises exception if user is disabled.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        Active User object

    Raises:
        HTTPException: If user is disabled

    Example:
        ```python
        @app.get("/users/me")
        async def read_users_me(
            current_user: User = Depends(get_current_active_user)
        ):
            return current_user
        ```
    """
    if not current_user.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def check_permission(
    required_role: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Check if current user has the required role.

    Args:
        required_role: Role code to check against
        current_user: User from get_current_active_user dependency
        db: Database session

    Returns:
        User object if role matches

    Raises:
        HTTPException: If user doesn't have required role

    Example:
        ```python
        from app.core.rbac import require_role

        @app.post("/admin/action")
        async def admin_action(
            current_user: User = Depends(require_role("admin")),
        ):
            return {"message": "Admin action performed"}
        ```
    """
    from app.models.contract import Role

    if current_user.role_id:
        role = await db.get(Role, current_user.role_id)
        if role and role.code == required_role:
            return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Requires role: {required_role}",
    )


__all__ = [
    "create_access_token",
    "decode_token",
    "get_password_hash",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "check_permission",
    "oauth2_scheme",
]
