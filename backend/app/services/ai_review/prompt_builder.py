# -*- coding: utf-8 -*-
"""Prompt 组装 — 清单/标签/类型策略驱动 LLM 审查。"""
from __future__ import annotations

from typing import Any, Optional

from app.core.config import settings
from app.services.ai_review.clause_parser import Clause
from app.services.ai_review.config_store import get_review_checklists, get_risk_labels
from app.services.ai_review.seed_store import get_contract_type_profiles

# LLM 五维 → 关联 gate_id
DIMENSION_GATE_MAP: dict[str, list[str]] = {
    "compliance": ["gate_validity", "gate_subject"],
    "risk": ["gate_clause"],
    "financial": ["gate_clause"],
    "capability": ["gate_clause"],
    "anomaly": ["gate_consistency"],
}

# checklist category 关键词 → dimension
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "compliance": ["宏观", "主体", "效力", "合规", "授权"],
    "risk": ["违约", "争议", "解除", "责任"],
    "financial": ["价款", "支付", "财务", "税务", "金额"],
    "capability": ["交付", "验收", "履约", "质量", "质保"],
    "anomaly": ["形式", "一致", "格式", "排版"],
}

VALID_LABEL_IDS = frozenset(
    {f"L{i:02d}" for i in range(1, 16)}
    | {f"RL-{i:03d}" for i in range(1, 16)}
)

_RISK_LEVEL_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def sanitize_label_id(raw: str | None) -> str | None:
    """校验 label_id，非法则返回 None。"""
    if not raw:
        return None
    key = raw.strip().upper()
    if key in VALID_LABEL_IDS:
        return key
    # 兼容 RL-001 → L01 简写（前端用 RL-xxx）
    if key.startswith("RL-"):
        try:
            num = int(key.split("-")[1])
            candidate = f"L{num:02d}"
            if candidate in VALID_LABEL_IDS:
                return candidate
        except (ValueError, IndexError):
            pass
    return None


def _profile_for_type(contract_type: str, profile_key: str | None) -> dict[str, Any]:
    try:
        profiles = get_contract_type_profiles().get("items", [])
    except Exception:
        return {}
    key = profile_key or contract_type
    for p in profiles:
        if p.get("profile_key") == key:
            return p
    for p in profiles:
        if contract_type and contract_type in (p.get("profile_key") or ""):
            return p
    return {}


def filter_checklist_for_dimension(
    items: list[dict[str, Any]],
    dimension: str,
    *,
    contract_type: str = "other",
    profile: dict[str, Any] | None = None,
    max_items: int = 15,
) -> list[dict[str, Any]]:
    """按维度与 gate 过滤 checklist 子集。"""
    profile = profile or {}
    gate_ids = set(DIMENSION_GATE_MAP.get(dimension, ["gate_clause"]))
    keywords = _CATEGORY_KEYWORDS.get(dimension, [])

    filtered: list[dict[str, Any]] = []
    for item in items:
        gate = item.get("gate_id") or ""
        category = item.get("category") or ""
        if gate in gate_ids:
            filtered.append(item)
            continue
        if any(kw in category for kw in keywords):
            filtered.append(item)

    def sort_key(it: dict) -> tuple:
        rl = _RISK_LEVEL_ORDER.get(it.get("risk_level") or "low", 9)
        gp = int(it.get("gate_priority") or 99)
        return (rl, gp)

    filtered.sort(key=sort_key)
    return filtered[:max_items]


def format_risk_labels_table(labels: list[dict[str, Any]]) -> str:
    lines = ["【风险标签枚举】输出 issue 时须选用下列 label_id 之一，无法匹配则留空："]
    for lb in labels:
        lid = lb.get("id") or ""
        name = lb.get("name") or ""
        gate = lb.get("gate_id") or ""
        lines.append(f"- {lid} {name} (gate: {gate})")
    return "\n".join(lines)


def format_checklist_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return "（本维度无专项清单项）"
    lines = []
    for it in items:
        iid = it.get("id")
        item = it.get("item") or ""
        desc = it.get("description") or ""
        lines.append(f"- [id={iid}] {item}：{desc}")
    return "\n".join(lines)


def build_dimension_prompt(
    *,
    dimension: str,
    dimension_instruction: str,
    contract_text: str,
    clauses: list[Clause],
    contract_type: str = "other",
    profile_key: str | None = None,
    segment_text: str | None = None,
) -> str:
    """构建单维度审查 user prompt。"""
    try:
        all_checklist = get_review_checklists().get("items", [])
    except Exception:
        all_checklist = []
    try:
        labels = get_risk_labels().get("items", [])
    except Exception:
        labels = []

    profile = _profile_for_type(contract_type, profile_key)
    checklist_subset = filter_checklist_for_dimension(
        all_checklist, dimension, contract_type=contract_type, profile=profile
    )

    relevant = _filter_clauses_for_dimension(clauses, dimension)
    clauses_text = ""
    for c in relevant[:12]:
        clauses_text += f"\n[条款 {c.clause_id}] {c.title}\n{c.content[:600]}\n"

    body = segment_text if segment_text is not None else contract_text
    profile_block = ""
    if profile:
        profile_block = (
            f"## 合同类型审查要点\n"
            f"类型：{profile.get('profile_key', contract_type)}\n"
            f"核心风险：{profile.get('core_risks', '')}\n"
            f"要点：\n" + "\n".join(f"- {p}" for p in (profile.get("review_points") or [])[:8])
        )

    return (
        f"{dimension_instruction}\n\n"
        f"## 合同类型\n{contract_type}\n\n"
        f"{profile_block}\n\n"
        f"## 合同正文\n{body[:10000]}\n\n"
        f"## 相关条款\n{clauses_text or '（无切分条款）'}\n\n"
        f"## 本维度审查清单（须逐条评估，输出 checklist_coverage）\n"
        f"{format_checklist_items(checklist_subset)}\n\n"
        f"{format_risk_labels_table(labels)}\n\n"
        f"## 输出要求\n"
        f"直接输出 JSON，包含 dimension、score(0-100)、issues、checklist_coverage、summary。\n"
        f"issues 每项含：keyword、severity、description、label_id、gate_id、"
        f"reasoning、evidence_quote（从正文摘录）、legal_basis_candidate。\n"
        f"checklist_coverage 每项含：item_id、status(pass|fail|unknown)、note。\n"
        f"prompt_version: {settings.AI_PROMPT_VERSION}\n"
    )


def _filter_clauses_for_dimension(clauses: list[Clause], dimension: str) -> list[Clause]:
    type_map = {
        "compliance": ["definitions", "rights_obligations", "other"],
        "risk": ["breach", "dispute", "termination", "force_majeure"],
        "financial": ["financial", "breach"],
        "capability": ["rights_obligations", "financial", "termination"],
        "anomaly": [],
    }
    target = type_map.get(dimension, [])
    if not target:
        return clauses
    return [c for c in clauses if c.section_type in target]


def get_prompt_version() -> str:
    return settings.AI_PROMPT_VERSION
