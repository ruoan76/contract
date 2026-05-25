"""AI 审查 schema / 规则 / 门禁测试（不调用 LLM）。"""
import pytest

from app.services.ai_review.issue_schema import (
    AiReviewIssue,
    demo_issue_to_schema,
    issues_to_clause_reviews_json,
    merge_issues,
)
from app.services.ai_review.orchestrator import build_mock_payload
from app.services.ai_review.rule_engine import run_rule_engine
from app.services.ai_review.runner import compute_gates_from_payload
from app.api.v1.ai_review_demo import DEMO_ISSUES


@pytest.mark.unit
def test_demo_issue_to_schema_has_label_and_gate():
    raw = DEMO_ISSUES[0]
    issue = demo_issue_to_schema(raw)
    assert issue.dimension
    assert issue.gate_id
    assert issue.source in ("llm", "rule", "mock")


@pytest.mark.unit
def test_build_mock_payload_unified_schema():
    payload = build_mock_payload()
    assert payload["overall_risk_level"] == "medium"
    assert len(payload["issues"]) >= 1
    assert len(payload["clause_reviews"]) == len(payload["issues"])
    first = payload["clause_reviews"][0]
    assert "clause" in first
    assert payload["summary"]["mock"] is True


@pytest.mark.unit
def test_rule_engine_prepayment():
    text = "预付款比例为 40%，其余分期支付"
    issues = run_rule_engine(text, contract_type="purchase", amount=500000)
    assert any(i.rule_id == "PR-001" for i in issues)
    assert all(i.source == "rule" for i in issues)


@pytest.mark.unit
def test_compute_gates_from_payload():
    payload = {
        "clause_reviews": [
            {
                "risk_level": "high",
                "dimension": "finance_check",
                "clause": "付款",
                "suggestion": "偏高",
            },
        ],
        "summary": {
            "dimensions": [{"dimension": "compliance", "score": 35.0}],
        },
    }
    gates = compute_gates_from_payload(payload)
    assert gates["gate_clause"]["status"] == "fail"
    assert gates["gate_validity"]["status"] == "warn"


@pytest.mark.unit
def test_merge_issues_dedup():
    a = AiReviewIssue(
        clause="第三条 付款",
        clause_ref="第三条 付款",
        dimension="finance_check",
        risk_level="medium",
        description="预付款偏高",
        source="rule",
    )
    b = AiReviewIssue(
        clause="第三条 付款",
        clause_ref="第三条 付款",
        dimension="finance_check",
        risk_level="high",
        description="预付款偏高",
        source="llm",
    )
    merged = merge_issues([a, b])
    assert len(merged) == 1
    rows = issues_to_clause_reviews_json(merged)
    assert rows[0]["risk_level"] == "high"
