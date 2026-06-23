"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import date, datetime


# ==================== 合同 ====================

class ContractBase(BaseModel):
    """合同基础模型"""
    title: str = Field(..., max_length=200, description="合同名称")
    contract_type: str = Field(..., description="合同类型")
    counterparty_id: Optional[int] = Field(None, description="相对方 ID")
    counterparty_name: str = Field(..., max_length=200, description="对方单位名称")
    counterparty_credit_code: Optional[str] = Field(None, description="统一社会信用代码")
    amount: Optional[float] = Field(None, description="合同金额")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")


class ContractCreate(ContractBase):
    """创建合同"""
    content: Optional[str] = Field(None, description="合同内容")
    template_id: Optional[int] = Field(None, description="引用的合同模板 ID")
    template_version: Optional[int] = Field(None, description="引用模板版本号")
    template_values: Optional[dict[str, Any]] = Field(None, description="模板变量填充值")


class ContractUpdate(BaseModel):
    """更新合同"""
    title: Optional[str] = None
    contract_type: Optional[str] = None
    counterparty_name: Optional[str] = None
    amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    content: Optional[str] = None


class ContractResponse(ContractBase):
    """合同响应"""
    id: int
    contract_no: str
    status: str
    approval_status: str
    risk_level: str
    template_id: Optional[int] = None
    template_version: Optional[int] = None
    sign_date: Optional[date] = None
    sign_method: Optional[str] = None
    archive_date: Optional[date] = None
    creator_id: int
    department_id: Optional[int] = None
    content: Optional[str] = None
    current_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    """合同列表响应"""
    total: int
    page: int
    page_size: int
    items: List[ContractResponse]


# ==================== 审批流程 ====================

class ApprovalSubmit(BaseModel):
    """提交审批"""
    contract_id: int
    flow_type: str = "standard"


class ApprovalAction(BaseModel):
    """审批操作"""
    action: str = Field(..., description="approve | reject | return | delegate | countersign")
    comment: Optional[str] = Field(None, description="审批意见")
    delegate_to: Optional[int] = Field(None, description="转交人 ID（delegate 操作时有效）")


class ApprovalNodeResponse(BaseModel):
    """审批节点响应"""
    step: int
    node_name: str
    approver_name: str
    action: Optional[str] = None
    comment: Optional[str] = None
    status: str
    duration_hours: Optional[float] = None
    completed_at: Optional[datetime] = None


class ApprovalFlowResponse(BaseModel):
    """审批流程响应"""
    flow_id: int
    status: str
    current_node: str
    progress: int
    total_steps: int
    steps: List[ApprovalNodeResponse]


# ==================== AI 审查 ====================

class AIReviewRequest(BaseModel):
    """AI 审查请求"""
    contract_id: int
    review_options: Optional[dict] = None


class AIReviewResult(BaseModel):
    """AI 审查结果"""
    review_id: str
    status: str
    overall: Optional[dict] = None
    clauses: Optional[List[dict]] = None
    rule_violations: Optional[List[dict]] = None
    summary: Optional[dict] = None
    review_time: Optional[datetime] = None


# ==================== 风险预警 ====================

class RiskAlertResponse(BaseModel):
    """风险预警响应"""
    id: int
    contract_id: int
    contract_no: str
    alert_type: str
    alert_level: str
    title: str
    message: str
    source: str
    status: str
    created_at: datetime


class RiskHandleRequest(BaseModel):
    """风险处理请求"""
    status: str = Field(..., description="resolved | ignored")
    comment: Optional[str] = Field(None, description="处理意见")


# ==================== 统计 ====================

class ContractStatistics(BaseModel):
    """合同统计"""
    total_contracts: int
    total_amount: float
    by_type: List[dict]
    by_status: List[dict]
    by_risk_level: List[dict]


class ApprovalEfficiency(BaseModel):
    """审批效率"""
    avg_approval_hours: float
    max_approval_hours: float
    min_approval_hours: float
    overtime_rate: float
    bottleneck_nodes: List[dict]
