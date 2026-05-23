"""
合同状态机 — 统一状态迁移
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessError
from app.models.contract import Contract

# 主状态合法迁移
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending"},
    "pending": {"approved", "draft", "rejected"},
    "approved": {"sealed", "archived", "executing", "draft"},
    "sealed": {"signed", "archived", "executing"},
    "signed": {"archived", "executing"},
    "executing": {"archived", "terminated"},
    "rejected": {"draft"},
    "returned": {"draft"},
}

# 审批子状态映射（节点 → approval_status）
NODE_APPROVAL_STATUS = {
    "dept_approval": "dept_approval",
    "legal_review": "legal_review",
    "finance_review": "finance_review",
    "executive_approval": "executive_approval",
    "board_approval": "board_approval",
    "done": "done",
}

# AI 审查已完成、可进入法务评审的状态
AI_READY_STATUSES = frozenset({"ai_done", "reviewed", "confirmed"})

# 评审角色 → 子状态（与 contract-status-dictionary §2 对齐）
REVIEW_ROLE_APPROVAL_STATUS = {
    "legal": "legal_review",
    "finance": "finance_review",
    "executive": "executive_approval",
}

# 主路径关键迁移（供单测断言）
PRIMARY_PATH_TRANSITIONS: list[tuple[str, Optional[str], str, Optional[str]]] = [
    ("draft", None, "pending", "dept_approval"),
    ("pending", "dept_approval", "pending", "legal_review"),
    ("pending", "legal_review", "approved", "seal_pending"),
    ("approved", "seal_pending", "sealed", None),
    ("pending", None, "draft", "returned"),
    ("pending", None, "rejected", "rejected"),
]


async def transition_contract(
    db: AsyncSession,
    contract: Contract,
    new_status: str,
    approval_status: Optional[str] = None,
) -> Contract:
    """执行合同主状态迁移，非法迁移抛出 BusinessError。"""
    current = contract.status
    allowed = VALID_TRANSITIONS.get(current, set())
    if new_status not in allowed and new_status != current:
        raise BusinessError(
            f"合同状态不允许从 {current} 迁移到 {new_status}"
        )
    contract.status = new_status
    if approval_status is not None:
        contract.approval_status = approval_status
    await db.flush()
    return contract


def approval_status_for_node(node_id: str) -> str:
    return NODE_APPROVAL_STATUS.get(node_id, node_id)


def initial_approval_status(ai_review_status: Optional[str]) -> str:
    """提交审批时的初始 approval_status。"""
    if ai_review_status == "reviewing":
        return "ai_screening"
    return "dept_approval"


def approval_status_after_review_role(
    role: str,
    required_roles: list[str],
    approved_roles: set[str],
) -> str:
    """某评审角色通过后，下一子状态。"""
    remaining = [r for r in required_roles if r not in approved_roles]
    if not remaining:
        return "seal_pending"
    return REVIEW_ROLE_APPROVAL_STATUS.get(remaining[0], "seal_pending")
