"""
JWT Token Utilities and Authentication Support

Provides JWT token creation/verification using python-jose and password
hashing using passlib with bcrypt. Includes OAuth2 password bearer scheme
and dependency for extracting the current user from JWT tokens.

Features:
- Token creation with configurable expiration
- Token verification and decoding
- Password hashing and verification
- OAuth2 password bearer scheme for FastAPI dependencies
- Async user lookup from JWT tokens

Imports:
    settings from app.core.config
    get_db from app.db.database
    User from app.models.contract

 Raises:
    HTTPException(401) on invalid/expired tokens
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.models.contract import User

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password bearer scheme for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/system/login",
    description="JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
)

# Token configuration from settings
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token with encoded data.

    Args:
        data: Dictionary containing token claims (e.g., {"sub": user_id, "role": "admin"})
        expires_delta: Optional timedelta for custom expiration. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": str(user.id), "role": "admin"})
        >>> decoded = decode_token(token)
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
    Decode and verify a JWT token, returning its payload.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload dictionary

    Raises:
        JWTError: If token is invalid or cannot be decoded
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Bcrypt hashed password string

    Example:
        >>> hashed = get_password_hash("my-password")
        >>> verify_password("my-password", hashed)
        True
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain text password against a bcrypt hash.

    Args:
        plain: Plain text password to verify
        hashed: Bcrypt hashed password to compare against

    Returns:
        True if password matches the hash, False otherwise

    Example:
        >>> is_valid = verify_password("my-password", user.password_hash)
        >>> if is_valid:
        >>>     # Login successful
    """
    return pwd_context.verify(plain, hashed)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Get the current authenticated user from JWT token.

    This function is designed to be used as a FastAPI dependency.
    It validates the JWT token and fetches the user from the database.

    Args:
        db: Database session (injected by FastAPI dependency)
        token: JWT token from Authorization header (injected by FastAPI)

    Returns:
        User object from database

    Raises:
        HTTPException(401): If token is invalid, expired, or user not found

    Example:
        >>> @router.get("/users/me")
        >>> async def read_current_user(user: User = Depends(get_current_user)):
        >>>     return user
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
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


__all__ = [
    "create_access_token",
    "decode_token",
    "get_password_hash",
    "verify_password",
    "oauth2_scheme",
    "get_current_user",
]
