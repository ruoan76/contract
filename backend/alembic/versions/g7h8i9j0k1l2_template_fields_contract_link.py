"""template code/variables and contract template link

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "g7h8i9j0k1l2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contract_templates", sa.Column("code", sa.String(50), nullable=True))
    op.add_column("contract_templates", sa.Column("variables", sa.Text(), nullable=True))
    op.add_column("contract_templates", sa.Column("archived_reason", sa.String(500), nullable=True))

    op.add_column("contracts", sa.Column("template_id", sa.Integer(), nullable=True))
    op.add_column("contracts", sa.Column("template_version", sa.Integer(), nullable=True))
    op.add_column("contracts", sa.Column("template_values", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("contracts", "template_values")
    op.drop_column("contracts", "template_version")
    op.drop_column("contracts", "template_id")
    op.drop_column("contract_templates", "archived_reason")
    op.drop_column("contract_templates", "variables")
    op.drop_column("contract_templates", "code")
