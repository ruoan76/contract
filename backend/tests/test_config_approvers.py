"""
审批人配置 API 测试
"""
import pytest


@pytest.mark.unit
class TestConfigApproversAPI:
    """GET/POST /api/v1/config/approvers"""

    async def test_get_approvers_returns_list(self, api_client):
        resp = await api_client.get("/api/v1/config/approvers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "flow_type" in data[0]

    async def test_admin_can_add_approver(self, client_for_user):
        async with await client_for_user("admin") as admin:
            resp = await admin.post(
                "/api/v1/config/approvers",
                json={
                    "flow_type": "standard",
                    "step": 3,
                    "role": "finance",
                    "user_id": 4,
                    "user_name": "赵财务",
                },
            )
        assert resp.status_code == 200
        item = resp.json()["data"]
        assert item["flow_type"] == "standard"
        assert item["step"] == 3
        assert item["role"] == "finance"
        assert item["user_name"] == "赵财务"
        assert item["id"] is not None

    async def test_drafter_cannot_add_approver(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                "/api/v1/config/approvers",
                json={"flow_type": "simple", "step": 1, "role": "approver"},
            )
        assert resp.status_code == 403

    async def test_admin_can_update_approver(self, client_for_user):
        async with await client_for_user("admin") as admin:
            create = await admin.post(
                "/api/v1/config/approvers",
                json={
                    "flow_type": "simple",
                    "step": 2,
                    "role": "legal",
                    "user_id": 3,
                    "user_name": "王法务",
                },
            )
            approver_id = create.json()["data"]["id"]
            update = await admin.put(
                f"/api/v1/config/approvers/{approver_id}",
                json={"user_name": "王法务-更新"},
            )
        assert update.status_code == 200
        assert update.json()["data"]["user_name"] == "王法务-更新"
