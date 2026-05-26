"""
合同领域服务 - CRUD
"""
import logging
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import async_session
from app.exceptions import BusinessError
from app.models.contract import Contract, ContractVersion
from app.services.contract_parse_service import _guess_file_type, extract_bytes_to_text

logger = logging.getLogger(__name__)

# 合同编号格式：CON-YYYYMM-XXXX
CONTRACT_NO_PREFIX = "CON"

# 看板「执行中」桶：与 contract-status-dictionary / list_dashboard_buckets 一致
EXECUTING_BUCKET_STATUSES = frozenset({"executing", "approved", "sealed", "signed"})
DASHBOARD_EXPIRING_DAYS = 30


def _dashboard_date_range() -> tuple[date, date]:
    from datetime import timedelta

    today = date.today()
    return today, today + timedelta(days=DASHBOARD_EXPIRING_DAYS)


def classify_contract_bucket(
    contract: Contract,
    today: date | None = None,
    expiring_threshold: date | None = None,
) -> str | None:
    """将合同归入看板桶：expired / expiring_soon / executing；其余返回 None。"""
    if today is None or expiring_threshold is None:
        today, expiring_threshold = _dashboard_date_range()
    end = contract.end_date
    if end is not None and end < today:
        return "expired"
    if end is not None and end <= expiring_threshold:
        return "expiring_soon"
    if contract.status == "executing":
        return "executing"
    if contract.status in EXECUTING_BUCKET_STATUSES and (end is None or end > today):
        return "executing"
    return None


def _bucket_filter_conditions(bucket: str, today: date, expiring_threshold: date) -> list:
    """列表 API bucket 参数，与看板三栏口径一致。"""
    from sqlalchemy import or_

    if bucket == "expired":
        return [
            Contract.end_date.isnot(None),
            Contract.end_date < today,
        ]
    if bucket == "expiring_soon":
        return [
            Contract.end_date.isnot(None),
            Contract.end_date >= today,
            Contract.end_date <= expiring_threshold,
        ]
    if bucket == "executing":
        return [
            or_(Contract.end_date.is_(None), Contract.end_date >= today),
            or_(Contract.end_date.is_(None), Contract.end_date > expiring_threshold),
            Contract.status.in_(tuple(EXECUTING_BUCKET_STATUSES)),
        ]
    raise BusinessError(f"未知看板桶: {bucket}")


async def _generate_contract_no(db: AsyncSession) -> str:
    """
    生成合同编号: CON-YYYYMM-XXXX
    
    Args:
        db: 数据库会话
        
    Returns:
        合同编号字符串
    """
    today = date.today()
    prefix = f"{CONTRACT_NO_PREFIX}-{today:%Y%m}-"
    
    result = await db.execute(
        select(func.count(Contract.id)).where(
            Contract.contract_no.like(f"{prefix}%")
        )
    )
    count = result.scalar() or 0
    seq = count + 1
    return f"{prefix}{seq:04d}"


async def create_contract(
    title: str,
    contract_type: str,
    counterparty_name: str,
    counterparty_type: Optional[str] = None,
    counterparty_credit_code: Optional[str] = None,
    counterparty_id: Optional[int] = None,
    amount: Optional[float] = None,
    currency: str = "CNY",
    tax_rate: Optional[float] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    content: Optional[str] = None,
    risk_level: str = "low",
    file_path: Optional[str] = None,
    file_type: Optional[str] = None,
    file_size: Optional[int] = None,
    file_hash: Optional[str] = None,
    creator_id: int = None,
    department_id: Optional[int] = None,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    创建合同
    
    Args:
        title: 合同名称
        contract_type: 合同类型
        counterparty_name: 对方单位名称
        counterparty_type: 对方类型
        counterparty_credit_code: 统一社会信用代码
        amount: 合同金额
        currency: 币种
        tax_rate: 税率
        start_date: 开始日期
        end_date: 结束日期
        content: 合同内容
        risk_level: 风险等级
        file_path: 文件路径（MinIO路径）
        file_type: 文件类型
        file_size: 文件大小
        file_hash: 文件哈希
        creator_id: 创建人ID
        department_id: 所属部门ID
        
    Returns:
        dict 包含合同信息
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db

    try:
        # 验证对方名称
        if not counterparty_name or not counterparty_name.strip():
            raise BusinessError("对方单位名称不能为空")

        # 黑名单校验
        from app.services.counterparty_service import check_blacklist
        await check_blacklist(
            session,
            counterparty_id=counterparty_id,
            credit_code=counterparty_credit_code,
            counterparty_name=counterparty_name if not counterparty_id else None,
        )

        # 若指定 counterparty_id，填充快照字段
        if counterparty_id:
            from app.models.counterparty import Counterparty
            cp = await session.get(Counterparty, counterparty_id)
            if cp:
                counterparty_name = cp.name
                counterparty_credit_code = counterparty_credit_code or cp.credit_code

        contract_no = await _generate_contract_no(session)

        contract = Contract(
            contract_no=contract_no,
            title=title,
            contract_type=contract_type,
            status="draft",
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            counterparty_type=counterparty_type,
            counterparty_credit_code=counterparty_credit_code,
            amount=amount,
            currency=currency,
            tax_rate=tax_rate,
            start_date=start_date,
            end_date=end_date,
            risk_level=risk_level,
            content=content,
            creator_id=creator_id,
            department_id=department_id,
        )
        
        session.add(contract)
        await session.flush()
        
        # 创建初始版本
        version = ContractVersion(
            contract_id=contract.id,
            version=1,
            title=title,
            content=content,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            creator_id=creator_id,
        )
        
        session.add(version)
        await session.flush()
        
        # 关联当前版本
        contract.current_version_id = version.id
        await session.flush()

        if use_own_session:
            await session.commit()
        await session.refresh(contract)

        from app.services.flow_match_service import match_flow_type
        flow_type = match_flow_type(amount, contract_type)

        return {
            "id": contract.id,
            "contract_no": contract.contract_no,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "flow_type": flow_type,
            "counterparty_name": contract.counterparty_name,
            "counterparty_id": contract.counterparty_id,
            "counterparty_type": contract.counterparty_type,
            "counterparty_credit_code": contract.counterparty_credit_code,
            "amount": contract.amount,
            "currency": contract.currency,
            "tax_rate": contract.tax_rate,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "risk_level": contract.risk_level,
            "content": contract.content,
            "creator_id": contract.creator_id,
            "department_id": contract.department_id,
            "current_version_id": contract.current_version_id,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
        }
    except Exception:
        if use_own_session:
            await session.rollback()
        raise
    finally:
        if use_own_session:
            await session.close()


async def get_contract(contract_id: int, db: Optional[AsyncSession] = None) -> dict:
    """
    获取合同详情
    
    Args:
        contract_id: 合同ID
        db: 数据库会话（可选，如果提供则使用，否则创建新会话）
        
    Returns:
        dict 包含合同及关联信息
    """
    from app.models.contract import User, Department, ApprovalFlow, ApprovalStep
    
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        result = await session.execute(
            select(Contract)
            .outerjoin(User, Contract.creator_id == User.id)
            .outerjoin(Department, Contract.department_id == Department.id)
            .outerjoin(ApprovalFlow, Contract.current_flow_id == ApprovalFlow.id)
            .where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")
        
        if contract.status == "deleted":
            raise BusinessError(f"Contract {contract_id} not found")
        
        # 获取当前版本
        version = None
        if contract.current_version_id:
            ver_result = await session.execute(
                select(ContractVersion).where(
                    ContractVersion.id == contract.current_version_id
                )
            )
            version = ver_result.scalar_one_or_none()
        
        # 获取审批流
        approval_flow = None
        if contract.current_flow_id:
            flow_result = await session.execute(
                select(ApprovalFlow).where(
                    ApprovalFlow.id == contract.current_flow_id
                )
            )
            approval_flow = flow_result.scalar_one_or_none()
        
        result_dict = {
            "id": contract.id,
            "contract_no": contract.contract_no,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "counterparty_name": contract.counterparty_name,
            "counterparty_id": contract.counterparty_id,
            "counterparty_type": contract.counterparty_type,
            "counterparty_credit_code": contract.counterparty_credit_code,
            "amount": contract.amount,
            "currency": contract.currency,
            "tax_rate": contract.tax_rate,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "approval_status": contract.approval_status,
            "sign_date": contract.sign_date.isoformat() if contract.sign_date else None,
            "sign_method": contract.sign_method,
            "archive_date": contract.archive_date.isoformat() if contract.archive_date else None,
            "archive_location": contract.archive_location,
            "creator_id": contract.creator_id,
            "department_id": contract.department_id,
            "risk_level": contract.risk_level,
            "content": contract.content,
            "current_version_id": contract.current_version_id,
            "current_flow_id": contract.current_flow_id,
            "creator_name": contract.User.real_name if hasattr(contract, "User") and contract.User else None,
            "department_name": contract.Department.name if hasattr(contract, "Department") and contract.Department else None,
            "current_version_content": version.content if version else None,
            "current_version_number": version.version if version else None,
            "approval_flow_id": approval_flow.id if approval_flow else None,
            "approval_flow_status": approval_flow.status if approval_flow else None,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        }
        
        return result_dict
    finally:
        if use_own_session:
            await session.close()


async def list_contracts(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    filters: Optional[dict] = None,
) -> dict:
    """
    获取合同列表（分页 + 过滤）
    
    Args:
        db: 数据库会话
        page: 页码
        page_size: 每页数量
        filters: 过滤条件 - status, type, risk_level, keyword, department_id, scope
        
    Returns:
        dict 包含分页和列表数据
    """
    from sqlalchemy import or_
    from app.models.contract import User, Department
    
    conditions = [Contract.status != "deleted"]
    
    if filters:
        scope = filters.get("scope")
        if scope == "mine" and filters.get("creator_id"):
            conditions.append(Contract.creator_id == filters["creator_id"])
        elif scope == "department" and filters.get("user_department_id"):
            conditions.append(Contract.department_id == filters["user_department_id"])
        if filters.get("status"):
            conditions.append(Contract.status == filters["status"])
        if filters.get("type"):
            conditions.append(Contract.contract_type == filters["type"])
        if filters.get("risk_level"):
            conditions.append(Contract.risk_level == filters["risk_level"])
        if filters.get("keyword"):
            conditions.append(
                or_(
                    Contract.title.contains(filters["keyword"]),
                    Contract.counterparty_name.contains(filters["keyword"]),
                    Contract.contract_no.contains(filters["keyword"]),
                )
            )
        if filters.get("department_id"):
            conditions.append(Contract.department_id == filters["department_id"])
        bucket = filters.get("bucket")
        if bucket:
            today, expiring_threshold = _dashboard_date_range()
            conditions.extend(_bucket_filter_conditions(bucket, today, expiring_threshold))
    
    # 查询总数
    count_query = select(func.count()).select_from(Contract).where(*conditions)
    total = await db.scalar(count_query)
    
    # 查询列表
    query = (
        select(
            Contract,
            User.real_name.label("creator_name"),
            Department.name.label("department_name"),
        )
        .outerjoin(User, Contract.creator_id == User.id)
        .outerjoin(Department, Contract.department_id == Department.id)
        .where(*conditions)
        .order_by(Contract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    contracts = []
    for row in rows:
        contract, creator_name, department_name = row
        contracts.append({
            "id": contract.id,
            "contract_no": contract.contract_no,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "counterparty_name": contract.counterparty_name,
            "amount": contract.amount,
            "risk_level": contract.risk_level,
            "creator_id": contract.creator_id,
            "creator_name": creator_name,
            "department_id": contract.department_id,
            "department_name": department_name,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
        })
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": contracts,
    }


async def update_contract(
    contract_id: int,
    updates: dict,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    更新合同
    
    Args:
        contract_id: 合同ID
        updates: 更新数据
        db: 数据库会话（可选）
        
    Returns:
        dict 更新后的合同信息
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        result = await session.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")
        
        # 验证状态 - 仅草稿可编辑
        if contract.status != "draft":
            raise BusinessError(f"Contract {contract_id} status is {contract.status}, only draft can be edited")
        
        # 验证金额
        if updates.get("amount") is not None and updates["amount"] <= 0:
            raise BusinessError("合同金额必须大于 0")
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(contract, key):
                setattr(contract, key, value)
        
        await session.flush()
        
        await session.refresh(contract)
        
        result = {
            "id": contract.id,
            "contract_no": contract.contract_no,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "counterparty_name": contract.counterparty_name,
            "counterparty_id": contract.counterparty_id,
            "counterparty_type": contract.counterparty_type,
            "counterparty_credit_code": contract.counterparty_credit_code,
            "amount": contract.amount,
            "currency": contract.currency,
            "tax_rate": contract.tax_rate,
            "start_date": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": contract.end_date.isoformat() if contract.end_date else None,
            "risk_level": contract.risk_level,
            "content": contract.content,
            "creator_id": contract.creator_id,
            "department_id": contract.department_id,
            "current_version_id": contract.current_version_id,
            "created_at": contract.created_at.isoformat() if contract.created_at else None,
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
        }
        if use_own_session:
            await session.commit()
        return result
    except Exception:
        if use_own_session:
            await session.rollback()
        raise
    finally:
        if use_own_session:
            await session.close()


async def delete_contract(contract_id: int, db: Optional[AsyncSession] = None) -> dict:
    """
    软删除合同
    
    Args:
        contract_id: 合同ID
        db: 数据库会话（可选）
        
    Returns:
        dict 删除结果
    """
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        result = await session.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")
        
        # 仅草稿可删除
        if contract.status != "draft":
            raise BusinessError(f"Contract {contract_id} status is {contract.status}, only draft can be deleted")
        
        # 软删除
        contract.status = "deleted"
        await session.flush()
        
        payload = {
            "success": True,
            "message": f"Contract {contract_id} deleted successfully",
            "contract_id": contract_id,
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


async def upload_contract_file(
    file_path: str,
    file_type: str,
    file_size: int,
    file_hash: str,
    contract_id: int,
    version_id: int,
    db: Optional[AsyncSession] = None,
) -> dict:
    """
    上传合同文件到 MinIO
    
    Args:
        file_path: 本地文件路径
        file_type: 文件类型
        file_size: 文件大小
        file_hash: 文件哈希
        contract_id: 合同ID
        version_id: 版本ID
        db: 数据库会话（可选）
        
    Returns:
        dict 文件上传结果
    """
    from app.utils.storage import MinIOStorage
    storage = MinIOStorage()
    
    use_own_session = db is None
    if use_own_session:
        session = async_session()
    else:
        session = db
    
    try:
        # 验证合同
        result = await session.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise BusinessError(f"Contract {contract_id} not found")
        
        # 生成 MinIO object key
        object_key = f"contracts/{contract.contract_no}/v{version_id}/{file_path.split('/')[-1]}"
        
        # 上传到 MinIO（实际实现需根据 MinioStorage 调整）
        # await storage.upload_file(...)
        
        await session.refresh(contract)
        
        payload = {
            "success": True,
            "object_key": object_key,
            "file_type": file_type,
            "file_size": file_size,
            "file_hash": file_hash,
            "contract_id": contract_id,
            "version_id": version_id,
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


async def list_dashboard_buckets(db: AsyncSession) -> dict:
    """看板三栏：executing / expiring_soon / expired，附带 stats 汇总。"""
    today, expiring_threshold = _dashboard_date_range()

    def _contract_brief(c: Contract) -> dict:
        return {
            "id": c.id,
            "contract_no": c.contract_no,
            "title": c.title,
            "counterparty_name": c.counterparty_name,
            "amount": c.amount,
            "status": c.status,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
        }

    executing = []
    expiring_soon = []
    expired = []

    result = await db.execute(
        select(Contract).where(Contract.status != "deleted")
    )
    for c in result.scalars().all():
        bucket = classify_contract_bucket(c, today, expiring_threshold)
        brief = _contract_brief(c)
        if bucket == "expired":
            expired.append(brief)
        elif bucket == "expiring_soon":
            expiring_soon.append(brief)
        elif bucket == "executing":
            executing.append(brief)

    total = await db.scalar(
        select(func.count()).select_from(Contract).where(Contract.status != "deleted")
    )
    # 与列表 status=pending 口径一致：待审批合同数（非审批步骤数）
    pending_approval = await db.scalar(
        select(func.count())
        .select_from(Contract)
        .where(Contract.status != "deleted", Contract.status == "pending")
    )

    return {
        "stats": {
            "total": total or 0,
            "pending_approval": pending_approval or 0,
            "executing_count": len(executing),
            "expiring_soon_count": len(expiring_soon),
            "expired_count": len(expired),
        },
        "executing": executing,
        "expiring_soon": expiring_soon,
        "expired": expired,
    }


async def list_contract_versions(db: AsyncSession, contract_id: int) -> list[dict]:
    """获取合同版本历史列表。"""
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise BusinessError(f"Contract {contract_id} not found")

    ver_result = await db.execute(
        select(ContractVersion)
        .where(ContractVersion.contract_id == contract_id)
        .order_by(ContractVersion.version.desc())
    )
    versions = ver_result.scalars().all()
    return [
        {
            "version": v.version,
            "content": v.content,
            "change_description": v.change_description,
            "file_path": v.file_path,
            "file_hash": v.file_hash,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


async def save_contract_upload(
    db: AsyncSession,
    contract_id: int,
    filename: str,
    content: bytes,
    content_type: str,
) -> dict:
    """保存合同附件（本地存储 fallback）。"""
    import hashlib
    import os

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise BusinessError(f"Contract {contract_id} not found")

    file_hash = hashlib.sha256(content).hexdigest()
    # DB file_type 列为 VARCHAR(10)，存扩展名 pdf/docx，不存完整 MIME
    stored_type = _guess_file_type(filename, content_type)[:10]

    if settings.FILE_STORAGE == "minio":
        from app.utils.storage import get_storage
        from io import BytesIO

        storage = get_storage()
        object_name = f"contracts/{contract.contract_no}/{filename}"
        try:
            await storage.ensure_bucket()
            await storage._run_in_executor(
                storage.client.put_object,
                storage.bucket,
                object_name,
                BytesIO(content),
                len(content),
                content_type=content_type or "application/octet-stream",
            )
            local_path = f"minio://{storage.bucket}/{object_name}"
        except Exception as exc:
            raise BusinessError(f"MinIO 上传失败: {exc}") from exc
    else:
        storage_dir = os.path.join(settings.FILE_STORAGE_PATH, "contracts", contract.contract_no)
        try:
            os.makedirs(storage_dir, exist_ok=True)
            local_path = os.path.join(storage_dir, filename)
            with open(local_path, "wb") as f:
                f.write(content)
        except OSError as exc:
            raise BusinessError(f"文件存储失败，请检查 FILE_STORAGE_PATH（{settings.FILE_STORAGE_PATH}）: {exc}") from exc

    ver_result = await db.execute(
        select(ContractVersion)
        .where(ContractVersion.contract_id == contract_id)
        .order_by(ContractVersion.version.desc())
        .limit(1)
    )
    version = ver_result.scalar_one_or_none()
    extracted_text = ""
    extracted_meta: dict = {}
    if stored_type in ("pdf", "docx", "txt"):
        try:
            extracted_text, extracted_meta = await extract_bytes_to_text(
                content, filename, content_type
            )
        except Exception as exc:
            logger.warning("上传文件正文提取失败 contract_id=%s: %s", contract_id, exc)

    if version:
        version.file_path = local_path
        version.file_type = stored_type
        version.file_size = len(content)
        version.file_hash = file_hash
        if extracted_text.strip():
            version.content = extracted_text
        await db.flush()

    if extracted_text.strip():
        contract.content = extracted_text

    return {
        "contract_id": contract_id,
        "file_path": local_path,
        "file_type": stored_type,
        "file_size": len(content),
        "file_hash": file_hash,
        "version_id": version.id if version else None,
        "char_count": len(extracted_text),
        "ocr_used": bool(extracted_meta.get("ocr_used")),
    }
