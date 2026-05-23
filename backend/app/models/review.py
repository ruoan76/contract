"""
评审域模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.db.base import Base


class ReviewSession(Base):
    """评审会话（与审批流分离）"""

    __tablename__ = "review_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    flow_type = Column(String(50), comment="关联流程类型 simple/standard/special")
    status = Column(String(20), default="pending", comment="pending/completed/returned")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_review_session_contract", "contract_id"),)


class ReviewOpinion(Base):
    """评审意见"""

    __tablename__ = "review_opinions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("review_sessions.id", ondelete="CASCADE"))
    role = Column(String(50), nullable=False, comment="legal/finance/executive")
    action = Column(String(20), nullable=False, comment="approve/reject/return")
    comment = Column(Text, comment="评审意见")
    reviewer_id = Column(Integer, nullable=False)
    reviewer_name = Column(String(50))
    status = Column(String(20), default="submitted")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_review_opinion_contract", "contract_id"),
        Index("idx_review_opinion_role", "role"),
    )


class Notification(Base):
    """站内通知"""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="接收人 ID")
    title = Column(String(200), nullable=False)
    message = Column(Text)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    is_read = Column(Integer, default=0, comment="0未读 1已读")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("idx_notification_user", "user_id"),)
