"""Phase 3 Stretch 后端最小测试"""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.contract import AIReview, Contract, RiskAlert


async def _seed_review(db_session, test_user) -> str:
    contract = Contract(
        contract_no="CON-TEST-0001",
        title="测试合同",
        contract_type="service",
        status="draft",
        counterparty_name="测试公司",
        amount=100000,
        creator_id=test_user.id,
        content="甲方：A公司\n乙方：B公司\n合同金额：50000元",
    )
    db_session.add(contract)
    await db_session.flush()

    review_id = "REV-TEST-001"
    review = AIReview(
        contract_id=contract.id,
        version_id=1,
        review_id=review_id,
        overall_risk_level="medium",
        overall_risk_score=65.0,
        recommendation="建议补充违约责任条款",
        clause_reviews='[{"clause":"付款","risk":"中"}]',
        rule_violations='[{"rule":"R001","message":"缺少验收条款"}]',
        summary='{"gates":[]}',
        review_status="ai_done",
        model_version="mock-v1",
    )
    db_session.add(review)
    await db_session.commit()
    return review_id


@pytest.mark.unit
class TestAiReviewReport:
    async def test_export_pdf_report(self, api_client, db_session, test_user):
        review_id = await _seed_review(db_session, test_user)
        resp = await api_client.get(
            f"/api/v1/ai-review/{review_id}/report",
            params={"format": "pdf"},
        )
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "pdf" in ct or "html" in ct or resp.headers.get("content-type", "").startswith("application/json")
        if "pdf" in ct:
            assert resp.content[:4] == b"%PDF"

    async def test_export_json_report(self, api_client, db_session, test_user):
        review_id = await _seed_review(db_session, test_user)
        resp = await api_client.get(
            f"/api/v1/ai-review/{review_id}/report",
            params={"format": "json"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["review_id"] == review_id


@pytest.mark.unit
class TestContractParse:
    async def test_parse_txt_file(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1)
        content = b"\xe7\x94\xb2\xe6\x96\xb9\xef\xbc\x9aA\xe5\x85\xac\xe5\x8f\xb8\n\xe4\xb9\x99\xe6\x96\xb9\xef\xbc\x9aB\xe5\x85\xac\xe5\x8f\xb8\n\xe5\x90\x88\xe5\x90\x8c\xe9\x87\x91\xe9\xa2\x9d\xef\xbc\x9a100000\xe5\x85\x83"
        files = {"file": ("contract.txt", BytesIO(content), "text/plain")}
        resp = await api_client.post(
            "/api/v1/contracts/parse",
            files=files,
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "fields" in data
        assert data["fields"]["mock"] is True
        assert data["fields"]["file_type"] == "txt"


@pytest.mark.unit
class TestExpirationReminders:
    async def test_create_expiration_reminders(self, api_client, db_session, test_user):
        contract = Contract(
            contract_no="CON-EXP-001",
            title="即将到期合同",
            contract_type="service",
            status="executing",
            counterparty_name="测试公司",
            amount=50000,
            creator_id=test_user.id,
            end_date=date.today() + timedelta(days=7),
        )
        db_session.add(contract)
        await db_session.commit()

        resp = await api_client.post(
            "/api/v1/reminders/expiration",
            json={"days_ahead": 30},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["contracts_scanned"] >= 1
        assert body["data"]["notifications_created"] >= 1


@pytest.mark.unit
class TestRiskHandle:
    async def test_handle_risk(self, api_client, db_session, test_user):
        contract = Contract(
            contract_no="CON-RISK-001",
            title="风险合同",
            contract_type="service",
            status="executing",
            counterparty_name="测试公司",
            amount=80000,
            creator_id=test_user.id,
        )
        db_session.add(contract)
        await db_session.flush()

        alert = RiskAlert(
            contract_id=contract.id,
            alert_type="compliance",
            alert_level="high",
            title="合规风险",
            message="缺少必备条款",
            source="ai",
            status="pending",
        )
        db_session.add(alert)
        await db_session.commit()

        resp = await api_client.post(
            f"/api/v1/risks/{alert.id}/handle",
            json={"status": "resolved", "comment": "已补充条款"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 200


@pytest.mark.unit
class TestWebSocketNotifications:
    def test_websocket_ping_pong(self):
        from starlette.testclient import TestClient
        from main import app

        client = TestClient(app)
        with client.websocket_connect("/api/v1/ws/notifications") as ws:
            ws.send_text("ping")
            msg = ws.receive_json()
            assert msg["type"] == "pong"
