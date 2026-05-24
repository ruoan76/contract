"""合同模板 ORM（V1.1 MVP）"""
from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.base import Base


class ContractTemplate(Base):
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="模板名称")
    category = Column(String(50), default="purchase", comment="分类")
    content = Column(Text, comment="模板正文")
    status = Column(
        String(30),
        default="draft",
        comment="draft|pending_publish|published|deprecated",
    )
    version = Column(Integer, default=1)
    creator_id = Column(Integer, comment="创建人 ID")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
