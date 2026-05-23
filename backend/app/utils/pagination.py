"""
Pagination utilities for SQLAlchemy async queries.

Provides Pydantic models and helper functions for implementing
pagination in API endpoints with SQLAlchemy 2.0 async.
"""
from typing import TypeVar, Generic, List, Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select
from sqlalchemy import func

T = TypeVar("T")


class PageParams(BaseModel):
    """
    Pagination parameters for API requests.

    Attributes:
        page: Page number (1-indexed), defaults to 1
        page_size: Number of items per page, defaults to 10, max 100
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page (max 100)")


@dataclass
class PageResult(Generic[T]):
    """
    Paginated result container.

    Attributes:
        items: List of items on current page
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def prev_page(self) -> Optional[int]:
        """Previous page number, or None if no previous page."""
        return self.page - 1 if self.has_prev else None

    @property
    def next_page(self) -> Optional[int]:
        """Next page number, or None if no next page."""
        return self.page + 1 if self.has_next else None


async def paginate(
    session: AsyncSession,
    query: Select,
    params: PageParams,
) -> PageResult:
    """
    Execute a paginated SQLAlchemy async query.

    Args:
        session: Async database session
        query: SQLAlchemy Select query (without limit/offset)
        params: PageParams containing page and page_size

    Returns:
        PageResult with paginated items and metadata

    Example:
        ```python
        from app.utils.pagination import PageParams, paginate
        from app.models.contract import Contract

        # Build base query
        query = select(Contract).where(Contract.status == "active")

        # Paginate results
        params = PageParams(page=1, page_size=20)
        result = await paginate(db, query, params)

        # Access results
        for contract in result.items:
            print(contract.title)
        print(f"Total: {result.total}, Pages: {result.total_pages}")
        ```
    """
    # Calculate offset
    offset = (params.page - 1) * params.page_size

    # Get total count
    count_query = query.with_only_columns(func.count())
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    # Apply pagination to main query
    paginated_query = query.offset(offset).limit(params.page_size)

    # Execute paginated query
    result = await session.execute(paginated_query)
    items = result.scalars().all()

    # Calculate total pages
    total_pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0

    return PageResult(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


async def paginate_list(
    session: AsyncSession,
    query: Select,
    params: PageParams,
) -> PageResult:
    """
    Alias for paginate function.

    This is provided for convenience and backward compatibility.
    See paginate() for full documentation.
    """
    return await paginate(session, query, params)
