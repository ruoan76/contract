"""
合同模型
"""
from sqlalchemy import Column, Integer, String, Float, Date, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func
from app.db.database import engine
from app.db.base import Base


class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(50), unique=True, nullable=False, comment="合同编号")
    title = Column(String(200), nullable=False, comment="合同名称")
    contract_type = Column(String(50), nullable=False, comment="合同类型")
    status = Column(String(20), nullable=False, default="draft", comment="状态")
    
    # 对方信息
    counterparty_id = Column(Integer, ForeignKey("counterparties.id"), comment="相对方 ID")
    counterparty_name = Column(String(200), nullable=False, comment="对方单位名称")
    counterparty_type = Column(String(50), comment="对方类型")
    counterparty_credit_code = Column(String(50), comment="统一社会信用代码")
    
    # 金额信息
    amount = Column(Float, comment="合同金额")
    currency = Column(String(10), default="CNY")
    tax_rate = Column(Float, comment="税率")
    
    # 期限信息
    start_date = Column(Date, comment="开始日期")
    end_date = Column(Date, comment="结束日期")
    
    # 审批信息
    current_flow_id = Column(Integer, comment="当前审批流程 ID")
    approval_status = Column(String(20), default="pending", comment="审批状态")
    
    # 签署信息
    sign_date = Column(Date, comment="签署日期")
    sign_method = Column(String(20), comment="签署方式")
    seal_record_id = Column(Integer, comment="用印记录 ID")
    
    # 归档信息
    archive_date = Column(Date, comment="归档日期")
    archive_location = Column(String(200), comment="归档位置")
    
    # 元数据
    creator_id = Column(Integer, nullable=False, comment="创建人 ID")
    department_id = Column(Integer, comment="所属部门")
    risk_level = Column(String(20), default="low", comment="风险等级")
    content = Column(Text().with_variant(LONGTEXT(), "mysql"), comment="合同内容")
    template_id = Column(Integer, comment="引用的合同模板 ID")
    template_version = Column(Integer, comment="引用模板版本号")
    template_values = Column(Text, comment="模板变量填充值 JSON")
    current_version_id = Column(Integer, comment="当前版本 ID")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_contract_no", "contract_no"),
        Index("idx_type", "contract_type"),
        Index("idx_status", "status"),
        Index("idx_creator", "creator_id"),
        Index("idx_department", "department_id"),
        Index("idx_counterparty", "counterparty_name"),
        Index("idx_counterparty_id", "counterparty_id"),
        Index("idx_risk_level", "risk_level"),
    )


class ContractVersion(Base):
    __tablename__ = "contract_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, comment="版本号")
    title = Column(String(200))
    content = Column(Text().with_variant(LONGTEXT(), "mysql"), comment="合同内容")
    file_path = Column(String(500), comment="文件路径")
    file_type = Column(String(10), comment="文件类型")
    file_size = Column(Integer, comment="文件大小")
    file_hash = Column(String(64), comment="文件哈希")
    change_description = Column(Text().with_variant(LONGTEXT(), "mysql"), comment="变更说明")
    creator_id = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())


class ApprovalFlow(Base):
    __tablename__ = "approval_flows"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    flow_template_id = Column(Integer, comment="流程模板 ID")
    flow_type = Column(String(50), comment="流程类型")
    status = Column(String(20), nullable=False, default="pending", comment="流程状态")
    current_node_id = Column(String(50), comment="当前节点 ID")
    current_step = Column(Integer, default=0, comment="当前步骤")
    total_steps = Column(Integer, comment="总步骤数")
    start_time = Column(DateTime, comment="开始时间")
    end_time = Column(DateTime, comment="结束时间")
    duration_hours = Column(Float, comment="耗时（小时）")
    comment = Column(Text, comment="流程备注")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_flow_contract", "contract_id"),
        Index("idx_flow_status", "status"),
    )


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_id = Column(Integer, ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False, comment="步骤序号")
    node_id = Column(String(50), nullable=False, comment="节点 ID")
    node_name = Column(String(100), comment="节点名称")
    approver_id = Column(Integer, nullable=False, comment="审批人 ID")
    approver_name = Column(String(50), comment="审批人姓名")
    action = Column(String(20), comment="审批动作")
    comment = Column(Text, comment="审批意见")
    status = Column(String(20), default="pending", comment="节点状态")
    start_time = Column(DateTime, comment="开始时间")
    complete_time = Column(DateTime, comment="完成时间")
    duration_hours = Column(Float, comment="处理耗时")
    
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_step_flow", "flow_id"),
        Index("idx_step_approver", "approver_id"),
        Index("idx_step_status", "status"),
    )


class AIReview(Base):
    __tablename__ = "ai_reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(Integer, nullable=False, comment="合同版本 ID")
    review_id = Column(String(50), unique=True, nullable=False, comment="审查记录 ID")
    
    # 审查结果
    overall_risk_level = Column(String(20), comment="整体风险等级")
    overall_risk_score = Column(Float, comment="整体风险评分")
    recommendation = Column(Text, comment="审查建议")
    
    # 审查详情
    clause_reviews = Column(Text, comment="条款审查结果 (JSON)")
    rule_violations = Column(Text, comment="规则违规项 (JSON)")
    summary = Column(Text, comment="审查摘要 (JSON)")
    
    # 元数据
    model_version = Column(String(50), comment="模型版本")
    review_duration_seconds = Column(Integer, comment="审查耗时（秒）")
    reviewer_id = Column(Integer, comment="人工复核人 ID")
    review_status = Column(String(20), default="ai_done", comment="pending/reviewing/ai_done/reviewed/confirmed/failed")
    celery_task_id = Column(String(100), comment="Celery 任务 ID")
    
    created_at = Column(DateTime, server_default=func.now())


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(50), nullable=False, comment="预警类型")
    alert_level = Column(String(20), nullable=False, comment="预警等级")
    title = Column(String(200), nullable=False, comment="预警标题")
    message = Column(Text, comment="预警内容")
    source = Column(String(50), comment="来源：ai | rule | manual")
    source_detail = Column(Text, comment="来源详情 (JSON)")
    
    # 处理状态
    status = Column(String(20), default="pending", comment="pending | processing | resolved | ignored")
    handler_id = Column(Integer, comment="处理人 ID")
    handle_comment = Column(Text, comment="处理意见")
    handle_time = Column(DateTime, comment="处理时间")
    
    # 关联信息
    related_clause = Column(String(100), comment="相关条款")
    legal_basis = Column(Text, comment="法律依据")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(50), comment="用户名")
    action = Column(String(100), nullable=False, comment="操作动作")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(Integer, comment="资源 ID")
    resource_name = Column(String(200), comment="资源名称")
    detail = Column(Text, comment="操作详情 (JSON)")
    ip_address = Column(String(50), comment="IP 地址")
    user_agent = Column(Text, comment="浏览器信息")
    status = Column(String(20), default="success", comment="操作状态")
    
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="手机号")
    department_id = Column(Integer, ForeignKey("departments.id"), comment="部门 ID")
    role_id = Column(Integer, ForeignKey("roles.id"), comment="角色 ID")
    status = Column(Integer, default=1, comment="1:启用 0:禁用")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_user_username", "username"),
        Index("idx_user_department", "department_id"),
        Index("idx_user_role", "role_id"),
    )


class Role(Base):
    """角色表"""
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色名称")
    code = Column(String(50), unique=True, nullable=False, comment="角色编码")
    description = Column(Text, comment="角色描述")
    permissions = Column(Text, comment="权限列表 (JSON)")
    status = Column(Integer, default=1, comment="1:启用 0:禁用")
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_role_code", "code"),
    )


class Department(Base):
    """部门表"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="部门名称")
    parent_id = Column(Integer, default=0, comment="父部门 ID")
    level = Column(Integer, default=1, comment="层级")
    path = Column(String(500), comment="部门路径")
    status = Column(Integer, default=1, comment="1:启用 0:禁用")
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_department_parent", "parent_id"),
        Index("idx_department_path", "path"),
    )


class SealRecord(Base):
    """用印记录表"""
    __tablename__ = "seal_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, comment="合同 ID")
    contract_no = Column(String(50), nullable=False, comment="合同编号")
    seal_type = Column(String(50), nullable=False, comment="用印类型：公章 | 合同章 | 财务章")
    seal_method = Column(String(50), comment="用印方式：电子 | 物理")
    status = Column(String(20), default="pending", comment="pending | approved | completed | rejected")
    
    # 审批信息
    approver_id = Column(Integer, comment="审批人 ID")
    approver_name = Column(String(50), comment="审批人姓名")
    approval_time = Column(DateTime, comment="审批时间")
    approval_comment = Column(Text, comment="审批意见")
    
    # 用印信息
    seal_time = Column(DateTime, comment="用印时间")
    seal_operator = Column(String(50), comment="用印操作人")
    seal_image_path = Column(String(500), comment="用印照片路径")
    
    comment = Column(Text, comment="备注")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_seal_contract", "contract_id"),
        Index("idx_seal_status", "status"),
        Index("idx_seal_type", "seal_type"),
    )


class ContractLedger(Base):
    """合同台账表（只读视图/汇总表）"""
    __tablename__ = "contract_ledger"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, nullable=False, comment="合同 ID")
    contract_no = Column(String(50), nullable=False, comment="合同编号")
    title = Column(String(200), nullable=False, comment="合同名称")
    contract_type = Column(String(50), comment="合同类型")
    counterparty_name = Column(String(200), comment="相对方名称")
    amount = Column(Float, comment="合同金额")
    status = Column(String(20), comment="状态")
    start_date = Column(Date, comment="开始日期")
    end_date = Column(Date, comment="结束日期")
    approval_status = Column(String(20), comment="审批状态")
    risk_level = Column(String(20), comment="风险等级")
    creator_name = Column(String(50), comment="创建人姓名")
    department_name = Column(String(100), comment="部门名称")
    created_at = Column(DateTime, comment="创建时间")
    signed_at = Column(DateTime, comment="签署时间")
    archived_at = Column(DateTime, comment="归档时间")
    
    __table_args__ = (
        Index("idx_ledger_contract", "contract_id"),
        Index("idx_ledger_no", "contract_no"),
        Index("idx_ledger_type", "contract_type"),
        Index("idx_ledger_status", "status"),
        Index("idx_ledger_counterparty", "counterparty_name"),
        Index("idx_ledger_time", "created_at"),
    )

