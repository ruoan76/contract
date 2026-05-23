"""兼容 ``from app.main import app`` 的入口 re-export。"""
from main import app

__all__ = ["app"]
