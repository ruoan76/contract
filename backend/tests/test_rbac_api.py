"""
RBAC API 测试 — Phase C-1
"""
import pytest


@pytest.mark.unit
class TestRBACForbidden:
    """5 个写接口 403 负向用例。"""

    async def _create_contract(self, client_for_user, amount=80000):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "RBAC测试合同",
                    "contract_type": "purchase",
                    "counterparty_name": "测试公司",
                    "amount": amount,
                    "content": "内容",
                },
            )
        return create.json()["data"]["id"]

    async def test_drafter_cannot_update_thresholds(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            resp = await drafter.put(
                "/api/v1/config/thresholds",
                json={"simple_max": 100000},
            )
        assert resp.status_code == 403

    async def test_drafter_cannot_blacklist_counterparty(self, client_for_user):
        async with await client_for_user("admin") as admin:
            cp = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "RBAC相对方", "credit_code": "91110000RBAC0001"},
            )
        cp_id = cp.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "测试"},
            )
        assert resp.status_code == 403

    async def test_drafter_cannot_approve_seal(self, client_for_user):
        cid = await self._create_contract(client_for_user)
        async with await client_for_user("drafter") as drafter:
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

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
        async with await client_for_user("legal") as legal:
            await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve"},
            )

        async with await client_for_user("drafter") as drafter:
            seal = await drafter.post(
                "/api/v1/seals/apply",
                json={"contract_id": cid, "seal_type": "公章"},
            )
        seal_id = seal.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                f"/api/v1/seals/{seal_id}/approve",
                json={"approved": True},
            )
        assert resp.status_code == 403

    async def test_legal_cannot_submit_finance_opinion(self, client_for_user):
        cid = await self._create_contract(client_for_user, amount=320000)

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

        async with await client_for_user("legal") as legal:
            resp = await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        assert resp.status_code == 403

    async def test_drafter_cannot_approve_flow(self, client_for_user):
        cid = await self._create_contract(client_for_user)
        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "simple"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve"},
            )
        assert resp.status_code == 403


@pytest.mark.unit
class TestRBACAllowed:
    async def test_admin_can_blacklist(self, client_for_user):
        async with await client_for_user("admin") as admin:
            cp = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "可拉黑公司", "credit_code": "91110000ADMIN001"},
            )
        cp_id = cp.json()["data"]["id"]

        async with await client_for_user("admin") as admin:
            resp = await admin.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "管理员操作"},
            )
        assert resp.status_code == 200
