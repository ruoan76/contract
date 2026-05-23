"""
配置 API
"""
from fastapi import APIRouter, Depends

from app.core.rbac import require_role
from app.models.contract import User
from app.services.config_service import get_thresholds, update_thresholds
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
