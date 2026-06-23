"""
系统用户 API 测试
"""
import pytest


@pytest.mark.unit
class TestSystemUsersAPI:
    async def test_list_users_requires_admin(self, client_for_user):
        async with await client_for_user("approver") as client:
            resp = await client.get("/api/v1/system/users")
        assert resp.status_code == 403

        async with await client_for_user("admin") as client:
            resp = await client.get("/api/v1/system/users")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "items" in data

    async def test_user_options_for_delegate(self, client_for_user):
        async with await client_for_user("approver") as client:
            resp = await client.get("/api/v1/system/users/options")
        assert resp.status_code == 200
        assert "items" in resp.json()["data"]

    async def test_profile_returns_role_code(self, client_for_user):
        async with await client_for_user("drafter") as client:
            resp = await client.get("/api/v1/system/profile")
        assert resp.status_code == 200
        assert resp.json()["data"].get("role_code") == "drafter"
