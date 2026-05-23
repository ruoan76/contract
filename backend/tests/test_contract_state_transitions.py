"""
合同状态机迁移单测 — 对齐 contract-status-dictionary.md
"""
import pytest

from app.services.contract_state import (
    AI_READY_STATUSES,
    NODE_APPROVAL_STATUS,
    PRIMARY_PATH_TRANSITIONS,
    REVIEW_ROLE_APPROVAL_STATUS,
    VALID_TRANSITIONS,
    approval_status_after_review_role,
    approval_status_for_node,
    initial_approval_status,
)


@pytest.mark.unit
class TestApprovalStatusHelpers:
    def test_initial_status_without_ai(self):
        assert initial_approval_status(None) == "dept_approval"

    def test_initial_status_ai_reviewing(self):
        assert initial_approval_status("reviewing") == "ai_screening"

    def test_initial_status_ai_done(self):
        assert initial_approval_status("ai_done") == "dept_approval"

    def test_approval_status_for_node(self):
        assert approval_status_for_node("legal_review") == "legal_review"
        assert approval_status_for_node("board_approval") == "board_approval"

    def test_review_role_progression_standard(self):
        required = ["legal", "finance", "executive"]
        assert approval_status_after_review_role("legal", required, {"legal"}) == "finance_review"
        assert approval_status_after_review_role(
            "finance", required, {"legal", "finance"}
        ) == "executive_approval"
        assert approval_status_after_review_role(
            "executive", required, {"legal", "finance", "executive"}
        ) == "seal_pending"

    def test_review_role_progression_simple(self):
        required = ["legal"]
        assert approval_status_after_review_role("legal", required, {"legal"}) == "seal_pending"


@pytest.mark.unit
class TestPrimaryPathDictionary:
    """§1.1 主路径关键迁移点。"""

    def test_draft_to_pending(self):
        assert "pending" in VALID_TRANSITIONS["draft"]

    def test_pending_to_approved(self):
        assert "approved" in VALID_TRANSITIONS["pending"]

    def test_approved_to_sealed(self):
        assert "sealed" in VALID_TRANSITIONS["approved"]

    def test_node_status_map_covers_demo_nodes(self):
        for node in (
            "dept_approval",
            "legal_review",
            "finance_review",
            "executive_approval",
            "board_approval",
        ):
            assert node in NODE_APPROVAL_STATUS

    def test_review_roles_map(self):
        assert REVIEW_ROLE_APPROVAL_STATUS["legal"] == "legal_review"
        assert REVIEW_ROLE_APPROVAL_STATUS["finance"] == "finance_review"

    def test_ai_ready_statuses(self):
        assert "ai_done" in AI_READY_STATUSES
        assert "reviewing" not in AI_READY_STATUSES

    def test_primary_path_transitions_defined(self):
        assert len(PRIMARY_PATH_TRANSITIONS) >= 5
