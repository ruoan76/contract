# -*- coding: utf-8 -*-
"""风险分 critical 保底策略测试。"""
import pytest

from app.services.ai_review.risk_scorer import calculate_risk_score


@pytest.mark.unit
class TestRiskScorerCriticalFloor:
    def test_critical_issue_raises_score_and_level(self):
        clause_reviews = [
            {
                "clause_id": "c1",
                "risk_score": 30.0,
                "issues": [
                    {
                        "keyword": "违约金",
                        "severity": "critical",
                        "description": "比例过高",
                    }
                ],
            }
        ]
        dimension_scores = [
            {"dimension": "risk", "score": 40.0},
            {"dimension": "compliance", "score": 45.0},
        ]
        result = calculate_risk_score(clause_reviews, dimension_scores)
        assert result["risk_score"] >= 70.0
        assert result["risk_level"] == "high"
        assert result["statistics"]["score_floor_applied"] is True

    def test_no_critical_no_floor(self):
        clause_reviews = [
            {
                "clause_id": "c1",
                "risk_score": 20.0,
                "issues": [
                    {
                        "keyword": "格式",
                        "severity": "low",
                        "description": "轻微问题",
                    }
                ],
            }
        ]
        result = calculate_risk_score(clause_reviews, None)
        assert result["statistics"]["score_floor_applied"] is False
