# -*- coding: utf-8 -*-
"""Issue 去重与每维 top-N 测试。"""
import pytest

from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    cap_issues_by_dimension,
    merge_issues,
)


@pytest.mark.unit
class TestIssueCap:
    def test_cap_per_dimension(self):
        issues = [
            AiReviewIssue(
                clause=f"c{i}",
                dimension="compliance_check",
                risk_level="medium",
                title=f"t{i}",
            )
            for i in range(20)
        ]
        capped = cap_issues_by_dimension(issues, max_per_dim=5)
        assert len(capped) == 5

    def test_rules_not_capped(self):
        rules = [
            AiReviewIssue(clause="r1", source="rule", rule_id="TH-1", risk_level="high"),
        ]
        llm = [
            AiReviewIssue(clause=f"c{i}", dimension="risk_assessment", risk_level="low")
            for i in range(20)
        ]
        capped = cap_issues_by_dimension(merge_issues(rules, llm), max_per_dim=3)
        assert any(i.rule_id for i in capped)
        assert len(capped) == 4

    def test_dedup_by_checklist_id(self):
        a = AiReviewIssue(
            clause="清单",
            checklist_item_id=5,
            risk_level="medium",
            description="a",
        )
        b = AiReviewIssue(
            clause="清单",
            checklist_item_id=5,
            risk_level="high",
            description="b",
        )
        merged = merge_issues([a], [b])
        assert len(merged) == 1
        assert merged[0].risk_level == "high"
