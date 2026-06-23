# -*- coding: utf-8
"""AI 审查 Session 编排器。"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

from app.api.v1.ai_review_demo import DEMO_GATES, DEMO_ISSUES
from app.core.config import settings
from app.services.ai_review.ai_engine import ReviewResult, review_contract
from app.services.ai_review.clause_parser import parse_clauses
from app.services.ai_review.completeness import compute_completeness, summarize_checklist_coverage
from app.services.ai_review.dimension_merge import (
    merge_dimension_scores,
    per_segment_status_summary,
)
from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    apply_high_risk_guardrail,
    cap_issues_by_dimension,
    demo_issue_to_schema,
    issues_to_clause_reviews_json,
    issues_to_rule_violations,
    merge_issues,
    normalize_dimension,
)
from app.services.ai_review.prompt_builder import get_prompt_version, sanitize_label_id
from app.services.ai_review.rag_service import enrich_issues
from app.services.ai_review.revision_router import apply_revision_routing
from app.services.ai_review.risk_scorer import calculate_risk_score
from app.services.ai_review.rule_engine import run_rule_engine
from app.services.ai_review.seed_store import get_review_checklists
from app.services.ai_review.skills.gates import build_gates_v2
from app.services.ai_review.skills.read_through import get_s2_status, run_read_through
from app.services.ai_review.skills.self_correction import run_self_correction
from app.services.ai_review.text_segmenter import segment_if_needed

logger = logging.getLogger(__name__)


def _dimension_issues_to_ai_issues(result: ReviewResult) -> list[AiReviewIssue]:
    """从五维 LLM 输出提取 AiReviewIssue。"""
    from app.services.ai_review.seed_store import get_risk_labels

    label_name_map = {}
    try:
        for lb in get_risk_labels().get("items", []):
            label_name_map[lb.get("id")] = lb.get("name")
    except Exception:
        pass

    issues: list[AiReviewIssue] = []
    for dim in result.dimension_scores:
        for item in dim.issues:
            lid = sanitize_label_id(item.label_id)
            issues.append(
                AiReviewIssue(
                    clause=item.keyword or dim.dimension,
                    clause_ref=item.keyword or "",
                    dimension=normalize_dimension(dim.dimension),
                    label_id=lid,
                    label_name=label_name_map.get(lid) if lid else None,
                    gate_id=item.gate_id or "gate_clause",
                    risk_level=item.severity or "medium",
                    confidence=0.75,
                    title=item.keyword or dim.dimension,
                    description=item.description or "",
                    suggestion=item.description or "",
                    legal_basis=item.legal_basis_candidate,
                    reasoning=item.reasoning,
                    evidence_quote=item.evidence_quote,
                    source="llm",
                )
            )
    return issues


def _checklist_gate_by_id() -> dict[int, str]:
    """清单 item_id → gate_id。"""
    try:
        items = get_review_checklists().get("items", [])
        return {int(i["id"]): str(i.get("gate_id") or "") for i in items if i.get("id") is not None}
    except Exception:
        return {}


def _coverage_fail_to_issues(
    result: ReviewResult,
    existing_rule_ids: set[str],
) -> list[AiReviewIssue]:
    """checklist_coverage 中 fail 且规则未覆盖 → 低置信 issue（仅效力门禁相关）。"""
    gate_map = _checklist_gate_by_id()
    extra: list[AiReviewIssue] = []
    for dim in result.dimension_scores:
        for cov in dim.checklist_coverage:
            if not isinstance(cov, dict) or cov.get("status") != "fail":
                continue
            item_id = cov.get("item_id")
            rule_key = f"CK-{item_id}"
            if rule_key in existing_rule_ids:
                continue
            gate_id = gate_map.get(int(item_id)) if item_id is not None else ""
            # 降噪：仅 gate_validity 相关清单 fail 转为 issue
            if gate_id != "gate_validity":
                continue
            extra.append(
                AiReviewIssue(
                    clause=f"清单项 #{item_id}",
                    dimension=normalize_dimension(dim.dimension),
                    gate_id=gate_id or "gate_validity",
                    risk_level="medium",
                    confidence=0.55,
                    title=f"清单项 #{item_id} 未通过",
                    description=str(cov.get("note") or "LLM 清单评估未通过"),
                    suggestion="请法务核对清单项",
                    source="llm",
                    checklist_item_id=int(item_id) if item_id is not None else None,
                )
            )
    return extra


def _build_merged_recommendation(merged_dimensions, last_result: ReviewResult | None) -> str:
    """合并各维摘要为总体建议。"""
    parts: list[str] = []
    for d in merged_dimensions:
        if d.summary and d.status != "failed":
            parts.append(f"【{d.dimension}】{d.summary}")
    if parts:
        return "\n".join(parts[:5])
    if last_result and last_result.recommendation:
        return last_result.recommendation
    return "请结合条款风险与门禁结论进行法务复核。"


def build_mock_payload() -> dict[str, Any]:
    issues = [demo_issue_to_schema(i) for i in DEMO_ISSUES]
    issues = merge_issues(issues)
    issues = apply_revision_routing(issues)
    summary = {
        "mock": True,
        "gates": DEMO_GATES,
        "read_through": {"overall": "Mock 通读摘要"},
        "review_completeness": "full",
        "prompt_version": get_prompt_version(),
    }
    return {
        "overall_risk_level": "medium",
        "overall_risk_score": 65.0,
        "recommendation": "建议关注付款条款",
        "issues": issues,
        "clause_reviews": issues_to_clause_reviews_json(issues),
        "rule_violations": issues_to_rule_violations(issues),
        "summary": summary,
        "model_version": "mock",
        "review_duration_seconds": 0,
    }


class AiReviewOrchestrator:
    """审查 Session 编排。"""

    async def run(
        self,
        contract_text: str,
        *,
        contract_type: str = "other",
        amount: Optional[float] = None,
        profile_key: str | None = None,
        counterparty_blacklisted: bool = False,
    ) -> dict[str, Any]:
        if settings.AI_REVIEW_MOCK:
            return build_mock_payload()

        text = (contract_text or "").strip()
        if not text:
            raise ValueError("合同内容为空，无法执行 AI 审查")

        started = datetime.now()
        pk = profile_key or contract_type

        read_through = await run_read_through(text, contract_type=contract_type)
        s2_status = get_s2_status(read_through)

        rule_issues = run_rule_engine(
            text,
            contract_type=contract_type,
            amount=amount,
            counterparty_blacklisted=counterparty_blacklisted,
        )
        rule_ids = {i.rule_id for i in rule_issues if i.rule_id}

        clauses = await parse_clauses(text, contract_type=contract_type)
        segments = segment_if_needed(text, clauses)

        all_llm_issues: list[AiReviewIssue] = []
        segment_dimension_results: list[list] = []
        segment_timings: list[dict[str, Any]] = []
        mlx_calls = 0
        last_result: ReviewResult | None = None

        for seg_idx, (seg_text, seg_clauses) in enumerate(segments):
            seg_start = time.monotonic()
            result = await review_contract(
                seg_text,
                seg_clauses,
                contract_type,
                profile_key=pk,
            )
            seg_ms = int((time.monotonic() - seg_start) * 1000)
            last_result = result
            segment_dimension_results.append(result.dimension_scores)
            mlx_calls += len(result.dimension_scores)
            segment_timings.append(
                {
                    "index": seg_idx,
                    "chars": len(seg_text),
                    "duration_ms": seg_ms,
                    "dimension_statuses": {
                        d.dimension: d.status for d in result.dimension_scores
                    },
                }
            )
            dim_issues = _dimension_issues_to_ai_issues(result)
            cov_issues = _coverage_fail_to_issues(result, rule_ids)
            all_llm_issues.extend(dim_issues)
            all_llm_issues.extend(cov_issues)

        if last_result is None:
            raise ValueError("审查未产生结果")

        merged_dimensions = merge_dimension_scores(segment_dimension_results)

        issues = merge_issues(rule_issues, all_llm_issues)
        issues = cap_issues_by_dimension(issues)
        issues = enrich_issues(issues)
        issues = await run_self_correction(issues, read_through)
        issues = apply_revision_routing(issues)

        dimension_summary = [
            {
                "dimension": d.dimension,
                "score": d.score,
                "summary": d.summary,
                "status": d.status,
                "error_type": getattr(d, "error_type", None),
                "checklist_coverage": d.checklist_coverage,
            }
            for d in merged_dimensions
        ]
        checklist_cov = [d.checklist_coverage for d in merged_dimensions]
        dim_statuses = [d.status for d in merged_dimensions]

        completeness, completeness_detail = compute_completeness(
            s2_status=s2_status,
            dimension_statuses=dim_statuses,
        )
        completeness_detail["failed_dimensions"] = [
            d["dimension"] for d in dimension_summary if d.get("status") == "failed"
        ]
        completeness_detail["degraded_dimensions"] = [
            d["dimension"] for d in dimension_summary if d.get("status") == "degraded"
        ]
        completeness_detail["segment_count"] = len(segments)
        completeness_detail["per_segment_status"] = per_segment_status_summary(
            segment_dimension_results
        )
        completeness_detail["dimension_errors"] = {
            d["dimension"]: d.get("error_type")
            for d in dimension_summary
            if d.get("error_type")
        }

        clause_reviews = issues_to_clause_reviews_json(issues)
        gates = build_gates_v2(
            issues,
            dimensions=dimension_summary,
            read_through=read_through,
            checklist_coverage=checklist_cov,
            review_completeness=completeness,
        )

        dim_dicts = [
            {"dimension": d.dimension, "score": d.score, "status": d.status}
            for d in merged_dimensions
        ]
        risk_data = calculate_risk_score(clause_reviews, dim_dicts)
        overall_score = float(risk_data["risk_score"])
        overall_level = risk_data["risk_level"]
        score_floor_applied = bool(risk_data.get("statistics", {}).get("score_floor_applied"))

        recommendation = _build_merged_recommendation(merged_dimensions, last_result)

        all_llm_failed = bool(merged_dimensions) and all(
            getattr(d, "status", None) == "failed" for d in merged_dimensions
        )
        if all_llm_failed:
            mlx_note = "MLX/LLM 五维审查均失败，以下结果主要基于规则引擎与通读占位摘要。"
            recommendation = (
                f"{mlx_note}\n{recommendation}" if recommendation else mlx_note
            )

        duration = int((datetime.now() - started).total_seconds())
        dimension_retry_count = sum(
            1 for d in merged_dimensions if getattr(d, "error_type", None)
        )

        summary: dict[str, Any] = {
            "read_through": read_through,
            "dimensions": dimension_summary,
            "gates": gates,
            "issue_count": len(issues),
            "issues_total": len(issues),
            "model_version": settings.AI_MODEL,
            "prompt_version": get_prompt_version(),
            "review_completeness": completeness,
            "completeness_detail": completeness_detail,
            "checklist_summary": summarize_checklist_coverage(checklist_cov),
            "segment_count": len(segments),
            "pipeline_stats": {
                "segment_count": len(segments),
                "mlx_calls": mlx_calls,
                "dimension_retry_count": dimension_retry_count,
                "duration_seconds": duration,
                "segments": segment_timings,
            },
        }
        if all_llm_failed:
            summary["mlx_degraded"] = True
            summary["mlx_degraded_reason"] = "all_dimensions_failed"

        critical_in_issues = sum(
            1 for i in issues if (i.risk_level or "").lower() == "critical"
        )
        summary["statistics"] = {
            "critical_issue_count": critical_in_issues,
            "score_floor_applied": score_floor_applied,
            **risk_data.get("statistics", {}),
        }

        return {
            "overall_risk_level": overall_level,
            "overall_risk_score": overall_score,
            "recommendation": recommendation,
            "issues": issues,
            "clause_reviews": clause_reviews,
            "rule_violations": issues_to_rule_violations(issues),
            "summary": summary,
            "model_version": settings.AI_MODEL,
            "review_duration_seconds": duration,
        }


async def run_orchestrated_review(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
    profile_key: str | None = None,
    counterparty_blacklisted: bool = False,
) -> dict[str, Any]:
    return await AiReviewOrchestrator().run(
        contract_text,
        contract_type=contract_type,
        amount=amount,
        profile_key=profile_key,
        counterparty_blacklisted=counterparty_blacklisted,
    )
