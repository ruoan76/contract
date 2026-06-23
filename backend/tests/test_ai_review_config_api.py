# -*- coding: utf-8 -*-
"""AI 审查配置 Admin API RBAC 与反馈统计。"""
import pytest
from sqlalchemy import select

from app.models.ai_review_config import AIRuleFeedbackStat
from app.models.ai_review_issue import AIReviewIssue
from app.models.contract import Contract
from app.services.ai_review.config_admin_service import record_issue_feedback


@pytest.mark.asyncio
async def test_legal_cannot_publish(client_for_user):
    async with await client_for_user("legal") as legal:
        res = await legal.post(
            "/api/v1/ai-review/config/publish",
            json={"note": "test"},
        )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_checklist(client_for_user):
    async with await client_for_user("admin") as admin:
        res = await admin.get("/api/v1/ai-review/config/checklist-items")
    assert res.status_code == 200
    body = res.json()
    assert body["code"] == 200
    assert "items" in body["data"]


@pytest.mark.asyncio
async def test_record_issue_feedback(db_session):
    contract = Contract(
        contract_no="T-001",
        title="反馈测试",
        contract_type="purchase",
        counterparty_name="测试供应商",
        status="draft",
        creator_id=1,
    )
    db_session.add(contract)
    await db_session.flush()

    issue = AIReviewIssue(
        review_id="REV-TEST",
        contract_id=contract.id,
        version_id=1,
        clause="付款",
        dimension="finance_check",
        risk_level="medium",
        title="预付款",
        description="测试",
        source="rule",
        rule_id="PR-001",
        human_status="pending",
    )
    db_session.add(issue)
    await db_session.flush()

    await record_issue_feedback(db_session, issue, "false_positive")
    await db_session.commit()

    stat = await db_session.scalar(
        select(AIRuleFeedbackStat).where(AIRuleFeedbackStat.rule_key == "PR-001")
    )
    assert stat is not None
    assert stat.fp_count >= 1


@pytest.mark.asyncio
async def test_disable_rule_refreshes_cache_when_published(db_session, client_for_user):
    from app.services.ai_review.config_seed import import_from_json_seeds
    from app.services.ai_review.config_store import get_hard_rules, clear_config_cache

    await import_from_json_seeds("test-disable-cache")
    clear_config_cache()
    from app.services.ai_review.config_store import refresh_config_cache

    await refresh_config_cache(db_session)
    before = len(get_hard_rules())

    async with await client_for_user("admin") as admin:
        res = await admin.post(
            "/api/v1/ai-review/config/disable-rule",
            json={"rule_key": "PR-001"},
        )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data.get("cache_refreshed") is True
    assert len(get_hard_rules()) < before
