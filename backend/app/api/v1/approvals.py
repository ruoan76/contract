"""
审批流程 API
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_any_role
from app.db.database import get_db
from app.models.contract import ApprovalFlow, User
from app.schemas.contract import ApprovalSubmit, ApprovalAction
from app.services.approval_service import (
    ApprovalSubmitRequest,
    approve_step,
    get_approval_history,
    get_pending_approvals,
    reject_step,
    return_to_draft,
    submit_approval,
)
from app.utils.auth import get_current_user

router = APIRouter()


def _flow_to_dict(flow: ApprovalFlow) -> dict:
    """将 ApprovalFlow ORM 转为 API 响应 dict。"""
    return {
        "flow_id": flow.id,
        "contract_id": flow.contract_id,
        "flow_type": flow.flow_type,
        "status": flow.status,
        "current_node_id": flow.current_node_id,
        "current_step": flow.current_step,
        "total_steps": flow.total_steps,
        "start_time": flow.start_time.isoformat() if flow.start_time else None,
        "end_time": flow.end_time.isoformat() if flow.end_time else None,
        "created_at": flow.created_at.isoformat() if flow.created_at else None,
    }


@router.post("/submit", summary="提交审批")
async def submit(
    body: ApprovalSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交合同审批"""
    flow = await submit_approval(
        db=db,
        user_id=user.id,
        username=user.real_name,
        req=ApprovalSubmitRequest(
            contract_id=body.contract_id,
            flow_type=body.flow_type,
        ),
    )
    return {"code": 200, "data": _flow_to_dict(flow)}


# 审批操作角色：部门主管 + 各评审节点角色（V1 role 级，节点级 Stretch）
_APPROVAL_ROLES = require_any_role("approver", "legal", "finance", "executive", "admin")


@router.post("/{flow_id}/approve", summary="审批操作")
async def approve(
    flow_id: int,
    action_in: ApprovalAction,
    user: User = Depends(_APPROVAL_ROLES),
    db: AsyncSession = Depends(get_db),
):
    """执行审批操作：approve / reject / return"""
    action = action_in.action
    if action == "return":
        flow = await return_to_draft(
            db=db,
            user_id=user.id,
            username=user.real_name,
            flow_id=flow_id,
            comment=action_in.comment,
        )
    elif action == "reject":
        flow = await reject_step(
            db=db,
            user_id=user.id,
            username=user.real_name,
            flow_id=flow_id,
            comment=action_in.comment,
        )
    elif action == "approve":
        flow = await approve_step(
            db=db,
            user_id=user.id,
            username=user.real_name,
            flow_id=flow_id,
            action="approve",
            comment=action_in.comment,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的审批动作: {action}",
        )
    return {"code": 200, "data": _flow_to_dict(flow)}


@router.get("/pending", summary="待办列表")
async def pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_type: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取待办审批列表"""
    result = await get_pending_approvals(
        db=db,
        user_id=user.id,
        page=page,
        page_size=page_size,
        contract_type=contract_type,
    )
    return {"code": 200, "data": result}


@router.get("/{flow_id}/history", summary="审批历史")
async def history(
    flow_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取审批历史"""
    result = await get_approval_history(db=db, flow_id=flow_id)
    return {"code": 200, "data": result}
