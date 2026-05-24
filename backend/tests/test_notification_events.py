"""通知事件触发测试"""
import pytest


@pytest.mark.unit
class TestNotificationEvents:
    async def test_submit_approval_creates_notification(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "通知测试合同",
                    "contract_type": "purchase",
                    "counterparty_name": "测试公司",
                    "amount": 80000,
                    "content": "内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "simple"},
            )

        async with await client_for_user("approver") as approver:
            notes = await approver.get("/api/v1/notifications/")
        items = notes.json()["data"]["items"]
        assert any("待办审批" in (n.get("title") or "") for n in items)
