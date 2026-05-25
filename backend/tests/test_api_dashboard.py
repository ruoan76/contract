"""
合同看板与流程匹配 API 测试
"""
from datetime import date, timedelta

import pytest


@pytest.mark.unit
class TestDashboardAPI:
    async def test_match_flow_simple(self, api_client):
        resp = await api_client.get("/api/v1/contracts/match-flow?amount=50000")
        assert resp.status_code == 200
        assert resp.json()["data"]["flow_type"] == "simple"

    async def test_match_flow_standard(self, api_client):
        resp = await api_client.get("/api/v1/contracts/match-flow?amount=500000")
        assert resp.json()["data"]["flow_type"] == "standard"

    async def test_dashboard_buckets(self, db_session, api_client):
        from app.models.contract import Contract

        today = date.today()
        db_session.add_all(
            [
                Contract(
                    contract_no="UT-DASH-1",
                    title="执行中",
                    contract_type="service",
                    status="executing",
                    counterparty_name="A",
                    creator_id=1,
                    end_date=today + timedelta(days=60),
                ),
                Contract(
                    contract_no="UT-DASH-2",
                    title="快到期",
                    contract_type="service",
                    status="sealed",
                    counterparty_name="B",
                    creator_id=1,
                    end_date=today + timedelta(days=10),
                ),
                Contract(
                    contract_no="UT-DASH-3",
                    title="已过期",
                    contract_type="service",
                    status="signed",
                    counterparty_name="C",
                    creator_id=1,
                    end_date=today - timedelta(days=3),
                ),
            ]
        )
        await db_session.commit()

        resp = await api_client.get("/api/v1/contracts/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["executing"]) >= 1
        assert len(data["expiring_soon"]) >= 1
        assert len(data["expired"]) >= 1
        assert "stats" in data
        assert data["stats"]["total"] >= 3
        assert data["stats"]["executing_count"] >= 1

    async def test_upload_contract_file(self, api_client, mock_auth_headers, tmp_path, monkeypatch):
        from app.core import config as cfg

        monkeypatch.setattr(cfg.settings, "FILE_STORAGE_PATH", str(tmp_path))
        headers = mock_auth_headers(user_id=1)
        create = await api_client.post(
            "/api/v1/contracts/",
            json={
                "title": "上传测试",
                "contract_type": "service",
                "counterparty_name": "公司",
            },
            headers=headers,
        )
        cid = create.json()["data"]["id"]
        files = {"file": ("test.txt", b"hello contract", "text/plain")}
        resp = await api_client.post(
            f"/api/v1/contracts/{cid}/upload",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["file_size"] == 14
