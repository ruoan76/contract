"""
配置：阈值与流程匹配、审批人同步 flow_config
"""
import json

import pytest

import app.services.config_service as config_service
import app.services.flow_match_service as flow_match_service


@pytest.fixture
def isolated_config_files(tmp_path, monkeypatch):
    """测试使用临时 JSON，不污染 app/data。"""
    approvers_path = tmp_path / "approvers.json"
    thresholds_path = tmp_path / "thresholds.json"
    flow_path = tmp_path / "flow_config.json"
    flow_path.write_text(
        json.dumps(
            {
                "thresholds": {
                    "simple_max": 100000,
                    "standard_max": 1000000,
                    "board_threshold": 1000000,
                },
                "simple": {"name": "简易审批", "nodes": []},
                "standard": {"name": "标准审批", "nodes": []},
                "large_amount": {"name": "大额审批", "nodes": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_service, "_APPROVERS_FILE", str(approvers_path))
    monkeypatch.setattr(config_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(config_service, "FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(config_service, "_FLOW_CONFIG_FILE", str(flow_path))
    monkeypatch.setattr(flow_match_service, "_THRESHOLDS_FILE", str(thresholds_path))
    monkeypatch.setattr(flow_match_service, "_FLOW_CONFIG_FILE", str(flow_path))
    flow_match_service.clear_thresholds_cache()
    yield tmp_path
    flow_match_service.clear_thresholds_cache()


@pytest.mark.unit
class TestConfigThresholdsFlow:
    def test_update_thresholds_affects_match_flow_type(self, isolated_config_files):
        config_service.update_thresholds(
            {"simple_max": 50000, "standard_max": 500000, "board_threshold": 500000}
        )
        flow_match_service.clear_thresholds_cache()
        assert flow_match_service.match_flow_type(40000) == "simple"
        assert flow_match_service.match_flow_type(200000) == "standard"
        assert flow_match_service.match_flow_type(600000) == "large_amount"

    def test_get_flow_match_detail_returns_updated_thresholds(self, isolated_config_files):
        config_service.update_thresholds({"simple_max": 80000, "standard_max": 800000, "board_threshold": 800000})
        flow_match_service.clear_thresholds_cache()
        detail = flow_match_service.get_flow_match_detail(900000)
        assert detail["flow_type"] == "large_amount"
        assert detail["thresholds"]["simple_max"] == 80000


@pytest.mark.unit
class TestConfigApproversSync:
    def test_add_approver_upserts_and_syncs_flow_config(self, isolated_config_files):
        config_service._save_approvers(list(config_service._DEFAULT_APPROVERS[:4]))
        config_service.add_approver(
            {
                "flow_type": "standard",
                "step": 3,
                "role": "finance",
                "user_id": 99,
                "user_name": "测试财务",
            }
        )
        items = config_service.get_approvers()
        std_step3 = [x for x in items if x["flow_type"] == "standard" and x["step"] == 3]
        assert len(std_step3) == 1
        assert std_step3[0]["user_id"] == 99

        nodes = config_service.get_flow_nodes_config("standard")
        assert len(nodes) == 3
        assert nodes[2].get("user_id") == 99

    def test_delete_approver_removes_row(self, isolated_config_files):
        config_service._save_approvers(list(config_service._DEFAULT_APPROVERS[:2]))
        config_service.delete_approver(2)
        items = config_service.get_approvers()
        assert all(x.get("id") != 2 for x in items)
