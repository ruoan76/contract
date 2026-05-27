"""
合同管理 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from typing import Optional

from app.core.config import settings
from app.db.database import get_db
from app.models.contract import User, Contract, ContractVersion
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
from app.services.ai_review_service import start_review
from app.utils.auth import get_current_user
from app.exceptions import BusinessError

router = APIRouter()


@router.post("/parse", summary="解析合同文件")
async def parse_contract(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """上传合同文件，提取文本并返回结构化字段（默认 mock 模式）。"""
    from app.services.contract_parse_service import parse_contract_file

    try:
        data = await parse_contract_file(file, db=db)
        return {"code": 200, "data": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/", summary="创建合同")
async def create(
    body: ContractCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新合同"""
    last_integrity: IntegrityError | None = None
    for attempt in range(5):
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
            await db.commit()
            return {"code": 200, "data": result}
        except IntegrityError as e:
            await db.rollback()
            last_integrity = e
            if "contract_no" not in str(e).lower() or attempt >= 4:
                raise HTTPException(status_code=409, detail="合同编号冲突，请重试") from e
            continue
        except DataError as e:
            await db.rollback()
            if "content" in str(e).lower():
                raise HTTPException(
                    status_code=400,
                    detail="合同正文过长，请联系管理员升级数据库字段或缩短正文后重试",
                ) from e
            raise HTTPException(status_code=400, detail="数据格式或长度不符合要求") from e
        except BusinessError as e:
            await db.rollback()
            if "黑名单" in str(e):
                raise HTTPException(status_code=403, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))
    if last_integrity:
        raise HTTPException(status_code=409, detail="合同编号冲突，请重试") from last_integrity


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
    bucket: Optional[str] = Query(
        None, description="看板桶：executing|expiring_soon|expired，与 dashboard 口径一致"
    ),
    contract_type: Optional[str] = None,
    keyword: Optional[str] = None,
    risk_level: Optional[str] = None,
    scope: Optional[str] = Query(None, description="mine|department|all"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取合同列表"""
    if scope and scope not in ("mine", "department", "all"):
        raise HTTPException(status_code=400, detail="scope 必须为 mine、department 或 all")
    if bucket and bucket not in ("executing", "expiring_soon", "expired"):
        raise HTTPException(status_code=400, detail="bucket 无效")
    filters = {
        "status": status,
        "bucket": bucket,
        "type": contract_type,
        "risk_level": risk_level,
        "keyword": keyword,
        "scope": scope,
        "creator_id": user.id,
        "user_department_id": user.department_id,
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
        if settings.AI_AUTO_REVIEW_ON_UPLOAD and result.get("version_id"):
            contract_result = await db.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = contract_result.scalar_one_or_none()
            version_result = await db.execute(
                select(ContractVersion).where(
                    ContractVersion.id == result["version_id"]
                )
            )
            version = version_result.scalar_one_or_none()
            text = ""
            if contract and version:
                text = (version.content or contract.content or "").strip()
            if text:
                review_data = await start_review(
                    db=db,
                    contract_id=contract_id,
                    version_id=result["version_id"],
                    user_id=user.id,
                    username=user.username,
                )
                result["auto_review"] = review_data
        await db.commit()
        return {"code": 200, "data": result}
    except BusinessError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail="合同不存在")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e}") from e


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
