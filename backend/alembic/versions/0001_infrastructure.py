"""Initialize pgvector and infrastructure metadata, without feature tables."""

import sqlalchemy as sa

from alembic import op

revision = "0001_infrastructure"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    table = op.create_table(
        "system_metadata",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.bulk_insert(table, [{"key": "phase", "value": "0"}])


def downgrade() -> None:
    op.drop_table("system_metadata")
    # Retain the shared extension: never cascade-delete unrelated vector data.
