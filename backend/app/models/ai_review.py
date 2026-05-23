"""
Contract 审计日志已移至 contract.py，避免重复定义
"""
from app.models.contract import AuditLog

__all__ = ["AuditLog"]
