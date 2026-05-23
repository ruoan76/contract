"""
Request/response logging middleware.

Provides comprehensive logging for all HTTP requests including:
- HTTP method and path
- Response status code
- Request duration in milliseconds
- User agent information
- Excludes health check and docs endpoints
"""
import time
import logging
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Configure logging for this middleware
logger = logging.getLogger(__name__)

# Endpoints to exclude from logging
EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all incoming requests and responses.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        # Skip logging for excluded paths
        if self._should_skip_logging(request):
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get user info from request if available
        user_id = self._get_user_id(request)

        # Log request details
        self._log_request(
            request=request,
            response=response,
            duration_ms=duration_ms,
            user_id=user_id,
        )

        return response

    def _should_skip_logging(self, request: Request) -> bool:
        """Check if request should be excluded from logging."""
        return request.url.path in EXCLUDED_PATHS

    def _get_user_id(self, request: Request) -> Optional[int]:
        """
        Extract user ID from request context.

        Args:
            request: HTTP request

        Returns:
            User ID if available, None otherwise
        """
        # Try to get user from request state
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return user.id
        return None

    def _log_request(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        user_id: Optional[int],
    ) -> None:
        """
        Log request details.

        Args:
            request: HTTP request
            response: HTTP response
            duration_ms: Request duration in milliseconds
            user_id: User ID if authenticated
        """
        # Build log message
        user_info = f"user={user_id}" if user_id else "user=anonymous"

        log_message = (
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration_ms:.2f}ms "
            f"{user_info} "
            f"ua={self._truncate(request.headers.get('user-agent', ''), 100)}"
        )

        # Log at appropriate level based on status
        if response.status_code >= 500:
            logger.error(log_message)
        elif response.status_code >= 400:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."


def setup_logging_middleware(app: FastAPI) -> None:
    """
    Register logging middleware with the application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(LoggingMiddleware)


__all__ = [
    "LoggingMiddleware",
    "setup_logging_middleware",
]
