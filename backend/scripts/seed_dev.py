"""开发环境种子数据脚本。

用法:
    cd backend && python scripts/seed_dev.py
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
        for username, real_name, role_code in users_data:
            exists = await session.scalar(select(User).where(User.username == username))
            if exists:
                continue
            session.add(
                User(
                    username=username,
                    password_hash=get_password_hash("123456"),
                    real_name=real_name,
                    email=f"{username}@example.com",
                    department_id=dept.id,
                    role_id=role_map[role_code].id,
                    status=1,
                )
            )

        await session.commit()
        print("种子数据写入完成。默认密码: 123456")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
