"""
Database Base - Shared declarative base for all models.

This module provides a single declarative base instance that all models inherit from.
All models in app.models import this Base, so Base.metadata will contain all tables.
"""
from sqlalchemy.orm import declarative_base

# Create shared Base
Base = declarative_base()

__all__ = ["Base"]