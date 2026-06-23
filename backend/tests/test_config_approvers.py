"""
审批人配置 API 测试
"""
import json

import pytest

import app.services.config_service as config_service
import app.services.flow_match_service as flow_match_service


@pytest.fixture
def isolated_config_files(tmp_path, monkeypatch):
    approvers_path = tmp_path / "approvers.json"
    thresholds_path = tmp_path / "thresholds.json"
    flow_path = tmp_path / "flow_config.json"
    flow_path.write_text(
        json.dumps({"thresholds": {"simple_max": 100000, "standard_max": 1000000}}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_service, "_APPROVERS_FILE", str(approvers_path))
    monkeypatch.setattr(config_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(config_service, "FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(config_service, "_FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(flow_match_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(flow_match_service, "_FLOW_CONFIG_FILE", str(flow_path))
    config_service._save_approvers(list(config_service._DEFAULT_APPROVERS[:3]))
    flow_match_service.clear_thresholds_cache()
    yield
    flow_match_service.clear_thresholds_cache()


@pytest.mark.unit
class TestConfigApproversAPI:
    """GET/POST /api/v1/config/approvers"""

    async def test_get_approvers_returns_list(self, api_client, isolated_config_files):
        resp = await api_client.get("/api/v1/config/approvers")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "flow_type" in data[0]

    async def test_admin_can_add_approver_upsert(self, client_for_user, isolated_config_files):
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
        assert item["user_name"] == "赵财务"

        async with await client_for_user("admin") as admin:
            resp2 = await admin.post(
                "/api/v1/config/approvers",
                json={
                    "flow_type": "standard",
                    "step": 3,
                    "role": "finance",
                    "user_id": 4,
                    "user_name": "赵财务",
                },
            )
        assert resp2.status_code == 200
        items = resp2.json()["data"]
        # 第二次 POST 同 step 应为 upsert，列表去重后 standard step3 仅一条
        async with await client_for_user("admin") as admin:
            lst = await admin.get("/api/v1/config/approvers")
        rows = [x for x in lst.json()["data"] if x["flow_type"] == "standard" and x["step"] == 3]
        assert len(rows) == 1

    async def test_drafter_cannot_add_approver(self, client_for_user, isolated_config_files):
        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                "/api/v1/config/approvers",
                json={"flow_type": "simple", "step": 1, "role": "approver"},
            )
        assert resp.status_code == 403

    async def test_admin_can_update_approver(self, client_for_user, isolated_config_files):
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

    async def test_admin_can_delete_approver(self, client_for_user, isolated_config_files):
        async with await client_for_user("admin") as admin:
            lst = await admin.get("/api/v1/config/approvers")
            before = len(lst.json()["data"])
            first_id = lst.json()["data"][0]["id"]
            del_resp = await admin.delete(f"/api/v1/config/approvers/{first_id}")
            assert del_resp.status_code == 200
            lst2 = await admin.get("/api/v1/config/approvers")
            assert len(lst2.json()["data"]) == before - 1
