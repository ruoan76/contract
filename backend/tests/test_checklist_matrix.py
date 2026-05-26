# -*- coding: utf-8 -*-
"""清单矩阵聚合测试。"""
import pytest

from app.services.ai_review.checklist_matrix_service import build_checklist_matrix


@pytest.mark.unit
class TestChecklistMatrix:
    def test_build_matrix_with_coverage(self):
        summary = {
            "dimensions": [
                {
                    "dimension": "compliance",
                    "checklist_coverage": [
                        {"item_id": 1, "status": "pass", "note": ""},
                        {"item_id": 2, "status": "fail", "note": "主体不明"},
                    ],
                }
            ]
        }
        matrix = build_checklist_matrix(summary, [])
        assert matrix["total"] >= 2
        assert matrix["fail"] >= 1
        assert matrix["categories"]

    def test_issue_maps_to_item(self):
        summary = {"dimensions": []}
        clauses = [
            {
                "checklist_item_id": 2,
                "risk_level": "high",
                "description": "需补授权",
                "evidence_quote": "甲方…",
            }
        ]
        matrix = build_checklist_matrix(summary, clauses)
        found = False
        for cat in matrix["categories"]:
            for item in cat["items"]:
                if item["id"] == 2:
                    found = True
                    assert item["ai_suggestion"]
        assert found
