# -*- coding: utf-8 -*-
"""AI 审查可配置规则 ORM。"""
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, Index
from sqlalchemy.sql import func

from app.db.base import Base


class AIConfigVersion(Base):
    __tablename__ = "ai_config_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(32), nullable=False, unique=True, comment="配置版本号")
    is_current = Column(Boolean, default=False, comment="是否为当前生效版本")
    published_at = Column(DateTime, server_default=func.now())
    published_by = Column(Integer, nullable=True, comment="发布人 user_id")
    note = Column(String(500), nullable=True)


class AIReviewChecklistItem(Base):
    __tablename__ = "ai_review_checklist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    legacy_id = Column(Integer, nullable=False, unique=True, comment="原 JSON id 1-53")
    category = Column(String(100), nullable=False, default="")
    item = Column(String(200), nullable=False, default="")
    description = Column(Text, nullable=True)
    applicable_contracts = Column(String(500), nullable=True)
    risk_level = Column(String(20), default="medium")
    gate_id = Column(String(50), default="gate_clause")
    gate_priority = Column(Integer, default=0)
    auto_detectable = Column(Boolean, default=False)
    detect_config = Column(Text, nullable=True, comment="JSON 检测配置")
    enabled = Column(Boolean, default=True)
    version_tag = Column(String(32), nullable=True, comment="所属配置版本")


class AIRiskLabel(Base):
    __tablename__ = "ai_risk_labels"

    label_id = Column(String(10), primary_key=True, comment="L01-L15")
    name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    gate_id = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    enabled = Column(Boolean, default=True)
    version_tag = Column(String(32), nullable=True)


class AIRevisionRoutingRule(Base):
    __tablename__ = "ai_revision_routing_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_type = Column(String(200), nullable=False)
    default_method = Column(String(30), default="comment")
    auto_applicable = Column(Boolean, default=True)
    self_check_questions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    version_tag = Column(String(32), nullable=True)


class AIHardRule(Base):
    __tablename__ = "ai_hard_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False, default="")
    enabled = Column(Boolean, default=True)
    rule_type = Column(String(50), nullable=False, comment="regex/keyword_any/missing_keywords/...")
    config_json = Column(Text, nullable=True, comment="规则参数 JSON")
    risk_level = Column(String(20), default="medium")
    label_id = Column(String(10), nullable=True)
    gate_id = Column(String(50), nullable=True)
    dimension = Column(String(50), default="compliance_check")
    title = Column(String(500), nullable=True)
    suggestion = Column(Text, nullable=True)
    legal_basis = Column(String(500), nullable=True)
    revision_method = Column(String(30), default="comment")
    clause = Column(String(200), default="")
    version_tag = Column(String(32), nullable=True)


class AILegalSnippet(Base):
    __tablename__ = "ai_legal_snippets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snippet_id = Column(String(50), nullable=False, unique=True)
    keywords = Column(Text, nullable=True, comment="JSON 关键词数组")
    text = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    version_tag = Column(String(32), nullable=True)


class AIRuleFeedbackStat(Base):
    __tablename__ = "ai_rule_feedback_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_key = Column(String(80), nullable=False, comment="rule_id 或 CK-{legacy_id}")
    source = Column(String(20), default="rule", comment="rule|checklist|llm")
    fp_count = Column(Integer, default=0)
    confirm_count = Column(Integer, default=0)
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_ai_feedback_rule_key", "rule_key", unique=True),)
