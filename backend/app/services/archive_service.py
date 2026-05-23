"""
归档管理服务
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import Contract

logger = logging.getLogger(__name__)


async def archive_contract(
    contract_id: int,
    location: str,
    archived_by: int,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    归档合同
    
    Args:
        contract_id: 合同ID
        location: 归档位置
        archived_by: 归档人ID
        db: 数据库会话（可选）
        
    Returns:
        dict 归档结果
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
        
        # 验证是否已归档
        if contract.status == "archived" or contract.archive_date:
            raise BusinessError(f"Contract {contract_id} is already archived")

        # 验证合同状态
        if contract.status not in ["approved", "signed", "sealed"]:
            raise BusinessError(
                f"Contract {contract_id} status is {contract.status}, "
                "only approved/signed/sealed can be archived"
            )
        
        current_time = datetime.now()
        
        # 更新合同归档信息
        contract.archive_date = datetime.now().date()
        contract.archive_location = location
        from app.services.contract_state import transition_contract
        await transition_contract(session, contract, "archived", approval_status="done")
        await session.flush()
        
        await session.refresh(contract)
        
        payload = {
            "contract_id": contract.id,
            "contract_no": contract.contract_no,
            "archive_date": current_time.isoformat(),
            "archive_location": location,
            "archived_by": archived_by,
            "status": "archived",
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


async def get_archive_records(
    filters: Optional[dict] = None,
    db: Optional[AsyncSession] = None,
) -> list:
    """
    获取归档记录列表
    
    Args:
        filters: 过滤条件
        db: 数据库会话（可选）
        
    Returns:
        list 归档记录列表
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        conditions = [Contract.archive_date.isnot(None)]
        
        if filters:
            if filters.get("contract_type"):
                conditions.append(Contract.contract_type == filters["contract_type"])
            if filters.get("start_date") and filters.get("end_date"):
                conditions.append(
                    Contract.archive_date.between(
                        filters["start_date"], filters["end_date"]
                    )
                )
        
        result = await session.execute(
            select(Contract)
            .where(*conditions)
            .order_by(Contract.archive_date.desc())
        )
        contracts = result.scalars().all()
        
        return [
            {
                "contract_id": c.id,
                "contract_no": c.contract_no,
                "title": c.title,
                "contract_type": c.contract_type,
                "counterparty_name": c.counterparty_name,
                "amount": c.amount,
                "archive_date": c.archive_date.isoformat() if c.archive_date else None,
                "archive_location": c.archive_location,
            }
            for c in contracts
        ]
    finally:
        if use_own_session:
            await session.close()
