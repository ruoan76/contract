# -*- coding: utf-8 -*-
"""S2 通读摘要 Skill。"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.services.ai_review.ai_engine import get_engine

logger = logging.getLogger(__name__)

_READ_THROUGH_PROMPT = """请通读以下合同，输出 JSON（不要 markdown）：
{
  "parties": "合同主体摘要",
  "subject": "标的/服务摘要",
  "price": "价款与支付摘要",
  "delivery": "交付与验收摘要",
  "breach": "违约责任摘要",
  "dispute": "争议解决摘要",
  "overall": "一句话总览"
}
合同类型: {contract_type}
合同正文:
{text}
"""


async def run_read_through(
    contract_text: str,
    *,
    contract_type: str = "other",
) -> dict[str, Any]:
    """S2：LLM 通读摘要；失败时返回启发式占位。"""
    text = (contract_text or "")[:12000]
    fallback = _heuristic_read_through(text)

    if settings.AI_REVIEW_MOCK:
        return fallback

    try:
        engine = get_engine()
        prompt = _READ_THROUGH_PROMPT.format(
            contract_type=contract_type,
            text=text,
        )
        raw = await engine._call_llm(prompt)
        if isinstance(raw, dict) and raw.get("overall"):
            return raw
    except Exception as exc:
        logger.warning("S2 read_through LLM 失败: %s", exc)

    return fallback


def _heuristic_read_through(text: str) -> dict[str, str]:
    """无 LLM 时的最小摘要。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:120] if lines else "合同"
    return {
        "parties": "待 LLM/法务确认主体信息",
        "subject": title,
        "price": "待确认价款条款" if "付款" in text or "价款" in text else "未识别价款条款",
        "delivery": "待确认交付条款" if "交付" in text or "验收" in text else "",
        "breach": "待确认违约条款" if "违约" in text else "",
        "dispute": "待确认争议解决" if "仲裁" in text or "管辖" in text else "",
        "overall": f"合同通读占位摘要（{len(text)} 字）",
    }
