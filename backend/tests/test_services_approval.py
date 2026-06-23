"""
Approval Service Tests
测试审批流程服务
"""
import pytest
from datetime import datetime
from sqlalchemy import select
from unittest.mock import patch, AsyncMock

# ==============================================================================
# Approval Service Tests
# ==============================================================================

@pytest.mark.unit
class TestSubmitApproval:
    """submit_approval 服务测试"""
    
    async def test_submit_approval_success(self, db_session, mock_data):
        """测试成功提交审批"""
        from app.services.approval_service import submit_approval
        from app.services.contract_service import create_contract
        from app.models.contract import ApprovalFlow, ApprovalStep
        
        # 创建合同
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 提交审批
        result = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        assert result.id is not None
        assert result.status == "approving"
        assert result.flow_type == "standard"
        assert result.current_step == 0
        assert result.total_steps >= 1  # 与 flow_config 节点数一致（标准流程可为多步）
    
    async def test_submit_approval_contract_not_found(self, db_session, mock_data):
        """测试提交不存在的合同审批"""
        from app.services.approval_service import submit_approval
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException, match="合同不存在"):
            await submit_approval(
                db=db_session,
                user_id=1,
                username="testuser",
                req=type("Req", (), {
                    "contract_id": 9999,
                    "flow_type": "standard",
                })(),
            )
    
    async def test_submit_approval_not_draft(self, db_session, mock_data):
        """测试提交非草稿合同审批"""
        from app.services.approval_service import submit_approval
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        from fastapi import HTTPException
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 更新状态为 pending
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "pending"
        await db_session.flush()
        
        with pytest.raises(HTTPException, match="仅草稿可提交审批"):
            await submit_approval(
                db=db_session,
                user_id=1,
                username="testuser",
                req=type("Req", (), {
                    "contract_id": created["id"],
                    "flow_type": "standard",
                })(),
            )


@pytest.mark.unit
class TestApproveStep:
    """approve_step 服务测试"""
    
    async def test_approve_step_success(self, db_session, mock_data):
        """测试成功审批通过"""
        from app.services.approval_service import submit_approval, approve_step
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        # 审批第一步（无角色用户时 fallback 审批人为提交人 user_id=1）
        result = await approve_step(
            db=db_session,
            user_id=1,
            username="approver",
            flow_id=flow.id,
            action="approve",
            comment="同意",
        )
        
        assert result.current_step == 1
        assert result.status == "approved"
    
    async def test_approve_step_reject(self, db_session, mock_data):
        """测试审批拒绝"""
        from app.services.approval_service import submit_approval, approve_step
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        # 拒绝第一步
        result = await approve_step(
            db=db_session,
            user_id=1,
            username="approver",
            flow_id=flow.id,
            action="reject",
            comment="不同意",
        )
        
        assert result.status == "rejected"
    
    async def test_approve_step_flow_not_found(self, db_session, mock_data):
        """测试审批不存在的流程"""
        from app.services.approval_service import approve_step
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException, match="审批流程不存在"):
            await approve_step(
                db=db_session,
                user_id=2,
                username="approver",
                flow_id=9999,
                action="approve",
            )
    
    async def test_approve_step_flow_not_approving(self, db_session, mock_data):
        """测试审批已结束的流程"""
        from app.services.approval_service import submit_approval, approve_step
        from app.services.contract_service import create_contract
        from fastapi import HTTPException
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        # 拒绝使流程结束
        await approve_step(
            db=db_session,
            user_id=1,
            username="approver",
            flow_id=flow.id,
            action="reject",
        )

        # 再次审批应失败
        with pytest.raises(HTTPException, match="当前不可审批"):
            await approve_step(
                db=db_session,
                user_id=1,
                username="approver",
                flow_id=flow.id,
                action="approve",
            )


@pytest.mark.unit
class TestRejectStep:
    """reject_step 服务测试"""
    
    async def test_reject_step_success(self, db_session, mock_data):
        """测试驳回审批"""
        from app.services.approval_service import submit_approval, reject_step
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        result = await reject_step(
            db=db_session,
            user_id=1,
            username="approver",
            flow_id=flow.id,
            comment="需要补充材料",
        )
        
        assert result.status == "rejected"


@pytest.mark.unit
class TestReturnToDraft:
    """return_to_draft 服务测试"""
    
    async def test_return_to_draft_success(self, db_session, mock_data):
        """测试成功退回草稿"""
        from app.services.approval_service import submit_approval, return_to_draft
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        # 退回草稿
        result = await return_to_draft(
            db=db_session,
            user_id=1,
            username="testuser",
            flow_id=flow.id,
            comment="需要修改",
        )
        
        assert result.status == "returned"
        
        # 验证合同状态回退
        stmt = select(Contract).where(Contract.id == created["id"])
        contract_result = await db_session.execute(stmt)
        contract = contract_result.scalar_one()
        assert contract.status == "draft"
    
    async def test_return_to_draft_not_found(self, db_session, mock_data):
        """测试退回不存在的流程"""
        from app.services.approval_service import return_to_draft
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException, match="审批流程不存在"):
            await return_to_draft(
                db=db_session,
                user_id=1,
                username="testuser",
                flow_id=9999,
            )


@pytest.mark.unit
class TestGetPendingApprovals:
    """get_pending_approvals 服务测试"""
    
    async def test_get_pending_approvals(self, db_session, mock_data):
        """测试获取待办审批"""
        from app.services.approval_service import (
            submit_approval, get_pending_approvals
        )
        from app.services.contract_service import create_contract
        
        # 创建并提交审批
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        result = await get_pending_approvals(
            db=db_session,
            user_id=1,
            page=1,
            page_size=20,
        )
        
        assert result["total"] >= 1
        assert len(result["items"]) >= 1
        item = result["items"][0]
        assert item["flow_id"] == flow.id
        assert item["counterparty_name"] == "公司"
        assert item["current_node_name"] == "部门审批"
        assert "ai_risk_level" in item

    async def test_pending_ai_risk_from_latest_review(self, db_session, mock_data):
        """待办列表 AI 风险应优先取最新 ai_reviews.overall_risk_level"""
        from app.services.approval_service import submit_approval, get_pending_approvals
        from app.services.contract_service import create_contract
        from app.models.contract import AIReview

        created = await create_contract(
            title="AI风险待办",
            contract_type="service",
            counterparty_name="测试方",
            creator_id=1,
        )
        await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "simple",
            })(),
        )
        db_session.add(
            AIReview(
                contract_id=created["id"],
                version_id=1,
                review_id="REV-PENDING-001",
                overall_risk_level="medium",
                review_status="ai_done",
            )
        )
        await db_session.commit()

        result = await get_pending_approvals(db=db_session, user_id=1)
        row = next(i for i in result["items"] if i["contract_id"] == created["id"])
        assert row["ai_risk_level"] == "medium"
        assert row["ai_review_status"] == "ai_done"


@pytest.mark.unit
class TestGetApprovalHistory:
    """get_approval_history 服务测试"""
    
    async def test_get_approval_history(self, db_session, mock_data):
        """测试获取审批历史"""
        from app.services.approval_service import (
            submit_approval, approve_step, get_approval_history
        )
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待审批合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        flow = await submit_approval(
            db=db_session,
            user_id=1,
            username="testuser",
            req=type("Req", (), {
                "contract_id": created["id"],
                "flow_type": "standard",
            })(),
        )
        
        # 审批一步
        await approve_step(
            db=db_session,
            user_id=1,
            username="approver",
            flow_id=flow.id,
            action="approve",
            comment="同意",
        )
        
        result = await get_approval_history(
            db=db_session,
            flow_id=flow.id,
        )
        
        assert result["flow_id"] == flow.id
        assert result["total_steps"] == 1
        assert len(result["steps"]) >= 1
        assert result["steps"][0]["action"] == "approve"
