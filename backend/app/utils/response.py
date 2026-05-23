"""
Unified API response wrapper.
"""
from typing import Any
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Unified API response model."""
    code: int
    message: str
    data: Any = None
    timestamp: float


def success(data: Any = None, message: str = "success") -> APIResponse:
    """
    Create a success response.

    Args:
        data: Response data
        message: Success message

    Returns:
        APIResponse with code=200
    """
    return APIResponse(code=200, message=message, data=data, timestamp=0.0)


def error(code: int = 400, message: str = "error", data: Any = None) -> APIResponse:
    """
    Create an error response.

    Args:
        code: HTTP status code
        message: Error message
        data: Error data

    Returns:
        APIResponse with specified code
    """
    return APIResponse(code=code, message=message, data=data, timestamp=0.0)


def paginate(items: list, total: int, page: int, page_size: int) -> APIResponse:
    """
    Create a paginated response.

    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number (0-indexed)
        page_size: Number of items per page

    Returns:
        APIResponse with paginated data
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return APIResponse(
        code=200,
        message="success",
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        timestamp=0.0,
    )


__all__ = ["APIResponse", "success", "error", "paginate"]
