"""开发环境种子数据脚本。

用法:
    cd backend && python scripts/seed_dev.py

拉代码后若 API 500 且日志含 no such column，先执行迁移再 seed：
    export DATABASE_URL=sqlite+aiosqlite:///./contract_dev.db
    alembic upgrade head
"""
import asyncio
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.contract import Role, Department, User

# 开发/演示环境统一默认密码
DEFAULT_DEV_PASSWORD = "admin123"


async def seed() -> None:
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    if db_url.startswith("mysql") and "asyncmy" not in db_url:
        db_url = db_url.replace("mysql://", "mysql+asyncmy://", 1)

    engine = create_async_engine(db_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        dept = await session.scalar(select(Department).where(Department.name == "法务部"))
        if not dept:
            dept = Department(name="法务部", parent_id=0, level=1, path="/1", status=1)
            session.add(dept)
            await session.flush()

        roles_data = [
            ("系统管理员", "admin"),
            ("业务员", "drafter"),
            ("部门主管", "approver"),
            ("法务专员", "legal"),
            ("财务专员", "finance"),
            ("高管", "executive"),
            ("档案管理员", "archivist"),
        ]
        role_map = {}
        for name, code in roles_data:
            role = await session.scalar(select(Role).where(Role.code == code))
            if not role:
                role = Role(name=name, code=code, status=1)
                session.add(role)
                await session.flush()
            role_map[code] = role

        users_data = [
            ("admin", "系统管理员", "admin"),
            ("drafter1", "张业务", "drafter"),
            ("approver1", "李主管", "approver"),
            ("legal1", "王法务", "legal"),
            ("finance1", "赵财务", "finance"),
            ("executive1", "刘高管", "executive"),
        ]
        pwd_hash = get_password_hash(DEFAULT_DEV_PASSWORD)
        for username, real_name, role_code in users_data:
            user = await session.scalar(select(User).where(User.username == username))
            if user:
                user.password_hash = pwd_hash
                continue
            session.add(
                User(
                    username=username,
                    password_hash=pwd_hash,
                    real_name=real_name,
                    email=f"{username}@example.com",
                    department_id=dept.id,
                    role_id=role_map[role_code].id,
                    status=1,
                )
            )

        await session.commit()

        from app.models.counterparty import Counterparty

        cp_exists = await session.scalar(select(Counterparty).limit(1))
        if not cp_exists:
            session.add_all(
                [
                    Counterparty(name="得力集团", credit_code="91310000123456789X", status=1),
                    Counterparty(name="华为技术", credit_code="91440300123456780A", status=1),
                    Counterparty(name="测试供应商", credit_code="91110000MA00000001", status=1),
                ]
            )
            await session.commit()

        # E2E demo-04 会拉黑相对方，重复 seed 时恢复默认状态
        for cp_name in ("得力集团", "华为技术", "测试供应商"):
            cp = await session.scalar(select(Counterparty).where(Counterparty.name == cp_name))
            if cp:
                cp.is_blacklist = 0
                cp.blacklist_reason = None
        await session.commit()

        from app.models.template import ContractTemplate
        from app.services.template_parser import extract_variables, variables_to_json

        standard_templates = [
            (
                "PUR-001",
                "标准采购合同",
                "purchase",
                "甲方（采购方）：{采购方名称}\n乙方（供应方）：{相对方}\n\n合同金额：人民币 {金额} 元。\n\n第一条 采购内容\n（标准条款）",
            ),
            (
                "SAL-001",
                "标准销售合同",
                "sales",
                "甲方（销售方）：{销售方名称}\n乙方（购买方）：{相对方}\n\n合同金额：人民币 {金额} 元。",
            ),
            (
                "LAB-001",
                "标准劳务合同",
                "labor",
                "甲方：{采购方名称}\n乙方（劳务方）：{相对方}\n\n劳务费用：人民币 {金额} 元。",
            ),
            (
                "NDA-001",
                "标准保密协议",
                "nda",
                "披露方：{采购方名称}\n接收方：{相对方}\n\n保密期限：{保密期限}。",
            ),
            (
                "SVC-001",
                "服务采购合同",
                "service",
                "甲方：{采购方名称}\n乙方（服务方）：{相对方}\n\n服务费用：人民币 {金额} 元；服务期限：{服务期限}。",
            ),
        ]
        for code, name, category, content in standard_templates:
            exists = await session.scalar(
                select(ContractTemplate).where(ContractTemplate.code == code)
            )
            if exists:
                continue
            vars_json = variables_to_json(extract_variables(content))
            session.add(
                ContractTemplate(
                    code=code,
                    name=name,
                    category=category,
                    content=content,
                    variables=vars_json,
                    status="published",
                    version=1,
                )
            )
        await session.commit()

        from app.models.review import Notification

        existing = await session.scalar(select(Notification).limit(1))
        if not existing:
            admin_user = await session.scalar(select(User).where(User.username == "admin"))
            drafter_user = await session.scalar(select(User).where(User.username == "drafter1"))
            if admin_user:
                session.add(
                    Notification(
                        user_id=admin_user.id,
                        title="系统通知示例",
                        message="这是一条系统渠道通知",
                        channel="system",
                        resource_type="system",
                    )
                )
            if drafter_user:
                session.add(
                    Notification(
                        user_id=drafter_user.id,
                        title="飞书审批提醒",
                        message="合同待审批，已通过飞书推送",
                        channel="feishu",
                        resource_type="contract",
                        resource_id=1,
                    )
                )
                session.add(
                    Notification(
                        user_id=drafter_user.id,
                        title="邮件归档通知",
                        message="合同已归档，邮件已发送",
                        channel="email",
                        resource_type="contract",
                    )
                )
            await session.commit()

        print(f"种子数据写入完成。默认密码: {DEFAULT_DEV_PASSWORD}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
