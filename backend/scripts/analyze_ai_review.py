#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 审查诊断 — 从 API 或本地 JSON 输出 completeness / gates / issue 分布。

用法:
  cd backend && python scripts/analyze_ai_review.py --contract-id 68
  python scripts/analyze_ai_review.py --review-id REV-xxx --format markdown
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

import httpx

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
USERNAME = os.environ.get("API_USER", "drafter1")
PASSWORD = os.environ.get("API_PASSWORD", "123456")


def _login(client: httpx.Client) -> str:
    r = client.post(
        f"{BASE_URL}/api/v1/system/login",
        params={"username": USERNAME, "password": PASSWORD},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"登录失败: {data}")
    return data["data"]["token"]


def _fetch_by_contract(client: httpx.Client, token: str, contract_id: int) -> dict[str, Any]:
    r = client.get(
        f"{BASE_URL}/api/v1/ai-review/contracts/{contract_id}/latest-review",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(body)
    data = body.get("data")
    if not data:
        raise RuntimeError(f"合同 {contract_id} 无审查记录")
    return data


def _fetch_by_review(client: httpx.Client, token: str, review_id: str) -> dict[str, Any]:
    r = client.get(
        f"{BASE_URL}/api/v1/ai-review/{review_id}/result",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 200:
        raise RuntimeError(body)
    return body.get("data") or {}


def build_diagnosis(data: dict[str, Any]) -> dict[str, Any]:
    summary = data.get("summary") or {}
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except json.JSONDecodeError:
            summary = {}

    clauses = data.get("clause_reviews") or []
    if isinstance(clauses, str):
        try:
            clauses = json.loads(clauses)
        except json.JSONDecodeError:
            clauses = []

    risk_counter = Counter(
        (c.get("risk_level") or "unknown").lower() for c in clauses if isinstance(c, dict)
    )
    source_counter = Counter(
        (c.get("source") or "unknown") for c in clauses if isinstance(c, dict)
    )

    stats = summary.get("statistics") or {}
    issue_count_summary = summary.get("issue_count")
    clause_count = len(clauses)
    truncated = bool(summary.get("clause_reviews_truncated"))
    issues_total = summary.get("issues_total", issue_count_summary or clause_count)

    gates = summary.get("gates") or data.get("gates") or {}
    completeness_detail = summary.get("completeness_detail") or data.get("completeness_detail") or {}

    return {
        "review_id": data.get("review_id"),
        "contract_id": data.get("contract_id"),
        "review_status": data.get("review_status"),
        "risk_level": data.get("risk_level"),
        "risk_score": data.get("risk_score"),
        "review_completeness": summary.get("review_completeness") or data.get("review_completeness"),
        "failed_dimensions": completeness_detail.get("failed_dimensions", []),
        "degraded_dimensions": completeness_detail.get("degraded_dimensions", []),
        "dimension_errors": completeness_detail.get("dimension_errors", {}),
        "segment_count": summary.get("segment_count"),
        "per_segment_status": completeness_detail.get("per_segment_status"),
        "dimensions": summary.get("dimensions", []),
        "checklist_summary": summary.get("checklist_summary"),
        "gates": gates,
        "score_floor_applied": stats.get("score_floor_applied"),
        "critical_issue_count": stats.get("critical_issue_count"),
        "issue_count_summary": issue_count_summary,
        "clause_reviews_count": clause_count,
        "issues_total": issues_total,
        "clause_reviews_truncated": truncated,
        "risk_distribution": dict(risk_counter),
        "source_distribution": dict(source_counter),
        "model_version": summary.get("model_version") or data.get("model_version"),
        "review_duration_seconds": data.get("review_duration_seconds"),
        "pipeline_stats": summary.get("pipeline_stats"),
    }


def to_markdown(diag: dict[str, Any]) -> str:
    lines = [
        "# AI 审查诊断报告",
        "",
        f"- **审查 ID**: {diag.get('review_id')}",
        f"- **风险**: {diag.get('risk_level')} / {diag.get('risk_score')}",
        f"- **完整度**: {diag.get('review_completeness')}",
        f"- **分段数**: {diag.get('segment_count')}",
        f"- **失败维度**: {', '.join(diag.get('failed_dimensions') or []) or '无'}",
        f"- **Critical 保底**: {diag.get('score_floor_applied')}",
        "",
        "## 管线统计",
    ]
    ps = diag.get("pipeline_stats") or {}
    if ps:
        lines.extend(
            [
                f"- MLX 调用次数: {ps.get('mlx_calls')}",
                f"- 审查耗时: {ps.get('duration_seconds')}s",
                f"- 各段: {json.dumps(ps.get('segments'), ensure_ascii=False)}",
            ]
        )
    else:
        lines.append("- （旧记录无 pipeline_stats）")
    lines.extend(
        [
        "",
        "## Issue 分布",
        f"- 摘要 issue_count: {diag.get('issue_count_summary')}",
        f"- clause_reviews 条数: {diag.get('clause_reviews_count')}",
        f"- issues_total: {diag.get('issues_total')}",
        f"- 已截断: {diag.get('clause_reviews_truncated')}",
        f"- 风险等级: {json.dumps(diag.get('risk_distribution'), ensure_ascii=False)}",
        f"- 来源: {json.dumps(diag.get('source_distribution'), ensure_ascii=False)}",
        "",
        "## 五维状态",
        ]
    )
    for dim in diag.get("dimensions") or []:
        lines.append(
            f"- {dim.get('dimension')}: status={dim.get('status')} score={dim.get('score')}"
        )
    lines.append("")
    lines.append("## 门禁")
    for gate_id, gate in (diag.get("gates") or {}).items():
        if isinstance(gate, dict):
            lines.append(f"- {gate_id}: {gate.get('status')} — {gate.get('summary', '')[:80]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 审查诊断")
    parser.add_argument("--contract-id", type=int, default=None)
    parser.add_argument("--review-id", default=None)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--compare", type=int, default=None, help="对比另一 contract-id 的审查")
    args = parser.parse_args()

    if not args.contract_id and not args.review_id:
        print("请指定 --contract-id 或 --review-id", file=sys.stderr)
        return 1

    with httpx.Client(timeout=60.0) as client:
        token = _login(client)
        if args.contract_id:
            data = _fetch_by_contract(client, token, args.contract_id)
        else:
            data = _fetch_by_review(client, token, args.review_id)

        diag = build_diagnosis(data)

        if args.compare:
            other = build_diagnosis(_fetch_by_contract(client, token, args.compare))
            diag["compare_with"] = {
                "contract_id": args.compare,
                "review_completeness": other.get("review_completeness"),
                "issues_total": other.get("issues_total"),
                "risk_score": other.get("risk_score"),
            }

    if args.format == "markdown":
        print(to_markdown(diag))
    else:
        print(json.dumps(diag, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
