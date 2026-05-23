"""
Audit Service Tests
测试审计服务
"""
import pytest
import json
from unittest.mock import patch, AsyncMock

# ==============================================================================
# Audit Service Tests
# ==============================================================================

@pytest.mark.unit
class TestLogAction:
    """log_action 服务测试"""
    
    async def test_log_action_success(self, db_session, mock_data):
        """测试成功记录审计日志"""
        from app.services.audit_service import log_action
        from app.models.contract import AuditLog
        from sqlalchemy import select
        
        await log_action(
            user_id=1,
            action="create_contract",
            resource_type="contract",
            resource_id=1,
            detail={"title": "Test Contract"},
            db=db_session,
        )
        
        result = await db_session.execute(select(AuditLog).order_by(AuditLog.id.desc()))
        log = result.scalar_one_or_none()
        
        assert log is not None
        assert log.user_id == 1
        assert log.action == "create_contract"
        assert log.resource_type == "contract"
        assert log.status == "success"
    
    async def test_log_action_with_detail(self, db_session, mock_data):
        """测试带详细信息的日志"""
        from app.services.audit_service import log_action
        from app.models.contract import AuditLog
        from sqlalchemy import select
        
        detail = {
            "contract_id": 1,
            "amount": 100000.00,
            "items": ["item1", "item2"],
        }
        
        await log_action(
            user_id=1,
            action="update_contract",
            resource_type="contract",
            resource_id=1,
            detail=detail,
            db=db_session,
        )
        
        result = await db_session.execute(select(AuditLog).order_by(AuditLog.id.desc()))
        log = result.scalar_one_or_none()
        
        assert log is not None
        parsed_detail = json.loads(log.detail)
        assert parsed_detail["contract_id"] == 1
        assert parsed_detail["amount"] == 100000.00


@pytest.mark.unit
class TestGetAuditLogs:
    """get_audit_logs 服务测试"""
    
    async def test_get_audit_logs_empty(self, db_session, mock_data):
        """测试空审计日志列表"""
        from app.services.audit_service import get_audit_logs
        
        result = await get_audit_logs(
            user_id=1,
            db=db_session,
        )
        
        assert result["total"] == 0
        assert result["items"] == []
    
    async def test_get_audit_logs_with_data(self, db_session, mock_data):
        """测试有数据的审计日志列表"""
        from app.services.audit_service import log_action, get_audit_logs
        
        # 创建多个审计日志
        for i in range(3):
            await log_action(
                user_id=1,
                action=f"action_{i}",
                resource_type="contract",
                resource_id=1,
                db=db_session,
            )
        
        result = await get_audit_logs(
            user_id=1,
            page=1,
            page_size=20,
            db=db_session,
        )
        
        assert result["total"] >= 3
        assert len(result["items"]) >= 3
    
    async def test_get_audit_logs_filter_by_action(self, db_session, mock_data):
        """测试按操作动作过滤"""
        from app.services.audit_service import log_action, get_audit_logs
        
        # 创建不同操作的日志
        await log_action(
            user_id=1,
            action="create_contract",
            resource_type="contract",
            resource_id=1,
            db=db_session,
        )
        
        await log_action(
            user_id=1,
            action="update_contract",
            resource_type="contract",
            resource_id=1,
            db=db_session,
        )
        
        # 按动作过滤
        result = await get_audit_logs(
            user_id=1,
            action="create_contract",
            db=db_session,
        )
        
        assert result["total"] >= 1
        assert result["items"][0]["action"] == "create_contract"
    
    async def test_get_audit_logs_filter_by_resource_type(self, db_session, mock_data):
        """测试按资源类型过滤"""
        from app.services.audit_service import log_action, get_audit_logs
        
        # 创建不同资源类型的日志
        await log_action(
            user_id=1,
            action="action1",
            resource_type="contract",
            resource_id=1,
            db=db_session,
        )
        
        await log_action(
            user_id=1,
            action="action2",
            resource_type="approval",
            resource_id=1,
            db=db_session,
        )
        
        # 按资源类型过滤
        result = await get_audit_logs(
            user_id=1,
            resource_type="contract",
            db=db_session,
        )
        
        assert result["total"] >= 1
        assert result["items"][0]["resource_type"] == "contract"
