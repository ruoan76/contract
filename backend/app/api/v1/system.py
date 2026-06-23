"""
系统管理 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional

from app.core.rbac import require_any_role
from app.db.database import get_db
from app.models.contract import User, Department, Role
from app.utils.auth import create_access_token, verify_password, get_current_user, get_password_hash

router = APIRouter()

_admin = require_any_role("admin")


class AdminUserUpdate(BaseModel):
    """管理员更新用户角色与状态"""
    role_id: Optional[int] = Field(None, description="角色 ID")
    status: Optional[int] = Field(None, ge=0, le=1, description="1:启用 0:禁用")


class AdminUserCreate(BaseModel):
    """管理员创建用户"""
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    real_name: str = Field(..., min_length=1, max_length=50)
    email: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[int] = None
    role_id: Optional[int] = None


class AdminResetPassword(BaseModel):
    """管理员重置密码"""
    password: str = Field(..., min_length=6, max_length=128)


@router.get("/users", summary="用户列表")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    department_id: Optional[int] = None,
    role_id: Optional[int] = None,
    status: Optional[int] = Query(None, ge=0, le=1, description="1 启用 0 禁用，不传则全部"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_admin),
):
    """获取用户列表（仅管理员）"""
    conditions = []
    if status is not None:
        conditions.append(User.status == status)
    if keyword:
        kw = f"%{keyword}%"
        conditions.append(
            or_(
                User.username.like(kw),
                User.real_name.like(kw),
                User.email.like(kw),
            )
        )
    if department_id:
        conditions.append(User.department_id == department_id)
    if role_id is not None:
        conditions.append(User.role_id == role_id)
    
    where_clause = and_(*conditions) if conditions else True

    count_query = select(func.count()).select_from(User).where(where_clause)
    total = await db.scalar(count_query)

    query = (
        select(User, Department.name.label("department_name"), Role.name.label("role_name"))
        .outerjoin(Department, User.department_id == Department.id)
        .outerjoin(Role, User.role_id == Role.id)
        .where(where_clause)
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for user, dept_name, role_name in rows:
        items.append({
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "email": user.email,
            "phone": user.phone,
            "department_name": dept_name,
            "role_name": role_name,
            "role_id": user.role_id,
            "status": user.status,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })
    
    return {"code": 200, "data": {"total": total, "page": page, "page_size": page_size, "items": items}}


@router.get("/users/options", summary="用户选项（委托等，已登录即可）")
async def list_user_options(
    keyword: Optional[str] = None,
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """供审批委托等场景选择用户，仅返回启用用户的基础字段。"""
    conditions = [User.status == 1]
    if keyword:
        kw = f"%{keyword}%"
        conditions.append(
            or_(
                User.username.like(kw),
                User.real_name.like(kw),
            )
        )
    where_clause = and_(*conditions)
    query = (
        select(User, Role.name.label("role_name"))
        .outerjoin(Role, User.role_id == Role.id)
        .where(where_clause)
        .order_by(User.real_name)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()
    items = [
        {
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "role_name": role_name,
        }
        for u, role_name in rows
    ]
    return {"code": 200, "data": {"items": items}}


@router.post("/users", summary="创建用户（管理员）")
async def create_user(
    body: AdminUserCreate,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员创建新用户"""
    exists = await db.scalar(select(User).where(User.username == body.username))
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.role_id is not None:
        role = await db.get(Role, body.role_id)
        if not role:
            raise HTTPException(status_code=400, detail="角色不存在")
    if body.department_id is not None:
        dept = await db.get(Department, body.department_id)
        if not dept:
            raise HTTPException(status_code=400, detail="部门不存在")

    new_user = User(
        username=body.username,
        password_hash=get_password_hash(body.password),
        real_name=body.real_name,
        email=body.email,
        phone=body.phone,
        department_id=body.department_id,
        role_id=body.role_id,
        status=1,
    )
    db.add(new_user)
    await db.flush()
    return {
        "code": 200,
        "data": {
            "id": new_user.id,
            "username": new_user.username,
            "real_name": new_user.real_name,
            "email": new_user.email,
            "phone": new_user.phone,
            "department_id": new_user.department_id,
            "role_id": new_user.role_id,
            "status": new_user.status,
        },
    }


@router.post("/users/{user_id}/reset-password", summary="重置用户密码（管理员）")
async def reset_user_password(
    user_id: int,
    body: AdminResetPassword,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员重置指定用户密码"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    target.password_hash = get_password_hash(body.password)
    await db.flush()
    return {"code": 200, "message": "密码已重置"}


@router.put("/users/{user_id}", summary="更新用户（管理员）")
async def update_user(
    user_id: int,
    body: AdminUserUpdate,
    user: User = Depends(_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员更新用户 role_id 与 status"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    updates = body.model_dump(exclude_unset=True)
    if "role_id" in updates and updates["role_id"] is not None:
        role = await db.get(Role, updates["role_id"])
        if not role:
            raise HTTPException(status_code=400, detail="角色不存在")
        target.role_id = updates["role_id"]
    if "status" in updates and updates["status"] is not None:
        target.status = updates["status"]

    await db.flush()
    return {
        "code": 200,
        "data": {
            "id": target.id,
            "username": target.username,
            "role_id": target.role_id,
            "status": target.status,
        },
    }


@router.get("/roles", summary="角色列表")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(_admin),
):
    """获取角色列表"""
    result = await db.execute(select(Role).where(Role.status == 1))
    roles = result.scalars().all()
    
    return {
        "code": 200,
        "data": [
            {"id": r.id, "name": r.name, "code": r.code, "description": r.description}
            for r in roles
        ]
    }


@router.get("/departments", summary="部门列表")
async def list_departments(db: AsyncSession = Depends(get_db)):
    """获取部门列表"""
    result = await db.execute(select(Department).where(Department.status == 1).order_by(Department.parent_id, Department.id))
    departments = result.scalars().all()
    
    # 构建树形结构
    nodes = {}
    roots = []
    for d in departments:
        nodes[d.id] = {"id": d.id, "name": d.name, "parent_id": d.parent_id, "level": d.level, "children": []}
    
    for d in departments:
        if d.parent_id == 0 or d.parent_id not in nodes:
            roots.append(nodes[d.id])
        else:
            parent = nodes.get(d.parent_id)
            if parent:
                parent["children"].append(nodes[d.id])
    
    return {"code": 200, "data": roots}


@router.post("/login", summary="用户登录")
async def login(username: str, password: str, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(
        select(User, Role.code.label("role_code"), Role.name.label("role_name"))
        .outerjoin(Role, User.role_id == Role.id)
        .where(User.username == username, User.status == 1)
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    user, role_code, role_name = row

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = create_access_token(data={"sub": str(user.id)})

    return {
        "code": 200,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "email": user.email,
                "phone": user.phone,
                "department_id": user.department_id,
                "role_id": user.role_id,
                "role_code": role_code,
                "role_name": role_name,
            },
        },
    }


@router.get("/profile", summary="用户信息")
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户信息"""
    # 获取用户详情（包含部门和角色）
    result = await db.execute(
        select(
            User,
            Department.name.label("department_name"),
            Role.name.label("role_name"),
            Role.code.label("role_code"),
        )
        .outerjoin(Department, User.department_id == Department.id)
        .outerjoin(Role, User.role_id == Role.id)
        .where(User.id == user.id)
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_obj, dept_name, role_name, role_code = row

    return {
        "code": 200,
        "data": {
            "id": user_obj.id,
            "username": user_obj.username,
            "real_name": user_obj.real_name,
            "email": user_obj.email,
            "phone": user_obj.phone,
            "department_name": dept_name,
            "role_name": role_name,
            "role_code": role_code,
            "permissions": user_obj.role.permissions if hasattr(user_obj, "role") and user_obj.role else [],
        },
    }
