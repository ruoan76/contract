"""
用户相关 Pydantic Schemas (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ==================== 用户 ====================

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    real_name: str = Field(..., max_length=50, description="真实姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    department_id: Optional[int] = Field(None, description="部门 ID")
    role_id: Optional[int] = Field(None, description="角色 ID")


class UserCreate(UserBase):
    """创建用户"""
    password: str = Field(..., min_length=8, max_length=128, description="登录密码")


class UserUpdate(BaseModel):
    """更新用户"""
    real_name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    department_id: Optional[int] = Field(None)
    role_id: Optional[int] = Field(None)
    status: Optional[int] = Field(None, ge=0, le=1, description="1:启用 0:禁用")


class UserResponse(UserBase):
    """用户响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: int = Field(default=1, description="1:启用 0:禁用")
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    items: List[UserResponse]


class UserDetail(UserResponse):
    """用户详情"""
    permissions: Optional[List[str]] = Field(None, description="权限列表")


# ==================== 角色 ====================

class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., max_length=50, description="角色名称")
    code: str = Field(..., max_length=50, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")


class RoleCreate(RoleBase):
    """创建角色"""
    permissions: Optional[List[str]] = Field(None, description="权限列表 (JSON)")


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None)
    permissions: Optional[List[str]] = Field(None)
    status: Optional[int] = Field(None, ge=0, le=1)


class RoleResponse(RoleBase):
    """角色响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    permissions: Optional[List[str]] = None
    status: int = Field(default=1)
    created_at: datetime


class RoleListResponse(BaseModel):
    """角色列表响应"""
    total: int
    page: int
    page_size: int
    items: List[RoleResponse]


# ==================== 部门 ====================

class DepartmentBase(BaseModel):
    """部门基础模型"""
    name: str = Field(..., max_length=100, description="部门名称")
    parent_id: int = Field(default=0, description="父部门 ID")
    level: int = Field(default=1, description="层级")
    path: Optional[str] = Field(None, description="部门路径")


class DepartmentCreate(DepartmentBase):
    """创建部门"""
    pass


class DepartmentUpdate(BaseModel):
    """更新部门"""
    name: Optional[str] = Field(None, max_length=100)
    parent_id: Optional[int] = Field(None)
    level: Optional[int] = Field(None)
    path: Optional[str] = Field(None)
    status: Optional[int] = Field(None, ge=0, le=1)


class DepartmentResponse(DepartmentBase):
    """部门响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: int = Field(default=1)
    created_at: datetime


class DepartmentTreeNode(DepartmentResponse):
    """部门树节点（含子部门）"""
    children: List["DepartmentTreeNode"] = Field(default_factory=list)


class DepartmentListResponse(BaseModel):
    """部门列表响应"""
    total: int
    page: int
    page_size: int
    items: List[DepartmentResponse]


DepartmentTreeNode.model_rebuild()


# ==================== 密码修改 ====================

class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


# ==================== 批量操 ====================

class BatchUserAction(BaseModel):
    """用户批量操作"""
    user_ids: List[int] = Field(..., min_length=1, max_length=100, description="用户 ID 列表")
    action: str = Field(..., description="enable | disable | delete")
