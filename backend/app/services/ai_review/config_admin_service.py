# -*- coding: utf-8 -*-
"""AI 审查配置管理（CRUD、发布、反馈统计）。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_review_config import (
    AIConfigVersion,
    AIHardRule,
    AILegalSnippet,
    AIReviewChecklistItem,
    AIRevisionRoutingRule,
    AIRiskLabel,
    AIRuleFeedbackStat,
)
from app.models.ai_review_issue import AIReviewIssue
from app.services.ai_review.config_store import (
    clear_config_cache,
    refresh_config_cache,
    sync_runtime_cache_if_published,
)
from app.services.ai_review.rule_executor import evaluate_detect_config, run_hard_rule


def _checklist_to_dict(row: AIReviewChecklistItem) -> dict[str, Any]:
    detect = None
    if row.detect_config:
        try:
            detect = json.loads(row.detect_config)
        except json.JSONDecodeError:
            pass
    return {
        "id": row.id,
        "legacy_id": row.legacy_id,
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


async def list_checklist_items(
    db: AsyncSession,
    *,
    gate_id: str | None = None,
    auto_detectable: bool | None = None,
    enabled: bool | None = None,
) -> list[dict]:
    q = select(AIReviewChecklistItem).order_by(
        AIReviewChecklistItem.gate_priority, AIReviewChecklistItem.legacy_id
    )
    if gate_id:
        q = q.where(AIReviewChecklistItem.gate_id == gate_id)
    if auto_detectable is not None:
        q = q.where(AIReviewChecklistItem.auto_detectable.is_(auto_detectable))
    if enabled is not None:
        q = q.where(AIReviewChecklistItem.enabled.is_(enabled))
    rows = (await db.execute(q)).scalars().all()
    return [_checklist_to_dict(r) for r in rows]


async def create_checklist_item(db: AsyncSession, data: dict) -> dict:
    legacy_id = int(data.get("legacy_id") or 0)
    if legacy_id <= 0:
        max_id = await db.scalar(select(func.max(AIReviewChecklistItem.legacy_id)))
        legacy_id = (max_id or 0) + 1
    exists = await db.scalar(
        select(AIReviewChecklistItem).where(AIReviewChecklistItem.legacy_id == legacy_id)
    )
    if exists:
        raise HTTPException(status_code=400, detail=f"legacy_id {legacy_id} 已存在")
    detect = data.get("detect_config")
    row = AIReviewChecklistItem(
        legacy_id=legacy_id,
        category=data.get("category", ""),
        item=data.get("item", ""),
        description=data.get("description"),
        applicable_contracts=data.get("applicable_contracts"),
        risk_level=data.get("risk_level", "medium"),
        gate_id=data.get("gate_id", "gate_clause"),
        gate_priority=int(data.get("gate_priority", 0)),
        auto_detectable=bool(data.get("auto_detectable")),
        detect_config=json.dumps(detect, ensure_ascii=False) if detect else None,
        enabled=bool(data.get("enabled", True)),
    )
    db.add(row)
    await db.flush()
    return _checklist_to_dict(row)


async def update_checklist_item(db: AsyncSession, item_id: int, data: dict) -> dict:
    row = await db.get(AIReviewChecklistItem, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="清单项不存在")
    for field in (
        "category", "item", "description", "applicable_contracts",
        "risk_level", "gate_id", "gate_priority", "auto_detectable", "enabled",
    ):
        if field in data:
            setattr(row, field, data[field])
    if "gate_priority" in data:
        row.gate_priority = int(data["gate_priority"])
    if "detect_config" in data:
        dc = data["detect_config"]
        row.detect_config = json.dumps(dc, ensure_ascii=False) if dc else None
    await db.flush()
    return _checklist_to_dict(row)


async def delete_checklist_item(db: AsyncSession, item_id: int) -> None:
    row = await db.get(AIReviewChecklistItem, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="清单项不存在")
    await db.delete(row)


async def list_risk_labels(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(AIRiskLabel).order_by(AIRiskLabel.label_id))).scalars().all()
    return [
        {
            "id": r.label_id,
            "name": r.name,
            "category": r.category,
            "gate_id": r.gate_id,
            "color": r.color,
            "enabled": r.enabled,
        }
        for r in rows
    ]


async def update_risk_label(db: AsyncSession, label_id: str, data: dict) -> dict:
    row = await db.get(AIRiskLabel, label_id)
    if not row:
        raise HTTPException(status_code=404, detail="标签不存在")
    for field in ("name", "category", "gate_id", "color", "enabled"):
        if field in data:
            setattr(row, field, data[field])
    await db.flush()
    return {
        "id": row.label_id,
        "name": row.name,
        "category": row.category,
        "gate_id": row.gate_id,
        "color": row.color,
        "enabled": row.enabled,
    }


async def list_revision_routing(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(AIRevisionRoutingRule).order_by(
                AIRevisionRoutingRule.priority, AIRevisionRoutingRule.id
            )
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "issue_type": r.issue_type,
            "default_method": r.default_method,
            "auto_applicable": r.auto_applicable,
            "self_check_questions": r.self_check_questions,
            "notes": r.notes,
            "priority": r.priority,
            "enabled": r.enabled,
        }
        for r in rows
    ]


async def create_revision_routing(db: AsyncSession, data: dict) -> dict:
    row = AIRevisionRoutingRule(
        issue_type=data.get("issue_type", ""),
        default_method=data.get("default_method", "comment"),
        auto_applicable=bool(data.get("auto_applicable", True)),
        self_check_questions=data.get("self_check_questions"),
        notes=data.get("notes"),
        priority=int(data.get("priority", 0)),
        enabled=bool(data.get("enabled", True)),
    )
    db.add(row)
    await db.flush()
    return {
        "id": row.id,
        "issue_type": row.issue_type,
        "default_method": row.default_method,
        "auto_applicable": row.auto_applicable,
        "self_check_questions": row.self_check_questions,
        "notes": row.notes,
        "priority": row.priority,
        "enabled": row.enabled,
    }


async def update_revision_routing(db: AsyncSession, rule_id: int, data: dict) -> dict:
    row = await db.get(AIRevisionRoutingRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="路由规则不存在")
    for field in (
        "issue_type", "default_method", "auto_applicable",
        "self_check_questions", "notes", "priority", "enabled",
    ):
        if field in data:
            setattr(row, field, data[field])
    await db.flush()
    return {
        "id": row.id,
        "issue_type": row.issue_type,
        "default_method": row.default_method,
        "auto_applicable": row.auto_applicable,
        "self_check_questions": row.self_check_questions,
        "notes": row.notes,
        "priority": row.priority,
        "enabled": row.enabled,
    }


async def delete_revision_routing(db: AsyncSession, rule_id: int) -> None:
    row = await db.get(AIRevisionRoutingRule, rule_id)
    if not row:
        raise HTTPException(status_code=404, detail="路由规则不存在")
    await db.delete(row)


def _hard_rule_to_dict(row: AIHardRule) -> dict:
    cfg = {}
    if row.config_json:
        try:
            cfg = json.loads(row.config_json)
        except json.JSONDecodeError:
            pass
    return {
        "id": row.id,
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


async def list_hard_rules(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(AIHardRule).order_by(AIHardRule.rule_id))).scalars().all()
    return [_hard_rule_to_dict(r) for r in rows]


async def create_hard_rule(db: AsyncSession, data: dict) -> dict:
    rid = data.get("rule_id")
    if not rid:
        raise HTTPException(status_code=400, detail="rule_id 必填")
    if await db.scalar(select(AIHardRule).where(AIHardRule.rule_id == rid)):
        raise HTTPException(status_code=400, detail="rule_id 已存在")
    cfg = data.get("config") or {}
    row = AIHardRule(
        rule_id=rid,
        name=data.get("name", rid),
        enabled=bool(data.get("enabled", True)),
        rule_type=data.get("rule_type", "regex"),
        config_json=json.dumps(cfg, ensure_ascii=False),
        risk_level=data.get("risk_level", "medium"),
        label_id=data.get("label_id"),
        gate_id=data.get("gate_id"),
        dimension=data.get("dimension", "compliance_check"),
        title=data.get("title"),
        suggestion=data.get("suggestion"),
        legal_basis=data.get("legal_basis"),
        revision_method=data.get("revision_method", "comment"),
        clause=data.get("clause", ""),
    )
    db.add(row)
    await db.flush()
    return _hard_rule_to_dict(row)


async def update_hard_rule(db: AsyncSession, pk_id: int, data: dict) -> dict:
    row = await db.get(AIHardRule, pk_id)
    if not row:
        raise HTTPException(status_code=404, detail="硬规则不存在")
    for field in (
        "rule_id", "name", "enabled", "rule_type", "risk_level", "label_id",
        "gate_id", "dimension", "title", "suggestion", "legal_basis",
        "revision_method", "clause",
    ):
        if field in data:
            setattr(row, field, data[field])
    if "config" in data:
        row.config_json = json.dumps(data["config"] or {}, ensure_ascii=False)
    await db.flush()
    return _hard_rule_to_dict(row)


async def delete_hard_rule(db: AsyncSession, pk_id: int) -> None:
    row = await db.get(AIHardRule, pk_id)
    if not row:
        raise HTTPException(status_code=404, detail="硬规则不存在")
    await db.delete(row)


async def list_legal_snippets(db: AsyncSession, *, keyword: str | None = None) -> list[dict]:
    rows = (await db.execute(select(AILegalSnippet).order_by(AILegalSnippet.snippet_id))).scalars().all()
    out = []
    for r in rows:
        kws = json.loads(r.keywords) if r.keywords else []
        if keyword and keyword not in " ".join(kws) and keyword not in r.text:
            continue
        out.append(
            {
                "id": r.id,
                "snippet_id": r.snippet_id,
                "keywords": kws,
                "text": r.text,
                "enabled": r.enabled,
            }
        )
    return out


async def create_legal_snippet(db: AsyncSession, data: dict) -> dict:
    sid = data.get("snippet_id")
    if not sid:
        raise HTTPException(status_code=400, detail="snippet_id 必填")
    row = AILegalSnippet(
        snippet_id=sid,
        keywords=json.dumps(data.get("keywords", []), ensure_ascii=False),
        text=data.get("text", ""),
        enabled=bool(data.get("enabled", True)),
    )
    db.add(row)
    await db.flush()
    return {
        "id": row.id,
        "snippet_id": row.snippet_id,
        "keywords": data.get("keywords", []),
        "text": row.text,
        "enabled": row.enabled,
    }


async def update_legal_snippet(db: AsyncSession, pk_id: int, data: dict) -> dict:
    row = await db.get(AILegalSnippet, pk_id)
    if not row:
        raise HTTPException(status_code=404, detail="法条不存在")
    if "snippet_id" in data:
        row.snippet_id = data["snippet_id"]
    if "keywords" in data:
        row.keywords = json.dumps(data["keywords"], ensure_ascii=False)
    if "text" in data:
        row.text = data["text"]
    if "enabled" in data:
        row.enabled = bool(data["enabled"])
    await db.flush()
    return {
        "id": row.id,
        "snippet_id": row.snippet_id,
        "keywords": json.loads(row.keywords) if row.keywords else [],
        "text": row.text,
        "enabled": row.enabled,
    }


async def delete_legal_snippet(db: AsyncSession, pk_id: int) -> None:
    row = await db.get(AILegalSnippet, pk_id)
    if not row:
        raise HTTPException(status_code=404, detail="法条不存在")
    await db.delete(row)


def _parse_csv_keywords(raw: str | None) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    for sep in (",", "，", "、", "|"):
        if sep in text:
            return [k.strip() for k in text.split(sep) if k.strip()]
    return [text]


def _parse_csv_enabled(raw: str | None) -> bool:
    if raw is None or str(raw).strip() == "":
        return True
    v = str(raw).strip().lower()
    if v in ("0", "false", "no", "否", "n"):
        return False
    return True


async def import_legal_snippets_csv(db: AsyncSession, text: str) -> dict[str, Any]:
    """CSV 批量导入法条：snippet_id,keywords,text,enabled（upsert，不刷新运行时缓存）。"""
    import csv
    from io import StringIO

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    reader = csv.DictReader(StringIO(text))
    for idx, row in enumerate(reader, start=2):
        sid = (row.get("snippet_id") or row.get("id") or "").strip()
        body_text = (row.get("text") or row.get("条文") or "").strip()
        if not sid:
            skipped += 1
            errors.append(f"行{idx}: 缺少 snippet_id")
            continue
        if not body_text:
            skipped += 1
            errors.append(f"行{idx}: 缺少 text")
            continue
        keywords = _parse_csv_keywords(row.get("keywords") or row.get("关键词"))
        enabled = _parse_csv_enabled(row.get("enabled") or row.get("启用"))
        kw_json = json.dumps(keywords, ensure_ascii=False)
        try:
            existing = await db.scalar(
                select(AILegalSnippet).where(AILegalSnippet.snippet_id == sid)
            )
            if existing:
                existing.keywords = kw_json
                existing.text = body_text
                existing.enabled = enabled
                updated += 1
            else:
                db.add(
                    AILegalSnippet(
                        snippet_id=sid,
                        keywords=kw_json,
                        text=body_text,
                        enabled=enabled,
                    )
                )
                created += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"行{idx}: {exc}")
    await db.flush()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


async def publish_config(db: AsyncSession, user_id: int, note: str | None = None) -> dict:
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    await db.execute(update(AIConfigVersion).values(is_current=False))
    db.add(
        AIConfigVersion(
            version=version,
            is_current=True,
            published_by=user_id,
            note=note or "发布",
        )
    )
    tag = version
    for model in (
        AIReviewChecklistItem,
        AIRiskLabel,
        AIRevisionRoutingRule,
        AIHardRule,
        AILegalSnippet,
    ):
        await db.execute(update(model).values(version_tag=tag))
    await db.commit()
    ver = await refresh_config_cache(db)
    return {"version": ver or version, "published_at": datetime.now(timezone.utc).isoformat()}


async def import_from_seeds(db: AsyncSession, user_id: int | None = None) -> dict:
    from app.services.ai_review.config_seed import import_from_json_seeds

    version = datetime.now(timezone.utc).strftime("import-%Y%m%d%H%M%S")
    await import_from_json_seeds(version, published_by=user_id)
    return {"version": version}


async def test_rule_sandbox(
    text: str,
    *,
    detect_config: dict | None = None,
    hard_rule: dict | None = None,
    amount: float | None = None,
) -> dict:
    hits = []
    if detect_config:
        ok, msg = evaluate_detect_config(text, detect_config)
        if ok:
            hits.append({"type": "detect_config", "message": msg})
    if hard_rule:
        issue = run_hard_rule(hard_rule, text, amount=amount)
        if issue:
            hits.append({"type": "hard_rule", "issue": issue.model_dump()})
    return {"hits": hits, "count": len(hits)}


async def record_issue_feedback(db: AsyncSession, issue: Any, human_status: str) -> None:
    """误报/确认时累加反馈统计。"""
    rule_key = None
    source = "llm"
    if issue.rule_id:
        rule_key = issue.rule_id
        source = "rule" if (issue.source or "") == "rule" else issue.source or "rule"
    elif issue.label_id:
        rule_key = f"label:{issue.label_id}"
        source = "llm"
    if not rule_key:
        return
    row = await db.scalar(select(AIRuleFeedbackStat).where(AIRuleFeedbackStat.rule_key == rule_key))
    if not row:
        row = AIRuleFeedbackStat(rule_key=rule_key, source=source or "rule")
        db.add(row)
    if human_status == "false_positive":
        row.fp_count = (row.fp_count or 0) + 1
    elif human_status == "confirmed":
        row.confirm_count = (row.confirm_count or 0) + 1
    row.last_seen_at = datetime.now(timezone.utc)


async def get_feedback_stats(db: AsyncSession, *, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(AIRuleFeedbackStat)
            .where(AIRuleFeedbackStat.last_seen_at >= since)
            .order_by(AIRuleFeedbackStat.fp_count.desc())
        )
    ).scalars().all()
    out = []
    for r in rows:
        total = (r.fp_count or 0) + (r.confirm_count or 0)
        fp_rate = (r.fp_count or 0) / max(total, 1)
        out.append(
            {
                "rule_key": r.rule_key,
                "source": r.source,
                "fp_count": r.fp_count or 0,
                "confirm_count": r.confirm_count or 0,
                "fp_rate": round(fp_rate, 4),
                "suggest_disable": fp_rate >= 0.4 and total >= 5,
            }
        )
    return out


async def disable_by_rule_key(db: AsyncSession, rule_key: str) -> dict:
    disabled_kind = None
    if rule_key.startswith("CK-"):
        legacy_str = rule_key.replace("CK-", "")
        row = await db.scalar(select(AIHardRule).where(AIHardRule.rule_id == rule_key))
        if row:
            row.enabled = False
            disabled_kind = "hard_rule"
        else:
            try:
                legacy = int(legacy_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效 rule_key")
            cl = await db.scalar(
                select(AIReviewChecklistItem).where(AIReviewChecklistItem.legacy_id == legacy)
            )
            if cl:
                cl.enabled = False
                disabled_kind = "checklist"
    else:
        row = await db.scalar(select(AIHardRule).where(AIHardRule.rule_id == rule_key))
        if row:
            row.enabled = False
            disabled_kind = "hard_rule"
    if not disabled_kind:
        raise HTTPException(status_code=404, detail="未找到对应规则")
    await db.flush()
    ver = await sync_runtime_cache_if_published(db)
    return {
        "rule_key": rule_key,
        "disabled": disabled_kind,
        "cache_refreshed": ver is not None,
        "hint": None if ver else "尚无已发布版本，请由管理员发布配置后生效",
    }
