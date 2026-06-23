# -*- coding: utf-8 -*-
"""OCR 评估指标 — CER、字段 F1。"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def character_error_rate(reference: str, hypothesis: str) -> float:
    """
    字符错误率 CER = edit_distance / len(reference)。
    空 reference 时：hypothesis 非空返回 1.0，否则 0.0。
    """
    ref = reference.strip()
    hyp = hypothesis.strip()
    if not ref:
        return 0.0 if not hyp else 1.0
    if not hyp:
        return 1.0
    dist = _levenshtein(ref, hyp)
    return dist / len(ref)


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            ins = curr[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (ca != cb)
            curr.append(min(ins, delete, replace))
        prev = curr
    return prev[-1]


def field_f1(
    reference_fields: dict[str, Any],
    predicted_fields: dict[str, Any],
    *,
    keys: tuple[str, ...] = ("title", "party_a", "party_b", "amount"),
) -> dict[str, float]:
    """逐字段精确匹配 F1（amount 允许 1 元误差）。"""
    tp = fp = fn = 0
    per_field: dict[str, float] = {}

    for key in keys:
        ref = reference_fields.get(key)
        pred = predicted_fields.get(key)
        if ref is None and pred is None:
            per_field[key] = 1.0
            continue
        if ref is None or pred is None:
            per_field[key] = 0.0
            if ref is not None:
                fn += 1
            if pred is not None:
                fp += 1
            continue

        match = False
        if key == "amount":
            try:
                match = abs(float(ref) - float(pred)) <= 1.0
            except (TypeError, ValueError):
                match = False
        else:
            match = str(ref).strip() == str(pred).strip()

        per_field[key] = 1.0 if match else 0.0
        if match:
            tp += 1
        else:
            fn += 1
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, **{f"{k}_match": v for k, v in per_field.items()}}


def text_similarity(a: str, b: str) -> float:
    """SequenceMatcher 相似度，供快速对比。"""
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()
