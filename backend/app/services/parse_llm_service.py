# -*- coding: utf-8 -*-
"""合同解析 — LLM 结构化字段提取与相对方模糊校正。"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.counterparty import Counterparty
from app.services.ai_review.llm_gateway import LLMCallError, get_llm_gateway

logger = logging.getLogger(__name__)

_PARSE_SYSTEM = (
    "你是合同信息抽取助手。从 OCR 可能含错别字的合同文本中提取结构化字段。"
    "公司名请尽量纠正明显 OCR 错误（如「软住」→「软件」、「钦住」→「软件」）。"
    "仅输出 JSON 对象，字段：title, party_a, party_b, amount（数字元）, contract_type"
    "（purchase|sales|service|other）, confidence（0-1）。"
    "无法确定的字段用 null。"
)


async def extract_fields_with_llm(
    text: str,
    filename: str,
) -> dict[str, Any] | None:
    """
    调用本地 MLX LLM 从合同文本提取字段。
    失败时返回 None，由调用方回退正则。
    """
    snippet = text.strip()
    if not snippet:
        return None
    max_chars = settings.AI_PARSE_LLM_MAX_CHARS
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars]

    user_content = (
        f"文件名：{filename}\n\n"
        f"合同正文（可能含 OCR 错字）：\n{snippet}\n\n"
        "请输出 JSON。"
    )
    try:
        gateway = get_llm_gateway()
        parsed, meta = await gateway.complete_json(
            messages=[{"role": "user", "content": user_content}],
            system_prompt=_PARSE_SYSTEM,
            caller="contract_parse",
            max_retries=1,
        )
        if not meta.success:
            return None
        return _normalize_llm_fields(parsed)
    except LLMCallError as exc:
        logger.warning("LLM 合同解析失败，回退正则: %s", exc)
        return None
    except Exception as exc:
        logger.warning("LLM 合同解析异常，回退正则: %s", exc)
        return None


def _normalize_llm_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """规范化 LLM 输出。"""
    amount = raw.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None

    confidence = raw.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = None

    contract_type = raw.get("contract_type")
    if contract_type not in ("purchase", "sales", "service", "other", None):
        contract_type = "other"

    return {
        "title": _clean_party_name(raw.get("title")),
        "party_a": _clean_party_name(raw.get("party_a")),
        "party_b": _clean_party_name(raw.get("party_b")),
        "amount": amount,
        "contract_type": contract_type or "other",
        "confidence": confidence,
    }


def _clean_party_name(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:120]


async def fuzzy_match_counterparty_names(
    db: AsyncSession,
    party_a: str | None,
    party_b: str | None,
    *,
    threshold: float = 0.72,
) -> tuple[str | None, str | None, list[str]]:
    """
    将相对方名与库中名称 fuzzy 匹配，返回校正后的 (party_a, party_b, corrections)。
    """
    result = await db.execute(select(Counterparty.name).where(Counterparty.status == 1))
    names = [row[0] for row in result.all() if row[0]]
    if not names:
        return party_a, party_b, []

    corrections: list[str] = []
    new_a = _fuzzy_one(party_a, names, threshold, corrections, "甲方")
    new_b = _fuzzy_one(party_b, names, threshold, corrections, "乙方")
    return new_a, new_b, corrections


def _fuzzy_one(
    name: str | None,
    candidates: list[str],
    threshold: float,
    corrections: list[str],
    label: str,
) -> str | None:
    if not name:
        return None
    best_name: str | None = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, name, candidate).ratio()
        if score > best_score:
            best_score = score
            best_name = candidate
    if best_name and best_score >= threshold and best_name != name:
        corrections.append(f"{label}「{name}」→「{best_name}」")
        return best_name
    return name


def detect_party_parse_warning(party_a: str | None, party_b: str | None) -> bool:
    """检测相对方名是否疑似 OCR 错误。"""
    pattern = re.compile(r"软住|公同|有限公[^司]|责任公[^司]|股俭|钦住|烟堂|兰灿")
    for name in (party_a, party_b):
        if name and pattern.search(name):
            return True
    return False
