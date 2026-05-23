# -*- coding: utf-8 -*-
"""从 backend/seeds/ai_review/generated 加载 JSON 种子（内存缓存）。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

# backend/seeds/ai_review/generated
SEEDS_DIR = Path(__file__).resolve().parents[3] / "seeds" / "ai_review" / "generated"


class SeedStoreError(Exception):
    pass


def _read_json(name: str) -> dict[str, Any]:
    path = SEEDS_DIR / name
    if not path.is_file():
        raise SeedStoreError(f"种子文件不存在: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SeedStoreError(f"种子 JSON 解析失败: {path}") from e


@lru_cache(maxsize=1)
def get_manifest() -> dict[str, Any]:
    return _read_json("manifest.json")


@lru_cache(maxsize=1)
def get_risk_labels() -> dict[str, Any]:
    return _read_json("risk_labels.json")


@lru_cache(maxsize=1)
def get_revision_routing() -> dict[str, Any]:
    return _read_json("revision_routing.json")


@lru_cache(maxsize=1)
def get_review_checklists() -> dict[str, Any]:
    return _read_json("review_checklists.json")


@lru_cache(maxsize=1)
def get_contract_type_map() -> dict[str, Any]:
    return _read_json("contract_type_map.json")


@lru_cache(maxsize=1)
def get_cuad_bridge() -> dict[str, Any]:
    return _read_json("cuad_label_bridge.json")


@lru_cache(maxsize=1)
def get_risk_templates_purchase() -> dict[str, Any]:
    return _read_json("risk_templates.purchase.json")


def reload_cache() -> None:
    """开发时热重载（清除 lru_cache）。"""
    for fn in (
        get_manifest,
        get_risk_labels,
        get_revision_routing,
        get_review_checklists,
        get_contract_type_map,
        get_cuad_bridge,
        get_risk_templates_purchase,
    ):
        fn.cache_clear()
