"""条款比对 API（V1.1 MVP）"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.contract import User
from app.services.clause_compare_service import compare_texts
from app.utils.auth import get_current_user

router = APIRouter()


class ClauseCompareRequest(BaseModel):
    left_text: str = Field(..., description="基准文本")
    right_text: str = Field(..., description="对比文本")
    left_label: str = "基准版"
    right_label: str = "对比版"


@router.post("/", summary="条款文本比对")
async def clause_compare(
    body: ClauseCompareRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = compare_texts(
        body.left_text,
        body.right_text,
        body.left_label,
        body.right_label,
    )
    return {"code": 200, "data": data}
