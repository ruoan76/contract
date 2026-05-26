# -*- coding: utf-8 -*-
"""review_completeness 单元测试。"""
import pytest

from app.services.ai_review.completeness import compute_completeness, summarize_checklist_coverage


@pytest.mark.unit
def test_completeness_full():
    c, detail = compute_completeness(
        s2_status="ok",
        dimension_statuses=["ok", "ok", "ok", "ok", "ok"],
    )
    assert c == "full"
    assert detail["dimension_failures"] == []


@pytest.mark.unit
def test_completeness_partial_on_dimension_failed():
    c, _ = compute_completeness(
        s2_status="ok",
        dimension_statuses=["ok", "failed", "ok", "ok", "ok"],
    )
    assert c == "partial"


@pytest.mark.unit
def test_completeness_partial_on_s2_heuristic():
    c, _ = compute_completeness(
        s2_status="heuristic",
        dimension_statuses=["ok", "ok", "ok", "ok", "ok"],
    )
    assert c == "partial"


@pytest.mark.unit
def test_completeness_failed_on_pipeline_exception():
    c, detail = compute_completeness(
        s2_status="ok",
        dimension_statuses=["ok"],
        pipeline_exception=True,
    )
    assert c == "failed"
    assert detail["reason"] == "pipeline_exception"


@pytest.mark.unit
def test_summarize_checklist_coverage():
    stats = summarize_checklist_coverage(
        [
            [{"status": "pass"}, {"status": "fail"}],
            [{"status": "unknown"}],
        ]
    )
    assert stats == {"total": 3, "pass": 1, "fail": 1, "unknown": 1}
