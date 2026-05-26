# -*- coding: utf-8 -*-
"""AI 审查执行器 — 薄封装 Orchestrator，供 API / Celery 共用。"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    issues_to_clause_reviews_json,
    issues_to_rule_violations,
)
from app.services.ai_review.orchestrator import run_orchestrated_review

logger = logging.getLogger(__name__)

# MySQL TEXT 上限约 64KB，预留 UTF-8 多字节余量
_MAX_JSON_BYTES = 60_000


def _truncate_utf8(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _compact_clause_reviews(rows: list) -> list:
    """压缩条款镜像，避免 clause_reviews 列溢出。"""
    compact: list = []
    for row in rows[:100]:
        if not isinstance(row, dict):
            compact.append(row)
            continue
        item = dict(row)
        for key in ("reasoning", "evidence_quote", "description", "suggestion"):
            val = item.get(key)
            if isinstance(val, str) and len(val) > 400:
                item[key] = val[:400] + "…"
        compact.append(item)
    return compact


def _json_dumps_bounded(obj: Any, max_bytes: int = _MAX_JSON_BYTES) -> str:
    raw = json.dumps(obj, ensure_ascii=False)
    if len(raw.encode("utf-8")) <= max_bytes:
        return raw
    if isinstance(obj, list) and obj:
        trimmed = _compact_clause_reviews(obj)
        while len(trimmed) > 10:
            trimmed = trimmed[: max(10, len(trimmed) * 3 // 4)]
            raw = json.dumps(trimmed, ensure_ascii=False)
            if len(raw.encode("utf-8")) <= max_bytes:
                return raw
        raw = json.dumps(trimmed[:10], ensure_ascii=False)
        if len(raw.encode("utf-8")) <= max_bytes:
            return raw
    return _truncate_utf8(raw, max_bytes)


async def run_contract_ai_review(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
    profile_key: Optional[str] = None,
    counterparty_blacklisted: bool = False,
) -> dict[str, Any]:
    payload = await run_orchestrated_review(
        contract_text,
        contract_type=contract_type,
        amount=amount,
        profile_key=profile_key,
        counterparty_blacklisted=counterparty_blacklisted,
    )
    # 确保 clause_reviews 镜像存在
    if "issues" in payload and not payload.get("clause_reviews"):
        issues: list[AiReviewIssue] = payload["issues"]
        payload["clause_reviews"] = issues_to_clause_reviews_json(issues)
        payload["rule_violations"] = issues_to_rule_violations(issues)
    return payload


def apply_payload_to_ai_review(ai_review: Any, payload: dict) -> None:
    """将审查结果写入 ORM 对象。"""
    ai_review.review_status = "ai_done"
    ai_review.overall_risk_level = payload.get("overall_risk_level")
    ai_review.overall_risk_score = payload.get("overall_risk_score")
    ai_review.recommendation = payload.get("recommendation")
    raw_clause_rows = payload.get("clause_reviews") or []
    issues_total = len(raw_clause_rows)
    clause_rows = _compact_clause_reviews(raw_clause_rows)
    summary = dict(payload.get("summary") or {})
    summary["issues_total"] = issues_total
    summary["clause_reviews_count"] = len(clause_rows)
    summary["clause_reviews_truncated"] = len(clause_rows) < issues_total
    ai_review.clause_reviews = _json_dumps_bounded(clause_rows)
    ai_review.rule_violations = _json_dumps_bounded(
        payload.get("rule_violations", [])
    )
    ai_review.summary = _json_dumps_bounded(summary)
    ai_review.model_version = payload.get("model_version") or ""
    ai_review.review_duration_seconds = payload.get("review_duration_seconds")


# 兼容旧测试：保留 gates 计算 re-export
from app.services.ai_review.skills.gates import compute_gates_from_payload  # noqa: E402
