import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
import app.db.database as db_module
from app.db.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.DATABASE_URL = TEST_DATABASE_URL

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(test_engine.sync_engine, "connect")
def _set_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


db_module._engine = test_engine
db_module._async_session = TestSessionLocal


async def _create_tables() -> None:
    async with test_engine.begin() as conn:
        from app.models import ai_review, ai_review_issue, contract, counterparty, review, user  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_create_tables())

from app.main import app
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.contract import User


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    """每个用例使用干净库表。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        username="testuser",
        password_hash="$2b$12$mockedhashmockedhashmocked",
        real_name="测试用户",
        email="test@example.com",
        status=1,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def users_by_role(db_session):
    """按角色 seed 多用户，供集成测试切换身份。"""
    from app.models.contract import Department, Role, User

    dept = Department(name="法务部", parent_id=0, level=1, path="/1", status=1)
    db_session.add(dept)
    await db_session.flush()

    role_specs = [
        ("drafter", "业务员"),
        ("approver", "部门主管"),
        ("legal", "法务专员"),
        ("finance", "财务专员"),
        ("executive", "高管"),
        ("admin", "系统管理员"),
    ]
    role_map = {}
    for code, name in role_specs:
        role = Role(name=name, code=code, status=1)
        db_session.add(role)
        await db_session.flush()
        role_map[code] = role

    user_specs = [
        ("drafter1", "张业务", "drafter"),
        ("approver1", "李主管", "approver"),
        ("legal1", "王法务", "legal"),
        ("finance1", "赵财务", "finance"),
        ("executive1", "刘高管", "executive"),
        ("admin", "系统管理员", "admin"),
    ]
    users = {}
    for username, real_name, code in user_specs:
        user = User(
            username=username,
            password_hash="$2b$12$mockedhashmockedhashmocked",
            real_name=real_name,
            email=f"{username}@example.com",
            department_id=dept.id,
            role_id=role_map[code].id,
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        users[code] = user

    await db_session.commit()
    for user in users.values():
        await db_session.refresh(user)
    return users


@pytest_asyncio.fixture
async def client_for_user(users_by_role):
    """返回 async callable(role) -> AsyncClient，按角色切换当前用户。"""

    async def _client(role: str) -> AsyncClient:
        user = users_by_role[role]

        async def override_get_db():
            async with TestSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        async def override_get_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    yield _client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client(test_user):
    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_no_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class MockDataFactory:
    @staticmethod
    def user(id=1, **kw):
        return {
            "id": id,
            "username": kw.get("username", f"user_{id}"),
            "real_name": kw.get("real_name", f"User {id}"),
            "email": kw.get("email", f"user{id}@example.com"),
            "password_hash": kw.get("password_hash", "$2b$12$mocked"),
            "role_id": kw.get("role_id", 1),
            "department_id": kw.get("department_id", 1),
            "status": kw.get("status", 1),
        }

    @staticmethod
    def role(id=1, **kw):
        return {
            "id": id,
            "name": kw.get("name", "User"),
            "code": kw.get("code", "user"),
            "permissions": kw.get("permissions", {}),
            "status": kw.get("status", 1),
        }

    @staticmethod
    def department(id=1, **kw):
        return {
            "id": id,
            "name": kw.get("name", "DEPT"),
            "parent_id": 0,
            "level": 1,
            "path": f"/{id}",
            "status": kw.get("status", 1),
        }

    @staticmethod
    def contract(id=1, **kw):
        return {
            "id": id,
            "contract_no": kw.get(
                "contract_no", f"CON-{datetime.now().strftime('%Y%m')}-0001"
            ),
            "title": kw.get("title", "Contract"),
            "contract_type": kw.get("contract_type", "service"),
            "status": kw.get("status", "draft"),
            "counterparty_name": kw.get("counterparty_name", "XX Co."),
            "counterparty_type": kw.get("counterparty_type", "company"),
            "counterparty_credit_code": kw.get("counterparty_credit_code", ""),
            "amount": kw.get("amount", 100000.0),
            "currency": "CNY",
            "tax_rate": kw.get("tax_rate", 0.06),
            "start_date": kw.get("start_date", datetime.now().date()),
            "end_date": kw.get(
                "end_date", datetime.now().date() + timedelta(days=365)
            ),
            "creator_id": kw.get("creator_id", 1),
            "department_id": kw.get("department_id", 1),
            "risk_level": kw.get("risk_level", "medium"),
            "content": kw.get("content", ""),
            "approval_status": kw.get("approval_status", "pending"),
            "current_flow_id": kw.get("current_flow_id"),
            "current_version_id": kw.get("current_version_id"),
        }

    @staticmethod
    def approval_flow(id=1, **kw):
        return {
            "id": id,
            "contract_id": kw.get("contract_id", 1),
            "flow_type": "standard",
            "status": "approving",
            "current_node_id": "dept_approval",
            "current_step": kw.get("current_step", 1),
            "total_steps": kw.get("total_steps", 4),
            "start_time": datetime.now(),
        }

    @staticmethod
    def approval_step(id=1, **kw):
        return {
            "id": id,
            "flow_id": kw.get("flow_id", 1),
            "step_number": kw.get("step_number", 1),
            "node_id": kw.get("node_id", "dept_approval"),
            "node_name": kw.get("node_name", "Dept"),
            "approver_id": kw.get("approver_id", 2),
            "approver_name": kw.get("approver_name", "User"),
            "status": kw.get("status", "pending"),
            "start_time": datetime.now(),
        }

    @staticmethod
    def seal_record(id=1, **kw):
        return {
            "id": id,
            "contract_id": kw.get("contract_id", 1),
            "contract_no": kw.get("contract_no", "CON-202601-0001"),
            "seal_type": kw.get("seal_type", "contract_seal"),
            "status": kw.get("status", "pending"),
        }


@pytest.fixture
def mock_data():
    return MockDataFactory()


@pytest.fixture
def mock_jwt_token():
    from app.core.security import create_access_token

    def _create(user_id=1, **claims):
        data = {"sub": str(user_id)}
        data.update(claims)
        return create_access_token(data=data)

    return _create


@pytest.fixture
def mock_auth_headers(mock_jwt_token):
    def _generate(user_id=1, role="user"):
        return {
            "Authorization": f"Bearer {mock_jwt_token(user_id=user_id, role=role)}"
        }

    return _generate


@pytest.fixture
def auth_headers(mock_auth_headers):
    return mock_auth_headers


@pytest.fixture
def mock_openai_client():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = (
        '{"dimension":"compliance","score":85.0,"issues":[],"summary":"pass","checklist_coverage":[]}'
    )
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    async def _complete_json(*, messages, caller, system_prompt=None, max_retries=2):
        raw = mock_resp.choices[0].message.content
        import json
        from app.services.ai_review.llm_gateway import LLMCallMeta
        return json.loads(raw), LLMCallMeta(
            caller=caller, latency_ms=1, prompt_hash="test", success=True
        )

    with patch(
        "app.services.ai_review.llm_gateway.AsyncOpenAI",
        return_value=mock_client,
    ):
        with patch(
            "app.services.ai_review.ai_engine.get_llm_gateway"
        ) as mock_gw_factory:
            gw = MagicMock()
            gw.complete_json = AsyncMock(side_effect=_complete_json)
            mock_gw_factory.return_value = gw
            yield mock_client


@pytest.fixture
def mock_minio():
    m = AsyncMock()
    m.upload_file = AsyncMock(return_value="test-key")
    with patch("app.utils.storage.MinIOStorage", return_value=m):
        yield m
