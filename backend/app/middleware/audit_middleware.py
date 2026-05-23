"""
Audit logging middleware.

Logs post-response audit events for tracking user activity.
Uses a deque for batch writes to avoid blocking the response.
"""
import time
import asyncio
from collections import deque
from typing import Deque, Dict, Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Skip audit logging for these paths
EXCLUDED_PATHS = {
    "/health",
    "/static",
    "/docs",
}


class AuditLogger:
    """
    Asynchronous audit logger using a deque for batch writes.
    
    Provides thread-safe audit logging with background processing.
    """

    def __init__(self):
        self._queue: Deque[Dict[str, Any]] = deque()
        self._max_size = 1000
        self._lock = asyncio.Lock()

    async def log(
        self,
        user_id: Optional[int],
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            user_id: ID of the user, None if unauthenticated
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            resource_type: Type of resource accessed (extracted from path)
            resource_id: ID of resource (extracted from path)
        """
        async with self._lock:
            if len(self._queue) >= self._max_size:
                self._queue.popleft()

            event = {
                "user_id": user_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "timestamp": time.time(),
            }

            self._queue.append(event)

    async def get_batch(self, size: int = 100) -> list[Dict[str, Any]]:
        """Get a batch of logged events."""
        async with self._lock:
            batch = []
            for _ in range(min(size, len(self._queue))):
                batch.append(self._queue.popleft())
            return batch

    async def clear(self) -> None:
        """Clear all logged events."""
        async with self._lock:
            self._queue.clear()


# Global audit logger instance
audit_logger = AuditLogger()


def extract_resource_info(path: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract resource type and ID from path.

    Args:
        path: URL path

    Returns:
        Tuple of (resource_type, resource_id) or (None, None)
    """
    parts = path.strip("/").split("/")

    # Pattern: /api/v1/{resource}/{id}
    if len(parts) >= 3 and parts[0] == "api":
        resource_type = parts[1] if len(parts) > 2 else None
        resource_id = parts[2] if len(parts) > 2 else None
        return resource_type, resource_id

    # Pattern: /{resource}/{id}
    if len(parts) >= 2:
        resource_type = parts[0]
        resource_id = parts[1]
        return resource_type, resource_id

    return None, None


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log audit events after each response.
    
    Logs user activity, response status, and duration.
    Uses background queue to avoid blocking.
    """

    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        """
        Process request and log audit event after response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response
        """
        # Skip audit for excluded paths
        if self._should_skip(request):
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Extract audit info
        user_id = getattr(request.state, "current_user_id", None)
        resource_type, resource_id = extract_resource_info(request.url.path)

        # Log audit event (non-blocking)
        await audit_logger.log(
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        return response

    def _should_skip(self, request: Request) -> bool:
        """Check if request should be skipped from audit logging."""
        path = request.url.path
        return any(path.startswith(prefix) for prefix in EXCLUDED_PATHS)


def setup_audit_middleware(app):
    """
    Register audit middleware with the application.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(AuditMiddleware)


__all__ = [
    "AuditMiddleware",
    "AuditLogger",
    "audit_logger",
    "setup_audit_middleware",
    "extract_resource_info",
]
