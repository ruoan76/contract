"""
用印管理 API
"""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.rbac import require_role
from app.db.database import get_db
from app.models.contract import Contract, SealRecord, User
from app.services.seal_service import create_seal_request, get_seal_records, approve_seal
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/", summary="用印列表")
async def list_seals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if status:
        conditions.append(SealRecord.status == status)
    count_q = select(func.count()).select_from(SealRecord)
    if conditions:
        count_q = count_q.where(*conditions)
    total = await db.scalar(count_q)
    query = select(SealRecord).order_by(SealRecord.created_at.desc())
    if conditions:
        query = query.where(*conditions)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = [
        {
            "id": r.id,
            "contract_id": r.contract_id,
            "contract_no": r.contract_no,
            "seal_type": r.seal_type,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in result.scalars().all()
    ]
    return {"code": 200, "data": {"total": total, "page": page, "page_size": page_size, "items": items}}


@router.post("/apply", summary="用印申请")
async def apply_seal(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """申请用印"""
    contract_id = body.get("contract_id")
    seal_type = body.get("seal_type", "公章")
    seal_method = body.get("seal_method")
    comment = body.get("comment")

    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    payload = await create_seal_request(
        contract_id=contract_id,
        seal_type=seal_type,
        operator_id=user.id,
        seal_method=seal_method,
        comment=comment,
        db=db,
    )
    return {"code": 200, "data": payload}


@router.post("/{seal_id}/approve", summary="审批用印")
async def approve_seal_endpoint(
    seal_id: int,
    body: dict,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    approved = body.get("approved", True)
    from app.exceptions import BusinessError
    try:
        data = await approve_seal(seal_id, approved, user.id, db=db)
        return {"code": 200, "data": data}
    except BusinessError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{seal_id}/upload-scan", summary="上传用印扫描件")
async def upload_seal_scan(
    seal_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.config import settings

    result = await db.execute(select(SealRecord).where(SealRecord.id == seal_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="用印记录不存在")

    upload_dir = os.path.join(settings.FILE_STORAGE_PATH or "uploads", "seals")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "scan.pdf")[1] or ".pdf"
    filename = f"seal_{seal_id}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    record.seal_image_path = path
    record.status = "completed"
    await db.flush()
    return {"code": 200, "data": {"id": record.id, "seal_image_path": path}}


@router.get("/records/{contract_id}", summary="用印记录")
async def get_seal_records_endpoint(
    contract_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用印记录"""
    result = await get_seal_records(contract_id=contract_id, db=db)
    return {"code": 200, "data": {"contract_id": contract_id, "records": result}}
