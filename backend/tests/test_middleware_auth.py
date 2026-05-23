"""
Auth Middleware Tests
测试认证中间件
"""
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import Request, Response
from datetime import datetime, timedelta


def _make_request(path: str, headers: dict | None = None):
    """构造带真实 state 对象的请求 mock。"""
    request = MagicMock()
    request.url.path = path
    request.headers = headers or {}
    request.state = SimpleNamespace()
    return request

# ==============================================================================
# Auth Middleware Tests
# ==============================================================================

@pytest.mark.unit
class TestAuthMiddleware:
    """AuthMiddleware 测试"""
    
    def test_is_public_path(self, mock_data):
        """测试公共路径判断"""
        from app.middleware.auth_middleware import AuthMiddleware, PUBLIC_PATHS
        
        assert "/health" in PUBLIC_PATHS
        assert "/api/v1/auth/login" in PUBLIC_PATHS
        assert "/docs" in PUBLIC_PATHS
        assert "/openapi.json" in PUBLIC_PATHS
        assert "/redoc" in PUBLIC_PATHS
    
    async def test_dispatch_skip_public_path(self, mock_data):
        """测试跳过公共路径"""
        from app.middleware.auth_middleware import AuthMiddleware
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        # Mock request to public path
        request = MagicMock()
        request.url.path = "/health"
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
    
    async def test_dispatch_with_valid_token(self, mock_data):
        """测试有效 token"""
        from app.middleware.auth_middleware import AuthMiddleware
        from app.core.security import create_access_token
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        # 创建有效 token
        token = create_access_token(data={"sub": "1"})
        
        request = _make_request("/api/v1/contracts", {"Authorization": f"Bearer {token}"})
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
        assert hasattr(request.state, "current_user_id")
        assert request.state.current_user_id == 1
    
    async def test_dispatch_with_invalid_token(self, mock_data):
        """测试无效 token"""
        from app.middleware.auth_middleware import AuthMiddleware
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        request = _make_request("/api/v1/contracts", {"Authorization": "Bearer invalid.token"})
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
        # current_user_id 不应被设置
        assert not hasattr(request.state, "current_user_id")
    
    async def test_dispatch_without_token(self, mock_data):
        """测试缺失 token"""
        from app.middleware.auth_middleware import AuthMiddleware
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        request = _make_request("/api/v1/contracts")
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
        assert not hasattr(request.state, "current_user_id")
    
    async def test_dispatch_with_invalid_bearer_format(self, mock_data):
        """测试无效的 Bearer 格式"""
        from app.middleware.auth_middleware import AuthMiddleware
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        request = _make_request("/api/v1/contracts", {"Authorization": "Invalid format"})
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
        assert not hasattr(request.state, "current_user_id")
    
    async def test_dispatch_with_expired_token(self, mock_data):
        """测试过期 token"""
        from app.middleware.auth_middleware import AuthMiddleware
        import jose
        
        app = MagicMock()
        middleware = AuthMiddleware(app)
        
        # 创建过期 token
        expired_token = jose.jwt.encode(
            {"sub": "1", "exp": datetime.utcnow() - timedelta(hours=1)},
            "your-secret-key-change-in-production",
            algorithm="HS256"
        )
        
        request = _make_request("/api/v1/contracts", {"Authorization": f"Bearer {expired_token}"})
        
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        assert response is not None
        call_next.assert_called_once()
        assert not hasattr(request.state, "current_user_id")


@pytest.mark.unit
class TestSetupAuthMiddleware:
    """setup_auth_middleware 测试"""
    
    def test_setup_auth_middleware(self, mock_data):
        """测试中间件注册"""
        from app.middleware.auth_middleware import AuthMiddleware, setup_auth_middleware
        
        app = MagicMock()
        app.add_middleware = MagicMock()
        
        setup_auth_middleware(app)
        
        app.add_middleware.assert_called_once_with(AuthMiddleware)
