"""
Contract Service Tests
测试 contract_service.py 的 CRUD 操作
"""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import select
from unittest.mock import AsyncMock, MagicMock, patch

# ==============================================================================
# Contract Service Tests
# ==============================================================================

@pytest.mark.unit
class TestCreateContract:
    """create_contract 服务测试"""
    
    async def test_create_contract_success(self, db_session, mock_data):
        """测试成功创建合同"""
        from app.services.contract_service import create_contract
        
        result = await create_contract(
            title="软件开发服务合同",
            contract_type="service",
            counterparty_name="XX科技有限公司",
            counterparty_credit_code="91310115MA1K3XK123",
            amount=100000.00,
            currency="CNY",
            tax_rate=0.06,
            start_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=365),
            content="合同内容...",
            risk_level="medium",
            creator_id=1,
            department_id=1,
        )
        
        assert result["id"] is not None
        assert result["title"] == "软件开发服务合同"
        assert result["counterparty_name"] == "XX科技有限公司"
        assert result["amount"] == 100000.00
        assert result["contract_no"].startswith("CON-")
        assert result["status"] == "draft"
        assert result["current_version_id"] is not None
    
    async def test_create_contract_empty_counterparty(self, db_session, mock_data):
        """测试创建合同时对方名称为空"""
        from app.services.contract_service import create_contract
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="对方单位名称不能为空"):
            await create_contract(
                title="Test",
                contract_type="service",
                counterparty_name="",
                creator_id=1,
            )
    
    async def test_generate_contract_no_format(self, db_session, mock_data):
        """测试合同编号生成格式"""
        from app.services.contract_service import create_contract
        import re
        
        result1 = await create_contract(
            title="Contract 1",
            contract_type="service",
            counterparty_name="Company 1",
            creator_id=1,
        )
        
        result2 = await create_contract(
            title="Contract 2",
            contract_type="service",
            counterparty_name="Company 2",
            creator_id=1,
        )
        
        # 检查格式 CON-YYYYMM-XXXX
        pattern = r"^CON-\d{6}-\d{4}$"
        assert re.match(pattern, result1["contract_no"])
        assert re.match(pattern, result2["contract_no"])
        
        # 检查月份相同
        assert result1["contract_no"][:10] == result2["contract_no"][:10]
        
        # 检查序号递增
        seq1 = int(result1["contract_no"][-4:])
        seq2 = int(result2["contract_no"][-4:])
        assert seq2 == seq1 + 1


@pytest.mark.unit
class TestGetContract:
    """get_contract 服务测试"""
    
    async def test_get_contract_exists(self, db_session, mock_data):
        """测试获取存在的合同"""
        from app.services.contract_service import create_contract, get_contract
        from app.exceptions import BusinessError
        
        # 先创建合同
        created = await create_contract(
            title="测试合同",
            contract_type="service",
            counterparty_name="XX公司",
            creator_id=1,
        )
        
        # 获取合同
        result = await get_contract(created["id"], db=db_session)
        
        assert result["id"] == created["id"]
        assert result["title"] == "测试合同"
        assert result["contract_no"] == created["contract_no"]
    
    async def test_get_contract_not_found(self, db_session, mock_data):
        """测试获取不存在的合同"""
        from app.services.contract_service import get_contract
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="not found"):
            await get_contract(9999, db=db_session)


@pytest.mark.unit
class TestListContracts:
    """list_contracts 服务测试"""
    
    async def test_list_contracts_empty(self, db_session, mock_data):
        """测试空列表"""
        from app.services.contract_service import list_contracts
        
        result = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
        )
        
        assert result["total"] == 0
        assert result["items"] == []
    
    async def test_list_contracts_with_data(self, db_session, mock_data):
        """测试有数据的列表"""
        from app.services.contract_service import create_contract, list_contracts
        
        # 创建多个合同
        for i in range(3):
            await create_contract(
                title=f"合同 {i+1}",
                contract_type=f"type_{i%2}",
                counterparty_name=f"公司 {i+1}",
                creator_id=1,
            )
        
        result = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
        )
        
        assert result["total"] == 3
        assert len(result["items"]) == 3
    
    async def test_list_contracts_filter_status(self, db_session, mock_data):
        """测试按状态过滤"""
        from app.services.contract_service import create_contract, list_contracts
        
        # 创建草稿合同
        await create_contract(
            title="草稿合同",
            contract_type="service",
            counterparty_name="Company",
            creator_id=1,
        )
        
        result = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
            filters={"status": "draft"},
        )
        
        assert result["total"] == 1
    
    async def test_list_contracts_filter_keyword(self, db_session, mock_data):
        """测试关键字搜索"""
        from app.services.contract_service import create_contract, list_contracts
        
        await create_contract(
            title="软件开发合同",
            contract_type="service",
            counterparty_name="XX科技有限公司",
            creator_id=1,
        )
        
        result = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
            filters={"keyword": "软件"},
        )
        
        assert result["total"] == 1


@pytest.mark.unit
class TestDashboardBucketFilters:
    async def test_list_contracts_bucket_executing(self, db_session, mock_data):
        from datetime import date, timedelta

        from app.models.contract import Contract
        from app.services.contract_service import list_contracts

        today = date.today()
        db_session.add_all(
            [
                Contract(
                    contract_no="BKT-EXEC-1",
                    title="执行中",
                    contract_type="service",
                    status="executing",
                    counterparty_name="A",
                    creator_id=1,
                    end_date=today + timedelta(days=60),
                ),
                Contract(
                    contract_no="BKT-EXP-1",
                    title="快到期",
                    contract_type="service",
                    status="sealed",
                    counterparty_name="B",
                    creator_id=1,
                    end_date=today + timedelta(days=10),
                ),
            ]
        )
        await db_session.commit()

        result = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
            filters={"bucket": "executing"},
        )
        assert result["total"] == 1
        assert result["items"][0]["contract_no"] == "BKT-EXEC-1"

    async def test_dashboard_pending_matches_status_filter(self, db_session, mock_data):
        from app.models.contract import Contract
        from app.services.contract_service import list_contracts, list_dashboard_buckets

        db_session.add_all(
            [
                Contract(
                    contract_no="PEND-1",
                    title="待审批1",
                    contract_type="service",
                    status="pending",
                    counterparty_name="A",
                    creator_id=1,
                ),
                Contract(
                    contract_no="PEND-2",
                    title="待审批2",
                    contract_type="service",
                    status="pending",
                    counterparty_name="B",
                    creator_id=1,
                ),
                Contract(
                    contract_no="DRAFT-1",
                    title="草稿",
                    contract_type="service",
                    status="draft",
                    counterparty_name="C",
                    creator_id=1,
                ),
            ]
        )
        await db_session.commit()

        dashboard = await list_dashboard_buckets(db_session)
        listed = await list_contracts(
            db=db_session,
            page=1,
            page_size=20,
            filters={"status": "pending"},
        )
        assert dashboard["stats"]["pending_approval"] == listed["total"] == 2


@pytest.mark.unit
class TestUpdateContract:
    """update_contract 服务测试"""
    
    async def test_update_contract_success(self, db_session, mock_data):
        """测试成功更新合同"""
        from app.services.contract_service import create_contract, update_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="原始合同",
            contract_type="service",
            counterparty_name="原始公司",
            amount=100000.00,
            creator_id=1,
        )
        
        # 更新合同
        result = await update_contract(
            contract_id=created["id"],
            updates={"title": "更新后的合同", "amount": 200000.00},
            db=db_session,
        )
        
        assert result["title"] == "更新后的合同"
        assert result["amount"] == 200000.00
    
    async def test_update_contract_not_draft(self, db_session, mock_data):
        """测试更新非草稿合同"""
        from app.services.contract_service import create_contract, update_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        # 更新状态为 pending
        from app.models.contract import Contract
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "pending"
        await db_session.flush()
        
        with pytest.raises(BusinessError, match="only draft can be edited"):
            await update_contract(
                contract_id=created["id"],
                updates={"title": "更新"},
                db=db_session,
            )
    
    async def test_update_contract_invalid_amount(self, db_session, mock_data):
        """测试更新无效金额"""
        from app.services.contract_service import create_contract, update_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        with pytest.raises(BusinessError, match="合同金额必须大于 0"):
            await update_contract(
                contract_id=created["id"],
                updates={"amount": -100},
                db=db_session,
            )


@pytest.mark.unit
class TestDeleteContract:
    """delete_contract 服务测试"""
    
    async def test_delete_contract_success(self, db_session, mock_data):
        """测试成功删除合同"""
        from app.services.contract_service import create_contract, delete_contract
        
        created = await create_contract(
            title="待删除合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        result = await delete_contract(contract_id=created["id"], db=db_session)
        
        assert result["success"] is True
        assert "deleted" in result["message"]
        
        # 验证已软删除
        from app.services.contract_service import get_contract
        from app.exceptions import BusinessError
        
        with pytest.raises(BusinessError, match="not found"):
            await get_contract(created["id"], db=db_session)
    
    async def test_delete_contract_not_draft(self, db_session, mock_data):
        """测试删除非草稿合同"""
        from app.services.contract_service import create_contract, delete_contract
        from app.exceptions import BusinessError
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        from app.models.contract import Contract
        stmt = select(Contract).where(Contract.id == created["id"])
        result = await db_session.execute(stmt)
        contract = result.scalar_one()
        contract.status = "pending"
        await db_session.flush()
        
        with pytest.raises(BusinessError, match="only draft can be deleted"):
            await delete_contract(contract_id=created["id"], db=db_session)


@pytest.mark.unit
class TestUploadContractFile:
    """upload_contract_file 服务测试"""
    
    async def test_upload_contract_file(self, db_session, mock_data):
        """测试上传合同文件（mock 存储）"""
        from app.services.contract_service import create_contract, upload_contract_file
        
        created = await create_contract(
            title="合同",
            contract_type="service",
            counterparty_name="公司",
            creator_id=1,
        )
        
        result = await upload_contract_file(
            file_path="/tmp/test.pdf",
            file_type="pdf",
            file_size=12345,
            file_hash="abc123",
            contract_id=created["id"],
            version_id=1,
            db=db_session,
        )
        
        assert result["success"] is True
        assert result["contract_id"] == created["id"]
        assert result["version_id"] == 1
