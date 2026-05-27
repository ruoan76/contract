"""contract_templates 补列 legal_snapshot / auto_review_on_publish

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contract_templates",
        sa.Column("legal_snapshot", sa.Text(), nullable=True, comment="法律条款快照 JSON"),
    )
    op.add_column(
        "contract_templates",
        sa.Column(
            "auto_review_on_publish",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="发布时是否自动AI审查",
        ),
    )


def downgrade() -> None:
    op.drop_column("contract_templates", "auto_review_on_publish")
    op.drop_column("contract_templates", "legal_snapshot")
