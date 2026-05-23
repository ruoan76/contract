"""
Archive Service Tests
测试归档服务
"""
import pytest
from unittest.mock import patch, AsyncMock

# ==============================================================================
# Archive Service Tests
# ==============================================================================

@pytest.mark.unit
class TestArchiveContract:
    """archive_contract 服务测试"""
    
    async def test_archive_contract_success(self, db_session, mock_data):
        """测试成功归档合同"""
        from app.services.archive_service import archive_contract
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        from sqlalchemy import select
        
        # 创建合同
        created = await create_contract(
            title="待归档合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 更新合同状态为 approved
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "approved"
        await db_session.flush()
        
        # 归档合同
        result = await archive_contract(
            contract_id=created["id"],
            location="/archive/2024/contract_001",
            archived_by=1,
            db=db_session,
        )
        
        assert result["contract_id"] == created["id"]
        assert result["status"] == "archived"
        assert result["archive_location"] == "/archive/2024/contract_001"
        assert result["archived_by"] == 1
    
    async def test_archive_contract_not_found(self, db_session, mock_data):
        """测试归档不存在的合同"""
        from app.services.archive_service import archive_contract
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="not found"):
            await archive_contract(
                contract_id=9999,
                location="/archive/test",
                archived_by=1,
                db=db_session,
            )
    
    async def test_archive_contract_not_approved(self, db_session, mock_data):
        """测试归档非审批通过的合同"""
        from app.services.archive_service import archive_contract
        from app.services.contract_service import create_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 状态是 draft，不是 approved
        with pytest.raises(BusinessError, match="only approved/signed/sealed can be archived"):
            await archive_contract(
                contract_id=created["id"],
                location="/archive/test",
                archived_by=1,
                db=db_session,
            )
    
    async def test_archive_contract_already_archived(self, db_session, mock_data):
        """测试重复归档"""
        from app.services.archive_service import archive_contract
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        from app.exceptions import BusinessError
        from sqlalchemy import select
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 更新状态为 approved
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "approved"
        await db_session.flush()
        
        # 首次归档
        await archive_contract(
            contract_id=created["id"],
            location="/archive/test",
            archived_by=1,
            db=db_session,
        )
        
        # 重复归档
        with pytest.raises(BusinessError, match="is already archived"):
            await archive_contract(
                contract_id=created["id"],
                location="/archive/test2",
                archived_by=1,
                db=db_session,
            )


@pytest.mark.unit
class TestGetArchiveRecords:
    """get_archive_records 服务测试"""
    
    async def test_get_archive_records_empty(self, db_session, mock_data):
        """测试空归档列表"""
        from app.services.archive_service import get_archive_records
        
        result = await get_archive_records(db=db_session)
        
        assert result == []
    
    async def test_get_archive_records_with_data(self, db_session, mock_data):
        """测试有数据的归档列表"""
        from app.services.archive_service import archive_contract, get_archive_records
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        from sqlalchemy import select
        
        # 创建并归档合同
        created = await create_contract(
            title="待归档合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 更新状态为 approved
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "approved"
        await db_session.flush()
        
        # 归档
        await archive_contract(
            contract_id=created["id"],
            location="/archive/test",
            archived_by=1,
            db=db_session,
        )
        
        # 获取归档记录
        result = await get_archive_records(db=db_session)
        
        assert len(result) >= 1
        assert result[0]["contract_id"] == created["id"]
        assert result[0]["archive_location"] == "/archive/test"
    
    async def test_get_archive_records_filter_by_type(self, db_session, mock_data):
        """测试按合同类型过滤"""
        from app.services.archive_service import archive_contract, get_archive_records
        from app.services.contract_service import create_contract
        from app.models.contract import Contract
        from sqlalchemy import select
        
        # 创建不同类型的合同
        for i, contract_type in enumerate(["service", "purchase"]):
            created = await create_contract(
                title=f"合同 {i+1}",
                contract_type=contract_type,
                counterparty_name=f"公司 {i+1}",
                creator_id=1,
            )
            
            stmt = select(Contract).where(Contract.id == created["id"])
            result = await db_session.execute(stmt)
            contract = result.scalar_one()
            contract.status = "approved"
            await db_session.flush()
            
            await archive_contract(
                contract_id=created["id"],
                location=f"/archive/test{i}",
                archived_by=1,
                db=db_session,
            )
        
        # 按类型过滤
        result = await get_archive_records(
            filters={"contract_type": "service"},
            db=db_session,
        )
        
        assert len(result) >= 1
        assert all(item["contract_type"] == "service" for item in result)
