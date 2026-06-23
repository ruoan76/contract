# -*- coding: utf-8 -*-
"""AI 审查配置管理 API（清单/标签/路由/硬规则/法条/发布/反馈）。"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_any_role, require_role
from app.db.database import get_db
from app.models.contract import User
from app.services.ai_review.config_admin_service import (
    create_checklist_item,
    create_hard_rule,
    create_legal_snippet,
    create_revision_routing,
    delete_checklist_item,
    delete_hard_rule,
    delete_legal_snippet,
    delete_revision_routing,
    disable_by_rule_key,
    get_feedback_stats,
    import_from_seeds,
    import_legal_snippets_csv,
    list_checklist_items,
    list_hard_rules,
    list_legal_snippets,
    list_revision_routing,
    list_risk_labels,
    publish_config,
    test_rule_sandbox,
    update_checklist_item,
    update_hard_rule,
    update_legal_snippet,
    update_revision_routing,
    update_risk_label,
)
from app.services.ai_review.config_store import get_current_config_version

router = APIRouter()

_admin = require_role("admin")
_legal_edit = require_any_role("admin", "legal")


def _wrap(data: Any) -> dict:
    return {"code": 200, "data": data}


class ChecklistBody(BaseModel):
    legacy_id: Optional[int] = None
    category: str = ""
    item: str = ""
    description: Optional[str] = None
    applicable_contracts: Optional[str] = None
    risk_level: str = "medium"
    gate_id: str = "gate_clause"
    gate_priority: int = 0
    auto_detectable: bool = False
    detect_config: Optional[dict] = None
    enabled: bool = True


class RiskLabelBody(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    gate_id: Optional[str] = None
    color: Optional[str] = None
    enabled: Optional[bool] = None


class RoutingBody(BaseModel):
    issue_type: str = ""
    default_method: str = "comment"
    auto_applicable: bool = True
    self_check_questions: Optional[str] = None
    notes: Optional[str] = None
    priority: int = 0
    enabled: bool = True


class HardRuleBody(BaseModel):
    rule_id: Optional[str] = None
    name: str = ""
    enabled: bool = True
    rule_type: str = "regex"
    config: dict = Field(default_factory=dict)
    risk_level: str = "medium"
    label_id: Optional[str] = None
    gate_id: Optional[str] = None
    dimension: str = "compliance_check"
    title: Optional[str] = None
    suggestion: Optional[str] = None
    legal_basis: Optional[str] = None
    revision_method: str = "comment"
    clause: str = ""


class LegalSnippetBody(BaseModel):
    snippet_id: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    text: str = ""
    enabled: bool = True


class PublishBody(BaseModel):
    note: Optional[str] = None


class RuleTestBody(BaseModel):
    text: str
    detect_config: Optional[dict] = None
    hard_rule: Optional[dict] = None
    amount: Optional[float] = None


class DisableRuleBody(BaseModel):
    rule_key: str


@router.get("/config/version", summary="当前配置版本")
async def config_version(_user: User = Depends(_legal_edit)):
    return _wrap({"version": get_current_config_version()})


@router.get("/config/checklist-items", summary="审查清单列表")
async def get_checklist_items(
    gate_id: str | None = None,
    auto_detectable: bool | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    items = await list_checklist_items(
        db, gate_id=gate_id, auto_detectable=auto_detectable, enabled=enabled
    )
    return _wrap({"items": items, "count": len(items)})


@router.post("/config/checklist-items", summary="新增清单项")
async def post_checklist_item(
    body: ChecklistBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    row = await create_checklist_item(db, body.model_dump())
    return _wrap(row)


@router.put("/config/checklist-items/{item_id}", summary="更新清单项")
async def put_checklist_item(
    item_id: int,
    body: ChecklistBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    row = await update_checklist_item(db, item_id, body.model_dump(exclude_unset=True))
    return _wrap(row)


@router.delete("/config/checklist-items/{item_id}", summary="删除清单项")
async def remove_checklist_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    await delete_checklist_item(db, item_id)
    return _wrap({"deleted": item_id})


@router.get("/config/risk-labels", summary="风险标签列表")
async def get_risk_labels_api(db: AsyncSession = Depends(get_db), _user: User = Depends(_legal_edit)):
    return _wrap({"items": await list_risk_labels(db)})


@router.put("/config/risk-labels/{label_id}", summary="更新风险标签")
async def put_risk_label(
    label_id: str,
    body: RiskLabelBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap(await update_risk_label(db, label_id, body.model_dump(exclude_unset=True)))


@router.get("/config/revision-routing", summary="修订路由列表")
async def get_revision_routing_api(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap({"items": await list_revision_routing(db)})


@router.post("/config/revision-routing", summary="新增修订路由")
async def post_revision_routing(
    body: RoutingBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap(await create_revision_routing(db, body.model_dump()))


@router.put("/config/revision-routing/{rule_id}", summary="更新修订路由")
async def put_revision_routing(
    rule_id: int,
    body: RoutingBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap(await update_revision_routing(db, rule_id, body.model_dump(exclude_unset=True)))


@router.delete("/config/revision-routing/{rule_id}", summary="删除修订路由")
async def remove_revision_routing(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    await delete_revision_routing(db, rule_id)
    return _wrap({"deleted": rule_id})


@router.get("/config/hard-rules", summary="硬规则列表")
async def get_hard_rules_api(db: AsyncSession = Depends(get_db), _user: User = Depends(_legal_edit)):
    return _wrap({"items": await list_hard_rules(db)})


@router.post("/config/hard-rules", summary="新增硬规则")
async def post_hard_rule(
    body: HardRuleBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    data = body.model_dump()
    if "config" in data:
        data["config"] = data["config"]
    return _wrap(await create_hard_rule(db, data))


@router.put("/config/hard-rules/{pk_id}", summary="更新硬规则")
async def put_hard_rule(
    pk_id: int,
    body: HardRuleBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    return _wrap(await update_hard_rule(db, pk_id, body.model_dump(exclude_unset=True)))


@router.delete("/config/hard-rules/{pk_id}", summary="删除硬规则")
async def remove_hard_rule(
    pk_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    await delete_hard_rule(db, pk_id)
    return _wrap({"deleted": pk_id})


@router.post("/config/rules/test", summary="规则沙箱测试")
async def rules_test(body: RuleTestBody, _user: User = Depends(_legal_edit)):
    return _wrap(
        await test_rule_sandbox(
            body.text,
            detect_config=body.detect_config,
            hard_rule=body.hard_rule,
            amount=body.amount,
        )
    )


@router.get("/config/legal-snippets", summary="法条库列表")
async def get_legal_snippets_api(
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap({"items": await list_legal_snippets(db, keyword=keyword)})


@router.post("/config/legal-snippets", summary="新增法条")
async def post_legal_snippet(
    body: LegalSnippetBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap(await create_legal_snippet(db, body.model_dump()))


@router.put("/config/legal-snippets/{pk_id}", summary="更新法条")
async def put_legal_snippet(
    pk_id: int,
    body: LegalSnippetBody,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    return _wrap(await update_legal_snippet(db, pk_id, body.model_dump(exclude_unset=True)))


@router.delete("/config/legal-snippets/{pk_id}", summary="删除法条")
async def remove_legal_snippet(
    pk_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    await delete_legal_snippet(db, pk_id)
    return _wrap({"deleted": pk_id})


@router.post("/config/legal-snippets/import-csv", summary="CSV 批量导入法条")
async def import_legal_snippets_csv_api(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gbk", errors="ignore")
    data = await import_legal_snippets_csv(db, text)
    return _wrap(data)


@router.post("/config/publish", summary="发布配置版本")
async def config_publish(
    body: PublishBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    return _wrap(await publish_config(db, user.id, body.note))


@router.post("/config/import-seeds", summary="从 JSON 种子导入")
async def config_import_seeds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    return _wrap(await import_from_seeds(db, user.id))


@router.get("/config/feedback-stats", summary="规则反馈统计")
async def config_feedback_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_legal_edit),
):
    stats = await get_feedback_stats(db, days=days)
    return _wrap({"items": stats, "days": days})


@router.post("/config/disable-rule", summary="一键停用规则")
async def config_disable_rule(
    body: DisableRuleBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_admin),
):
    result = await disable_by_rule_key(db, body.rule_key)
    return _wrap(result)
