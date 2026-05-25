# -*- coding: utf-8 -*-
"""轻量 RAG — 法规片段与 risk_templates 关键词匹配。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.services.ai_review.issue_schema import AiReviewIssue
from app.services.ai_review.seed_store import get_risk_templates_purchase

logger = logging.getLogger(__name__)

SNIPPETS_PATH = (
    Path(__file__).resolve().parents[3] / "seeds" / "ai_review" / "legal_snippets.json"
)


def _load_snippets() -> list[dict[str, Any]]:
    try:
        return json.loads(SNIPPETS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("legal_snippets 加载失败: %s", exc)
        return []


def _score_text(query: str, keywords: list[str]) -> int:
    q = query.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in q:
            score += 2
    return score


def find_legal_basis(text: str) -> Optional[str]:
    """为 issue 文本检索最佳法律依据。"""
    snippets = _load_snippets()
    best: tuple[int, str] | None = None

    for sn in snippets:
        score = _score_text(text, sn.get("keywords") or [])
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, sn.get("text") or "")

    try:
        templates = get_risk_templates_purchase().get("items", [])
        for tpl in templates:
            kws = tpl.get("keywords") or []
            if isinstance(kws, str):
                kws = [kws]
            score = _score_text(text, kws)
            if score > 0:
                basis = tpl.get("legal_basis") or tpl.get("suggestion")
                if basis and (best is None or score >= best[0]):
                    best = (score, basis)
    except Exception:
        pass

    return best[1] if best else None


def enrich_issues(issues: list[AiReviewIssue]) -> list[AiReviewIssue]:
    """为 high/critical 且无法律依据的 issue 填充 RAG 结果。"""
    enriched: list[AiReviewIssue] = []
    for item in issues:
        if item.legal_basis:
            enriched.append(item)
            continue
        if item.risk_level not in ("high", "critical", "medium"):
            enriched.append(item)
            continue
        query = " ".join(
            filter(
                None,
                [item.title, item.description, item.suggestion, item.clause],
            )
        )
        basis = find_legal_basis(query)
        if basis:
            item.legal_basis = basis
            if item.source == "llm":
                item.source = "rag"
        else:
            item.needs_research = True
        enriched.append(item)
    return enriched
