# -*- coding: utf-8 -*-
"""Self-Correction — 审查结果二次质检。"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.services.ai_review.ai_engine import get_engine
from app.services.ai_review.issue_schema import AiReviewIssue, apply_high_risk_guardrail

logger = logging.getLogger(__name__)

_CORRECTION_PROMPT = """你是合同审查质检员。通读摘要与初审查 issues 如下。
请检查：1) 无依据的高风险 2) 与通读摘要明显矛盾 3) 重复项。
输出 JSON：{{"accepted_indices": [0,1], "rejected_indices": [2], "notes": "..."}}
若无法解析，返回 {{"accepted_indices": [], "rejected_indices": [], "notes": "skip"}}

通读摘要:
{read_through}

Issues JSON:
{issues}
"""


async def run_self_correction(
    issues: list[AiReviewIssue],
    read_through: dict[str, Any],
) -> list[AiReviewIssue]:
    """S6 后反思；Mock 或关闭时仅跑 guardrail。"""
    if not settings.AI_REVIEW_SELF_CORRECT or settings.AI_REVIEW_MOCK:
        return apply_high_risk_guardrail(issues)

    try:
        engine = get_engine()
        issues_json = [i.model_dump_public() for i in issues]
        import json as _json

        prompt = _CORRECTION_PROMPT.format(
            read_through=_json.dumps(read_through, ensure_ascii=False)[:4000],
            issues=_json.dumps(issues_json, ensure_ascii=False)[:6000],
        )
        result = await engine._call_llm(prompt)
        rejected = set(result.get("rejected_indices") or [])
        filtered = [i for idx, i in enumerate(issues) if idx not in rejected]
        return apply_high_risk_guardrail(filtered)
    except Exception as exc:
        logger.warning("Self-correction 失败: %s", exc)
        return apply_high_risk_guardrail(issues)
