"""
Custom exception hierarchy for the application.
"""
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """
    Base application exception.

    All custom exceptions should inherit from this class.

    Attributes:
        code: HTTP status code
        message: Human-readable error message
        details: Additional error details (optional)
    """

    code: int = 500
    message: str = "Internal server error"
    details: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize AppError.

        Args:
            message: Error message (overrides class default)
            details: Additional error details
        """
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class NotFoundError(AppError):
    """Exception raised when a resource is not found."""

    code: int = 404
    message: str = "Resource not found"


class UnprocessableError(AppError):
    """Exception raised when request is well-formed but semantically incorrect."""

    code: int = 422
    message: str = "Unprocessable entity"


class AuthError(AppError):
    """Exception raised when authentication fails."""

    code: int = 401
    message: str = "Authentication required"


class FlowError(AppError):
    """Exception raised when workflow state is invalid."""

    code: int = 400
    message: str = "Invalid workflow state"


class ValidationError(AppError):
    """Exception raised when validation fails."""

    code: int = 400
    message: str = "Validation failed"


class ConflictError(AppError):
    """Exception raised when there's a resource conflict."""

    code: int = 409
    message: str = "Resource conflict"


class BusinessError(AppError):
    """Exception raised for business logic errors."""

    code: int = 400
    message: str = "Business logic error"


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle FastAPI/Starlette HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
        },
    )


async def _app_error_handler(
    request: Request, exc: AppError
) -> JSONResponse:
    """Handle custom AppError exceptions."""
    content: Dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.details:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.code, content=content)


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "Validation failed",
            "details": exc.errors(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)


__all__ = [
    "AppError",
    "NotFoundError",
    "UnprocessableError",
    "AuthError",
    "FlowError",
    "ValidationError",
    "ConflictError",
    "BusinessError",
    "register_exception_handlers",
]
