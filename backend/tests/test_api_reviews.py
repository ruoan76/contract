"""
评审域 API 测试 — Phase B-2
"""
import pytest


@pytest.mark.unit
class TestReviewOpinionsAPI:
    async def _create_approved_contract(self, client_for_user, amount=320000):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "评审测试合同",
                    "contract_type": "service",
                    "counterparty_name": "测试公司",
                    "amount": amount,
                    "content": "条款内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        for role in ("approver", "legal", "finance", "executive"):
            async with await client_for_user(role) as client:
                pending = await client.get("/api/v1/approvals/pending")
                items = [
                    i for i in pending.json()["data"]["items"] if i["contract_id"] == cid
                ]
                if not items:
                    continue
                fid = items[0]["flow_id"]
                await client.post(
                    f"/api/v1/approvals/{fid}/approve",
                    json={"action": "approve"},
                )
        return cid

    async def test_simple_flow_rejects_finance(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "简易评审",
                    "contract_type": "purchase",
                    "counterparty_name": "供应商",
                    "amount": 80000,
                    "content": "内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "simple"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        async with await client_for_user("approver") as approver:
            await approver.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve"},
            )

        async with await client_for_user("finance") as finance:
            resp = await finance.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        assert resp.status_code == 400

    async def test_finance_before_legal_rejected(self, client_for_user):
        cid = await self._create_approved_contract(client_for_user)

        async with await client_for_user("finance") as finance:
            resp = await finance.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        assert resp.status_code == 400
        assert "法务" in resp.json()["detail"]

    async def test_legal_without_ai_rejected(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "无AI评审",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                    "amount": 320000,
                    "content": "内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        for role in ("approver", "legal", "finance", "executive"):
            async with await client_for_user(role) as client:
                pending = await client.get("/api/v1/approvals/pending")
                items = [
                    i for i in pending.json()["data"]["items"] if i["contract_id"] == cid
                ]
                if not items:
                    continue
                fid = items[0]["flow_id"]
                await client.post(
                    f"/api/v1/approvals/{fid}/approve",
                    json={"action": "approve"},
                )

        async with await client_for_user("legal") as legal:
            resp = await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve"},
            )
        assert resp.status_code == 400
        assert "AI" in resp.json()["detail"]

    async def test_review_sequence_legal_finance_executive(self, client_for_user):
        cid = await self._create_approved_contract(client_for_user)

        async with await client_for_user("legal") as legal:
            r1 = await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve"},
            )
        assert r1.status_code == 200

        async with await client_for_user("finance") as finance:
            r2 = await finance.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        assert r2.status_code == 200

        async with await client_for_user("executive") as executive:
            r3 = await executive.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "executive", "action": "approve"},
            )
        assert r3.status_code == 200
        assert r3.json()["data"]["session_status"] == "completed"

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["approval_status"] == "seal_pending"
