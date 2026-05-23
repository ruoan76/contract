"""
CORS middleware configuration.

Sets up CORS (Cross-Origin Resource Sharing) for the FastAPI application
using the allowed origins from configuration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Configure and apply CORS middleware to the application.

    Args:
        app: FastAPI application instance

    The middleware allows:
    - All methods (GET, POST, PUT, DELETE, etc.)
    - All headers
    - Credentials (cookies, authorization headers)
    - Origins from settings.ALLOWED_ORIGINS
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Expose common headers
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
        #Max age for preflight缓存 (10 minutes)
        max_age=600,
    )


__all__ = ["setup_cors"]
