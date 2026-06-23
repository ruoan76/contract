"""合同模板 ORM（V1.1 MVP）"""
from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.base import Base


class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), comment="模板编码，如 PUR-001")
    name = Column(String(200), nullable=False, comment="模板名称")
    category = Column(String(50), default="purchase", comment="分类")
    variables = Column(Text, comment="可变字段列表 JSON")
    content = Column(Text, comment="模板正文")
    status = Column(
        String(30),
        default="draft",
        comment="draft|pending_publish|published|deprecated",
    )
    version = Column(Integer, default=1)
    creator_id = Column(Integer, comment="创建人 ID")
    legal_snapshot = Column(Text, comment="法律条款快照 JSON: {label_ids, review_items}")
    auto_review_on_publish = Column(Integer, default=0, comment="发布时是否自动AI审查 (1=是, 0=否)")
    archived_reason = Column(String(500), comment="废止原因")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
