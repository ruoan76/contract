# -*- coding: utf-8
"""risk_scorer 扁平 issue 格式测试。"""
import pytest

from app.services.ai_review.risk_scorer import calculate_risk_score


@pytest.mark.unit
class TestRiskScorerFlatIssues:
    def test_flat_clause_reviews_detect_critical(self):
        rows = [
            {"clause": "9.1.3", "risk_level": "critical", "description": "违约金过高"},
            {"clause": "付款", "risk_level": "medium", "description": "缺失付款计划"},
        ]
        dim = [{"dimension": "risk", "score": 50.0}]
        result = calculate_risk_score(rows, dim)
        assert result["statistics"]["critical_count"] >= 1
        assert result["risk_score"] >= 70.0
        assert result["statistics"]["score_floor_applied"] is True
