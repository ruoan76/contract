"""
认证相关 Pydantic Schema (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ==================== 登录 / Token ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class Token(BaseModel):
    """Token 响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class TokenData(BaseModel):
    """Token 数据"""
    sub: str = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    role: Optional[str] = Field(None, description="角色编码")
    exp: Optional[int] = Field(None, description="过期时间戳")


# ==================== 注册 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    real_name: str = Field(..., max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department_id: Optional[int] = Field(None, description="部门 ID")


class RegisterResponse(BaseModel):
    """注册响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    real_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    status: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 密码修改 ====================

class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: str = Field(..., max_length=100, description="邮箱地址")


class PasswordChangeRequest(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., max_length=128, description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    confirm_password: str = Field(..., max_length=128, description="确认新密码")


# ==================== 用户信息 ====================

class UserInfo(BaseModel):
    """用户信息"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    real_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    role_id: Optional[int] = None
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    permissions: Optional[list[str]] = None
    status: int = 1
    created_at: datetime
    updated_at: Optional[datetime] = None
