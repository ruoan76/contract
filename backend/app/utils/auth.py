"""Authentication utilities - re-exports from core.security for convenience."""
from app.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
    get_current_user,
    get_current_active_user,
    check_permission,
    oauth2_scheme,
    pwd_context,
    ALGORITHM,
    SECRET_KEY,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# Backward-compatible aliases
oauth2_bearer = oauth2_scheme
decode_access_token = decode_token
verify_access_token = decode_token

__all__ = [
    "create_access_token",
    "decode_token",
    "decode_access_token",
    "verify_access_token",
    "get_password_hash",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "check_permission",
    "oauth2_scheme",
    "oauth2_bearer",
    "pwd_context",
    "ALGORITHM",
    "SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]
