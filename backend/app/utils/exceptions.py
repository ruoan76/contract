"""
Custom Exceptions for Contract Management

Provides application-specific exceptions for consistent error handling:
- BusinessError: Business logic validation errors
- AuthError: Authentication/authorization errors
- NotFoundError: Resource not found
- AlreadyExistsError: Resource already exists

All exceptions include error handlers that return JSON responses
in the format: {code, message, detail}
"""
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError


class AppError(Exception):
    """Base application exception with structured error response."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "AppError",
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.detail = detail or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class BusinessError(AppError):
    """Raised when business logic validation fails."""

    def __init__(
        self,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BusinessError",
            detail=detail,
        )


class AuthError(AppError):
    """Raised when authentication or authorization fails."""

    def __init__(
        self,
        message: str = "Authentication required",
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AuthError",
            detail=detail,
        )


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str,
        identifier: Any,
        message: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"{resource} not found: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
            code="NotFoundError",
            detail=detail or {"resource": resource, "id": identifier},
        )


class AlreadyExistsError(AppError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(
        self,
        resource: str,
        identifier: Any,
        message: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message or f"{resource} already exists: {identifier}",
            status_code=status.HTTP_409_CONFLICT,
            code="AlreadyExistsError",
            detail=detail or {"resource": resource, "id": identifier},
        )


# Exception handlers

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    Handle AppError exceptions and return JSON response.

    Args:
        request: Incoming request
        exc: Caught exception

    Returns:
        JSONResponse with error details in {code, message, detail} format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: Incoming request
        exc: Caught validation error

    Returns:
        JSONResponse with validation details
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "ValidationError",
            "message": "Validation failed",
            "detail": {
                "errors": errors,
                "body": exc.body if hasattr(exc, "body") else None,
            },
        },
    )


async def pydantic_validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """
    Handle Pydantic ValidationError.

    Args:
        request: Incoming request
        exc: Caught validation error

    Returns:
        JSONResponse with validation details
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "ValidationError",
            "message": "Validation failed",
            "detail": {"errors": errors},
        },
    )


# Register all exception handlers
def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)


__all__ = [
    "AppError",
    "BusinessError",
    "AuthError",
    "NotFoundError",
    "AlreadyExistsError",
    "app_error_handler",
    "validation_error_handler",
    "pydantic_validation_error_handler",
    "register_exception_handlers",
]
