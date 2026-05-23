"""
相对方领域服务
"""
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessError
from app.models.counterparty import Counterparty


def _to_dict(cp: Counterparty) -> dict:
    return {
        "id": cp.id,
        "name": cp.name,
        "credit_code": cp.credit_code,
        "legal_person": cp.legal_person,
        "contact_name": cp.contact_name,
        "contact_phone": cp.contact_phone,
        "address": cp.address,
        "industry": cp.industry,
        "credit_rating": cp.credit_rating,
        "is_blacklist": cp.is_blacklist,
        "blacklist_reason": cp.blacklist_reason,
        "status": cp.status,
        "created_at": cp.created_at.isoformat() if cp.created_at else None,
    }


async def create_counterparty(db: AsyncSession, data: dict) -> dict:
    if not data.get("name", "").strip():
        raise BusinessError("相对方名称不能为空")
    if data.get("credit_code"):
        exists = await db.scalar(
            select(Counterparty).where(Counterparty.credit_code == data["credit_code"])
        )
        if exists:
            raise BusinessError("统一社会信用代码已存在")
    cp = Counterparty(**{k: v for k, v in data.items() if hasattr(Counterparty, k)})
    db.add(cp)
    await db.flush()
    await db.refresh(cp)
    return _to_dict(cp)


async def get_counterparty(db: AsyncSession, cp_id: int) -> dict:
    cp = await db.get(Counterparty, cp_id)
    if not cp:
        raise BusinessError(f"Counterparty {cp_id} not found")
    return _to_dict(cp)


async def list_counterparties(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    is_blacklist: Optional[int] = None,
) -> dict:
    conditions = [Counterparty.status == 1]
    if keyword:
        conditions.append(
            or_(
                Counterparty.name.contains(keyword),
                Counterparty.credit_code.contains(keyword),
            )
        )
    if is_blacklist is not None:
        conditions.append(Counterparty.is_blacklist == is_blacklist)

    total = await db.scalar(
        select(func.count()).select_from(Counterparty).where(*conditions)
    )
    result = await db.execute(
        select(Counterparty)
        .where(*conditions)
        .order_by(Counterparty.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_to_dict(cp) for cp in result.scalars().all()]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def update_counterparty(db: AsyncSession, cp_id: int, updates: dict) -> dict:
    cp = await db.get(Counterparty, cp_id)
    if not cp:
        raise BusinessError(f"Counterparty {cp_id} not found")
    for key, value in updates.items():
        if hasattr(cp, key) and value is not None:
            setattr(cp, key, value)
    await db.flush()
    await db.refresh(cp)
    return _to_dict(cp)


async def add_to_blacklist(db: AsyncSession, cp_id: int, reason: str) -> dict:
    cp = await db.get(Counterparty, cp_id)
    if not cp:
        raise BusinessError(f"Counterparty {cp_id} not found")
    cp.is_blacklist = 1
    cp.blacklist_reason = reason
    await db.flush()
    return _to_dict(cp)


async def check_blacklist(
    db: AsyncSession,
    counterparty_id: Optional[int] = None,
    credit_code: Optional[str] = None,
) -> None:
    """校验相对方是否在黑名单，命中则抛出 BusinessError。"""
    cp = None
    if counterparty_id:
        cp = await db.get(Counterparty, counterparty_id)
    elif credit_code:
        cp = await db.scalar(
            select(Counterparty).where(Counterparty.credit_code == credit_code)
        )
    if cp and cp.is_blacklist:
        raise BusinessError(f"相对方「{cp.name}」在黑名单中，无法创建合同")
