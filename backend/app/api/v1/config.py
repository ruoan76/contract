"""
配置 API
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.rbac import require_role
from app.models.contract import User
from app.services.config_service import (
    add_approver,
    delete_approver,
    get_approvers,
    get_flow_nodes_config,
    get_thresholds,
    update_approver,
    update_thresholds,
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/thresholds", summary="获取审批阈值")
async def read_thresholds():
    return {"code": 200, "data": get_thresholds()}


@router.put("/thresholds", summary="更新审批阈值")
async def write_thresholds(
    body: dict,
    user: User = Depends(require_role("admin")),
):
    data = update_thresholds(body)
    return {"code": 200, "data": data}


@router.get("/approvers", summary="审批人配置列表")
async def read_approvers():
    return {"code": 200, "data": get_approvers()}


@router.post("/approvers", summary="新增审批人配置")
async def create_approver(
    body: dict,
    user: User = Depends(require_role("admin")),
):
    data = add_approver(body)
    return {"code": 200, "data": data}


@router.put("/approvers/{approver_id}", summary="更新审批人配置")
async def patch_approver(
    approver_id: int,
    body: dict,
    user: User = Depends(require_role("admin")),
):
    try:
        data = update_approver(approver_id, body)
        return {"code": 200, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/approvers/{approver_id}", summary="删除审批人配置")
async def remove_approver(
    approver_id: int,
    user: User = Depends(require_role("admin")),
):
    try:
        delete_approver(approver_id)
        return {"code": 200, "data": None}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/flow-nodes", summary="当前运行时流程节点（来自 flow_config）")
async def read_flow_nodes(flow_type: str | None = None):
    data = get_flow_nodes_config(flow_type)
    return {"code": 200, "data": data}
