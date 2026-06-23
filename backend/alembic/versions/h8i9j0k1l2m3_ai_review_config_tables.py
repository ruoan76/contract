"""AI 审查可配置规则表

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_config_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=True),
        sa.Column("published_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_table(
        "ai_review_checklist_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("legacy_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("item", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("applicable_contracts", sa.String(500), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("gate_id", sa.String(50), nullable=True),
        sa.Column("gate_priority", sa.Integer(), nullable=True),
        sa.Column("auto_detectable", sa.Boolean(), nullable=True),
        sa.Column("detect_config", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version_tag", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_id"),
    )
    op.create_table(
        "ai_risk_labels",
        sa.Column("label_id", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("gate_id", sa.String(50), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version_tag", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("label_id"),
    )
    op.create_table(
        "ai_revision_routing_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("issue_type", sa.String(200), nullable=False),
        sa.Column("default_method", sa.String(30), nullable=True),
        sa.Column("auto_applicable", sa.Boolean(), nullable=True),
        sa.Column("self_check_questions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version_tag", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ai_hard_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("label_id", sa.String(10), nullable=True),
        sa.Column("gate_id", sa.String(50), nullable=True),
        sa.Column("dimension", sa.String(50), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("legal_basis", sa.String(500), nullable=True),
        sa.Column("revision_method", sa.String(30), nullable=True),
        sa.Column("clause", sa.String(200), nullable=True),
        sa.Column("version_tag", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_id"),
    )
    op.create_table(
        "ai_legal_snippets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("snippet_id", sa.String(50), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("version_tag", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snippet_id"),
    )
    op.create_table(
        "ai_rule_feedback_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_key", sa.String(80), nullable=False),
        sa.Column("source", sa.String(20), nullable=True),
        sa.Column("fp_count", sa.Integer(), nullable=True),
        sa.Column("confirm_count", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_feedback_rule_key", "ai_rule_feedback_stats", ["rule_key"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_ai_feedback_rule_key", table_name="ai_rule_feedback_stats")
    op.drop_table("ai_rule_feedback_stats")
    op.drop_table("ai_legal_snippets")
    op.drop_table("ai_hard_rules")
    op.drop_table("ai_revision_routing_rules")
    op.drop_table("ai_risk_labels")
    op.drop_table("ai_review_checklist_items")
    op.drop_table("ai_config_versions")
