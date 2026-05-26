# -*- coding: utf-8 -*-
"""S0 审查上下文加载。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_review.seed_store import get_contract_type_map, get_contract_type_profiles


@dataclass
class ReviewContext:
    contract_type: str = "other"
    amount: Optional[float] = None
    counterparty_name: Optional[str] = None
    counterparty_blacklisted: bool = False
    flow_type: Optional[str] = None
    profile_key: str = "other"
    type_profile: dict[str, Any] = field(default_factory=dict)


async def load_review_context(
    db: AsyncSession,
    *,
    contract_id: int,
    contract_type: str | None = None,
    amount: float | None = None,
    counterparty_name: str | None = None,
) -> ReviewContext:
    """轻量 S0：合同类型 profile + 相对方黑名单标记。"""
    from app.models.contract import Contract

    contract = await db.get(Contract, contract_id)
    ctx = ReviewContext(
        contract_type=contract_type or (contract.contract_type if contract else "other") or "other",
        amount=amount if amount is not None else (contract.amount if contract else None),
        counterparty_name=counterparty_name or (contract.counterparty_name if contract else None),
    )

    profile_key = _resolve_profile_key(ctx.contract_type)
    ctx.profile_key = profile_key
    ctx.type_profile = _load_type_profile(profile_key)

    if ctx.counterparty_name:
        ctx.counterparty_blacklisted = await _is_blacklisted(db, ctx.counterparty_name)

    return ctx


def _resolve_profile_key(contract_type: str) -> str:
    try:
        type_map = get_contract_type_map()
        for mapping in type_map.get("platform_mapping", []):
            if mapping.get("contract_type") == contract_type:
                return mapping.get("ai_profile_key") or contract_type
    except Exception:
        pass
    return contract_type or "other"


def _load_type_profile(profile_key: str) -> dict[str, Any]:
    try:
        for p in get_contract_type_profiles().get("items", []):
            if p.get("profile_key") == profile_key:
                return p
    except Exception:
        pass
    return {}


async def _is_blacklisted(db: AsyncSession, name: str) -> bool:
    try:
        from sqlalchemy import select
        from app.models.counterparty import Counterparty

        result = await db.execute(
            select(Counterparty).where(
                Counterparty.name == name,
                Counterparty.status == "blacklisted",
            )
        )
        return result.scalar_one_or_none() is not None
    except Exception:
        return False
