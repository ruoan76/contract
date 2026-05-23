"""
Seal Service Tests
测试用印服务
"""
import pytest
from unittest.mock import patch, AsyncMock

# ==============================================================================
# Seal Service Tests
# ==============================================================================

@pytest.mark.unit
class TestCreateSealRequest:
    """create_seal_request 服务测试"""
    
    async def test_create_seal_request_success(self, db_session, mock_data):
        """测试成功创建用印申请"""
        from app.services.seal_service import create_seal_request
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待用印合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        result = await create_seal_request(
            contract_id=created["id"],
            seal_type="contract_seal",
            seal_method="electronic",
            comment="待用印",
            db=db_session,
        )
        
        assert result["contract_id"] == created["id"]
        assert result["seal_type"] == "contract_seal"
        assert result["status"] == "pending"
    
    async def test_create_seal_request_not_found(self, db_session, mock_data):
        """测试用印不存在的合同"""
        from app.services.seal_service import create_seal_request
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="not found"):
            await create_seal_request(
                contract_id=9999,
                seal_type="contract_seal",
                db=db_session,
            )


@pytest.mark.unit
class TestApproveSeal:
    """approve_seal 服务测试"""
    
    async def test_approve_seal_success(self, db_session, mock_data):
        """测试成功审批用印"""
        from app.services.seal_service import create_seal_request, approve_seal
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待用印合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        seal = await create_seal_request(
            contract_id=created["id"],
            seal_type="contract_seal",
            db=db_session,
        )
        
        result = await approve_seal(
            seal_id=seal["id"],
            approved=True,
            approver_id=2,
            db=db_session,
        )
        
        assert result["status"] == "approved"
        assert result["approver_id"] == 2
    
    async def test_approve_seal_reject(self, db_session, mock_data):
        """测试拒绝用印"""
        from app.services.seal_service import create_seal_request, approve_seal
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待用印合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        seal = await create_seal_request(
            contract_id=created["id"],
            seal_type="contract_seal",
            db=db_session,
        )
        
        result = await approve_seal(
            seal_id=seal["id"],
            approved=False,
            approver_id=2,
            db=db_session,
        )
        
        assert result["status"] == "rejected"
    
    async def test_approve_seal_not_found(self, db_session, mock_data):
        """测试审批不存在的用印记录"""
        from app.services.seal_service import approve_seal
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="not found"):
            await approve_seal(
                seal_id=9999,
                approved=True,
                approver_id=2,
                db=db_session,
            )
    
    async def test_approve_seal_not_pending(self, db_session, mock_data):
        """测试审批已处理的用印记录"""
        from app.services.seal_service import create_seal_request, approve_seal
        from app.services.contract_service import create_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="待用印合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        seal = await create_seal_request(
            contract_id=created["id"],
            seal_type="contract_seal",
            db=db_session,
        )
        
        # 首次审批
        await approve_seal(
            seal_id=seal["id"],
            approved=True,
            approver_id=2,
            db=db_session,
        )
        
        # 再次审批应失败
        with pytest.raises(BusinessError, match="only pending can be approved"):
            await approve_seal(
                seal_id=seal["id"],
                approved=False,
                approver_id=2,
                db=db_session,
            )


@pytest.mark.unit
class TestGetSealRecords:
    """get_seal_records 服务测试"""
    
    async def test_get_seal_records_empty(self, db_session, mock_data):
        """测试空用印记录"""
        from app.services.seal_service import get_seal_records
        
        result = await get_seal_records(contract_id=1, db=db_session)
        
        assert result == []
    
    async def test_get_seal_records_with_data(self, db_session, mock_data):
        """测试有数据的用印记录"""
        from app.services.seal_service import create_seal_request, get_seal_records
        from app.services.contract_service import create_contract
        
        created = await create_contract(
            title="待用印合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 创建多个用印记录
        for i in range(3):
            await create_seal_request(
                contract_id=created["id"],
                seal_type=f"seal_type_{i}",
                db=db_session,
            )
        
        result = await get_seal_records(contract_id=created["id"], db=db_session)
        
        assert len(result) >= 3
