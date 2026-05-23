"""
评审域 Pydantic 模型
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ReviewOpinionSubmit(BaseModel):
    role: str = Field(..., description="legal | finance | executive")
    action: str = Field(..., description="approve | reject | return")
    comment: Optional[str] = None


class ReviewReturnRequest(BaseModel):
    comment: Optional[str] = None
    role: str = "legal"


class RevisionSubmit(BaseModel):
    content: Optional[str] = None
    change_description: Optional[str] = None
    title: Optional[str] = None
