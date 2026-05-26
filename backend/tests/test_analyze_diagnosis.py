# -*- coding: utf-8 -*-
"""诊断脚本 build_diagnosis 单元测试。"""
import pytest

from scripts.analyze_ai_review import build_diagnosis


@pytest.mark.unit
class TestAnalyzeDiagnosis:
    def test_build_diagnosis_truncation_flag(self):
        data = {
            "review_id": "REV-1",
            "risk_level": "high",
            "risk_score": 72,
            "clause_reviews": [{"risk_level": "critical", "source": "llm"}],
            "summary": {
                "review_completeness": "partial",
                "issue_count": 50,
                "issues_total": 50,
                "clause_reviews_count": 20,
                "clause_reviews_truncated": True,
                "completeness_detail": {"failed_dimensions": ["risk"]},
                "statistics": {"score_floor_applied": True},
            },
        }
        diag = build_diagnosis(data)
        assert diag["clause_reviews_truncated"] is True
        assert diag["issues_total"] == 50
        assert diag["failed_dimensions"] == ["risk"]
        assert diag["score_floor_applied"] is True
