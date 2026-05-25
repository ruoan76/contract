# -*- coding: utf-8 -*-
"""AI 审查 Issue ORM。"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.db.base import Base


class AIReviewIssue(Base):
    __tablename__ = "ai_review_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(50), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, nullable=False)

    clause = Column(String(200), default="")
    clause_id = Column(String(50), default="")
    clause_ref = Column(String(200), default="")
    dimension = Column(String(50), default="compliance_check")
    label_id = Column(String(10))
    label_name = Column(String(100))
    gate_id = Column(String(50))
    cuad_code = Column(String(20))
    risk_level = Column(String(20), default="medium")
    confidence = Column(Float, default=0.7)
    title = Column(String(500), default="")
    description = Column(Text)
    suggestion = Column(Text)
    legal_basis = Column(Text)
    revision_method = Column(String(30), default="comment")
    exposure_summary = Column(String(500))
    source = Column(String(20), default="llm")
    needs_research = Column(Integer, default=0)
    rule_id = Column(String(50))

    human_status = Column(String(20), default="pending")
    human_comment = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_ai_issue_review", "review_id"),
        Index("idx_ai_issue_contract", "contract_id"),
    )
