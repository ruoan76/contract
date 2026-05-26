# -*- coding: utf-8 -*-
"""prompt_builder 单元测试。"""
import pytest

from app.services.ai_review.prompt_builder import (
    build_dimension_prompt,
    filter_checklist_for_dimension,
    sanitize_label_id,
)


@pytest.mark.unit
def test_sanitize_label_id_valid():
    assert sanitize_label_id("L01") == "L01"
    assert sanitize_label_id("rl-001") == "RL-001"
    assert sanitize_label_id("invalid") is None
    assert sanitize_label_id(None) is None


@pytest.mark.unit
def test_filter_checklist_for_dimension_caps_at_15():
    from app.services.ai_review.seed_store import get_review_checklists

    items = get_review_checklists().get("items", [])
    subset = filter_checklist_for_dimension(items, "financial")
    assert len(subset) <= 15
    assert len(subset) >= 1


@pytest.mark.unit
def test_build_dimension_prompt_contains_checklist_and_labels():
    prompt = build_dimension_prompt(
        dimension="financial",
        dimension_instruction="审查财务条款",
        contract_text="预付款 40%，合同金额 100 万元",
        clauses=[],
        contract_type="purchase",
    )
    assert "审查清单" in prompt or "checklist" in prompt.lower()
    assert "label_id" in prompt or "风险标签" in prompt
    assert "checklist_coverage" in prompt
    assert "reasoning" in prompt
    assert "evidence_quote" in prompt
