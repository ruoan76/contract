"""ai_review_issues 表

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_review_issues",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.String(length=50), nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("clause", sa.String(length=200), nullable=True),
        sa.Column("clause_id", sa.String(length=50), nullable=True),
        sa.Column("clause_ref", sa.String(length=200), nullable=True),
        sa.Column("dimension", sa.String(length=50), nullable=True),
        sa.Column("label_id", sa.String(length=10), nullable=True),
        sa.Column("label_name", sa.String(length=100), nullable=True),
        sa.Column("gate_id", sa.String(length=50), nullable=True),
        sa.Column("cuad_code", sa.String(length=20), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("legal_basis", sa.Text(), nullable=True),
        sa.Column("revision_method", sa.String(length=30), nullable=True),
        sa.Column("exposure_summary", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("needs_research", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.String(length=50), nullable=True),
        sa.Column("human_status", sa.String(length=20), nullable=True),
        sa.Column("human_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_issue_review", "ai_review_issues", ["review_id"])
    op.create_index("idx_ai_issue_contract", "ai_review_issues", ["contract_id"])


def downgrade() -> None:
    op.drop_index("idx_ai_issue_contract", table_name="ai_review_issues")
    op.drop_index("idx_ai_issue_review", table_name="ai_review_issues")
    op.drop_table("ai_review_issues")
