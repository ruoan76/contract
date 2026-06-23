# -*- coding: utf-8 -*-
"""OCR 字段词典后处理 — 相对方名与法律高频词纠错。"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

# 常见 OCR 混淆对（错误 → 正确片段）
_OCR_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("软住", "软件"),
    ("股俭", "股份"),
    ("烟堂", "烟草"),
    ("兰灿茧", "兰州"),
    ("钦住", "软件"),
    ("公同", "公司"),
    ("有限公", "有限公司"),
)

_LEGAL_TERMS: tuple[str, ...] = (
    "有限公司",
    "股份有限公司",
    "第一条",
    "第二条",
    "合同金额",
    "甲方",
    "乙方",
)


def apply_ocr_replacements(text: str) -> str:
    """全局常见 OCR 错字替换（保守）。"""
    if not text:
        return ""
    out = text
    for wrong, right in _OCR_REPLACEMENTS:
        out = out.replace(wrong, right)
    return out


def correct_party_name(
    name: str | None,
    candidates: Iterable[str],
    *,
    threshold: float = 0.78,
) -> tuple[str | None, bool]:
    """
    用相对方库候选纠正公司名。
    返回 (纠正后名称, 是否发生纠正)。
    """
    if not name:
        return name, False
    cleaned = apply_ocr_replacements(name.strip())
    best: str | None = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, cleaned, candidate).ratio()
        if score > best_score:
            best_score = score
            best = candidate
    if best and best_score >= threshold and best != cleaned:
        return best, True
    return cleaned, cleaned != name


def enrich_fields_with_dictionary(
    fields: dict,
    counterparty_names: Iterable[str] | None = None,
) -> dict:
    """对解析字段应用词典纠错，写入 counterparty_corrections。"""
    result = dict(fields)
    corrections: list[str] = list(result.get("counterparty_corrections") or [])
    names = list(counterparty_names or [])

    for key, label in (("party_a", "甲方"), ("party_b", "乙方")):
        raw = result.get(key)
        if not raw:
            continue
        fixed, changed = correct_party_name(str(raw), names)
        if changed and fixed:
            corrections.append(f"{label}「{raw}」→「{fixed}」（词典纠错）")
            result[key] = fixed

    if corrections:
        result["counterparty_corrections"] = corrections
    return result


def extract_amount_from_text(text: str) -> float | None:
    """从正文提取金额（词典纠错后）。"""
    normalized = apply_ocr_replacements(text)
    match = re.search(
        r"(?:金额|总价|合同金额|人民币)\s*[：:￥]?\s*([\d,]+(?:\.\d+)?)\s*(?:元|万元)?",
        normalized,
    )
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        amount = float(raw)
        if "万元" in match.group(0):
            amount *= 10000
        return amount
    except ValueError:
        return None
