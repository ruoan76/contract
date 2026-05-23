"""
数据统计 API 测试 — Phase B-3
"""
from datetime import datetime, timedelta

import pytest


@pytest.mark.unit
class TestStatisticsAPI:
    async def test_approval_efficiency_uses_approved_status(
        self, db_session, api_client, mock_data
    ):
        from app.models.contract import ApprovalFlow, Contract

        contract = Contract(
            contract_no="STAT-001",
            title="统计测试",
            contract_type="service",
            status="approved",
            counterparty_name="公司",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()

        flow = ApprovalFlow(
            contract_id=contract.id,
            flow_type="standard",
            status="approved",
            current_node_id="done",
            current_step=4,
            total_steps=4,
            duration_hours=24.0,
        )
        db_session.add(flow)
        await db_session.commit()

        resp = await api_client.get("/api/v1/statistics/approval-efficiency")
        assert resp.status_code == 200
        assert resp.json()["data"]["total_flows"] >= 1

    async def test_risk_trend_sqlite_compatible(self, db_session, api_client):
        from app.models.contract import Contract, RiskAlert

        contract = Contract(
            contract_no="STAT-002",
            title="风险趋势",
            contract_type="service",
            status="draft",
            counterparty_name="公司",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()

        alert = RiskAlert(
            contract_id=contract.id,
            alert_type="compliance",
            alert_level="high",
            title="合规风险",
            source="ai",
            status="pending",
            created_at=datetime.now() - timedelta(days=10),
        )
        db_session.add(alert)
        await db_session.commit()

        resp = await api_client.get("/api/v1/statistics/risk-trend")
        assert resp.status_code == 200
        trend = resp.json()["data"]["trend"]
        assert isinstance(trend, list)

    async def test_contract_statistics(self, api_client):
        resp = await api_client.get("/api/v1/statistics/contracts")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_contracts" in data
        assert "by_status" in data
