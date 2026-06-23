"""
相对方 CRUD、黑名单、禁用 API 测试
"""
import pytest


@pytest.mark.unit
class TestCounterpartiesCrudAPI:
    async def test_list_keyword_and_pagination(self, client_for_user):
        suffix = "CRUDTEST"
        async with await client_for_user("admin") as admin:
            await admin.post(
                "/api/v1/counterparties/",
                json={"name": f"关键词公司{suffix}", "credit_code": f"91110000{suffix[:8]}"},
            )
            resp = await admin.get(
                "/api/v1/counterparties/",
                params={"keyword": suffix, "page": 1, "page_size": 5},
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert any(suffix in (i.get("name") or "") for i in data["items"])

    async def test_get_detail_includes_contract_count(self, client_for_user):
        async with await client_for_user("admin") as admin:
            created = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "详情测试公司", "credit_code": "91110000DETAIL01"},
            )
            cp_id = created.json()["data"]["id"]
            resp = await admin.get(f"/api/v1/counterparties/{cp_id}")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["name"] == "详情测试公司"
        assert "contract_count" in body

    async def test_update_counterparty(self, client_for_user):
        async with await client_for_user("drafter") as client:
            created = await client.post(
                "/api/v1/counterparties/",
                json={"name": "待更新公司", "credit_code": "91110000UPD0001"},
            )
            cp_id = created.json()["data"]["id"]
            resp = await client.put(
                f"/api/v1/counterparties/{cp_id}",
                json={"contact_name": "王五", "credit_rating": "B"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["contact_name"] == "王五"
        assert resp.json()["data"]["credit_rating"] == "B"

    async def test_blacklist_and_unblacklist(self, client_for_user):
        async with await client_for_user("admin") as admin:
            created = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "拉黑测试公司", "credit_code": "91110000BLTEST01"},
            )
            cp_id = created.json()["data"]["id"]
            bl = await admin.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "测试拉黑"},
            )
            assert bl.status_code == 200
            assert bl.json()["data"]["is_blacklist"] == 1
            un = await admin.post(f"/api/v1/counterparties/{cp_id}/unblacklist")
            assert un.status_code == 200
            assert un.json()["data"]["is_blacklist"] == 0

    async def test_disable_counterparty(self, client_for_user):
        async with await client_for_user("admin") as admin:
            created = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "禁用测试公司", "credit_code": "91110000DIS0001"},
            )
            cp_id = created.json()["data"]["id"]
            resp = await admin.post(f"/api/v1/counterparties/{cp_id}/disable")
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == 0

    async def test_list_filter_blacklist(self, client_for_user):
        async with await client_for_user("admin") as admin:
            resp = await admin.get(
                "/api/v1/counterparties/",
                params={"is_blacklist": 1, "page_size": 5},
            )
        assert resp.status_code == 200
        for item in resp.json()["data"]["items"]:
            assert item["is_blacklist"] == 1

    async def test_drafter_cannot_unblacklist(self, client_for_user):
        async with await client_for_user("admin") as admin:
            created = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "权限测试公司", "credit_code": "91110000AUTH0001"},
            )
            cp_id = created.json()["data"]["id"]
            await admin.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "x"},
            )
        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(f"/api/v1/counterparties/{cp_id}/unblacklist")
        assert resp.status_code == 403
