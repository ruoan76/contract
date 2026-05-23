"""
AI 审查相关 Pydantic Schema (Pydantic v2)
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime


# ==================== AI 审查请求 ====================

class AIReviewRequest(BaseModel):
    """发起 AI 审查"""
    contract_id: int = Field(..., description="合同 ID")
    version_id: Optional[int] = Field(None, description="合同版本 ID，默认取最新版本")


class AIReviewResult(BaseModel):
    """AI 审查结果"""
    review_id: str = Field(..., description="审查记录 ID")
    status: str = Field(..., description="审查状态: reviewing | completed | failed")
    overall: Optional[dict] = Field(None, description="总体评估")
    clauses: Optional[List[dict]] = Field(None, description="条款级审查结果")
    rule_violations: Optional[List[dict]] = Field(None, description="规则违规项")
    summary: Optional[dict] = Field(None, description="审查摘要")
    review_time: Optional[datetime] = Field(None, description="审查时间")


# ==================== AI 审查完整响应 ====================

class AIReviewResponse(BaseModel):
    """AI 审查完整响应（对应 AIReview ORM 模型）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    version_id: int = Field(..., description="合同版本 ID")
    review_id: str = Field(..., description="审查记录 ID")
    status: Optional[str] = Field(None, description="审查状态")
    overall_risk_level: Optional[str] = Field(None, description="整体风险等级")
    overall_risk_score: Optional[float] = Field(None, description="整体风险评分")
    recommendation: Optional[str] = Field(None, description="审查建议")
    clause_reviews: Optional[Any] = Field(None, description="条款审查结果 (JSON)")
    rule_violations: Optional[Any] = Field(None, description="规则违规项 (JSON)")
    summary: Optional[Any] = Field(None, description="审查摘要 (JSON)")
    model_version: Optional[str] = Field(None, description="AI 模型版本")
    review_duration_seconds: Optional[int] = Field(None, description="审查耗时（秒）")
    reviewer_id: Optional[int] = Field(None, description="人工复核人 ID")
    review_status: str = Field(default="ai_done", description="ai_done | reviewed | confirmed")
    created_at: datetime


class AIReviewListResponse(BaseModel):
    """AI 审查列表"""
    total: int
    page: int
    page_size: int
    items: List[AIReviewResponse]


# ==================== 风险预警 ====================

class RiskAlertResponse(BaseModel):
    """风险预警响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    alert_type: str = Field(..., description="预警类型")
    alert_level: str = Field(..., description="预警等级")
    title: str = Field(..., description="预警标题")
    message: Optional[str] = Field(None, description="预警内容")
    source: Optional[str] = Field(None, description="来源：ai | rule | manual")
    source_detail: Optional[Any] = Field(None, description="来源详情 (JSON)")
    status: str = Field(default="pending", description="pending | processing | resolved | ignored")
    handler_id: Optional[int] = Field(None, description="处理人 ID")
    handle_comment: Optional[str] = Field(None, description="处理意见")
    handle_time: Optional[datetime] = Field(None, description="处理时间")
    related_clause: Optional[str] = Field(None, description="相关条款")
    legal_basis: Optional[str] = Field(None, description="法律依据")
    created_at: datetime
    updated_at: Optional[datetime] = None


class RiskAlertCreate(BaseModel):
    """创建风险预警"""
    contract_id: int = Field(..., description="合同 ID")
    alert_type: str = Field(..., max_length=50, description="预警类型")
    alert_level: str = Field(..., max_length=20, description="预警等级")
    title: str = Field(..., max_length=200, description="预警标题")
    message: Optional[str] = Field(None, description="预警内容")
    source: Optional[str] = Field(None, max_length=50, description="来源")
    related_clause: Optional[str] = Field(None, max_length=100, description="相关条款")
    legal_basis: Optional[str] = Field(None, description="法律依据")


class RiskAlertUpdate(BaseModel):
    """更新风险预警"""
    status: Optional[str] = Field(None, description="pending | processing | resolved | ignored")
    handler_id: Optional[int] = Field(None, description="处理人 ID")
    handle_comment: Optional[str] = Field(None, description="处理意见")


class RiskAlertListResponse(BaseModel):
    """风险预警列表"""
    total: int
    page: int
    page_size: int
    items: List[RiskAlertResponse]


# ==================== 审计日志 ====================

class AuditLogResponse(BaseModel):
    """审计日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: Optional[str] = Field(None, description="用户名")
    action: str = Field(..., description="操作动作")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[int] = Field(None, description="资源 ID")
    resource_name: Optional[str] = Field(None, description="资源名称")
    detail: Optional[Any] = Field(None, description="操作详情 (JSON)")
    ip_address: Optional[str] = Field(None, description="IP 地址")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    status: str = Field(default="success", description="操作状态")
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """审计日志列表"""
    total: int
    page: int
    page_size: int
    items: List[AuditLogResponse]


# ==================== 用印记录 ====================

class SealRecordResponse(BaseModel):
    """用印记录响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    contract_no: str = Field(..., description="合同编号")
    seal_type: str = Field(..., description="用印类型：公章 | 合同章 | 财务章")
    seal_method: Optional[str] = Field(None, description="用印方式：电子 | 物理")
    status: str = Field(default="pending", description="pending | approved | completed | rejected")
    approver_id: Optional[int] = Field(None, description="审批人 ID")
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    approval_time: Optional[datetime] = Field(None, description="审批时间")
    approval_comment: Optional[str] = Field(None, description="审批意见")
    seal_time: Optional[datetime] = Field(None, description="用印时间")
    seal_operator: Optional[str] = Field(None, description="用印操作人")
    seal_image_path: Optional[str] = Field(None, description="用印照片路径")
    comment: Optional[str] = Field(None, description="备注")
    created_at: datetime
    updated_at: Optional[datetime] = None


class SealRecordCreate(BaseModel):
    """创建用印记录"""
    contract_id: int = Field(..., description="合同 ID")
    seal_type: str = Field(..., max_length=50, description="用印类型")
    seal_method: Optional[str] = Field(None, max_length=50, description="用印方式")


class SealRecordListResponse(BaseModel):
    """用印记录列表"""
    total: int
    page: int
    page_size: int
    items: List[SealRecordResponse]


# ==================== 合同台账 ====================

class ContractLedgerResponse(BaseModel):
    """合同台账响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    contract_no: str
    title: str
    contract_type: Optional[str] = None
    counterparty_name: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    approval_status: Optional[str] = None
    risk_level: Optional[str] = None
    creator_name: Optional[str] = None
    department_name: Optional[str] = None
    created_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


class ContractLedgerListResponse(BaseModel):
    """合同台账列表"""
    total: int
    page: int
    page_size: int
    items: List[ContractLedgerResponse]
