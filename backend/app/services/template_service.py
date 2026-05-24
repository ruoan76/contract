"""合同模板服务"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import ContractTemplate

VALID_STATUSES = {"draft", "pending_publish", "published", "deprecated"}


def _to_dict(t: ContractTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "content": t.content,
        "status": t.status,
        "version": t.version,
        "creator_id": t.creator_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
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
    """管理员一键发布（V1.1 alpha）"""
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.status = "published"
    t.version = (t.version or 1) + 1
    await db.flush()
    return _to_dict(t)
