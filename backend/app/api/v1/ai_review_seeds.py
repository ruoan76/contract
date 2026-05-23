# -*- coding: utf-8 -*-
"""AI 审查种子数据只读 API（无需数据库）。"""

from fastapi import APIRouter, HTTPException, Query

from app.services.ai_review.seed_store import (
    SeedStoreError,
    get_contract_type_map,
    get_cuad_bridge,
    get_manifest,
    get_review_checklists,
    get_revision_routing,
    get_risk_labels,
    get_risk_templates_purchase,
    reload_cache,
)

router = APIRouter()


def _wrap(data: dict) -> dict:
    return {"code": 200, "data": data}


@router.get("/seeds/manifest", summary="种子元数据")
async def seeds_manifest():
    try:
        return _wrap(get_manifest())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/risk-labels", summary="15 风险标签")
async def seeds_risk_labels():
    try:
        return _wrap(get_risk_labels())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/revision-routing", summary="修订方式路由规则")
async def seeds_revision_routing():
    try:
        return _wrap(get_revision_routing())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/review-checklists", summary="审查清单")
async def seeds_checklists(
    auto_detectable_only: bool = Query(False, description="仅返回可规则检测项"),
    gate_id: str | None = Query(None, description="按门禁过滤，如 gate_validity"),
):
    try:
        payload = get_review_checklists()
        items = payload.get("items", [])
        if auto_detectable_only:
            items = [i for i in items if i.get("auto_detectable")]
        if gate_id:
            items = [i for i in items if i.get("gate_id") == gate_id]
        return _wrap(
            {
                "version": payload.get("version"),
                "count": len(items),
                "items": items,
            }
        )
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/contract-type-map", summary="平台合同类型映射")
async def seeds_contract_type_map():
    try:
        return _wrap(get_contract_type_map())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/cuad-bridge", summary="风险标签与 CUAD 对照")
async def seeds_cuad_bridge():
    try:
        return _wrap(get_cuad_bridge())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/seeds/risk-templates/purchase", summary="采购类风险模板子集")
async def seeds_templates_purchase():
    try:
        return _wrap(get_risk_templates_purchase())
    except SeedStoreError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/seeds/reload", summary="重载种子缓存（开发）")
async def seeds_reload():
    reload_cache()
    return _wrap({"reloaded": True})
