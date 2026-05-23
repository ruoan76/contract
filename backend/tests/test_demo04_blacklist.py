"""
DEMO-04 黑名单集成测试
"""
import pytest


@pytest.mark.unit
class TestDemo04Blacklist:
    async def test_blacklist_blocks_contract_create(self, api_client, mock_auth_headers, db_session):
        from app.models.counterparty import Counterparty

        cp = Counterparty(
            name="黑名单公司",
            credit_code="91110000BLACK001",
            is_blacklist=1,
            blacklist_reason="违规",
            status=1,
        )
        db_session.add(cp)
        await db_session.commit()

        headers = mock_auth_headers(user_id=1)
        resp = await api_client.post(
            "/api/v1/contracts/",
            json={
                "title": "黑名单测试",
                "contract_type": "purchase",
                "counterparty_id": cp.id,
                "counterparty_name": cp.name,
            },
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_counterparty_crud(self, client_for_user):
        async with await client_for_user("admin") as admin:
            create = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "正常公司", "credit_code": "91110000OK001"},
            )
        assert create.status_code == 200
        cp_id = create.json()["data"]["id"]

        async with await client_for_user("admin") as admin:
            bl = await admin.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "测试"},
            )
        assert bl.status_code == 200
        assert bl.json()["data"]["is_blacklist"] == 1
