"""
Authentication middleware.

Checks Authorization header for JWT token verification.
Attaches user_id to request.state for downstream use.
Skips auth for public endpoints.
"""
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError

from app.core.config import settings


# Public endpoints that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/api/v1/auth/login",
    "/api/v1/system/login",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests using JWT tokens.
    
    Extracts user_id from JWT token and attaches to request.state.current_user_id.
    Skips auth for public paths. Logs auth failures but doesn't block.
    """

    def __init__(self, app):
        super().__init__(app)
        self.algorithm = settings.ALGORITHM
        self.secret_key = settings.SECRET_KEY

    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        """
        Process request and verify authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        # Skip auth for public paths
        if self._is_public_path(request):
            return await call_next(request)

        # Extract and verify token
        user_id = await self._verify_request_token(request)

        # Attach to request state if valid
        if user_id is not None:
            request.state.current_user_id = user_id

        return await call_next(request)

    def _is_public_path(self, request: Request) -> bool:
        """Check if request path is public."""
        path = request.url.path
        return any(path.startswith(prefix) for prefix in PUBLIC_PATHS)

    async def _verify_request_token(self, request: Request) -> Optional[int]:
        """
        Verify JWT token from Authorization header.

        Args:
            request: HTTP request

        Returns:
            User ID if valid, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None

        # Check Bearer scheme
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]

        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            user_id = payload.get("sub")
            
            if user_id is None:
                return None

            # Validate expiration
            from time import time as time_time
            exp = payload.get("exp")
            if exp is not None:
                if time_time() > exp:
                    return None

            return int(user_id)

        except JWTError:
            return None
        except (ValueError, TypeError):
            return None


def setup_auth_middleware(app):
    """
    Register authentication middleware with the application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(AuthMiddleware)


__all__ = ["AuthMiddleware", "setup_auth_middleware"]
