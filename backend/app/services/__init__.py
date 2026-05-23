"""
合同审批平台 - 领域服务层
"""
from app.services.contract_service import (
    create_contract,
    get_contract,
    list_contracts,
    update_contract,
    delete_contract,
)
from app.services.approval_service import (
    ApprovalSubmitRequest,
    ApprovalStepAction,
    ApprovalStepResponse,
    submit_approval,
    approve_step,
    reject_step,
    return_to_draft,
    get_pending_approvals,
    get_approval_history,
    get_next_node,
    get_flow_nodes,
)
from app.services.seal_service import (
    create_seal_request,
    approve_seal,
    get_seal_records,
)
from app.services.archive_service import (
    archive_contract,
    get_archive_records,
)
from app.services.audit_service import (
    log_action,
    get_audit_logs,
)
from app.services.ai_review_service import (
    start_review,
    get_review_status,
    get_review_result,
    retry_review,
)
from app.services.ai_review import (
    ExtractedText,
    extract_text,
    Clause,
    parse_clauses,
    ReviewContext,
    ReviewResult,
    ClauseReview,
    review_contract,
    RiskScore,
    calculate_risk_score,
    generate_report,
)

__all__ = [
    "create_contract",
    "get_contract",
    "list_contracts",
    "update_contract",
    "delete_contract",
    "ApprovalSubmitRequest",
    "ApprovalStepAction",
    "ApprovalStepResponse",
    "submit_approval",
    "approve_step",
    "reject_step",
    "return_to_draft",
    "get_pending_approvals",
    "get_approval_history",
    "get_next_node",
    "get_flow_nodes",
    "create_seal_request",
    "approve_seal",
    "get_seal_records",
    "archive_contract",
    "get_archive_records",
    "log_action",
    "get_audit_logs",
    "start_review",
    "get_review_status",
    "get_review_result",
    "retry_review",
    "ExtractedText",
    "extract_text",
    "Clause",
    "parse_clauses",
    "ReviewContext",
    "ReviewResult",
    "ClauseReview",
    "review_contract",
    "RiskScore",
    "calculate_risk_score",
    "generate_report",
]
