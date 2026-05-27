"""
审批流程领域服务
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.contract import ApprovalFlow, ApprovalStep, Contract, User, Department, AIReview
from app.services.audit_service import log_action
from app.services.contract_state import (
    transition_contract,
    approval_status_for_node,
    initial_approval_status,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 流程配置 (JSON)
# ---------------------------------------------------------------------------

_DEFAULT_FLOW_CONFIG: dict[str, Any] = {
    "standard": {
        "name": "标准审批",
        "nodes": [
            {"node_id": "dept_approval", "node_name": "部门审批", "approver_role": "部门主管"},
        ],
    },
    "simple": {
        "name": "简易审批",
        "nodes": [
            {"node_id": "dept_approval", "node_name": "部门审批", "approver_role": "部门主管"},
        ],
    },
    "large_amount": {
        "name": "大额审批",
        "nodes": [
            {"node_id": "dept_approval", "node_name": "部门审批", "approver_role": "部门主管"},
            {"node_id": "legal_review", "node_name": "法务审查", "approver_role": "法务专员"},
            {"node_id": "finance_review", "node_name": "财务审查", "approver_role": "财务总监"},
            {"node_id": "executive_approval", "node_name": "高管审批", "approver_role": "总经理"},
            {"node_id": "board_approval", "node_name": "董事会审批", "approver_role": "董事长"},
        ],
    },
}

_flow_config_cache: dict[str, Any] | None = None


def _load_flow_config() -> dict[str, Any]:
    """加载流程配置，优先读取 flow_config.json，否则使用内置默认值"""
    global _flow_config_cache
    if _flow_config_cache is not None:
        return _flow_config_cache

    config_path = os.path.join(os.path.dirname(__file__), "flow_config.json")
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _flow_config_cache = json.load(f)
                logger.info("Loaded flow_config.json")
                return _flow_config_cache
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load flow_config.json: %s, using defaults", exc)

    _flow_config_cache = _DEFAULT_FLOW_CONFIG
    return _flow_config_cache


def get_next_node(flow_type: str, current_node_id: str) -> Optional[str]:
    """根据流程配置获取下一个节点 ID"""
    config = _load_flow_config()
    flow_def = config.get(flow_type)
    if not flow_def:
        return None
    nodes = flow_def.get("nodes", [])
    for i, node in enumerate(nodes):
        if node["node_id"] == current_node_id and i + 1 < len(nodes):
            return nodes[i + 1]["node_id"]
    return None


def get_flow_nodes(flow_type: str) -> list[dict[str, Any]]:
    """获取流程类型对应的节点列表"""
    config = _load_flow_config()
    flow_def = config.get(flow_type)
    if not flow_def:
        raise HTTPException(status_code=400, detail=f"未知的流程类型: {flow_type}")
    return flow_def.get("nodes", [])


# ---------------------------------------------------------------------------
# 服务 DTO
# ---------------------------------------------------------------------------


class ApprovalSubmitRequest(BaseModel):
    """提交审批请求"""

    model_config = ConfigDict(extra="forbid")

    contract_id: int
    flow_type: str = "standard"


class ApprovalStepAction(BaseModel):
    """审批步骤操作"""

    model_config = ConfigDict(extra="forbid")

    action: str  # "approve" | "reject" | "return"
    comment: Optional[str] = None


class ApprovalStepResponse(BaseModel):
    """审批步骤响应"""

    model_config = ConfigDict(from_attributes=True)

    step: int
    node_id: str
    node_name: str
    approver_name: str
    action: Optional[str] = None
    comment: Optional[str] = None
    status: str
    duration_hours: Optional[float] = None
    completed_at: Optional[datetime] = None


# 审批节点 → 角色 code（与 seed_dev / roles 表一致）
NODE_TO_ROLE_CODE: dict[str, str] = {
    "dept_approval": "approver",
    "legal_review": "legal",
    "finance_review": "finance",
    "executive_approval": "executive",
    "board_approval": "executive",
}


async def resolve_approver_for_node(
    db: AsyncSession,
    node_id: str,
    fallback_user_id: int,
) -> tuple[int, str]:
    """按节点 ID 解析审批人 user_id 与显示名。"""
    from app.models.contract import Role

    role_code = NODE_TO_ROLE_CODE.get(node_id)
    if not role_code:
        return fallback_user_id, node_id

    result = await db.execute(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.code == role_code, User.status == 1)
        .limit(1)
    )
    user = result.scalar_one_or_none()
    if user:
        return user.id, user.real_name
    return fallback_user_id, role_code


async def submit_approval(
    db: AsyncSession,
    user_id: int,
    username: str,
    req: ApprovalSubmitRequest,
) -> ApprovalFlow:
    """提交合同审批

    1. 校验合同状态为 draft
    2. 根据 flow_type 查找流程模板节点
    3. 创建 approval_flow + approval_steps
    4. 更新合同状态为 pending

    Returns:
        新创建的 ApprovalFlow
    """
    # 获取合同
    result = await db.execute(
        select(Contract).where(Contract.id == req.contract_id)
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    if contract.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"合同状态为 {contract.status}，仅草稿可提交审批",
        )

    # 获取流程节点
    nodes = get_flow_nodes(req.flow_type)

    # 创建审批流程
    flow = ApprovalFlow(
        contract_id=req.contract_id,
        flow_type=req.flow_type,
        status="approving",
        current_node_id=nodes[0]["node_id"],
        current_step=0,
        total_steps=len(nodes),
        start_time=datetime.now(timezone.utc),
    )
    db.add(flow)
    await db.flush()

    # 创建初始审批步骤
    first_node = nodes[0]
    approver_id, approver_name = await resolve_approver_for_node(
        db, first_node["node_id"], user_id
    )
    step = ApprovalStep(
        flow_id=flow.id,
        step_number=1,
        node_id=first_node["node_id"],
        node_name=first_node["node_name"],
        approver_id=approver_id,
        approver_name=approver_name,
        status="pending",
        start_time=datetime.now(timezone.utc),
    )
    db.add(step)
    await db.flush()

    # 根据 AI 审查状态确定初始 approval_status
    ai_result = await db.execute(
        select(AIReview)
        .where(AIReview.contract_id == req.contract_id)
        .order_by(AIReview.created_at.desc())
        .limit(1)
    )
    latest_ai = ai_result.scalar_one_or_none()
    ai_status = latest_ai.review_status if latest_ai else None
    first_status = initial_approval_status(ai_status)

    # 更新合同状态
    await transition_contract(db, contract, "pending", approval_status=first_status)
    contract.current_flow_id = flow.id

    await log_action(
        db=db,
        user_id=user_id,
        action="submit_approval",
        resource_type="contract",
        resource_id=contract.id,
        detail={"username": username, "resource_name": contract.title},
    )

    from app.services.notification_events import notify_approval_pending

    await notify_approval_pending(db, approver_id, contract.id, contract.title)

    await db.refresh(flow)
    return flow


async def approve_step(
    db: AsyncSession,
    user_id: int,
    username: str,
    flow_id: int,
    action: str = "approve",
    comment: Optional[str] = None,
) -> ApprovalFlow:
    """执行审批操作

    1. 校验当前审批人
    2. 插入审批步骤记录
    3. 推进 current_node
    4. 全部审批完成时更新流程状态

    Returns:
        更新后的 ApprovalFlow
    """
    result = await db.execute(
        select(ApprovalFlow).where(ApprovalFlow.id == flow_id)
    )
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")

    if flow.status != "approving":
        raise HTTPException(
            status_code=400,
            detail=f"流程状态为 {flow.status}，当前不可审批",
        )

    flow_type = flow.flow_type or "standard"
    nodes = get_flow_nodes(flow_type)
    current_node_idx = flow.current_step
    if current_node_idx >= len(nodes):
        raise HTTPException(status_code=400, detail="审批步骤已超出预期")

    current_node = nodes[current_node_idx]

    pending_result = await db.execute(
        select(ApprovalStep)
        .where(
            ApprovalStep.flow_id == flow.id,
            ApprovalStep.status == "pending",
        )
        .order_by(ApprovalStep.step_number)
        .limit(1)
    )
    step_record = pending_result.scalar_one_or_none()

    from app.models.contract import Role

    role_row = await db.execute(
        select(Role.code)
        .join(User, User.role_id == Role.id)
        .where(User.id == user_id)
    )
    actor_role = role_row.scalar_one_or_none()

    if step_record and step_record.approver_id:
        allowed = step_record.approver_id == user_id or actor_role == "admin"
        if not allowed:
            raise HTTPException(status_code=403, detail="非当前步骤审批人，无权操作")

    if step_record:
        step_record.approver_id = user_id
        step_record.approver_name = username
        step_record.action = action
        step_record.comment = comment
        step_record.status = "completed"
        step_record.start_time = step_record.start_time or datetime.now(timezone.utc)
        step_record.complete_time = datetime.now(timezone.utc)
    else:
        step_record = ApprovalStep(
            flow_id=flow.id,
            step_number=flow.current_step + 1,
            node_id=current_node["node_id"],
            node_name=current_node["node_name"],
            approver_id=user_id,
            approver_name=username,
            action=action,
            comment=comment,
            status="completed",
            start_time=datetime.now(timezone.utc),
            complete_time=datetime.now(timezone.utc),
        )
        db.add(step_record)

    # 根据动作处理
    if action == "approve":
        flow.current_step += 1

        if flow.current_step >= flow.total_steps:
            # 所有节点审批完成
            flow.status = "approved"
            flow.current_node_id = "done"
            flow.end_time = datetime.now(timezone.utc)

            # 更新合同状态
            contract_result = await db.execute(
                select(Contract).where(Contract.id == flow.contract_id)
            )
            contract = contract_result.scalar_one_or_none()
            if contract:
                await transition_contract(
                    db, contract, "approved", approval_status="seal_pending"
                )
        else:
            # 流转到下一个节点
            next_node_id = get_next_node(flow_type, flow.current_node_id) or "done"
            flow.current_node_id = next_node_id
            contract_result = await db.execute(
                select(Contract).where(Contract.id == flow.contract_id)
            )
            contract = contract_result.scalar_one_or_none()
            if contract:
                contract.approval_status = approval_status_for_node(next_node_id)
            if flow.current_step < len(nodes):
                next_node = nodes[flow.current_step]
                next_approver_id, next_approver_name = await resolve_approver_for_node(
                    db, next_node["node_id"], user_id
                )
                db.add(
                    ApprovalStep(
                        flow_id=flow.id,
                        step_number=flow.current_step + 1,
                        node_id=next_node["node_id"],
                        node_name=next_node["node_name"],
                        approver_id=next_approver_id,
                        approver_name=next_approver_name,
                        status="pending",
                        start_time=datetime.now(timezone.utc),
                    )
                )
                from app.services.notification_events import notify_approval_pending

                contract_result2 = await db.execute(
                    select(Contract).where(Contract.id == flow.contract_id)
                )
                c2 = contract_result2.scalar_one_or_none()
                await notify_approval_pending(
                    db,
                    next_approver_id,
                    flow.contract_id,
                    c2.title if c2 else f"#{flow.contract_id}",
                )

    elif action == "reject":
        flow.status = "rejected"
        flow.end_time = datetime.now(timezone.utc)
        contract_result = await db.execute(
            select(Contract).where(Contract.id == flow.contract_id)
        )
        contract = contract_result.scalar_one_or_none()
        if contract:
            await transition_contract(db, contract, "rejected", approval_status="rejected")

    elif action == "return":
        flow.status = "returned"
        flow.end_time = datetime.now(timezone.utc)
    else:
        raise HTTPException(status_code=400, detail=f"未知的审批动作: {action}")

    await db.flush()

    await log_action(
        db=db,
        user_id=user_id,
        action=f"{action}_step",
        resource_type="approval",
        resource_id=flow.id,
        detail={"username": username, "resource_name": f"审批流程 #{flow.id}"},
    )

    await db.refresh(flow)
    return flow


async def delegate_step(
    db: AsyncSession,
    user_id: int,
    username: str,
    flow_id: int,
    delegate_to: int,
    comment: Optional[str] = None,
) -> ApprovalFlow:
    """审批委托：将当前 pending 步骤转交他人。"""
    result = await db.execute(select(ApprovalFlow).where(ApprovalFlow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")
    if flow.status != "approving":
        raise HTTPException(status_code=400, detail=f"流程状态为 {flow.status}，无法委托")

    pending_result = await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.flow_id == flow.id, ApprovalStep.status == "pending")
        .order_by(ApprovalStep.step_number)
        .limit(1)
    )
    step_record = pending_result.scalar_one_or_none()
    if not step_record:
        raise HTTPException(status_code=400, detail="无待处理审批步骤")

    from app.models.contract import Role

    role_row = await db.execute(
        select(Role.code).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    actor_role = role_row.scalar_one_or_none()
    if step_record.approver_id:
        allowed = step_record.approver_id == user_id or actor_role == "admin"
        if not allowed:
            raise HTTPException(status_code=403, detail="非当前步骤审批人，无权委托")

    delegate_user = await db.get(User, delegate_to)
    if not delegate_user or delegate_user.status != 1:
        raise HTTPException(status_code=400, detail="被委托人不存在或已禁用")

    step_record.approver_id = delegate_to
    step_record.approver_name = delegate_user.real_name or delegate_user.username
    if comment:
        step_record.comment = comment

    contract_result = await db.execute(select(Contract).where(Contract.id == flow.contract_id))
    contract = contract_result.scalar_one_or_none()
    from app.services.notification_events import notify_approval_pending

    await notify_approval_pending(
        db,
        delegate_to,
        flow.contract_id,
        contract.title if contract else f"#{flow.contract_id}",
    )

    await log_action(
        db=db,
        user_id=user_id,
        action="delegate_step",
        resource_type="approval",
        resource_id=flow.id,
        detail={
            "username": username,
            "delegate_to": delegate_to,
            "resource_name": f"审批流程 #{flow.id}",
        },
    )
    await db.flush()
    await db.refresh(flow)
    return flow


async def reject_step(
    db: AsyncSession,
    user_id: int,
    username: str,
    flow_id: int,
    comment: Optional[str] = None,
) -> ApprovalFlow:
    """驳回审批（approve_step 的便捷封装）"""
    return await approve_step(
        db, user_id, username, flow_id, action="reject", comment=comment
    )


async def return_to_draft(
    db: AsyncSession,
    user_id: int,
    username: str,
    flow_id: int,
    comment: Optional[str] = None,
) -> ApprovalFlow:
    """退回至草稿

    1. 更新审批流程状态为 returned
    2. 将合同状态回退至 draft
    """
    result = await db.execute(
        select(ApprovalFlow).where(ApprovalFlow.id == flow_id)
    )
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")

    if flow.status not in ("approving", "pending"):
        raise HTTPException(
            status_code=400,
            detail=f"流程状态为 {flow.status}，无法退回草稿",
        )

    pending_result = await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.flow_id == flow.id, ApprovalStep.status == "pending")
        .order_by(ApprovalStep.step_number)
        .limit(1)
    )
    step_record = pending_result.scalar_one_or_none()
    from app.models.contract import Role

    role_row = await db.execute(
        select(Role.code).join(User, User.role_id == Role.id).where(User.id == user_id)
    )
    actor_role = role_row.scalar_one_or_none()
    if step_record and step_record.approver_id:
        allowed = step_record.approver_id == user_id or actor_role == "admin"
        if not allowed:
            raise HTTPException(status_code=403, detail="非当前步骤审批人，无权操作")

    flow.status = "returned"
    flow.end_time = datetime.now(timezone.utc)

    contract_result = await db.execute(
        select(Contract).where(Contract.id == flow.contract_id)
    )
    contract = contract_result.scalar_one_or_none()
    if contract:
        await transition_contract(db, contract, "draft", approval_status="returned")

    await log_action(
        db=db,
        user_id=user_id,
        action="return_to_draft",
        resource_type="approval",
        resource_id=flow.id,
        detail={"username": username, "resource_name": f"审批流程 #{flow.id}"},
    )

    await db.flush()
    await db.refresh(flow)
    return flow


async def get_pending_approvals(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    contract_type: Optional[str] = None,
) -> dict:
    """获取待办审批列表 — 仅返回当前用户为 pending 步骤审批人的流程。"""
    conditions = [
        ApprovalFlow.status == "approving",
        ApprovalStep.status == "pending",
        ApprovalStep.approver_id == user_id,
    ]
    if contract_type:
        conditions.append(Contract.contract_type == contract_type)

    count_query = (
        select(func.count())
        .select_from(ApprovalFlow)
        .join(ApprovalStep, ApprovalStep.flow_id == ApprovalFlow.id)
        .join(Contract, ApprovalFlow.contract_id == Contract.id)
        .where(*conditions)
    )
    total = await db.scalar(count_query)

    query = (
        select(ApprovalFlow, Contract)
        .join(ApprovalStep, ApprovalStep.flow_id == ApprovalFlow.id)
        .join(Contract, ApprovalFlow.contract_id == Contract.id)
        .where(*conditions)
        .order_by(ApprovalFlow.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for flow, contract in rows:
        items.append(
            {
                "flow_id": flow.id,
                "contract_id": contract.id,
                "contract_no": contract.contract_no,
                "title": contract.title,
                "contract_title": contract.title,
                "amount": contract.amount,
                "current_node": flow.current_node_id,
                "current_step": flow.current_step,
                "flow_type": flow.flow_type,
                "ai_risk_level": contract.risk_level or "unknown",
                "created_at": flow.created_at,
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


async def get_approval_history(
    db: AsyncSession,
    flow_id: int,
) -> dict:
    """获取审批历史

    RETURN: 按 step_number 排序的审批步骤列表
    """
    result = await db.execute(
        select(ApprovalFlow).where(ApprovalFlow.id == flow_id)
    )
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="审批流程不存在")

    step_result = await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.flow_id == flow_id)
        .order_by(ApprovalStep.step_number)
    )
    steps = step_result.scalars().all()

    step_list = []
    for s in steps:
        step_list.append(
            {
                "step": s.step_number,
                "node_id": s.node_id,
                "node_name": s.node_name,
                "approver_id": s.approver_id,
                "approver_name": s.approver_name,
                "action": s.action,
                "comment": s.comment,
                "status": s.status,
                "duration_hours": s.duration_hours,
                "completed_at": s.complete_time,
                "created_at": s.created_at,
            }
        )

    return {
        "flow_id": flow_id,
        "status": flow.status,
        "flow_type": flow.flow_type,
        "current_node": flow.current_node_id,
        "total_steps": flow.total_steps,
        "steps": step_list,
    }
