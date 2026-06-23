"""合同模板服务"""
import json
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import ContractTemplate
from app.services.template_parser import (
    extract_variables,
    fill_template,
    validate_template_values,
    variables_from_json,
    variables_to_json,
)

VALID_STATUSES = {"draft", "pending_publish", "published", "deprecated"}

_CATEGORY_CODE_PREFIX = {
    "purchase": "PUR",
    "sales": "SAL",
    "labor": "LAB",
    "nda": "NDA",
    "service": "SVC",
    "cooperation": "COOP",
}


def _sync_variables(t: ContractTemplate) -> None:
    names = extract_variables(t.content)
    t.variables = variables_to_json(names)


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
    var_list = variables_from_json(getattr(t, "variables", None))
    if not var_list and t.content:
        var_list = extract_variables(t.content)
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "category": t.category,
        "content": t.content,
        "status": t.status,
        "version": t.version,
        "creator_id": t.creator_id,
        "variables": var_list,
        "variable_count": len(var_list),
        "archived_reason": getattr(t, "archived_reason", None),
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


async def _generate_template_code(db: AsyncSession, category: str) -> str:
    prefix = _CATEGORY_CODE_PREFIX.get(category or "", "TPL")
    pattern = f"{prefix}-%"
    count = await db.scalar(
        select(func.count())
        .select_from(ContractTemplate)
        .where(ContractTemplate.code.like(pattern))
    )
    return f"{prefix}-{(count or 0) + 1:03d}"


async def list_templates(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
) -> dict:
    conditions = []
    if status:
        conditions.append(ContractTemplate.status == status)
    if category:
        conditions.append(ContractTemplate.category == category)
    if keyword:
        kw = f"%{keyword}%"
        conditions.append(
            or_(
                ContractTemplate.name.like(kw),
                ContractTemplate.code.like(kw),
            )
        )
    where_clause = and_(*conditions) if conditions else True
    total = await db.scalar(
        select(func.count()).select_from(ContractTemplate).where(where_clause)
    )
    result = await db.execute(
        select(ContractTemplate)
        .where(where_clause)
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


async def fill_template_content(
    db: AsyncSession,
    template_id: int,
    values: dict[str, Any],
) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "published":
        raise HTTPException(status_code=400, detail="仅已发布模板可用于起草")
    errors = validate_template_values(t.content, values)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    filled = fill_template(t.content, values)
    return {
        "template_id": t.id,
        "template_version": t.version,
        "content": filled,
        "variables": variables_from_json(t.variables) or extract_variables(t.content),
    }


async def create_template(
    db: AsyncSession,
    name: str,
    category: str,
    content: str,
    creator_id: int,
    code: Optional[str] = None,
) -> dict:
    tpl_code = code or await _generate_template_code(db, category)
    t = ContractTemplate(
        code=tpl_code,
        name=name,
        category=category,
        content=content,
        status="draft",
        creator_id=creator_id,
    )
    _sync_variables(t)
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
    if t.status not in ("draft",):
        raise HTTPException(status_code=400, detail="仅草稿状态可编辑正文与名称")
    for key in ("name", "category", "content", "status"):
        if key in fields and fields[key] is not None:
            if key == "status" and fields[key] not in VALID_STATUSES:
                raise HTTPException(status_code=400, detail="无效模板状态")
            setattr(t, key, fields[key])
    if "content" in fields and fields["content"] is not None:
        _sync_variables(t)
    await db.flush()
    return _to_dict(t)


async def publish_template(db: AsyncSession, template_id: int) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "pending_publish":
        raise HTTPException(status_code=400, detail="仅待发布状态可一键发布，草稿请先提交发布审批")
    t.status = "published"
    t.version = (t.version or 0) + 1
    await db.flush()
    return _to_dict(t)


async def submit_for_publish(db: AsyncSession, template_id: int) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿状态可提交发布")
    t.status = "pending_publish"
    await db.flush()
    return _to_dict(t)


async def approve_publish(db: AsyncSession, template_id: int) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "pending_publish":
        raise HTTPException(status_code=400, detail="仅待发布状态可批准")
    t.status = "published"
    t.version = (t.version or 0) + 1

    if t.auto_review_on_publish and t.content:
        try:
            from app.services.ai_review.rule_engine import run_rule_engine

            issues = run_rule_engine(t.content)
            if issues:
                snapshot = [
                    {"title": i.title, "severity": i.risk_level, "suggestion": i.suggestion}
                    for i in issues
                ]
                t.legal_snapshot = json.dumps(snapshot, ensure_ascii=False)
        except Exception:
            pass

    await db.flush()
    return _to_dict(t)


async def reject_publish(db: AsyncSession, template_id: int) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "pending_publish":
        raise HTTPException(status_code=400, detail="仅待发布状态可驳回")
    t.status = "draft"
    await db.flush()
    return _to_dict(t)


async def deprecate_template(
    db: AsyncSession,
    template_id: int,
    reason: Optional[str] = None,
) -> dict:
    t = await db.get(ContractTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status != "published":
        raise HTTPException(status_code=400, detail="仅已发布模板可废止")
    t.status = "deprecated"
    if reason:
        t.archived_reason = reason.strip()
    await db.flush()
    return _to_dict(t)
