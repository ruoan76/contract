"""条款比对 API（V1.1 MVP）"""
from fastapi import APIRouter, Depends, File, UploadFile
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


async def _read_upload_text(file: UploadFile) -> str:
    """从上传文件中读取文本（优先 UTF-8）"""
    raw = await file.read()
    for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


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


@router.post("/upload", summary="上传文本文件比对")
async def clause_compare_upload(
    left_file: UploadFile = File(..., description="基准文本文件"),
    right_file: UploadFile = File(..., description="对比文本文件"),
    left_label: str = "基准版",
    right_label: str = "对比版",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """multipart 上传 txt 等文本文件并 diff"""
    left_text = await _read_upload_text(left_file)
    right_text = await _read_upload_text(right_file)
    data = compare_texts(left_text, right_text, left_label, right_label)
    return {"code": 200, "data": data}
