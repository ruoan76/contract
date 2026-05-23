"""
相对方 Pydantic 模型
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CounterpartyBase(BaseModel):
    name: str = Field(..., max_length=200)
    credit_code: Optional[str] = None
    legal_person: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    credit_rating: Optional[str] = None


class CounterpartyCreate(CounterpartyBase):
    pass


class CounterpartyUpdate(BaseModel):
    name: Optional[str] = None
    credit_code: Optional[str] = None
    legal_person: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    industry: Optional[str] = None
    credit_rating: Optional[str] = None
    status: Optional[int] = None


class CounterpartyResponse(CounterpartyBase):
    id: int
    is_blacklist: int = 0
    blacklist_reason: Optional[str] = None
    status: int = 1
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CounterpartyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[CounterpartyResponse]
