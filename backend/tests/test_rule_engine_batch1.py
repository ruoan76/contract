# -*- coding: utf-8 -*-
"""rule_engine Batch-1 规则单元测试。"""
import pytest

from app.services.ai_review.rule_engine import run_rule_engine


@pytest.mark.unit
def test_prepayment_rule():
    issues = run_rule_engine("预付款比例为 40%，其余货到付款", contract_type="purchase")
    prepay = [i for i in issues if i.rule_id == "PR-001"]
    assert len(prepay) == 1
    assert prepay[0].label_id == "L06"
    assert prepay[0].source == "rule"


@pytest.mark.unit
def test_currency_mix_rule():
    text = "合同总价为 ¥1,000,000 美元 equivalent USD 100,000"
    issues = run_rule_engine(text)
    mixed = [i for i in issues if i.rule_id == "CK-46"]
    assert len(mixed) == 1


@pytest.mark.unit
def test_unilateral_termination_rule():
    issues = run_rule_engine("甲方有权单方解除合同")
    hits = [i for i in issues if i.rule_id == "CK-47"]
    assert len(hits) == 1
    assert hits[0].risk_level == "high"


@pytest.mark.unit
def test_dispute_missing_rule():
    issues = run_rule_engine("本合同双方就采购事宜达成一致，付款按约定执行")
    hits = [i for i in issues if i.rule_id == "CK-50"]
    assert len(hits) == 1


@pytest.mark.unit
def test_blacklist_counterparty():
    issues = run_rule_engine("普通合同正文", counterparty_blacklisted=True)
    hits = [i for i in issues if i.rule_id == "TH-BLACKLIST"]
    assert len(hits) == 1
    assert hits[0].risk_level == "critical"


@pytest.mark.unit
def test_sign_area_unclear_triggers():
    """CK-49：有签字/盖章字样但无明确签署栏占位时应告警。"""
    text = "本合同由双方签字生效，未列明签署栏。"
    issues = run_rule_engine(text)
    hits = [i for i in issues if i.rule_id == "CK-49"]
    assert len(hits) == 1


@pytest.mark.unit
def test_sign_area_clear_no_ck49():
    """CK-49：存在明确签署栏占位时不应告警。"""
    text = "甲方（盖章）：__________  乙方（签字）：__________"
    issues = run_rule_engine(text)
    hits = [i for i in issues if i.rule_id == "CK-49"]
    assert len(hits) == 0
