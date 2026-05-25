"""
配置服务 — 阈值等持久化（JSON 文件）
"""
import json
import os
from typing import Any

from app.services.flow_match_service import _load_thresholds

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_THRESHOLDS_FILE = os.path.join(_CONFIG_DIR, "thresholds.json")

_DEFAULT = {
    "simple_max": 100000,
    "standard_max": 1000000,
    "board_threshold": 1000000,
}


def _ensure_dir() -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def get_thresholds() -> dict:
    if os.path.isfile(_THRESHOLDS_FILE):
        try:
            with open(_THRESHOLDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    loaded = _load_thresholds()
    return {
        "simple_max": loaded.get("simple_max", _DEFAULT["simple_max"]),
        "standard_max": loaded.get("standard_max", _DEFAULT["standard_max"]),
        "board_threshold": loaded.get("standard_max", _DEFAULT["board_threshold"]),
    }


def update_thresholds(data: dict[str, Any]) -> dict:
    _ensure_dir()
    current = get_thresholds()
    current.update({k: v for k, v in data.items() if k in _DEFAULT})
    with open(_THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current


_APPROVERS_FILE = os.path.join(_CONFIG_DIR, "approvers.json")

_DEFAULT_APPROVERS = [
    {"id": 1, "flow_type": "simple", "step": 1, "role": "approver", "user_id": 2, "user_name": "部门主管"},
    {"id": 2, "flow_type": "standard", "step": 1, "role": "approver", "user_id": 2, "user_name": "部门主管"},
    {"id": 3, "flow_type": "standard", "step": 2, "role": "legal", "user_id": 3, "user_name": "法务专员"},
]


def get_approvers() -> list[dict]:
    if os.path.isfile(_APPROVERS_FILE):
        try:
            with open(_APPROVERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return list(_DEFAULT_APPROVERS)


def _save_approvers(items: list[dict]) -> list[dict]:
    _ensure_dir()
    with open(_APPROVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return items


def add_approver(data: dict) -> dict:
    items = get_approvers()
    next_id = max((i.get("id", 0) for i in items), default=0) + 1
    item = {
        "id": next_id,
        "flow_type": data.get("flow_type", "standard"),
        "step": int(data.get("step", 1)),
        "role": data.get("role", "approver"),
        "user_id": data.get("user_id"),
        "user_name": data.get("user_name", ""),
    }
    items.append(item)
    _save_approvers(items)
    return item


def update_approver(approver_id: int, data: dict) -> dict:
    items = get_approvers()
    for i, item in enumerate(items):
        if item.get("id") == approver_id:
            item.update({k: v for k, v in data.items() if k in ("flow_type", "step", "role", "user_id", "user_name")})
            items[i] = item
            _save_approvers(items)
            return item
    raise ValueError(f"approver {approver_id} not found")
