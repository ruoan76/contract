"""
DEMO 脚本集成测试（DEMO-01～05）— Phase A 加深版
"""
import pytest


@pytest.mark.integration
class TestDemo01SimpleFlow:
    """IT-01: create → submit → approve → review → seal"""

    async def test_simple_full_chain(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "简易流程合同",
                    "contract_type": "purchase",
                    "counterparty_name": "供应商A",
                    "amount": 80000,
                    "content": "采购合同内容",
                },
            )
        assert create.status_code == 200
        cid = create.json()["data"]["id"]
        assert create.json()["data"]["flow_type"] == "simple"

        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "simple"},
            )
        assert submit.status_code == 200
        flow_id = submit.json()["data"]["flow_id"]

        async with await client_for_user("approver") as approver:
            approve = await approver.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve", "comment": "通过"},
            )
        assert approve.status_code == 200

        async with await client_for_user("drafter") as drafter:
            ai = await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
        assert ai.status_code == 200

        async with await client_for_user("legal") as legal:
            opinion = await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve", "comment": "法务通过"},
            )
        assert opinion.status_code == 200

        async with await client_for_user("drafter") as drafter:
            seal_apply = await drafter.post(
                "/api/v1/seals/apply",
                json={"contract_id": cid, "seal_type": "公章"},
            )
        assert seal_apply.status_code == 200
        seal_id = seal_apply.json()["data"]["id"]

        async with await client_for_user("admin") as admin:
            seal_ok = await admin.post(
                f"/api/v1/seals/{seal_id}/approve",
                json={"approved": True},
            )
        assert seal_ok.status_code == 200

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["status"] == "sealed"


@pytest.mark.integration
class TestDemo02StandardReview:
    """IT-02: ai → 三角色评审 → archive"""

    async def test_standard_review_archive(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "标准评审合同",
                    "contract_type": "service",
                    "counterparty_name": "客户B",
                    "amount": 320000,
                    "content": "服务合同条款内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            ai = await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
        assert ai.status_code == 200

        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        # 标准流程：仅部门主管走审批链，法务/财务/高管走评审工作台
        for role in ("approver",):
            async with await client_for_user(role) as client:
                pending = await client.get("/api/v1/approvals/pending")
                items = [
                    i for i in pending.json()["data"]["items"] if i["contract_id"] == cid
                ]
                if not items:
                    continue
                fid = items[0]["flow_id"]
                resp = await client.post(
                    f"/api/v1/approvals/{fid}/approve",
                    json={"action": "approve"},
                )
                assert resp.status_code == 200

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["status"] == "approved"

        async with await client_for_user("legal") as legal:
            await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve"},
            )
        async with await client_for_user("finance") as finance:
            await finance.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        async with await client_for_user("executive") as executive:
            await executive.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "executive", "action": "approve"},
            )

        async with await client_for_user("admin") as admin:
            archive = await admin.post(
                f"/api/v1/archives/{cid}/archive",
                json={"archive_location": "/archive/2026/demo02"},
            )
        assert archive.status_code == 200
        assert archive.json()["data"]["status"] == "archived"


@pytest.mark.integration
class TestDemo03SpecialFlow:
    """IT-03: 特殊流程 history 含 board 节点"""

    async def test_large_amount_history(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "DEMO-03 特殊流程",
                    "contract_type": "purchase",
                    "counterparty_name": "大客户",
                    "amount": 2500000,
                    "content": "大额合同",
                },
            )
        cid = create.json()["data"]["id"]
        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "large_amount"},
            )
        flow_id = submit.json()["data"]["flow_id"]
        async with await client_for_user("drafter") as drafter:
            history = await drafter.get(f"/api/v1/approvals/{flow_id}/history")
        assert history.status_code == 200
        assert history.json()["data"]["total_steps"] == 5


@pytest.mark.integration
class TestDemo05Revision:
    """IT-05: return → revision → ai"""

    async def test_return_and_revision(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "退回修订合同",
                    "contract_type": "service",
                    "counterparty_name": "客户C",
                    "amount": 150000,
                    "content": "原始内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        async with await client_for_user("approver") as approver:
            await approver.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve"},
            )

        async with await client_for_user("legal") as legal:
            ret = await legal.post(
                f"/api/v1/reviews/contracts/{cid}/return",
                json={"role": "legal", "comment": "请修改付款条款"},
            )
        assert ret.status_code == 200
        assert ret.json()["data"]["status"] == "draft"

        async with await client_for_user("drafter") as drafter:
            rev = await drafter.post(
                f"/api/v1/contracts/{cid}/revisions",
                json={"content": "修订后内容", "change_description": "修改付款条款"},
            )
        assert rev.status_code == 200
        assert rev.json()["data"]["version"] == 2

        async with await client_for_user("drafter") as drafter:
            ai = await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
        assert ai.status_code == 200


@pytest.mark.integration
class TestPendingFilter:
    """IT-06: 待办按审批人过滤"""

    async def test_approver_sees_pending_legal_does_not(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "待办过滤测试",
                    "contract_type": "purchase",
                    "counterparty_name": "公司X",
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
            pending_a = await approver.get("/api/v1/approvals/pending")
        async with await client_for_user("legal") as legal:
            pending_l = await legal.get("/api/v1/approvals/pending")

        assert pending_a.json()["data"]["total"] >= 1
        assert pending_l.json()["data"]["total"] == 0


@pytest.mark.integration
class TestDemo04Blacklist:
    """IT-04: 黑名单拦截创建合同"""

    async def test_blacklist_blocks_create(self, client_for_user, db_session):
        from app.models.counterparty import Counterparty

        cp = Counterparty(
            name="IT04黑名单",
            credit_code="91110000IT04001",
            is_blacklist=1,
            blacklist_reason="违规",
            status=1,
        )
        db_session.add(cp)
        await db_session.commit()

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "黑名单测试",
                    "contract_type": "purchase",
                    "counterparty_id": cp.id,
                    "counterparty_name": cp.name,
                },
            )
        assert resp.status_code == 403


@pytest.mark.integration
class TestDashboardBuckets:
    """IT-07: 看板三栏语义"""

    async def test_dashboard_three_buckets(self, client_for_user, db_session):
        from datetime import date, timedelta
        from app.models.contract import Contract

        today = date.today()
        contracts = [
            Contract(
                contract_no="DASH-EXEC",
                title="执行中合同",
                contract_type="service",
                status="approved",
                counterparty_name="A",
                creator_id=1,
                end_date=today + timedelta(days=90),
            ),
            Contract(
                contract_no="DASH-EXP",
                title="即将到期",
                contract_type="service",
                status="sealed",
                counterparty_name="B",
                creator_id=1,
                end_date=today + timedelta(days=15),
            ),
            Contract(
                contract_no="DASH-OVD",
                title="已过期",
                contract_type="service",
                status="signed",
                counterparty_name="C",
                creator_id=1,
                end_date=today - timedelta(days=5),
            ),
        ]
        db_session.add_all(contracts)
        await db_session.commit()

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.get("/api/v1/contracts/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["executing"]) >= 1
        assert len(data["expiring_soon"]) >= 1
        assert len(data["expired"]) >= 1


@pytest.mark.integration
class TestReviewSequenceGate:
    """IT-10: 评审顺序门禁"""

    async def test_finance_before_legal_returns_400(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "顺序门禁",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                    "amount": 320000,
                    "content": "内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        flow_id = submit.json()["data"]["flow_id"]

        for role in ("approver",):
            async with await client_for_user(role) as client:
                pending = await client.get("/api/v1/approvals/pending")
                items = [
                    i for i in pending.json()["data"]["items"] if i["contract_id"] == cid
                ]
                if not items:
                    continue
                fid = items[0]["flow_id"]
                await client.post(
                    f"/api/v1/approvals/{fid}/approve",
                    json={"action": "approve"},
                )

        async with await client_for_user("finance") as finance:
            resp = await finance.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "finance", "action": "approve"},
            )
        assert resp.status_code == 400


@pytest.mark.integration
class TestRBACIntegration:
    """IT-08: RBAC 403 聚合验证"""

    async def test_rbac_forbidden_endpoints(self, client_for_user):
        async with await client_for_user("admin") as admin:
            cp = await admin.post(
                "/api/v1/counterparties/",
                json={"name": "IT08公司", "credit_code": "91110000IT08001"},
            )
        cp_id = cp.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            r1 = await drafter.put(
                "/api/v1/config/thresholds",
                json={"simple_max": 100000},
            )
            r2 = await drafter.post(
                f"/api/v1/counterparties/{cp_id}/blacklist",
                json={"reason": "x"},
            )
        assert r1.status_code == 403
        assert r2.status_code == 403


@pytest.mark.integration
class TestApprovalStatusSteps:
    """IT-09: approval_status 逐步断言"""

    async def test_standard_flow_approval_status_progression(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "状态字典测试",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                    "amount": 320000,
                    "content": "内容",
                },
            )
        cid = create.json()["data"]["id"]

        async with await client_for_user("drafter") as drafter:
            submit = await drafter.post(
                "/api/v1/approvals/submit",
                json={"contract_id": cid, "flow_type": "standard"},
            )
        assert submit.status_code == 200
        flow_id = submit.json()["data"]["flow_id"]

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["status"] == "pending"
        assert detail.json()["data"]["approval_status"] == "dept_approval"

        async with await client_for_user("approver") as approver:
            await approver.post(
                f"/api/v1/approvals/{flow_id}/approve",
                json={"action": "approve"},
            )

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["status"] == "approved"
        assert detail.json()["data"]["approval_status"] == "seal_pending"

        async with await client_for_user("drafter") as drafter:
            await drafter.post(
                "/api/v1/ai-review/review",
                json={"contract_id": cid},
            )

        async with await client_for_user("legal") as legal:
            await legal.post(
                f"/api/v1/reviews/contracts/{cid}/opinions",
                json={"role": "legal", "action": "approve"},
            )

        async with await client_for_user("drafter") as drafter:
            detail = await drafter.get(f"/api/v1/contracts/{cid}")
        assert detail.json()["data"]["approval_status"] == "finance_review"


@pytest.mark.integration
class TestIT11NotificationEvents:
    """IT-11: 提交审批后 approver 收到通知"""

    async def test_approval_triggers_notification(self, client_for_user):
        async with await client_for_user("drafter") as drafter:
            create = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "IT11 通知合同",
                    "contract_type": "purchase",
                    "counterparty_name": "供应商",
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
            resp = await approver.get("/api/v1/notifications/")
        items = resp.json()["data"]["items"]
        assert any(n.get("resource_id") == cid for n in items)


@pytest.mark.integration
class TestIT12TemplateApprovalFlow:
    """IT-12: 模板提交发布 → 批准 → 废止"""

    async def test_template_publish_approval_flow(self, client_for_user):
        async with await client_for_user("admin") as admin:
            create = await admin.post(
                "/api/v1/templates/",
                json={
                    "name": "IT12 采购模板",
                    "category": "purchase",
                    "content": "模板正文",
                },
            )
        assert create.status_code == 200
        tid = create.json()["data"]["id"]
        assert create.json()["data"]["status"] == "draft"

        async with await client_for_user("admin") as admin:
            submit = await admin.post(f"/api/v1/templates/{tid}/submit-publish")
        assert submit.status_code == 200
        assert submit.json()["data"]["status"] == "pending_publish"

        async with await client_for_user("approver") as approver:
            approve = await approver.post(
                f"/api/v1/templates/{tid}/approve-publish"
            )
        assert approve.status_code == 200
        assert approve.json()["data"]["status"] == "published"
        assert approve.json()["data"]["version"] == 2

        async with await client_for_user("admin") as admin:
            deprecate = await admin.post(f"/api/v1/templates/{tid}/deprecate")
        assert deprecate.status_code == 200
        assert deprecate.json()["data"]["status"] == "deprecated"
