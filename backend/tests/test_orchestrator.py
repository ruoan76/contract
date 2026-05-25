"""Orchestrator / RAG / Issues API 集成测试。"""
import pytest


@pytest.mark.asyncio
async def test_mock_review_persists_issues(client_for_user):
    """Mock 审查应写入 ai_review_issues 表。"""
    async with await client_for_user("drafter") as drafter:
        create = await drafter.post(
            "/api/v1/contracts/",
            json={
                "title": "Issue 持久化测试",
                "contract_type": "purchase",
                "counterparty_name": "供应商",
                "amount": 100000,
                "content": "预付款 40%，采购合同正文",
            },
        )
        assert create.status_code == 200
        cid = create.json()["data"]["id"]

        resp = await drafter.post(
            "/api/v1/ai-review/review",
            json={"contract_id": cid},
        )
        assert resp.status_code == 200
        review_id = resp.json()["data"]["review_id"]

        issue_resp = await drafter.get(f"/api/v1/ai-review/{review_id}/issues")
        assert issue_resp.status_code == 200
        items = issue_resp.json()["data"]["items"]
        assert len(items) >= 1
        assert items[0].get("human_status") == "pending"


@pytest.mark.asyncio
async def test_confirm_review(client_for_user):
    async with await client_for_user("drafter") as drafter:
        create = await drafter.post(
            "/api/v1/contracts/",
            json={
                "title": "确认测试",
                "contract_type": "purchase",
                "counterparty_name": "供应商",
                "amount": 80000,
                "content": "合同正文",
            },
        )
        cid = create.json()["data"]["id"]
        review = await drafter.post(
            "/api/v1/ai-review/review",
            json={"contract_id": cid},
        )
        review_id = review.json()["data"]["review_id"]

    async with await client_for_user("legal") as legal:
        resp = await legal.post(f"/api/v1/ai-review/{review_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["data"]["review_status"] == "reviewed"


@pytest.mark.asyncio
async def test_patch_issue_human_status(client_for_user):
    async with await client_for_user("drafter") as drafter:
        create = await drafter.post(
            "/api/v1/contracts/",
            json={
                "title": "Issue PATCH 测试",
                "contract_type": "purchase",
                "counterparty_name": "供应商",
                "amount": 50000,
                "content": "预付款 35%",
            },
        )
        cid = create.json()["data"]["id"]
        review = await drafter.post(
            "/api/v1/ai-review/review",
            json={"contract_id": cid},
        )
        review_id = review.json()["data"]["review_id"]
        items = (
            await drafter.get(f"/api/v1/ai-review/{review_id}/issues")
        ).json()["data"]["items"]
        issue_id = items[0]["id"]

    async with await client_for_user("legal") as legal:
        patch = await legal.patch(
            f"/api/v1/ai-review/issue/{issue_id}",
            json={"human_status": "confirmed", "human_comment": "同意"},
        )
    assert patch.status_code == 200
    assert patch.json()["data"]["human_status"] == "confirmed"


@pytest.mark.unit
def test_rag_enriches_prepayment_issue():
    from app.services.ai_review.issue_schema import AiReviewIssue
    from app.services.ai_review.rag_service import enrich_issues

    issue = AiReviewIssue(
        clause="预付款",
        clause_ref="第三条",
        dimension="finance_check",
        risk_level="high",
        description="预付款比例 40% 超过上限",
        source="llm",
    )
    enriched = enrich_issues([issue])
    assert enriched[0].legal_basis or enriched[0].needs_research
