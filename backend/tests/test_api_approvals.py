"""
审批 API 集成测试
"""
import pytest
from app.services.approval_service import ApprovalSubmitRequest


@pytest.mark.unit
class TestApprovalAPI:
    """审批 API 端点测试"""

    async def test_submit_and_history(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1)
        create_resp = await api_client.post(
            "/api/v1/contracts/",
            json={
                "title": "审批测试合同",
                "contract_type": "service",
                "counterparty_name": "测试公司",
            },
            headers=headers,
        )
        assert create_resp.status_code == 200
        contract_id = create_resp.json()["data"]["id"]

        submit_resp = await api_client.post(
            "/api/v1/approvals/submit",
            json={"contract_id": contract_id, "flow_type": "standard"},
            headers=headers,
        )
        assert submit_resp.status_code == 200
        flow_id = submit_resp.json()["data"]["flow_id"]
        assert flow_id is not None

        history_resp = await api_client.get(
            f"/api/v1/approvals/{flow_id}/history",
            headers=headers,
        )
        assert history_resp.status_code == 200
        data = history_resp.json()["data"]
        assert data["flow_id"] == flow_id
        assert len(data["steps"]) >= 1

    async def test_approve_step(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create_resp = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "待审批合同",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                    "amount": 80000,
                    "content": "内容",
                },
            )
        contract_id = create_resp.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            submit_resp = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": contract_id, "flow_type": "simple"},
            )
        flow_id = submit_resp.json()["data"]["flow_id"]

        async with await client_for_user("approver") as approver:
            approve_resp = await approver.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve", "comment": "同意"},
            )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["data"]["status"] in ("approving", "approved")

    async def test_pending_list(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1)
        resp = await api_client.get("/api/v1/approvals/pending", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    async def test_pending_filtered_by_role(
        self, client_for_user, users_by_role
    ):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "待办测试",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                    "amount": 80000,
                    "content": "x",
                },
            )
        cid = create.json()["data"]["id"]
        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "simple"},
            )
        async with await client_for_user("approver") as approver:
            pa = await approver.get("/api/v1/approvals/pending")
        async with await client_for_user("legal") as legal:
            pl = await legal.get("/api/v1/approvals/pending")
        assert pa.json()["data"]["total"] >= 1
        assert pl.json()["data"]["total"] == 0
