"""
用印领域服务
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import SealRecord, Contract

logger = logging.getLogger(__name__)


async def create_seal_request(
    contract_id: int,
    seal_type: str,
    operator_id: int = None,
    seal_method: Optional[str] = None,
    comment: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    创建用印申请
    
    Args:
        contract_id: 合同ID
        seal_type: 用印类型（公章|合同章|财务章）
        operator_id: 操作人ID
        seal_method: 用印方式（电子|物理）
        comment: 备注
        db: 数据库会话（可选）
        
    Returns:
        dict 用印申请信息
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        # 查询合同
        result = await session.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")
        
        # 创建用印记录
        seal_record = SealRecord(
            contract_id=contract_id,
            contract_no=contract.contract_no,
            seal_type=seal_type,
            seal_method=seal_method,
            status="pending",
            comment=comment,
        )
        session.add(seal_record)
        await session.flush()
        
        await session.refresh(seal_record)
        
        payload = {
            "id": seal_record.id,
            "contract_id": seal_record.contract_id,
            "contract_no": seal_record.contract_no,
            "seal_type": seal_record.seal_type,
            "seal_method": seal_record.seal_method,
            "status": seal_record.status,
            "comment": seal_record.comment,
            "created_at": seal_record.created_at.isoformat() if seal_record.created_at else None,
        }
        if use_own_session:
            await session.commit()
        return payload
    except Exception:
        if use_own_session:
            await session.rollback()
        raise
    finally:
        if use_own_session:
            await session.close()


async def approve_seal(
    seal_id: int,
    approved: bool,
    approver_id: int,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    审批用印
    
    Args:
        seal_id: 用印记录ID
        approved: 是否批准
        approver_id: 审批人ID
        db: 数据库会话（可选）
        
    Returns:
        dict 审批结果
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        # 查询用印记录
        result = await session.execute(
            select(SealRecord).where(SealRecord.id == seal_id)
        )
        record = result.scalar_one_or_none()
        
        if not record:
            raise BusinessError(f"SealRecord {seal_id} not found")
        
        # 验证状态
        if record.status != "pending":
            raise BusinessError(f"SealRecord {seal_id} status is {record.status}, only pending can be approved")
        
        current_time = datetime.now()
        
        if approved:
            record.status = "approved"
            # 用印批准后更新合同状态
            contract_result = await session.execute(
                select(Contract).where(Contract.id == record.contract_id)
            )
            contract = contract_result.scalar_one_or_none()
            if contract and contract.status == "approved":
                from app.services.contract_state import transition_contract
                await transition_contract(session, contract, "sealed", approval_status="seal_pending")
        else:
            record.status = "rejected"
        
        record.approver_id = approver_id
        record.approval_time = current_time
        await session.flush()
        
        await session.refresh(record)
        
        payload = {
            "id": record.id,
            "status": record.status,
            "approver_id": record.approver_id,
            "approval_time": record.approval_time.isoformat() if record.approval_time else None,
        }
        if use_own_session:
            await session.commit()
        return payload
    except Exception:
        if use_own_session:
            await session.rollback()
        raise
    finally:
        if use_own_session:
            await session.close()


async def get_seal_records(
    contract_id: int,
    db: Optional[AsyncSession] = None,
) -> list:
    """
    获取用印记录列表
    
    Args:
        contract_id: 合同ID
        db: 数据库会话（可选）
        
    Returns:
        list 用印记录列表
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        result = await session.execute(
            select(SealRecord)
            .where(SealRecord.contract_id == contract_id)
            .order_by(SealRecord.created_at.desc())
        )
        records = result.scalars().all()
        
        return [
            {
                "id": r.id,
                "contract_id": r.contract_id,
                "contract_no": r.contract_no,
                "seal_type": r.seal_type,
                "seal_method": r.seal_method,
                "status": r.status,
                "approver_id": r.approver_id,
                "approver_name": r.approver_name,
                "approval_time": r.approval_time.isoformat() if r.approval_time else None,
                "seal_time": r.seal_time.isoformat() if r.seal_time else None,
                "seal_operator": r.seal_operator,
                "comment": r.comment,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    finally:
        if use_own_session:
            await session.close()
