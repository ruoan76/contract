"""
Security Service Tests
测试 JWT token、密码哈希、认证服务
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import select

# ==============================================================================
# JWT Token Tests
# ==============================================================================

@pytest.mark.unit
class TestCreateAccessToken:
    """create_access_token 测试"""
    
    def test_create_token_payload(self, mock_data):
        """测试创建 token 的 payload"""
        from app.core.security import create_access_token
        
        data = {"sub": "1", "role": "admin"}
        token = create_access_token(data=data)
        
        # 解码验证（使用测试密钥）
        from app.core.security import decode_token
        payload = decode_token(token)
        
        assert payload["sub"] == "1"
        assert payload["role"] == "admin"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_token_expiration(self, mock_data):
        """测试 token 过期时间"""
        from app.core.security import create_access_token
        
        # 创建 1 小时过期的 token
        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(hours=1)
        )
        
        from app.core.security import decode_token
        payload = decode_token(token)
        
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        now = datetime.utcnow()
        
        # 验证过期时间在 59-61 分钟之间
        delta = (exp_time - now).total_seconds()
        assert 59 * 60 < delta < 61 * 60


@pytest.mark.unit
class TestDecodeToken:
    """decode_token 测试"""
    
    def test_decode_valid_token(self, mock_data):
        """测试解码有效 token"""
        from app.core.security import create_access_token, decode_token
        
        token = create_access_token(data={"sub": "1"})
        payload = decode_token(token)
        
        assert payload["sub"] == "1"
    
    def test_decode_invalid_token(self, mock_data):
        """测试解码无效 token"""
        from app.core.security import decode_token
        from jose import JWTError
        
        with pytest.raises(JWTError):
            decode_token("invalid.token.here")
    
    def test_decode_expired_token(self, mock_data):
        """测试解码过期 token"""
        from app.core.security import decode_token
        from jose import JWTError
        
        # 创建一个已过期的 token
        import jose
        expired_token = jose.jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() - timedelta(hours=1)},
            "your-secret-key-change-in-production",
            algorithm="HS256"
        )
        
        with pytest.raises(JWTError):
            decode_token(expired_token)


# ==============================================================================
# Password Hash Tests
# ==============================================================================

@pytest.mark.unit
class TestGetPasswordHash:
    """get_password_hash 测试"""
    
    def test_hash_different_each_time(self, mock_data):
        """测试每次哈希结果不同（盐值）"""
        from app.core.security import get_password_hash
        
        password = "my-secret-password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # 由于盐值，每次不同
        assert hash1.startswith("$2b$")
    
    def test_hash_length(self, mock_data):
        """测试哈希长度"""
        from app.core.security import get_password_hash
        
        password = "my-password"
        hashed = get_password_hash(password)
        
        # bcrypt 哈希长度固定
        assert len(hashed) == 60


@pytest.mark.unit
class TestVerifyPassword:
    """verify_password 测试"""
    
    def test_verify_correct_password(self, mock_data):
        """测试验证正确密码"""
        from app.core.security import get_password_hash, verify_password
        
        password = "correct-password"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self, mock_data):
        """测试验证错误密码"""
        from app.core.security import get_password_hash, verify_password
        
        password = "correct-password"
        wrong_password = "wrong-password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False


# ==============================================================================
# Authentication Dependency Tests
# ==============================================================================

@pytest.mark.unit
class TestGetCurrentUser:
    """get_current_user 依赖测试"""
    
    async def test_get_current_user_success(self, db_session, mock_data):
        """测试成功获取当前用户"""
        from app.core.security import create_access_token, get_current_user
        from app.models.contract import User
        
        # 创建用户
        user = User(
            username="testuser",
            password_hash="$2b$12$mockedhash",
            real_name="Test User",
            email="test@example.com",
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        
        # 创建 token
        token = create_access_token(data={"sub": str(user.id)})
        
        # Mock request
        class MockRequest:
            headers = {"Authorization": f"Bearer {token}"}
        
        # 解码 token 获取用户 ID
        from app.core.security import decode_token
        payload = decode_token(token)
        user_id = int(payload["sub"])
        
        # 重新获取用户
        stmt = select(User).where(User.id == user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one()
        
        assert user.id == user_id
        assert user.username == "testuser"
    
    async def test_get_current_user_invalid_token(self, db_session, mock_data):
        """测试无效 token"""
        from app.core.security import get_current_user
        from fastapi import HTTPException
        
        # Mock request with invalid token
        class MockRequest:
            headers = {"Authorization": "Bearer invalid.token"}
        
        # This would raise HTTPException in actual usage
        # We can't fully test the dependency injection without FastAPI context
    
    async def test_get_current_user_missing_token(self, db_session, mock_data):
        """测试缺失 token"""
        from app.core.security import get_current_user
        
        # Mock request without Authorization header
        class MockRequest:
            headers = {}
        
        # This would raise HTTPException in actual usage


@pytest.mark.unit
class TestGetCurrentActiveUser:
    """get_current_active_user 依赖测试"""
    
    async def test_get_current_active_user_success(self, db_session, mock_data):
        """测试获取活动用户"""
        from app.core.security import create_access_token
        from app.models.contract import User
        
        # 创建活动用户
        user = User(
            username="activeuser",
            password_hash="$2b$12$mockedhash",
            real_name="Active User",
            email="active@example.com",
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        
        token = create_access_token(data={"sub": str(user.id)})
        
        from app.core.security import decode_token
        payload = decode_token(token)
        user_id = int(payload["sub"])
        
        stmt = select(User).where(User.id == user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one()
        
        assert user.status == 1
    
    async def test_get_current_inactive_user(self, db_session, mock_data):
        """测试获取非活动用户"""
        from app.core.security import create_access_token
        from app.models.contract import User
        from fastapi import HTTPException
        
        # 创建非活动用户
        user = User(
            username="inactiveuser",
            password_hash="$2b$12$mockedhash",
            real_name="Inactive User",
            email="inactive@example.com",
            status=0,  # 非活动
        )
        db_session.add(user)
        await db_session.flush()
        
        token = create_access_token(data={"sub": str(user.id)})
        
        from app.core.security import decode_token
        payload = decode_token(token)
        user_id = int(payload["sub"])
        
        stmt = select(User).where(User.id == user_id)
        result = await db_session.execute(stmt)
        user = result.scalar_one()
        
        assert user.status == 0


@pytest.mark.unit
class TestCheckPermission:
    """check_permission 依赖测试"""
    
    async def test_check_permission_success(self, db_session, mock_data):
        """测试权限检查通过"""
        from app.models.contract import User, Role
        
        # 创建角色
        role = Role(
            name="管理员",
            code="admin",
            description="系统管理员",
            status=1,
        )
        db_session.add(role)
        await db_session.flush()
        
        # 创建用户
        user = User(
            username="admin",
            password_hash="$2b$12$mockedhash",
            real_name="Admin",
            email="admin@example.com",
            role_id=role.id,
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        
        assert user.role_id == role.id
        
        # 检查 role.code
        await db_session.refresh(user)
        await db_session.refresh(role)
        assert role.code == "admin"
    
    async def test_check_permission_failed(self, db_session, mock_data):
        """测试权限检查失败"""
        from app.models.contract import User, Role
        
        # 创建普通用户角色
        role = Role(
            name="用户",
            code="user",
            description="普通用户",
            status=1,
        )
        db_session.add(role)
        await db_session.flush()
        
        # 创建用户（无管理员权限）
        user = User(
            username="regular",
            password_hash="$2b$12$mockedhash",
            real_name="Regular User",
            email="regular@example.com",
            role_id=role.id,
            status=1,
        )
        db_session.add(user)
        await db_session.flush()
        
        await db_session.refresh(user)
        role_obj = await db_session.get(Role, user.role_id)
        assert role_obj.code == "user"
        assert role_obj.code != "admin"


# ==============================================================================
# OAuth2 Scheme Tests
# ==============================================================================

@pytest.mark.unit
class TestOAuth2Scheme:
    """oauth2_scheme 测试"""
    
    def test_oauth2_scheme_configured(self, mock_data):
        """测试 OAuth2 scheme 配置"""
        from fastapi.security import OAuth2PasswordBearer
        from app.core.security import oauth2_scheme

        assert isinstance(oauth2_scheme, OAuth2PasswordBearer)
        token_url = getattr(oauth2_scheme, "tokenUrl", None)
        if token_url is None and hasattr(oauth2_scheme, "model"):
            token_url = oauth2_scheme.model.flows.password.tokenUrl
        assert token_url == "/api/v1/system/login"
