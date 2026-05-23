"""
Contracts model tests
测试 Contract、ContractVersion、ApprovalFlow、ApprovalStep、AIReview、RiskAlert、AuditLog、Role、Department、SealRecord、ContractLedger 模型
"""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ==============================================================================
# Contract Model Tests
# ==============================================================================

@pytest.mark.unit
class TestContractModel:
    """Contract 模型测试"""
    
    async def test_contract_creation(self, db_session, mock_data):
        """测试 Contract 创建"""
        from app.models.contract import Contract
        
        contract_data = mock_data.contract()
        contract = Contract(**contract_data)
        
        db_session.add(contract)
        await db_session.flush()
        await db_session.refresh(contract)
        
        assert contract.id is not None
        assert contract.contract_no == contract_data["contract_no"]
        assert contract.title == contract_data["title"]
        assert contract.counterparty_name == contract_data["counterparty_name"]
        assert contract.status == "draft"
    
    async def test_contract_unique_constraint(self, db_session, mock_data):
        """测试 Contract 编号唯一性约束"""
        from app.models.contract import Contract
        
        contract1 = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract1)
        await db_session.flush()
        
        contract2 = Contract(
            contract_no="CON-202401-0001",
            title="Duplicate Contract",
            contract_type="service",
            counterparty_name="Test Corp 2",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract2)
        
        with pytest.raises(Exception):
            await db_session.flush()
    
    async def test_contract_index(self, db_session, mock_data):
        """测试 Contract 索引存在（SQLite 兼容）"""
        from sqlalchemy import text

        result = await db_session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='contracts'"
            )
        )
        indexes = [row[0] for row in result.fetchall()]

        expected_indexes = [
            "idx_contract_no",
            "idx_type",
            "idx_status",
            "idx_creator",
            "idx_department",
            "idx_counterparty",
            "idx_risk_level",
        ]

        for idx in expected_indexes:
            assert idx in indexes


@pytest.mark.unit
class TestContractVersionModel:
    """ContractVersion 模型测试"""
    
    async def test_contract_version_creation(self, db_session, mock_data):
        """测试 ContractVersion 创建"""
        from app.models.contract import Contract, ContractVersion
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        version = ContractVersion(
            contract_id=contract.id,
            version=1,
            title="Test Contract v1",
            content="Contract content",
            creator_id=1,
        )
        db_session.add(version)
        await db_session.flush()
        
        assert version.id is not None
        assert version.contract_id == contract.id
        assert version.version == 1
    
    async def test_contract_version_cascade_delete(self, db_session, mock_data):
        """测试 ContractVersion 级联删除"""
        from app.models.contract import Contract, ContractVersion
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        version = ContractVersion(
            contract_id=contract.id,
            version=1,
            title="Test Contract v1",
            content="Contract content",
            creator_id=1,
        )
        db_session.add(version)
        await db_session.flush()
        
        await db_session.delete(contract)
        await db_session.flush()
        
        # 验证版本被级联删除
        result = await db_session.execute(
            select(ContractVersion).where(ContractVersion.id == version.id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.unit
class TestApprovalFlowModel:
    """ApprovalFlow 模型测试"""
    
    async def test_approval_flow_creation(self, db_session, mock_data):
        """测试 ApprovalFlow 创建"""
        from app.models.contract import Contract, ApprovalFlow
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        flow = ApprovalFlow(
            contract_id=contract.id,
            flow_type="standard",
            status="approving",
            current_node_id="dept_approval",
            current_step=0,
            total_steps=4,
            start_time=datetime.now(),
        )
        db_session.add(flow)
        await db_session.flush()
        
        assert flow.id is not None
        assert flow.contract_id == contract.id
        assert flow.status == "approving"
    
    async def test_approval_flow_end_time(self, db_session, mock_data):
        """测试 ApprovalFlow 结束时间"""
        from app.models.contract import Contract, ApprovalFlow
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
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
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=2),
            duration_hours=2.0,
        )
        db_session.add(flow)
        await db_session.flush()
        
        assert flow.end_time is not None
        assert flow.duration_hours == 2.0


@pytest.mark.unit
class TestApprovalStepModel:
    """ApprovalStep 模型测试"""
    
    async def test_approval_step_creation(self, db_session, mock_data):
        """测试 ApprovalStep 创建"""
        from app.models.contract import Contract, ApprovalFlow, ApprovalStep
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        flow = ApprovalFlow(
            contract_id=contract.id,
            flow_type="standard",
            status="approving",
            current_node_id="dept_approval",
            current_step=0,
            total_steps=4,
            start_time=datetime.now(),
        )
        db_session.add(flow)
        await db_session.flush()
        
        step = ApprovalStep(
            flow_id=flow.id,
            step_number=1,
            node_id="dept_approval",
            node_name="部门审批",
            approver_id=2,
            approver_name="张三",
            status="completed",
            action="approve",
            comment="同意",
            start_time=datetime.now(),
            complete_time=datetime.now(),
            duration_hours=1.0,
        )
        db_session.add(step)
        await db_session.flush()
        
        assert step.id is not None
        assert step.flow_id == flow.id
        assert step.status == "completed"
        assert step.action == "approve"
    
    async def test_approval_step_cascade_delete(self, db_session, mock_data):
        """测试 ApprovalStep 级联删除"""
        from app.models.contract import Contract, ApprovalFlow, ApprovalStep
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        flow = ApprovalFlow(
            contract_id=contract.id,
            flow_type="standard",
            status="approving",
            current_node_id="dept_approval",
            current_step=0,
            total_steps=4,
            start_time=datetime.now(),
        )
        db_session.add(flow)
        await db_session.flush()
        
        step = ApprovalStep(
            flow_id=flow.id,
            step_number=1,
            node_id="dept_approval",
            node_name="部门审批",
            approver_id=2,
            approver_name="张三",
            status="completed",
            start_time=datetime.now(),
            complete_time=datetime.now(),
        )
        db_session.add(step)
        await db_session.flush()
        
        await db_session.delete(flow)
        await db_session.flush()
        
        result = await db_session.execute(
            select(ApprovalStep).where(ApprovalStep.id == step.id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.unit
class TestAIReviewModel:
    """AIReview 模型测试"""
    
    async def test_ai_review_creation(self, db_session, mock_data):
        """测试 AIReview 创建"""
        from app.models.contract import Contract, AIReview
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        review = AIReview(
            contract_id=contract.id,
            version_id=1,
            review_id="REV-001",
            overall_risk_level="medium",
            overall_risk_score=45.5,
            recommendation="建议补充违约条款",
            clause_reviews="[]",
            rule_violations="[]",
            summary="{}",
            model_version="Qwen3.6-35B-A3B",
            review_duration_seconds=120,
            review_status="ai_done",
        )
        db_session.add(review)
        await db_session.flush()
        
        assert review.id is not None
        assert review.contract_id == contract.id
        assert review.overall_risk_level == "medium"


@pytest.mark.unit
class TestRiskAlertModel:
    """RiskAlert 模型测试"""
    
    async def test_risk_alert_creation(self, db_session, mock_data):
        """测试 RiskAlert 创建"""
        from app.models.contract import Contract, RiskAlert
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        alert = RiskAlert(
            contract_id=contract.id,
            alert_type="high_risk_clause",
            alert_level="high",
            title="违约条款过重",
            message="违约金比例超过法定上限",
            source="ai",
            source_detail='{"clause": "第5条", "issue": "违约金"}',
            status="pending",
            related_clause="违约责任",
            legal_basis="民法典第585条",
        )
        db_session.add(alert)
        await db_session.flush()
        
        assert alert.id is not None
        assert alert.alert_level == "high"
        assert alert.status == "pending"
    
    async def test_risk_alert_status_update(self, db_session, mock_data):
        """测试 RiskAlert 状态更新"""
        from app.models.contract import Contract, RiskAlert
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="draft",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        alert = RiskAlert(
            contract_id=contract.id,
            alert_type="high_risk_clause",
            alert_level="high",
            title="违约条款过重",
            message="违约金比例超过法定上限",
            source="ai",
            status="pending",
        )
        db_session.add(alert)
        await db_session.flush()
        
        alert.status = "resolved"
        alert.handler_id = 1
        alert.handle_comment = "已修改违约条款"
        await db_session.flush()
        
        assert alert.status == "resolved"
        assert alert.handler_id == 1


@pytest.mark.unit
class TestAuditLogModel:
    """AuditLog 模型测试"""
    
    async def test_audit_log_creation(self, db_session, mock_data):
        """测试 AuditLog 创建"""
        from app.models.contract import AuditLog
        
        log = AuditLog(
            user_id=1,
            username="admin",
            action="create_contract",
            resource_type="contract",
            resource_id=1,
            resource_name="Test Contract",
            detail='{"title": "Test Contract"}',
            ip_address="127.0.0.1",
            user_agent="TestClient",
            status="success",
        )
        db_session.add(log)
        await db_session.flush()
        
        assert log.id is not None
        assert log.action == "create_contract"
        assert log.status == "success"


@pytest.mark.unit
class TestRoleModel:
    """Role 模型测试"""
    
    async def test_role_creation(self, db_session, mock_data):
        """测试 Role 创建"""
        from app.models.contract import Role
        
        role = Role(
            name="管理员",
            code="admin",
            description="系统管理员",
            permissions='{"read": true, "write": true, "delete": true}',
            status=1,
        )
        db_session.add(role)
        await db_session.flush()
        
        assert role.id is not None
        assert role.code == "admin"
        assert role.status == 1


@pytest.mark.unit
class TestDepartmentModel:
    """Department 模型测试"""
    
    async def test_department_creation(self, db_session, mock_data):
        """测试 Department 创建"""
        from app.models.contract import Department
        
        dept = Department(
            name="技术部",
            parent_id=0,
            level=1,
            path="/1",
            status=1,
        )
        db_session.add(dept)
        await db_session.flush()
        
        assert dept.id is not None
        assert dept.name == "技术部"
        assert dept.parent_id == 0
    
    async def test_department_hierarchy(self, db_session, mock_data):
        """测试部门层级关系"""
        from app.models.contract import Department
        
        parent_dept = Department(
            name="技术中心",
            parent_id=0,
            level=1,
            path="/1",
            status=1,
        )
        db_session.add(parent_dept)
        await db_session.flush()
        
        child_dept = Department(
            name="研发部",
            parent_id=parent_dept.id,
            level=2,
            path="/1/2",
            status=1,
        )
        db_session.add(child_dept)
        await db_session.flush()
        
        assert child_dept.parent_id == parent_dept.id
        assert child_dept.level == 2


@pytest.mark.unit
class TestSealRecordModel:
    """SealRecord 模型测试"""
    
    async def test_seal_record_creation(self, db_session, mock_data):
        """测试 SealRecord 创建"""
        from app.models.contract import Contract, SealRecord
        
        contract = Contract(
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            status="approved",
            creator_id=1,
        )
        db_session.add(contract)
        await db_session.flush()
        
        seal = SealRecord(
            contract_id=contract.id,
            contract_no=contract.contract_no,
            seal_type="contract_seal",
            seal_method="electronic",
            status="pending",
            comment="待审批",
        )
        db_session.add(seal)
        await db_session.flush()
        
        assert seal.id is not None
        assert seal.status == "pending"


@pytest.mark.unit
class TestContractLedgerModel:
    """ContractLedger 模型测试"""
    
    async def test_contract_ledger_creation(self, db_session, mock_data):
        """测试 ContractLedger 创建"""
        from app.models.contract import ContractLedger
        
        ledger = ContractLedger(
            contract_id=1,
            contract_no="CON-202401-0001",
            title="Test Contract",
            contract_type="service",
            counterparty_name="Test Corp",
            amount=100000.00,
            status="approved",
            approval_status="approved",
            risk_level="medium",
            creator_name="admin",
            department_name="技术部",
            created_at=datetime.now(),
        )
        db_session.add(ledger)
        await db_session.flush()
        
        assert ledger.id is not None
        assert ledger.amount == 100000.00
