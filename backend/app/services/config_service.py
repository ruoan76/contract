"""
配置服务 — 阈值、审批人、流程节点（JSON 持久化，保存时同步 flow_config.json）
"""
import json
import os
from typing import Any, Optional

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_THRESHOLDS_FILE = os.path.join(_CONFIG_DIR, "thresholds.json")
_APPROVERS_FILE = os.path.join(_CONFIG_DIR, "approvers.json")
FLOW_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "flow_config.json")
_FLOW_CONFIG_FILE = FLOW_CONFIG_FILE

_DEFAULT = {
    "simple_max": 100000,
    "standard_max": 1000000,
    "board_threshold": 1000000,
}

# 各流程步骤序号 → 审批节点 ID（与 approval_service.NODE_DISPLAY_NAMES 一致）
_FLOW_NODE_ORDER: dict[str, list[str]] = {
    "simple": ["dept_approval"],
    "standard": ["dept_approval", "legal_review", "finance_review"],
    "large_amount": [
        "dept_approval",
        "legal_review",
        "finance_review",
        "executive_approval",
        "board_approval",
    ],
}

_NODE_DISPLAY_NAMES: dict[str, str] = {
    "dept_approval": "部门审批",
    "legal_review": "法务审查",
    "finance_review": "财务审查",
    "executive_approval": "高管审批",
    "board_approval": "董事会审批",
}

_ROLE_APPROVER_LABELS: dict[str, str] = {
    "approver": "部门主管",
    "legal": "法务专员",
    "finance": "财务总监",
    "executive": "总经理",
}

_FLOW_LABELS: dict[str, str] = {
    "simple": "简易审批",
    "standard": "标准审批",
    "large_amount": "大额审批",
}

_DEFAULT_APPROVERS = [
    {"id": 1, "flow_type": "simple", "step": 1, "role": "approver", "user_id": 2, "user_name": "部门主管"},
    {"id": 2, "flow_type": "standard", "step": 1, "role": "approver", "user_id": 2, "user_name": "部门主管"},
    {"id": 3, "flow_type": "standard", "step": 2, "role": "legal", "user_id": 3, "user_name": "法务专员"},
    {"id": 4, "flow_type": "standard", "step": 3, "role": "finance", "user_id": 4, "user_name": "赵财务"},
    {"id": 5, "flow_type": "large_amount", "step": 1, "role": "approver", "user_id": 2, "user_name": "部门主管"},
    {"id": 6, "flow_type": "large_amount", "step": 2, "role": "legal", "user_id": 3, "user_name": "法务专员"},
    {"id": 7, "flow_type": "large_amount", "step": 3, "role": "finance", "user_id": 4, "user_name": "赵财务"},
    {"id": 8, "flow_type": "large_amount", "step": 4, "role": "executive", "user_id": 5, "user_name": "高管"},
    {"id": 9, "flow_type": "large_amount", "step": 5, "role": "executive", "user_id": 5, "user_name": "董事长"},
]


def _ensure_dir() -> None:
    os.makedirs(_CONFIG_DIR, exist_ok=True)


def _sort_approvers(items: list[dict]) -> list[dict]:
    order = {"simple": 0, "standard": 1, "large_amount": 2}
    return sorted(
        items,
        key=lambda x: (order.get(x.get("flow_type", ""), 99), int(x.get("step", 0))),
    )


def _dedupe_approvers(items: list[dict]) -> list[dict]:
    """按 (flow_type, step) 保留 id 较大的一条，避免历史脏数据。"""
    seen: dict[tuple[str, int], dict] = {}
    for item in items:
        key = (str(item.get("flow_type", "")), int(item.get("step", 0)))
        prev = seen.get(key)
        if prev is None or int(item.get("id", 0)) >= int(prev.get("id", 0)):
            seen[key] = item
    return _sort_approvers(list(seen.values()))


def _load_flow_config_raw() -> dict[str, Any]:
    if os.path.isfile(_FLOW_CONFIG_FILE):
        try:
            with open(_FLOW_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"thresholds": dict(_DEFAULT)}


def _save_flow_config_raw(data: dict[str, Any]) -> None:
    with open(_FLOW_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _invalidate_runtime_caches()


def _invalidate_runtime_caches() -> None:
    from app.services.flow_match_service import clear_thresholds_cache

    clear_thresholds_cache()
    try:
        from app.services.approval_service import clear_flow_config_cache

        clear_flow_config_cache()
    except ImportError:
        pass


def sync_approvers_to_flow_config() -> None:
    """将 approvers.json 同步为 flow_config 各流程的 nodes（运行时审批真源）。"""
    items = _dedupe_approvers(get_approvers())
    config = _load_flow_config_raw()

    for flow_type, node_ids in _FLOW_NODE_ORDER.items():
        rows = [a for a in items if a.get("flow_type") == flow_type]
        rows = sorted(rows, key=lambda x: int(x.get("step", 0)))
        if not rows:
            continue
        nodes: list[dict[str, Any]] = []
        for i, row in enumerate(rows):
            node_id = node_ids[i] if i < len(node_ids) else f"custom_step_{i + 1}"
            role_code = str(row.get("role", "approver"))
            node: dict[str, Any] = {
                "node_id": node_id,
                "node_name": _NODE_DISPLAY_NAMES.get(node_id, f"步骤{i + 1}"),
                "approver_role": _ROLE_APPROVER_LABELS.get(role_code, role_code),
            }
            if row.get("user_id") is not None:
                node["user_id"] = int(row["user_id"])
            nodes.append(node)
        config[flow_type] = {"name": _FLOW_LABELS.get(flow_type, flow_type), "nodes": nodes}

    _save_flow_config_raw(config)


def get_flow_nodes_config(flow_type: Optional[str] = None) -> dict[str, Any] | list[dict]:
    """返回当前 flow_config 中的流程节点（供配置页只读展示）。"""
    config = _load_flow_config_raw()
    if flow_type:
        flow_def = config.get(flow_type)
        if not flow_def:
            return []
        return flow_def.get("nodes", [])
    result: dict[str, Any] = {}
    for ft in _FLOW_NODE_ORDER:
        flow_def = config.get(ft)
        if flow_def and flow_def.get("nodes"):
            result[ft] = flow_def["nodes"]
    return result


def get_thresholds() -> dict:
    if os.path.isfile(_THRESHOLDS_FILE):
        try:
            with open(_THRESHOLDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {
                        "simple_max": data.get("simple_max", _DEFAULT["simple_max"]),
                        "standard_max": data.get("standard_max", _DEFAULT["standard_max"]),
                        "board_threshold": data.get("board_threshold", _DEFAULT["board_threshold"]),
                    }
        except (json.JSONDecodeError, OSError):
            pass
    cfg = _load_flow_config_raw()
    th = cfg.get("thresholds", {})
    return {
        "simple_max": th.get("simple_max", _DEFAULT["simple_max"]),
        "standard_max": th.get("standard_max", _DEFAULT["standard_max"]),
        "board_threshold": th.get("board_threshold", th.get("standard_max", _DEFAULT["board_threshold"])),
    }


def _sync_thresholds_to_flow_config(thresholds: dict[str, Any]) -> None:
    config = _load_flow_config_raw()
    config["thresholds"] = {
        "simple_max": thresholds["simple_max"],
        "standard_max": thresholds["standard_max"],
        "board_threshold": thresholds.get("board_threshold", thresholds["standard_max"]),
    }
    _save_flow_config_raw(config)


def update_thresholds(data: dict[str, Any]) -> dict:
    _ensure_dir()
    current = get_thresholds()
    current.update({k: v for k, v in data.items() if k in _DEFAULT})
    with open(_THRESHOLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    _sync_thresholds_to_flow_config(current)
    return current


def get_approvers() -> list[dict]:
    if os.path.isfile(_APPROVERS_FILE):
        try:
            with open(_APPROVERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return _sort_approvers(_dedupe_approvers(data))
        except (json.JSONDecodeError, OSError):
            pass
    return list(_DEFAULT_APPROVERS)


def _save_approvers(items: list[dict]) -> list[dict]:
    _ensure_dir()
    items = _dedupe_approvers(items)
    with open(_APPROVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    sync_approvers_to_flow_config()
    return items


def add_approver(data: dict) -> dict:
    items = get_approvers()
    flow_type = data.get("flow_type", "standard")
    step = int(data.get("step", 1))
    payload = {
        "flow_type": flow_type,
        "step": step,
        "role": data.get("role", "approver"),
        "user_id": data.get("user_id"),
        "user_name": data.get("user_name", ""),
    }
    existing_idx = next(
        (i for i, x in enumerate(items) if x.get("flow_type") == flow_type and int(x.get("step", 0)) == step),
        None,
    )
    if existing_idx is not None:
        item = items[existing_idx]
        item.update(payload)
        items[existing_idx] = item
        saved = item
    else:
        next_id = max((i.get("id", 0) for i in items), default=0) + 1
        saved = {"id": next_id, **payload}
        items.append(saved)
    _save_approvers(items)
    return saved


def update_approver(approver_id: int, data: dict) -> dict:
    items = get_approvers()
    for i, item in enumerate(items):
        if item.get("id") == approver_id:
            new_flow = data.get("flow_type", item.get("flow_type"))
            new_step = int(data.get("step", item.get("step", 1)))
            # 若改 flow_type/step 与另一条冲突，先删冲突条
            for j, other in enumerate(items):
                if j != i and other.get("flow_type") == new_flow and int(other.get("step", 0)) == new_step:
                    items.pop(j)
                    break
            item.update(
                {k: v for k, v in data.items() if k in ("flow_type", "step", "role", "user_id", "user_name")}
            )
            if "step" in data:
                item["step"] = new_step
            items[i] = item
            _save_approvers(items)
            return item
    raise ValueError(f"approver {approver_id} not found")


def delete_approver(approver_id: int) -> None:
    items = get_approvers()
    new_items = [x for x in items if x.get("id") != approver_id]
    if len(new_items) == len(items):
        raise ValueError(f"approver {approver_id} not found")
    _save_approvers(new_items)


def init_default_config_files() -> None:
    """开发/测试启动时确保 JSON 与 flow_config 一致（可选调用）。"""
    if not os.path.isfile(_APPROVERS_FILE):
        _save_approvers(list(_DEFAULT_APPROVERS))
    else:
        sync_approvers_to_flow_config()
