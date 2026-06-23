"""
配置 API：阈值与 match-flow 联动
"""
import json

import pytest

import app.services.config_service as config_service
import app.services.flow_match_service as flow_match_service


@pytest.fixture
def isolated_config_files(tmp_path, monkeypatch):
    thresholds_path = tmp_path / "thresholds.json"
    flow_path = tmp_path / "flow_config.json"
    approvers_path = tmp_path / "approvers.json"
    flow_path.write_text(
        json.dumps({"thresholds": {"simple_max": 100000, "standard_max": 1000000}}, ensure_ascii=False),
        encoding="utf-8",
    )
    approvers_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(config_service, "_APPROVERS_FILE", str(approvers_path))
    monkeypatch.setattr(config_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(config_service, "FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(config_service, "_FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(flow_match_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(flow_match_service, "_FLOW_CONFIG_FILE", str(flow_path))
    flow_match_service.clear_thresholds_cache()
    yield
    flow_match_service.clear_thresholds_cache()


@pytest.mark.unit
class TestConfigApiFlowMatch:
    async def test_match_flow_after_threshold_put(self, client_for_user, api_client, isolated_config_files):
        async with await client_for_user("admin") as admin:
            put = await admin.put(
                "/api/v1/config/thresholds",
                json={"simple_max": 200000, "standard_max": 2000000, "board_threshold": 2000000},
            )
        assert put.status_code == 200
        flow_match_service.clear_thresholds_cache()
        resp = await api_client.get("/api/v1/contracts/match-flow", params={"amount": 150000})
        assert resp.status_code == 200
        assert resp.json()["data"]["flow_type"] == "simple"
        resp2 = await api_client.get("/api/v1/contracts/match-flow", params={"amount": 2500000})
        assert resp2.json()["data"]["flow_type"] == "large_amount"
