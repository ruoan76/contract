"""
流程类型匹配服务
"""
import json
import os
from typing import Optional

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_THRESHOLDS_FILE = os.path.join(_CONFIG_DIR, "thresholds.json")
from app.services.config_service import FLOW_CONFIG_FILE as _FLOW_CONFIG_FILE

_DEFAULT_THRESHOLDS = {
    "simple_max": 100000,
    "standard_max": 1000000,
    "board_threshold": 1000000,
    "flow_mapping": {
        "simple": "simple",
        "standard": "standard",
        "special": "large_amount",
    },
}

_thresholds_cache: dict | None = None


def clear_thresholds_cache() -> None:
    global _thresholds_cache
    _thresholds_cache = None


def _load_thresholds() -> dict:
    global _thresholds_cache
    if _thresholds_cache is not None:
        return _thresholds_cache

    if os.path.isfile(_THRESHOLDS_FILE):
        try:
            with open(_THRESHOLDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _thresholds_cache = {
                        "simple_max": data.get("simple_max", _DEFAULT_THRESHOLDS["simple_max"]),
                        "standard_max": data.get("standard_max", _DEFAULT_THRESHOLDS["standard_max"]),
                        "board_threshold": data.get(
                            "board_threshold",
                            data.get("standard_max", _DEFAULT_THRESHOLDS["board_threshold"]),
                        ),
                    }
                    return _thresholds_cache
        except (json.JSONDecodeError, OSError):
            pass

    if os.path.isfile(_FLOW_CONFIG_FILE):
        try:
            with open(_FLOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                th = data.get("thresholds", _DEFAULT_THRESHOLDS)
                _thresholds_cache = {
                    "simple_max": th.get("simple_max", _DEFAULT_THRESHOLDS["simple_max"]),
                    "standard_max": th.get("standard_max", _DEFAULT_THRESHOLDS["standard_max"]),
                    "board_threshold": th.get(
                        "board_threshold",
                        th.get("standard_max", _DEFAULT_THRESHOLDS["board_threshold"]),
                    ),
                }
                return _thresholds_cache
        except (json.JSONDecodeError, OSError):
            pass

    _thresholds_cache = dict(_DEFAULT_THRESHOLDS)
    return _thresholds_cache


def match_flow_type(amount: Optional[float] = None, contract_type: Optional[str] = None) -> str:
    """按金额匹配流程类型：simple / standard / large_amount。"""
    thresholds = _load_thresholds()
    simple_max = thresholds.get("simple_max", 100000)
    standard_max = thresholds.get("standard_max", 1000000)

    if amount is None or amount < simple_max:
        return "simple"
    if amount < standard_max:
        return "standard"
    return "large_amount"


def get_flow_match_detail(amount: Optional[float] = None, contract_type: Optional[str] = None) -> dict:
    flow_type = match_flow_type(amount, contract_type)
    thresholds = _load_thresholds()
    labels = {"simple": "简易流程", "standard": "标准流程", "large_amount": "特殊流程（含董事会）"}
    return {
        "flow_type": flow_type,
        "flow_label": labels.get(flow_type, flow_type),
        "amount": amount,
        "contract_type": contract_type,
        "thresholds": {
            "simple_max": thresholds.get("simple_max", 100000),
            "standard_max": thresholds.get("standard_max", 1000000),
            "board_threshold": thresholds.get("board_threshold", 1000000),
        },
    }
