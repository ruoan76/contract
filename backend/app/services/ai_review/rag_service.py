# -*- coding: utf-8
"""轻量 RAG — keyword / BM25 法规片段检索。"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.services.ai_review.issue_schema import AiReviewIssue
from app.services.ai_review.seed_store import get_risk_templates_purchase

logger = logging.getLogger(__name__)

def clear_snippet_cache() -> None:
    _bm25_index.cache_clear()


def _load_snippets() -> list[dict[str, Any]]:
    from app.services.ai_review.config_store import get_legal_snippets

    try:
        return get_legal_snippets() or []
    except Exception as exc:
        logger.warning("legal_snippets 加载失败: %s", exc)
        return []


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}", (text or "").lower())


@lru_cache(maxsize=1)
def _bm25_index() -> tuple[list[dict], list[Counter], float, dict[str, float]]:
    """构建 BM25 索引。"""
    docs = _load_snippets()
    tokenized = [Counter(_tokenize(" ".join(d.get("keywords") or []) + " " + (d.get("text") or ""))) for d in docs]
    df: dict[str, int] = {}
    for tc in tokenized:
        for t in tc:
            df[t] = df.get(t, 0) + 1
    n = max(len(docs), 1)
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    avgdl = sum(sum(tc.values()) for tc in tokenized) / n if tokenized else 1.0
    return docs, tokenized, avgdl, idf


def _bm25_score(query_tokens: list[str], doc_tf: Counter, avgdl: float, idf: dict[str, float], k1: float = 1.5, b: float = 0.75) -> float:
    dl = sum(doc_tf.values()) or 1
    score = 0.0
    for t in query_tokens:
        if t not in doc_tf:
            continue
        tf = doc_tf[t]
        idf_t = idf.get(t, 0.0)
        score += idf_t * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def find_legal_basis_bm25(text: str) -> tuple[Optional[str], Optional[str]]:
    """BM25 检索，返回 (legal_basis, snippet_id)。"""
    docs, tokenized, avgdl, idf = _bm25_index()
    q_tokens = _tokenize(text)
    if not q_tokens:
        return None, None
    best_score = 0.0
    best_doc: dict | None = None
    for doc, doc_tf in zip(docs, tokenized):
        s = _bm25_score(q_tokens, doc_tf, avgdl, idf)
        if s > best_score:
            best_score = s
            best_doc = doc
    if best_doc and best_score >= settings.AI_RAG_BM25_MIN_SCORE:
        sid = best_doc.get("id") or best_doc.get("snippet_id")
        return best_doc.get("text") or "", str(sid) if sid else None
    return None, None


def _score_text_keyword(query: str, keywords: list[str]) -> int:
    q = query.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in q:
            score += 2
    return score


def find_legal_basis_keyword(text: str) -> tuple[Optional[str], Optional[str]]:
    snippets = _load_snippets()
    best: tuple[int, str, str | None] | None = None

    for sn in snippets:
        score = _score_text_keyword(text, sn.get("keywords") or [])
        if score <= 0:
            continue
        sid = sn.get("id") or sn.get("snippet_id")
        if best is None or score > best[0]:
            best = (score, sn.get("text") or "", str(sid) if sid else None)

    try:
        templates = get_risk_templates_purchase().get("items", [])
        for tpl in templates:
            kws = tpl.get("keywords") or []
            if isinstance(kws, str):
                kws = [kws]
            score = _score_text_keyword(text, kws)
            if score > 0:
                basis = tpl.get("legal_basis") or tpl.get("suggestion")
                if basis and (best is None or score >= best[0]):
                    best = (score, basis, None)
    except Exception:
        pass

    if best:
        return best[1], best[2]
    return None, None


def find_legal_basis(text: str) -> Optional[str]:
    basis, _ = find_legal_basis_with_meta(text)
    return basis


def find_legal_basis_with_meta(text: str) -> tuple[Optional[str], Optional[str]]:
    mode = (settings.AI_RAG_MODE or "keyword").lower()
    if mode == "bm25":
        return find_legal_basis_bm25(text)
    return find_legal_basis_keyword(text)


def enrich_issues(issues: list[AiReviewIssue]) -> list[AiReviewIssue]:
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
                [item.title, item.description, item.suggestion, item.clause, item.evidence_quote],
            )
        )
        basis, snippet_id = find_legal_basis_with_meta(query)
        if basis:
            item.legal_basis = basis
            item.snippet_id = snippet_id
            if item.source == "llm":
                item.source = "rag"
        else:
            item.needs_research = True
        enriched.append(item)
    return enriched
