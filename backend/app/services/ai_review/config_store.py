# -*- coding: utf-8 -*-
"""AI 审查配置统一读取：DB 优先，JSON 种子 fallback。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_review_config import (
    AIConfigVersion,
    AIHardRule,
    AILegalSnippet,
    AIReviewChecklistItem,
    AIRevisionRoutingRule,
    AIRiskLabel,
)

SEEDS_DIR = Path(__file__).resolve().parents[3] / "seeds" / "ai_review" / "generated"
LEGAL_SNIPPETS_PATH = Path(__file__).resolve().parents[3] / "seeds" / "ai_review" / "legal_snippets.json"

_cache: dict[str, Any] | None = None


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _json_fallback_checklists() -> dict[str, Any]:
    path = SEEDS_DIR / "review_checklists.json"
    return _read_json_file(path)


@lru_cache(maxsize=1)
def _json_fallback_labels() -> dict[str, Any]:
    path = SEEDS_DIR / "risk_labels.json"
    return _read_json_file(path)


@lru_cache(maxsize=1)
def _json_fallback_routing() -> dict[str, Any]:
    path = SEEDS_DIR / "revision_routing.json"
    return _read_json_file(path)


@lru_cache(maxsize=1)
def _json_fallback_legal_snippets() -> list[dict[str, Any]]:
    if LEGAL_SNIPPETS_PATH.is_file():
        data = _read_json_file(LEGAL_SNIPPETS_PATH)
        return data if isinstance(data, list) else []
    return []


def _checklist_row_to_dict(row: AIReviewChecklistItem) -> dict[str, Any]:
    detect = None
    if row.detect_config:
        try:
            detect = json.loads(row.detect_config)
        except json.JSONDecodeError:
            detect = None
    return {
        "id": row.legacy_id,
        "category": row.category,
        "item": row.item,
        "description": row.description,
        "applicable_contracts": row.applicable_contracts,
        "risk_level": row.risk_level,
        "gate_id": row.gate_id,
        "gate_priority": row.gate_priority,
        "auto_detectable": row.auto_detectable,
        "detect_config": detect,
        "enabled": row.enabled,
    }


def _hard_rule_row_to_dict(row: AIHardRule) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    if row.config_json:
        try:
            cfg = json.loads(row.config_json)
        except json.JSONDecodeError:
            cfg = {}
    return {
        "rule_id": row.rule_id,
        "name": row.name,
        "enabled": row.enabled,
        "rule_type": row.rule_type,
        "config": cfg,
        "risk_level": row.risk_level,
        "label_id": row.label_id,
        "gate_id": row.gate_id,
        "dimension": row.dimension,
        "title": row.title,
        "suggestion": row.suggestion,
        "legal_basis": row.legal_basis,
        "revision_method": row.revision_method,
        "clause": row.clause,
    }


async def refresh_config_cache(db: AsyncSession) -> str | None:
    """从数据库加载当前配置到内存缓存。"""
    global _cache

    ver_row = await db.scalar(
        select(AIConfigVersion).where(AIConfigVersion.is_current.is_(True)).order_by(
            AIConfigVersion.id.desc()
        )
    )
    version_tag = ver_row.version if ver_row else None

    cl_rows = (
        await db.execute(
            select(AIReviewChecklistItem)
            .where(AIReviewChecklistItem.enabled.is_(True))
            .order_by(AIReviewChecklistItem.gate_priority, AIReviewChecklistItem.legacy_id)
        )
    ).scalars().all()

    if not cl_rows:
        _cache = None
        clear_config_cache()
        return None

    label_rows = (
        await db.execute(select(AIRiskLabel).where(AIRiskLabel.enabled.is_(True)))
    ).scalars().all()
    route_rows = (
        await db.execute(
            select(AIRevisionRoutingRule)
            .where(AIRevisionRoutingRule.enabled.is_(True))
            .order_by(AIRevisionRoutingRule.priority, AIRevisionRoutingRule.id)
        )
    ).scalars().all()
    hard_rows = (
        await db.execute(select(AIHardRule).where(AIHardRule.enabled.is_(True)))
    ).scalars().all()
    snippet_rows = (
        await db.execute(select(AILegalSnippet).where(AILegalSnippet.enabled.is_(True)))
    ).scalars().all()

    items = [_checklist_row_to_dict(r) for r in cl_rows]
    _cache = {
        "version": version_tag or "db",
        "checklists": {
            "version": version_tag or "db",
            "count": len(items),
            "auto_detectable_count": sum(1 for i in items if i.get("auto_detectable")),
            "items": items,
        },
        "risk_labels": {
            "version": version_tag or "db",
            "count": len(label_rows),
            "items": [
                {
                    "id": r.label_id,
                    "name": r.name,
                    "category": r.category,
                    "gate_id": r.gate_id,
                    "color": r.color,
                }
                for r in label_rows
            ],
        },
        "revision_routing": {
            "version": version_tag or "db",
            "count": len(route_rows),
            "items": [
                {
                    "issue_type": r.issue_type,
                    "default_method": r.default_method,
                    "auto_applicable": r.auto_applicable,
                    "self_check_questions": r.self_check_questions or "",
                    "notes": r.notes or "",
                }
                for r in route_rows
            ],
        },
        "hard_rules": [_hard_rule_row_to_dict(r) for r in hard_rows],
        "legal_snippets": [
            {
                "id": r.snippet_id,
                "keywords": json.loads(r.keywords) if r.keywords else [],
                "text": r.text,
            }
            for r in snippet_rows
        ],
    }
    return version_tag


def clear_config_cache() -> None:
    global _cache
    _cache = None
    _json_fallback_labels.cache_clear()
    _json_fallback_routing.cache_clear()
    _json_fallback_legal_snippets.cache_clear()
    _json_fallback_hard_rules.cache_clear()
    from app.services.ai_review.revision_router import clear_routing_cache
    from app.services.ai_review.seed_store import reload_cache
    from app.services.ai_review.rag_service import clear_snippet_cache

    reload_cache()
    clear_routing_cache()
    clear_snippet_cache()


def _use_cache() -> bool:
    return _cache is not None and bool(_cache.get("checklists", {}).get("items"))


def get_review_checklists() -> dict[str, Any]:
    if _use_cache():
        return _cache["checklists"]
    return _json_fallback_checklists()


def get_risk_labels() -> dict[str, Any]:
    if _use_cache():
        return _cache["risk_labels"]
    return _json_fallback_labels()


def get_revision_routing() -> dict[str, Any]:
    if _use_cache():
        return _cache["revision_routing"]
    return _json_fallback_routing()


@lru_cache(maxsize=1)
def _json_fallback_hard_rules() -> list[dict[str, Any]]:
    from app.services.ai_review.config_seed import DEFAULT_HARD_RULES

    out: list[dict[str, Any]] = []
    for row in DEFAULT_HARD_RULES:
        cfg = row.get("config_json") or {}
        out.append(
            {
                "rule_id": row["rule_id"],
                "name": row.get("name", row["rule_id"]),
                "enabled": True,
                "rule_type": row.get("rule_type", "regex"),
                "config": cfg,
                "risk_level": row.get("risk_level", "medium"),
                "label_id": row.get("label_id"),
                "gate_id": row.get("gate_id"),
                "dimension": row.get("dimension", "compliance_check"),
                "title": row.get("title"),
                "suggestion": row.get("suggestion"),
                "legal_basis": row.get("legal_basis"),
                "revision_method": row.get("revision_method", "comment"),
                "clause": row.get("clause", ""),
            }
        )
    return out


def get_hard_rules() -> list[dict[str, Any]]:
    if _use_cache():
        return _cache.get("hard_rules", [])
    return _json_fallback_hard_rules()


def get_legal_snippets() -> list[dict[str, Any]]:
    if _use_cache():
        return _cache.get("legal_snippets", [])
    return _json_fallback_legal_snippets()


def get_current_config_version() -> Optional[str]:
    if _use_cache():
        return _cache.get("version")
    return None


async def sync_runtime_cache_if_published(db: AsyncSession) -> str | None:
    """若存在已发布版本则刷新内存缓存，使 DB 变更对审查任务生效。"""
    has_current = await db.scalar(
        select(AIConfigVersion.id).where(AIConfigVersion.is_current.is_(True)).limit(1)
    )
    if not has_current:
        return None
    return await refresh_config_cache(db)
