"""合同模板 API（V1.1 MVP）"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_any_role
from app.db.database import get_db
from app.models.contract import User
from app.services.template_service import (
    approve_publish,
    create_template,
    deprecate_template,
    fill_template_content,
    get_template,
    list_templates,
    publish_template,
    reject_publish,
    submit_for_publish,
    update_template,
)
from app.utils.auth import get_current_user

router = APIRouter()

_admin = require_any_role("admin")
_approver = require_any_role("admin", "approver")


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str = "purchase"
    content: str = ""


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    content: str | None = None
    status: str | None = None


class TemplateFillRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict, description="模板变量名→值")


class TemplateDeprecateRequest(BaseModel):
    reason: str | None = Field(None, max_length=500, description="废止原因")


@router.get("/", summary="模板列表")
async def templates_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await list_templates(db, page, page_size, status, category, keyword)
    return {"code": 200, "data": data}


@router.get("/{template_id}", summary="模板详情")
async def templates_get(
    template_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await get_template(db, template_id)
    return {"code": 200, "data": data}


@router.post("/", summary="创建模板")
async def templates_create(
    body: TemplateCreate,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await create_template(db, body.name, body.category, body.content, user.id)
    return {"code": 200, "data": data}


@router.put("/{template_id}", summary="更新模板")
async def templates_update(
    template_id: int,
    body: TemplateUpdate,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await update_template(
        db,
        template_id,
        **body.model_dump(exclude_unset=True),
    )
    return {"code": 200, "data": data}


@router.post("/{template_id}/publish", summary="发布模板")
async def templates_publish(
    template_id: int,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await publish_template(db, template_id)
    return {"code": 200, "data": data}


@router.post("/{template_id}/submit-publish", summary="提交发布审批")
async def templates_submit_publish(
    template_id: int,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await submit_for_publish(db, template_id)
    return {"code": 200, "data": data}


@router.post("/{template_id}/approve-publish", summary="批准发布")
async def templates_approve_publish(
    template_id: int,
    user: User = Depends(_approver),
    db: AsyncSession = Depends(get_db),
):
    data = await approve_publish(db, template_id)
    return {"code": 200, "data": data}


@router.post("/{template_id}/reject-publish", summary="驳回发布")
async def templates_reject_publish(
    template_id: int,
    user: User = Depends(_approver),
    db: AsyncSession = Depends(get_db),
):
    data = await reject_publish(db, template_id)
    return {"code": 200, "data": data}


@router.post("/{template_id}/fill", summary="填充模板变量")
async def templates_fill(
    template_id: int,
    body: TemplateFillRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await fill_template_content(db, template_id, body.values)
    return {"code": 200, "data": data}


@router.post("/{template_id}/deprecate", summary="废止模板")
async def templates_deprecate(
    template_id: int,
    body: TemplateDeprecateRequest | None = None,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    reason = body.reason if body else None
    data = await deprecate_template(db, template_id, reason)
    return {"code": 200, "data": data}
