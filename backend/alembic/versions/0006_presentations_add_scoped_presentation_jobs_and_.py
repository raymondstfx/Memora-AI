"""add scoped presentation jobs and artifacts

Revision ID: 0006_presentations
Revises: 0005_memories
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_presentations"
down_revision = "0005_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presentations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_key", sa.Uuid(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("outline_json", sa.JSON(), nullable=False),
        sa.Column("sources_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=60), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_key"),
    )
    op.create_index(
        op.f("ix_presentations_user_id"), "presentations", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_presentations_user_id"), table_name="presentations")
    op.drop_table("presentations")
