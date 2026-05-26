# -*- coding: utf-8 -*-
"""多段五维合并单元测试。"""
import pytest

from app.services.ai_review.ai_engine import DimensionScore
from app.services.ai_review.dimension_merge import merge_dimension_scores


@pytest.mark.unit
class TestDimensionMerge:
    def test_failed_segment_wins_over_ok(self):
        seg1 = [
            DimensionScore(
                dimension="compliance",
                score=0.0,
                status="failed",
                error_type="json_parse",
            ),
            DimensionScore(dimension="risk", score=80.0, status="ok"),
        ]
        seg2 = [
            DimensionScore(dimension="compliance", score=90.0, status="ok"),
            DimensionScore(dimension="risk", score=70.0, status="ok"),
        ]
        merged = merge_dimension_scores([seg1, seg2])
        by_name = {d.dimension: d for d in merged}
        assert by_name["compliance"].status == "failed"
        assert by_name["compliance"].error_type == "json_parse"
        assert by_name["compliance"].score == 90.0
        assert by_name["risk"].score == 80.0

    def test_checklist_coverage_fail_wins(self):
        seg1 = [
            DimensionScore(
                dimension="compliance",
                score=50.0,
                status="ok",
                checklist_coverage=[{"item_id": 1, "status": "pass", "note": ""}],
            ),
        ]
        seg2 = [
            DimensionScore(
                dimension="compliance",
                score=60.0,
                status="ok",
                checklist_coverage=[{"item_id": 1, "status": "fail", "note": "缺失"}],
            ),
        ]
        merged = merge_dimension_scores([seg1, seg2])
        cov = merged[0].checklist_coverage
        assert cov[0]["status"] == "fail"
