"""
相对方模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func

from app.db.base import Base


class Counterparty(Base):
    """相对方档案表"""

    __tablename__ = "counterparties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="单位名称")
    credit_code = Column(String(50), unique=True, comment="统一社会信用代码")
    legal_person = Column(String(50), comment="法定代表人")
    contact_name = Column(String(50), comment="联系人")
    contact_phone = Column(String(20), comment="联系电话")
    address = Column(String(500), comment="地址")
    industry = Column(String(50), comment="行业分类")
    credit_rating = Column(String(10), comment="信用评级")
    is_blacklist = Column(Integer, default=0, comment="是否黑名单 0否 1是")
    blacklist_reason = Column(Text, comment="列入黑名单原因")
    status = Column(Integer, default=1, comment="1:启用 0:禁用")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_cp_name", "name"),
        Index("idx_cp_credit_code", "credit_code"),
        Index("idx_cp_blacklist", "is_blacklist"),
    )
