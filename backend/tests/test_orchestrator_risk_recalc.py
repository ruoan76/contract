# -*- coding: utf-8 -*-
"""orchestrator 综合分基于合并 issues 重算。"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.ai_review.ai_engine import DimensionScore, ReviewResult
from app.services.ai_review.issue_schema import AiReviewIssue


@pytest.mark.unit
class TestOrchestratorRiskRecalc:
    async def test_score_from_merged_issues_not_last_segment(self):
        """最后一段分数低、合并 issues 含 critical 时，综合分应反映合并结果。"""
        from app.services.ai_review.orchestrator import AiReviewOrchestrator

        seg1_dims = [
            DimensionScore(dimension="compliance", score=40.0, status="ok"),
            DimensionScore(dimension="risk", score=40.0, status="ok"),
            DimensionScore(dimension="financial", score=40.0, status="ok"),
            DimensionScore(dimension="capability", score=40.0, status="ok"),
            DimensionScore(dimension="anomaly", score=40.0, status="ok"),
        ]
        seg2_dims = [
            DimensionScore(dimension="compliance", score=30.0, status="ok"),
            DimensionScore(dimension="risk", score=30.0, status="ok"),
            DimensionScore(dimension="financial", score=30.0, status="ok"),
            DimensionScore(dimension="capability", score=30.0, status="ok"),
            DimensionScore(dimension="anomaly", score=30.0, status="ok"),
        ]

        async def fake_review(text, clauses, contract_type, profile_key=None):
            if "SEG2" in text:
                return ReviewResult(
                    overall_risk_score=30.0,
                    overall_risk_level="low",
                    recommendation="seg2 low",
                    dimension_scores=seg2_dims,
                )
            return ReviewResult(
                overall_risk_score=80.0,
                overall_risk_level="medium",
                recommendation="seg1 ok",
                dimension_scores=seg1_dims,
            )

        with patch(
            "app.services.ai_review.orchestrator.run_read_through",
            new_callable=AsyncMock,
            return_value={"overall": "ok"},
        ), patch(
            "app.services.ai_review.orchestrator.get_s2_status",
            return_value="ok",
        ), patch(
            "app.services.ai_review.orchestrator.run_rule_engine",
            return_value=[],
        ), patch(
            "app.services.ai_review.orchestrator.parse_clauses",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "app.services.ai_review.orchestrator.segment_if_needed",
            return_value=[("SEG1 text", []), ("SEG2 text", [])],
        ), patch(
            "app.services.ai_review.orchestrator.review_contract",
            side_effect=fake_review,
        ), patch(
            "app.services.ai_review.orchestrator.enrich_issues",
            side_effect=lambda x: x,
        ), patch(
            "app.services.ai_review.orchestrator.run_self_correction",
            new_callable=AsyncMock,
            side_effect=lambda issues, rt: issues,
        ), patch(
            "app.services.ai_review.orchestrator.apply_revision_routing",
            side_effect=lambda x: x,
        ), patch(
            "app.services.ai_review.orchestrator._dimension_issues_to_ai_issues",
            return_value=[
                AiReviewIssue(
                    clause="违约金",
                    dimension="risk_assessment",
                    risk_level="critical",
                    title="违约金过高",
                    description="3%/日",
                )
            ],
        ), patch(
            "app.services.ai_review.orchestrator._coverage_fail_to_issues",
            return_value=[],
        ):
            payload = await AiReviewOrchestrator().run(
                "SEG1\n\nSEG2",
                contract_type="service",
                amount=1_000_000,
            )

        assert payload["overall_risk_score"] >= 70.0
        assert payload["overall_risk_level"] in ("high", "critical")
        assert payload["summary"]["statistics"]["critical_count"] >= 1
        assert payload["summary"]["pipeline_stats"]["segment_count"] == 2
        assert payload["overall_risk_score"] != 30.0
