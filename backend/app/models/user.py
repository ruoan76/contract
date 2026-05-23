"""
用户 / 角色 / 部门模型（导出自 contract.py，避免重复定义）
"""
from app.models.contract import User, Role, Department

__all__ = ["User", "Role", "Department"]
