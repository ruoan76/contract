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
