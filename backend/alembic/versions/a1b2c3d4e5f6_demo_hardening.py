"""demo_hardening: counterparties, review, notifications, schema updates

Revision ID: a1b2c3d4e5f6
Revises: e9380d077795
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e9380d077795"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "counterparties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, comment="单位名称"),
        sa.Column("credit_code", sa.String(length=50), nullable=True, comment="统一社会信用代码"),
        sa.Column("legal_person", sa.String(length=50), nullable=True),
        sa.Column("contact_name", sa.String(length=50), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("industry", sa.String(length=50), nullable=True),
        sa.Column("credit_rating", sa.String(length=10), nullable=True),
        sa.Column("is_blacklist", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("blacklist_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credit_code"),
    )
    op.create_index("idx_cp_name", "counterparties", ["name"], unique=False)
    op.create_index("idx_cp_credit_code", "counterparties", ["credit_code"], unique=False)
    op.create_index("idx_cp_blacklist", "counterparties", ["is_blacklist"], unique=False)

    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("counterparty_id", sa.Integer(), nullable=True, comment="相对方 ID"))
        batch_op.create_index("idx_counterparty_id", ["counterparty_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_contracts_counterparty_id",
            "counterparties",
            ["counterparty_id"],
            ["id"],
        )

    with op.batch_alter_table("ai_reviews", schema=None) as batch_op:
        batch_op.add_column(sa.Column("celery_task_id", sa.String(length=100), nullable=True))

    op.create_table(
        "review_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("flow_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_review_session_contract", "review_sessions", ["contract_id"], unique=False)

    op.create_table(
        "review_opinions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_name", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["review_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_review_opinion_contract", "review_opinions", ["contract_id"], unique=False)
    op.create_index("idx_review_opinion_role", "review_opinions", ["role"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="接收人 ID"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notification_user", "notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_notification_user", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_review_opinion_role", table_name="review_opinions")
    op.drop_index("idx_review_opinion_contract", table_name="review_opinions")
    op.drop_table("review_opinions")
    op.drop_index("idx_review_session_contract", table_name="review_sessions")
    op.drop_table("review_sessions")

    with op.batch_alter_table("ai_reviews", schema=None) as batch_op:
        batch_op.drop_column("celery_task_id")

    with op.batch_alter_table("contracts", schema=None) as batch_op:
        batch_op.drop_constraint("fk_contracts_counterparty_id", type_="foreignkey")
        batch_op.drop_index("idx_counterparty_id")
        batch_op.drop_column("counterparty_id")

    op.drop_index("idx_cp_blacklist", table_name="counterparties")
    op.drop_index("idx_cp_credit_code", table_name="counterparties")
    op.drop_index("idx_cp_name", table_name="counterparties")
    op.drop_table("counterparties")
