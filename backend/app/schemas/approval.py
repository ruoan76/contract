"""
审批流程 Pydantic Schema (Pydantic v2)

注意: ApprovalSubmit, ApprovalAction, ApprovalNodeResponse, ApprovalFlowResponse
已在 schemas/contract.py 中定义（为兼容原有 API），此处提供完整版本。
新项目应优先使用本模块的 schema。
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ==================== 审批提交 ====================

class ApprovalSubmitRequest(BaseModel):
    """提交审批请求"""
    contract_id: int = Field(..., description="合同 ID")
    flow_type: str = Field(default="standard", description="审批流程类型")


class ApprovalSubmitResponse(BaseModel):
    """提交审批响应"""
    code: int = Field(default=200)
    flow_id: int = Field(..., description="审批流程 ID")
    status: str = Field(..., description="流程状态")
    current_node: str = Field(..., description="当前审批节点")
    next_approvers: Optional[List[dict]] = Field(None, description="下一审批人列表")


# ==================== 审批操作 ====================

class ApprovalActionRequest(BaseModel):
    """审批操作请求"""
    action: str = Field(
        ...,
        description="审批动作: approve | reject | return | delegate | countersign"
    )
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")
    delegate_to: Optional[int] = Field(None, description="转交人 ID（delegate 操作时有效）")


# ==================== 审批节点 ====================

class ApprovalStepResponse(BaseModel):
    """审批步骤（节点）响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    flow_id: int
    step_number: int = Field(..., description="步骤序号")
    node_id: str = Field(..., description="节点 ID")
    node_name: Optional[str] = Field(None, description="节点名称")
    approver_id: int = Field(..., description="审批人 ID")
    approver_name: Optional[str] = Field(None, description="审批人姓名")
    action: Optional[str] = Field(None, description="审批动作")
    comment: Optional[str] = Field(None, description="审批意见")
    status: str = Field(default="pending", description="节点状态")
    start_time: Optional[datetime] = None
    complete_time: Optional[datetime] = Field(None, description="完成时间")
    duration_hours: Optional[float] = Field(None, description="处理耗时（小时）")
    created_at: datetime


class ApprovalFlowDetail(BaseModel):
    """审批流程详情"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_id: int
    flow_template_id: Optional[int] = None
    flow_type: Optional[str] = None
    status: str = Field(default="pending", description="流程状态")
    current_node_id: Optional[str] = Field(None, description="当前节点 ID")
    current_step: int = Field(default=0, description="当前步骤")
    total_steps: Optional[int] = Field(None, description="总步骤数")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ==================== 审批流程响应 ====================

class ApprovalFlowResponse(BaseModel):
    """审批流程响应"""
    flow_id: int = Field(..., description="审批流程 ID")
    status: str = Field(..., description="流程状态")
    current_node: str = Field(..., description="当前节点")
    progress: int = Field(..., description="当前进度")
    total_steps: int = Field(..., description="总步骤数")
    steps: List[dict] = Field(default_factory=list)


class ApprovalFlowListResponse(BaseModel):
    """审批流程列表响应"""
    code: int = Field(default=200)
    data: dict = Field(default_factory=dict)


# ==================== 待办审批 ====================

class PendingApprovalItem(BaseModel):
    """待办审批项"""
    flow_id: int
    contract_id: int
    contract_no: str
    title: str
    amount: Optional[float] = None
    current_node: str
    initiator_name: Optional[str] = None
    created_at: datetime
    urgency: Optional[str] = Field(None, description="紧急程度: high | medium | low")


class PendingApprovalListResponse(BaseModel):
    """待办审批列表"""
    total: int
    page: int
    page_size: int
    items: List[PendingApprovalItem]


# ==================== 审批模板（预留） ====================

class ApprovalTemplateCreate(BaseModel):
    """创建审批模板"""
    name: str = Field(..., max_length=100, description="模板名称")
    code: str = Field(..., max_length=50, description="模板编码")
    description: Optional[str] = Field(None, description="模板描述")
    steps: List[dict] = Field(..., description="审批步骤配置 (JSON)")
    enabled: bool = Field(default=True, description="是否启用")


class ApprovalTemplateUpdate(BaseModel):
    """更新审批模板"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    steps: Optional[List[dict]] = None
    enabled: Optional[bool] = None


class ApprovalTemplateResponse(BaseModel):
    """审批模板响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: Optional[str] = None
    steps: Optional[List[dict]] = None
    enabled: bool = True
    created_at: datetime
