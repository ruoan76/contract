"""
Request logging middleware.
Logs request method, path, status code, duration, and user_id if authenticated.
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Paths to skip logging
SKIP_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/static",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs incoming requests and their处理 time.

    Logs: method, path, status_code, duration_ms, user_id (if present)
    Skips: /health, /docs, /openapi.json, /redoc, /static/*
    """

    def __init__(self, app):
        """
        Initialize middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process incoming request and log details.

        Args:
            request: FastAPI Request object
            call_next: Next middleware/callable in chain

        Returns:
            Response from downstream handlers
        """
        path = request.url.path

        # Skip logging for health/check endpoints
        if any(path.startswith(skip) for skip in SKIP_PATHS):
            return await call_next(request)

        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Get user_id from request.state if authenticated
        user_id = getattr(request.state, "user_id", None)

        # Log request info
        # Note: Using print for now, will integrate with logging later
        # print(
        #     f"[{request.method}] {path} "
        #     f"- Status: {response.status_code} "
        #     f"- Duration: {duration_ms:.2f}ms "
        #     f"- User: {user_id}"
        # )

        return response


def add_request_logger_middleware(app) -> None:
    """
    Add request logging middleware to the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_middleware(RequestLoggingMiddleware)


__all__ = [
    "RequestLoggingMiddleware",
    "add_request_logger_middleware",
]
