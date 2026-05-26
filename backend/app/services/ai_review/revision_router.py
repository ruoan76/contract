# -*- coding: utf-8 -*-
"""修订方式路由 — revision_routing 种子驱动。"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.services.ai_review.issue_schema import AiReviewIssue
from app.services.ai_review.seed_store import get_cuad_bridge, get_revision_routing

logger = logging.getLogger(__name__)

# label_id / 维度 → 默认 issue_type（用于查 routing 表）
_LABEL_TO_ISSUE_TYPE: dict[str, str] = {
    "L01": "合同效力问题",
    "L02": "格式条款问题",
    "L03": "主体授权问题",
    "L06": "价款与支付问题",
    "L07": "交付验收问题",
    "L08": "违约责任问题",
}

_TRACK_CHANGE_KEYWORDS = (
    "错别字",
    "笔误",
    "标点",
    "日期格式",
    "格式",
    "排版",
    "名称错误",
)


@lru_cache(maxsize=1)
def _routing_index() -> dict[str, str]:
    """issue_type → default_method"""
    try:
        items = get_revision_routing().get("items", [])
    except Exception:
        return {}
    return {
        (it.get("issue_type") or ""): (it.get("default_method") or "comment")
        for it in items
        if it.get("issue_type")
    }


def resolve_revision_method(issue: AiReviewIssue) -> str:
    """为单条 issue 解析 revision_method。"""
    routing = _routing_index()
    issue_type = _infer_issue_type(issue)
    if issue_type and issue_type in routing:
        return routing[issue_type]

    title_desc = f"{issue.title} {issue.description}"
    if any(kw in title_desc for kw in _TRACK_CHANGE_KEYWORDS):
        return "track_changes"

    if issue.gate_id == "gate_consistency":
        return "track_changes"

    return "comment"


def apply_revision_routing(issues: list[AiReviewIssue]) -> list[AiReviewIssue]:
    """批量填充 revision_method。"""
    for item in issues:
        if item.source == "rule" and item.revision_method:
            continue
        item.revision_method = resolve_revision_method(item)
    return issues


def _infer_issue_type(issue: AiReviewIssue) -> str | None:
    if issue.label_id and issue.label_id in _LABEL_TO_ISSUE_TYPE:
        return _LABEL_TO_ISSUE_TYPE[issue.label_id]
    try:
        bridge = get_cuad_bridge().get("items", [])
        for row in bridge:
            if row.get("label_id") == issue.label_id:
                return row.get("issue_type")
    except Exception:
        pass
    return None
