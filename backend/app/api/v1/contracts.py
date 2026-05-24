"""
合同管理 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.models.contract import User
from app.schemas.contract import ContractCreate, ContractUpdate
from app.schemas.review import RevisionSubmit
from app.services.contract_service import (
    create_contract,
    get_contract,
    list_contracts,
    update_contract,
    delete_contract,
    list_dashboard_buckets,
    save_contract_upload,
    list_contract_versions,
)
from app.services.flow_match_service import get_flow_match_detail
from app.services.review_service import submit_revision
from app.utils.auth import get_current_user
from app.exceptions import BusinessError

router = APIRouter()


@router.post("/", summary="创建合同")
async def create(
    body: ContractCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新合同"""
    try:
        result = await create_contract(
            title=body.title,
            contract_type=body.contract_type,
            counterparty_name=body.counterparty_name,
            counterparty_id=body.counterparty_id,
            counterparty_credit_code=body.counterparty_credit_code,
            amount=body.amount,
            content=body.content,
            creator_id=user.id,
            db=db,
        )
        return {"code": 200, "data": result}
    except BusinessError as e:
        if "黑名单" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dashboard", summary="合同看板")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """executing / expiring_soon / expired 三栏"""
    data = await list_dashboard_buckets(db)
    return {"code": 200, "data": data}


@router.get("/match-flow", summary="流程类型匹配")
async def match_flow(
    amount: Optional[float] = None,
    contract_type: Optional[str] = None,
):
    data = get_flow_match_detail(amount, contract_type)
    return {"code": 200, "data": data}


@router.get("/", summary="合同列表")
async def list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    contract_type: Optional[str] = None,
    keyword: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """获取合同列表"""
    filters = {
        "status": status,
        "type": contract_type,
        "risk_level": risk_level,
        "keyword": keyword,
    }
    filters = {k: v for k, v in filters.items() if v is not None}
    result = await list_contracts(db=db, page=page, page_size=page_size, filters=filters)
    return {"code": 200, "data": result}


@router.get("/{contract_id}/versions", summary="合同版本历史")
async def versions(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取合同版本列表"""
    try:
        data = await list_contract_versions(db, contract_id)
        return {"code": 200, "data": data}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        raise


@router.get("/{contract_id}", summary="合同详情")
async def get(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取合同详情"""
    try:
        result = await get_contract(contract_id=contract_id, db=db)
        return {"code": 200, "data": result}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        raise


@router.put("/{contract_id}", summary="更新合同")
async def update(
    contract_id: int,
    body: ContractUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新合同"""
    updates = body.model_dump(exclude_unset=True)
    try:
        result = await update_contract(
            contract_id=contract_id,
            updates=updates,
            db=db,
        )
        return {"code": 200, "data": result}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        if "only draft can be edited" in str(e):
            raise HTTPException(status_code=400, detail="合同状态不允许编辑")
        if "金额必须大于 0" in str(e):
            raise HTTPException(status_code=400, detail="合同金额必须大于 0")
        raise


@router.delete("/{contract_id}", summary="删除合同")
async def delete(
    contract_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除合同"""
    try:
        result = await delete_contract(contract_id=contract_id, db=db)
        return {"code": 200, "message": result["message"]}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        if "only draft can be deleted" in str(e):
            raise HTTPException(status_code=400, detail="合同状态不允许删除")
        raise


@router.post("/{contract_id}/upload", summary="上传合同文件")
async def upload(
    contract_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        result = await save_contract_upload(
            db,
            contract_id,
            file.filename or "upload.bin",
            content,
            file.content_type or "application/octet-stream",
        )
        return {"code": 200, "data": result}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{contract_id}/revisions", summary="提交修订")
async def revision(
    contract_id: int,
    body: RevisionSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await submit_revision(
            db,
            contract_id,
            body.content,
            body.change_description,
            body.title,
            user.id,
        )
        return {"code": 200, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
