"""合同模板服务"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import ContractTemplate

VALID_STATUSES = {"draft", "pending_publish", "published", "deprecated"}


def _to_dict(t: ContractTemplate) -> dict:
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(t)
    if "updated_at" in state.unloaded:
        updated_at = None
    else:
        updated_at = t.updated_at
    if "created_at" in state.unloaded:
        created_at = None
    else:
        created_at = t.created_at
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "content": t.content,
        "status": t.status,
        "version": t.version,
        "creator_id": t.creator_id,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


async def list_templates(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    conditions = []
    if status:
        conditions.append(ContractTemplate.status == status)
    if category:
        conditions.append(ContractTemplate.category == category)
    total = await db.scalar(
        select(func.count()).select_from(ContractTemplate).where(*conditions)
    )
    result = await db.execute(
        select(ContractTemplate)
        .where(*conditions)
        .order_by(ContractTemplate.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(t) for t in result.scalars().all()]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_template(db: AsyncSession, template_id: int) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _to_dict(t)


async def create_template(
    db: AsyncSession,
    name: str,
    category: str,
    content: str,
    creator_id: int,
) -> dict:
    t = ContractTemplate(
        name=name,
        category=category,
        content=content,
        status="draft",
        creator_id=creator_id,
    )
    db.add(t)
    await db.flush()
    return _to_dict(t)


async def update_template(
    db: AsyncSession,
    template_id: int,
    **fields,
) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    for key in ("name", "category", "content", "status"):
        if key in fields and fields[key] is not None:
            if key == "status" and fields[key] not in VALID_STATUSES:
                raise HTTPException(status_code=400, detail="无效模板状态")
            setattr(t, key, fields[key])
    await db.flush()
    return _to_dict(t)


async def publish_template(db: AsyncSession, template_id: int) -> dict:
    """管理员一键发布（兼容旧 API，允许 draft 直接发布）"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status not in ("draft", "pending_publish"):
        raise HTTPException(status_code=400, detail="仅草稿或待发布状态可发布")
    t.status = "published"
    t.version = (t.version or 0) + 1
    await db.flush()
    return _to_dict(t)


async def submit_for_publish(db: AsyncSession, template_id: int) -> dict:
    """草稿提交发布审批"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿状态可提交发布")
    t.status = "pending_publish"
    await db.flush()
    return _to_dict(t)


async def approve_publish(db: AsyncSession, template_id: int) -> dict:
    """批准发布：pending_publish → published（审批流专用，不可从 draft 跳过）"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "pending_publish":
        raise HTTPException(status_code=400, detail="仅待发布状态可批准")
    t.status = "published"
    t.version = (t.version or 0) + 1
    await db.flush()
    return _to_dict(t)


async def reject_publish(db: AsyncSession, template_id: int) -> dict:
    """驳回发布：pending_publish → draft"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "pending_publish":
        raise HTTPException(status_code=400, detail="仅待发布状态可驳回")
    t.status = "draft"
    await db.flush()
    return _to_dict(t)


async def deprecate_template(db: AsyncSession, template_id: int) -> dict:
    """废止模板：published -> deprecated"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "published":
        raise HTTPException(status_code=400, detail="仅已发布模板可废止")
    t.status = "deprecated"
    await db.flush()
    return _to_dict(t)
