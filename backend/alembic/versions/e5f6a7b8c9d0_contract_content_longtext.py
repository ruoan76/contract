"""contracts.content 扩为 LONGTEXT，支持 OCR 长文本

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MySQL TEXT 仅 64KB（按字节计），OCR 中文正文易超限
    op.alter_column(
        "contracts",
        "content",
        existing_type=sa.Text(),
        type_=mysql.LONGTEXT(),
        existing_nullable=True,
    )
    op.alter_column(
        "contract_versions",
        "content",
        existing_type=sa.Text(),
        type_=mysql.LONGTEXT(),
        existing_nullable=True,
    )
    op.alter_column(
        "contract_versions",
        "change_description",
        existing_type=sa.Text(),
        type_=mysql.LONGTEXT(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "contract_versions",
        "change_description",
        existing_type=mysql.LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "contract_versions",
        "content",
        existing_type=mysql.LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "contracts",
        "content",
        existing_type=mysql.LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=True,
    )
